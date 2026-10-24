"""Generate the six-value OG trait progression delta without writing a game pack.

The input is the original PFH3 data.pack, not CE's compressed PFHs archive.
Only a JSON recipe is written. Header/index/table structure remain byte-exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

SOURCE_SHA256 = "6596d4f5e51f3a95c79a90df782d9ef53c850e30c46bbbf9b0d2444f3668670a"
SOURCE_LENGTH = 2565173720
TABLE = r"db\trait_level_effects_tables\trait_level_effects"
LEVELS = r"db\character_trait_levels_tables\character_trait_levels"
EFFECTS = r"db\effects_tables\effects"
GUID_MARKER = bytes.fromhex("fd fe fc ff")
VERSION_MARKER = bytes.fromhex("fc fd fe ff")
LINES = (
    ("bloodthirsty", "mod_unit_morale_enemy", -1.0),
    ("brave", "mod_unit_morale_local", 1.0),
    ("coward", "mod_unit_morale_local", -1.0),
)


class Cursor:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.pos + count > len(self.data):
            raise ValueError("Truncated database row")
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def string16(self) -> str:
        count = struct.unpack("<H", self.take(2))[0]
        return self.take(count * 2).decode("utf-16le")

    def optional_string16(self) -> str | None:
        present = self.take(1)[0]
        if present not in (0, 1):
            raise ValueError("Invalid optional string flag")
        return self.string16() if present else None


def pack_index(path: Path) -> dict[str, tuple[int, int]]:
    with path.open("rb") as source:
        header = source.read(32)
        if len(header) != 32:
            raise ValueError("Truncated pack header")
        magic, flags, dependencies, dependency_size, count, index_size = struct.unpack_from("<4s5I", header)
        if magic != b"PFH3" or flags & 0x40 or dependencies or dependency_size:
            raise ValueError("Expected original OG PFH3 without timestamp entries/dependencies")
        index = source.read(index_size)
    if len(index) != index_size:
        raise ValueError("Truncated pack index")
    entries = {}
    cursor = 0
    offset = 32 + index_size
    for _ in range(count):
        if cursor + 4 > len(index):
            raise ValueError("Truncated pack index entry")
        size = struct.unpack_from("<I", index, cursor)[0]
        cursor += 4
        end = index.find(b"\0", cursor)
        if end < 0:
            raise ValueError("Unterminated pack path")
        name = index[cursor:end].decode("ascii")
        if name in entries:
            raise ValueError("Duplicate pack path: " + name)
        entries[name] = (offset, size)
        offset += size
        cursor = end + 1
    if cursor != len(index) or offset != path.stat().st_size:
        raise ValueError("Pack index/body length mismatch")
    return entries


def read_entry(path: Path, entries: dict, name: str) -> bytes:
    offset, size = entries[name]
    with path.open("rb") as source:
        source.seek(offset)
        result = source.read(size)
    if len(result) != size:
        raise ValueError("Truncated table: " + name)
    return result


def table_rows(data: bytes, kind: str) -> tuple[int, list[dict]]:
    cursor = Cursor(data)
    if cursor.take(4) != GUID_MARKER:
        raise ValueError("Expected original GUID-bearing database table")
    cursor.string16()
    if data[cursor.pos:cursor.pos + 4] == VERSION_MARKER:
        raise ValueError("Expected original versionless schema-0 table")
    if cursor.take(1) != b"\x01":
        raise ValueError("Unexpected database enabled flag")
    count = cursor.u32()
    rows = []
    for _ in range(count):
        key = cursor.string16()
        if kind == "trait-effects":
            effect = cursor.string16()
            value_offset = cursor.pos
            value = struct.unpack("<f", cursor.take(4))[0]
            row = dict(key=key, effect=effect, value=value, value_offset=value_offset)
        elif kind == "levels":
            row = dict(key=key, level=cursor.i32(), trait=cursor.string16(), threshold=cursor.i32())
        elif kind == "effects":
            row = dict(key=key, icon=cursor.optional_string16(), priority=cursor.i32())
        else:
            raise ValueError("Unknown table kind")
        rows.append(row)
    if cursor.pos != len(data):
        raise ValueError("Table rows do not consume exact payload")
    return count, rows


def only(rows: list[dict], **values) -> dict:
    matches = [row for row in rows if all(row.get(key) == value for key, value in values.items())]
    if len(matches) != 1:
        raise ValueError("Expected one row: " + repr(values))
    return matches[0]


def streamed_hashes(path: Path, writes: list[dict]) -> tuple[str, str]:
    original_hash = hashlib.sha256()
    output_hash = hashlib.sha256()
    position = 0
    with path.open("rb") as source:
        while block := source.read(8 * 1024 * 1024):
            original_hash.update(block)
            changed = bytearray(block)
            for write in writes:
                start = int(write["offset"], 0)
                before = bytes.fromhex(write["expect"])
                after = bytes.fromhex(write["bytes"])
                lo, hi = max(position, start), min(position + len(block), start + len(before))
                if lo >= hi:
                    continue
                relative, delta, count = lo - position, lo - start, hi - lo
                if block[relative:relative + count] != before[delta:delta + count]:
                    raise ValueError("Source bytes differ at trait delta")
                changed[relative:relative + count] = after[delta:delta + count]
            output_hash.update(changed)
            position += len(block)
    return original_hash.hexdigest(), output_hash.hexdigest()


def generate(pack: Path) -> dict:
    if pack.stat().st_size != SOURCE_LENGTH:
        raise ValueError("Unsupported original OG data.pack length")
    entries = pack_index(pack)
    table_offset, table_size = entries[TABLE]
    original = read_entry(pack, entries, TABLE)
    count, rows = table_rows(original, "trait-effects")
    _, levels = table_rows(read_entry(pack, entries, LEVELS), "levels")
    _, effects = table_rows(read_entry(pack, entries, EFFECTS), "effects")
    if count != 335 or table_size != 40327:
        raise ValueError("Unsupported original trait table shape")
    writes = []
    modified = bytearray(original)
    for line, effect, sign in LINES:
        only(effects, key=effect)
        for level in (1, 2, 3):
            key = f"S2_trait_general_{line}_{level}"
            only(levels, key=key, level=level, trait=f"S2_trait_general_{line}")
            row = only(rows, key=key, effect=effect)
            if row["value"] != sign:
                raise ValueError("Unsupported existing morale value: " + key)
            if level == 1:
                continue
            before, after = struct.pack("<f", sign), struct.pack("<f", sign * level)
            position = row["value_offset"]
            modified[position:position + 4] = after
            writes.append({
                "offset": hex(table_offset + position),
                "expect": before.hex(" "),
                "bytes": after.hex(" "),
                "note": f"{key} / {effect}: {sign:g} -> {sign * level:g}",
            })
    security = only(rows, key="S2_trait_general_coward_3", effect="personal_security")
    if security["value"] != -2.0:
        raise ValueError("Unexpected Cowardly personal-security penalty")
    if len(writes) != 6:
        raise ValueError("Expected exactly six changed float fields")
    _, updated_rows = table_rows(bytes(modified), "trait-effects")
    if only(updated_rows, key="S2_trait_general_coward_3", effect="personal_security")["value"] != -2.0:
        raise ValueError("Personal security changed unexpectedly")
    allowed = {int(w["offset"], 0) - table_offset + i for w in writes for i in range(4)}
    if any(a != b and i not in allowed for i, (a, b) in enumerate(zip(original, modified))):
        raise ValueError("Unexpected table bytes changed")
    source_hash, output_hash = streamed_hashes(pack, writes)
    if source_hash != SOURCE_SHA256:
        raise ValueError("Unsupported original OG data.pack SHA-256: " + source_hash)
    return {
        "id": "trait-progression",
        "title": "Progressive general traits: Bloodthirsty, Brave and Cowardly",
        "description": "Match the CE progression correction: change only the six morale floats at levels 2/3 of the three base-campaign trait lines. Keep level 1, Cowardly personal security, thresholds, FOTS traits, every other table, PFH3 header and index unchanged.",
        "enabled": True,
        "source": "data/data.pack",
        "destination": "data/data.pack",
        "sourceSha256": source_hash,
        "length": SOURCE_LENGTH,
        "sha256": output_hash,
        "writes": writes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--game-dir", "--game", type=Path)
    group.add_argument("--pack", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "patches/data/trait-progression.json")
    parser.add_argument("--check", action="store_true", help="Verify the existing recipe without writing it")
    args = parser.parse_args()
    pack = (args.pack or args.game_dir / "data/data.pack").resolve()
    output = args.output.resolve()
    if output == pack or output.suffix.lower() != ".json":
        raise ValueError("Output must be a separate JSON recipe")
    recipe = generate(pack)
    if args.check:
        if json.loads(output.read_text(encoding="utf-8")) != recipe:
            raise ValueError("Existing recipe does not match the supported original pack")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "verified" if args.check else "generated", "recipe": str(output), "changes": len(recipe["writes"]), "sourceSha256": recipe["sourceSha256"], "sha256": recipe["sha256"], "pack_written": False}))


if __name__ == "__main__":
    main()
