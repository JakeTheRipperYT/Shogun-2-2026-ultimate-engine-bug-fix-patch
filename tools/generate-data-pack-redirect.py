"""Generate a disabled, data.pack-only OG CreateFileW redirect recipe.

Never changes a game file. Requires exact vanilla engine input, checks all import
call operands/relocations and rejects overlaps with other enabled recipes.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct

SHA256 = '022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5'
STUB, WRAPPER, TABLE, STRINGS, IAT = 0x115A0C40, 0x115A0C4A, 0x115A0D78, 0x11793AE8, 0x115A1144
WRITE_ACCESS_MASK = 0x530D0156  # write/all, maximum-allowed/security access, delete/DAC/owner and file writes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--engine', type=Path, required=True)
    ap.add_argument('--enable', action='store_true', help='Deliberately enable the generated recipe; otherwise leave it disabled')
    args = ap.parse_args()
    raw = args.engine.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError('Unsupported vanilla OG engine SHA-256')
    nt = struct.unpack_from('<I', raw, 0x3C)[0]
    opt = nt + 24
    if struct.unpack_from('<H', raw, nt + 4)[0] != 0x14C:
        raise ValueError('Expected x86 PE')
    base = struct.unpack_from('<I', raw, opt + 28)[0]
    section_table = opt + struct.unpack_from('<H', raw, nt + 20)[0]
    sections = []
    for i in range(struct.unpack_from('<H', raw, nt + 6)[0]):
        at = section_table + i * 40
        vs, rva, size, offset = struct.unpack_from('<IIII', raw, at + 8)
        sections.append((raw[at:at + 8].rstrip(b'\0'), vs, rva, size, offset, at))
    text = next(s for s in sections if s[0] == b'.text')
    rdata = next(s for s in sections if s[0] == b'.rdata')

    def offset(va):
        for _, _, rva, size, at, _ in sections:
            if rva <= va - base < rva + size:
                return at + va - base - rva
        raise ValueError('Unbacked VA: ' + hex(va))

    def va(file_offset):
        for _, _, rva, size, at, _ in sections:
            if at <= file_offset < at + size:
                return base + rva + file_offset - at
        raise ValueError('Unmapped file offset')

    code, labels, fixups = bytearray(), {}, []

    def emit(h):
        code.extend(bytes.fromhex(h))

    def label(name):
        labels[name] = len(code)

    def branch(h, target, size=1):
        emit(h)
        fixups.append((len(code), target, size))
        code.extend(bytes(size))

    emit('56 57 53 e8 00 00 00 00 5f')  # preserve nonvolatile; PIC anchor EDI
    anchor = WRAPPER + 8
    emit('8b 74 24 10 85 f6'); branch('0f84', 'finish', 4)
    emit('83 7c 24 20 03'); branch('0f85', 'finish', 4)  # OPEN_EXISTING
    emit('f7 44 24 14'); code.extend(struct.pack('<I', WRITE_ACCESS_MASK))
    branch('0f85', 'finish', 4)
    emit('89 f1')
    label('length'); emit('83 c1 02 66 83 79 fe 00'); branch('75', 'length')
    emit('89 ca 52 31 db')
    label('entry'); emit('8d 87'); code.extend(struct.pack('<I', TABLE - anchor))
    emit('8d 04 d8 8d 04 98 0f b6 08 50 8b 54 24 04 c1 e1 01 29 ca 39 f2')
    branch('72', 'next'); branch('74', 'boundary_ok')
    emit('0f b7 4a fe 83 f9 5c'); branch('74', 'boundary_ok')
    emit('83 f9 2f'); branch('75', 'next')
    label('boundary_ok'); emit('8b 04 24 0f b6 00 48 50 31 c9')
    label('compare'); emit('0f b7 04 4a 83 f8 2f'); branch('75', 'slash_ok')
    emit('b0 5c'); label('slash_ok'); emit('83 f8 41'); branch('72', 'lowercase')
    emit('83 f8 5a'); branch('77', 'lowercase'); emit('0c 20')
    label('lowercase'); emit('53 8b 5c 24 08 8b 5b 04 01 fb 66 3b 04 4b 5b')
    branch('75', 'next_compare')
    emit('41 3b 4c 24 00'); branch('72', 'compare')
    emit('8b 44 24 04 8b 40 08 01 f8 89 44 24 1c 83 c4 0c')
    branch('e9', 'finish', 4)
    label('next_compare'); emit('58')
    label('next'); emit('58 43 83 fb 01'); branch('0f82', 'entry', 4)
    emit('5a')
    label('finish'); emit('8b 87'); code.extend(struct.pack('<I', IAT - anchor))
    emit('5b 5f 5e ff e0')
    for at, target, size in fixups:
        delta = labels[target] - at - size
        code[at:at + size] = delta.to_bytes(size, 'little', signed=True)
    if len(code) != 210 or WRAPPER + len(code) > 0x115A0D20:
        raise ValueError('Wrapper would overlap naval adapter')

    path = 'UltimatePatch\\data\\data.pack'
    strings = (path + '\0').encode('utf-16le')
    pattern = STRINGS + len('UltimatePatch\\'.encode('utf-16le'))
    table = struct.pack('<III', len('data\\data.pack') + 1, pattern - anchor, STRINGS - anchor)
    loader = bytes.fromhex('e8 00 00 00 00 5b 8d 5b 05 c3')
    writes = []

    def add(address, value, note, by_offset=False):
        at = address if by_offset else offset(address)
        writes.append({('offset' if by_offset else 'va'): hex(address),
                       'expect': raw[at:at + len(value)].hex(' '), 'bytes': value.hex(' '), 'note': note})

    if STRINGS != base + rdata[2] + rdata[1]:
        raise ValueError('Unexpected original .rdata end')
    # Reserve the adjacent zero padding through 3B80 for adapter100 as well.
    # Keep one owner for the shared VirtualSize header write.
    new_rdata_size = max(STRINGS + len(strings), 0x11793B80) - base - rdata[2]
    if new_rdata_size > rdata[3]:
        raise ValueError('String exceeds existing raw padding')
    add(rdata[5] + 8, struct.pack('<I', new_rdata_size), 'Map the shadow path and adjacent reserved adapter100 zero padding within existing raw .rdata', True)
    for address, value, note in [(STUB, loader, 'PIC loader for original mov ebx,[CreateFileW] site'),
                                 (WRAPPER, code, 'Data.pack-only read-only OPEN_EXISTING wrapper, PIC'),
                                 (TABLE, table, 'Exactly one match-table entry; no models/local_en redirects'),
                                 (STRINGS, strings, 'UTF-16 UltimatePatch\\data\\data.pack; pattern reuses its suffix')]:
        if raw[offset(address):offset(address) + len(value)] != bytes(len(value)):
            raise ValueError('Cave/string data is not original zero padding')
        add(address, value, note)

    # Discover precisely the original direct imports, then neutralize each old
    # absolute-operand relocation. Relative calls must never receive a base delta.
    reloc_rva, reloc_size = struct.unpack_from('<II', raw, opt + 96 + 5 * 8)
    reloc_at, reloc_end = offset(base + reloc_rva), offset(base + reloc_rva) + reloc_size
    relocs = {}
    while reloc_at < reloc_end:
        page, block_size = struct.unpack_from('<II', raw, reloc_at)
        if block_size < 8:
            raise ValueError('Malformed relocation block')
        for at in range(reloc_at + 8, reloc_at + block_size, 2):
            value = struct.unpack_from('<H', raw, at)[0]
            if value >> 12 == 3:
                relocs[base + page + (value & 0xFFF)] = (at, value)
        reloc_at += block_size
    counts = []
    text_bytes = raw[text[4]:text[4] + text[3]]
    for opcode, target, expected_count in [(b'\xff\x15', WRAPPER, 15), (b'\x8b\x1d', STUB, 1)]:
        needle, found, pos = opcode + struct.pack('<I', IAT), [], 0
        while True:
            at = text_bytes.find(needle, pos)
            if at < 0:
                break
            found.append(va(text[4] + at)); pos = at + len(needle)
        if len(found) != expected_count:
            raise ValueError('Unexpected CreateFileW import references')
        for site in found:
            add(site, b'\xe8' + struct.pack('<i', target - site - 5) + b'\x90', 'Relative call to data.pack wrapper/EBX loader')
            at, value = relocs[site + 2]
            add(va(at), struct.pack('<H', value & 0xFFF), 'Old IAT operand HIGHLOW relocation -> ABSOLUTE padding')
        counts.append(len(found))

    folder = Path(__file__).resolve().parents[1] / 'patches' / 'engine'
    ranges = [(int(w['offset'], 0) if 'offset' in w else offset(int(w['va'], 0)), len(bytes.fromhex(w['bytes']))) for w in writes]
    mapped_text = text[1]
    for file in folder.glob('*.json'):
        if file.name == '090-data-pack-redirect.json':
            continue
        recipe = json.loads(file.read_text(encoding='utf-8-sig'))
        if not recipe.get('enabled'):
            continue
        for w in recipe['writes']:
            at = int(w['offset'], 0) if 'offset' in w else offset(int(w['va'], 0))
            data = bytes.fromhex(w['bytes'])
            if any(at < begin + size and begin < at + len(data) for begin, size in ranges):
                raise ValueError('Overlap with enabled recipe ' + file.name)
            if at == text[5] + 8:
                mapped_text = struct.unpack('<I', data)[0]
    if WRAPPER + len(code) > base + text[2] + mapped_text or TABLE + len(table) > base + text[2] + mapped_text:
        raise ValueError('Current enabled 000 recipe does not map wrapper/table')
    recipe = {
        'id': 'data-pack-redirect',
        'title': ('Read the managed data.pack shadow only' if args.enable else 'DISABLED candidate: read the managed data.pack shadow only'),
        'description': 'Redirect only read-only OPEN_EXISTING CreateFileW requests whose case-insensitive path suffix is data\\data.pack, with a directory boundary, to UltimatePatch\\data\\data.pack. All models.pack, local_en.pack and other paths pass through. Reject write/delete/ownership/DAC, MAXIMUM_ALLOWED and ACCESS_SYSTEM_SECURITY access. Preserve Win32 stack arguments and nonvolatile registers; tail-call the original IAT function. PIC wrapper C4A..D1B, loader C40..C49, one table entry D78..D83; disjoint from naval D20..D76 and rank DA0..DF9. Store 58 path-string bytes in original raw .rdata padding; map adjacent reserved padding through 0x11793B7F for adapter100. Neutralize all16 old absolute IAT operand relocations. Generated from exact supported original engine; no game files modified.',
        'enabled': args.enable,
        'writes': writes,
    }
    (folder / '090-data-pack-redirect.json').write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')
    print('Generated', 'ENABLED' if args.enable else 'DISABLED', 'data.pack-only redirect:', len(code), 'wrapper bytes;', counts, 'import sites; no game file modified.')


if __name__ == '__main__':
    main()
