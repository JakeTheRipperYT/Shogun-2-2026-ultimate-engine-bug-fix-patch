"""Read-only OG rank-fire snapshots. No debugger, injection or process writes.

Supply a CURRENT process PID and CURRENT task or soldier address. Addresses from
old CSVs are not reusable after a restart. --selftest needs no Windows process.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path
import struct
import time

PREFERRED = 0x10000000
STATES = dict(zip(range(0x1179A0F0, 0x1179A120, 4), (
    "STOP_STATE", "START_STATE", "TURN_STATE", "GET_AMMO_STATE",
    "MISFIRE_STATE", "AIM_STATE", "AIM_RELOAD_STATE", "AIM_FINISHED_STATE",
    "FIRE_STATE", "RELOAD_STATE", "WATCH_STATE", "FINISH_STATE")))
COMPATIBLE = {1, 2, 13, 14, 17, 18, 19, 20}
MOVEMENT_STATES = dict(zip(range(0x11799410, 0x11799444, 4), (
    "BEGIN_STATE", "MOVING_STATE", "LOCK_SPEED_AND_BEARING_STATE", "STOPPING_STATE",
    "INITIAL_TURN_STATE", "FINAL_TURN_STATE", "FINAL_TURN_OPERATION_STATE",
    "PRECISE_MOVEMENT_STATE", "STOP_BEFORE_TURN_STATE", "TURN_BEFORE_MOVE_STATE",
    "WAIT_STATE", "PIPE_STATE", "FINISHED_STATE")))


def number(value):
    return int(value, 0)


def u32(data, offset=0):
    return struct.unpack_from("<I", data, offset)[0]


def f32(data, offset=0):
    value = struct.unpack_from("<f", data, offset)[0]
    return value if math.isfinite(value) else None


def preferred(pointer, base):
    return pointer - base + PREFERRED if pointer else 0


def snapshot(read, soldier, base):
    """Decode one fixture/process snapshot; only `read(address, size)` accesses it."""
    data = read(soldier, 0x700)
    controller = preferred(u32(data, 0x2F8), base)
    action = u32(data, 0x248)
    active, latched = data[0x384], data[0x308]
    if active != 1 or latched == 1:
        ready = True
    elif action == 0:
        ready = False
    elif controller == 0x115DD1C0:
        ready = action in COMPATIBLE
    else:
        ready = None  # Other controller policy is not guessed.
    state = preferred(u32(data, 0x270), base)
    movement_state = preferred(u32(data, 0xFC), base)
    clip_pointer = u32(data, 0x474)
    out = {
        "soldier": hex(soldier), "soldier_id": u32(data, 0x218),
        "ready": ready, "active384": active, "ready308": latched,
        "entered385": data[0x385], "action_id248": action,
        "controller_vtable": hex(controller), "controller_type": u32(data, 0x338),
        "controller_mode": u32(data, 0x33C), "controller_started": data[0x368],
        "sequence_owned": data[0x2E8],
        "sequence_vtable": hex(preferred(u32(data, 0x250), base)),
        "sequence_done": data[0x258], "sequence_result": u32(data, 0x268),
        "sequence_state": STATES.get(state, hex(state)),
        "sequence_type": u32(data, 0x294), "sequence_mode": u32(data, 0x298),
        "delay": f32(data, 0x2A0), "start_time": f32(data, 0x2C4),
        "flag11f": data[0x11F], "goal_mode1f0": u32(data, 0x1F0),
        "movement_finished": data[0x11F],
        "movement_state": MOVEMENT_STATES.get(movement_state, hex(movement_state)),
        "movement_state_address": hex(movement_state),
        "pending_pipe138": data[0x138], "locked_until140": f32(data, 0x140),
        "stopping144": data[0x144], "bearing_speed_lock145": data[0x145],
        "stance_state1d0": u32(data, 0x1D0), "clip_pointer": hex(clip_pointer),
        "clip_elapsed_ticks": u32(data, 0x1D8),
    }
    scope = u32(data, 0x28)
    if scope:
        world = u32(read(scope + 8, 4))
        if world:
            ticks = u32(read(world + 0x50, 4))
            out["world_tick"] = ticks
            out["world_time"] = struct.unpack("<f", struct.pack("<f", ticks * 0.10000000149011612))[0]
    if clip_pointer:
        clip = read(clip_pointer, 8)
        clip_id, metadata = u32(clip), u32(clip, 4)
        out["clip_id"] = clip_id
        out["clip_is_standing_idle"] = 141 <= clip_id <= 157
        if metadata:
            total = u32(read(metadata + 0x64, 4))
            out["clip_total_ticks"] = total
            out["clip_remaining_ticks"] = max(0, total - out["clip_elapsed_ticks"])
    # The snapshot does not call the game's virtual loaded predicate. It does
    # not claim to observe muzzle firing, enemy distance, line of sight or range.
    return out


class ProcessReader:
    def __init__(self, pid):
        from ctypes import wintypes as W
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.p = ctypes.WinDLL("psapi", use_last_error=True)
        self.k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self.k.OpenProcess.restype = W.HANDLE
        self.k.ReadProcessMemory.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                           ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.k.CloseHandle.argtypes = [W.HANDLE]
        self.p.EnumProcessModulesEx.argtypes = [W.HANDLE, ctypes.c_void_p, W.DWORD,
                                               ctypes.POINTER(W.DWORD), W.DWORD]
        self.p.GetModuleFileNameExW.argtypes = [W.HANDLE, ctypes.c_void_p, W.LPWSTR, W.DWORD]
        # QUERY_INFORMATION | VM_READ. No VM_WRITE/VM_OPERATION/debugger rights.
        self.handle = self.k.OpenProcess(0x410, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None

    def read(self, address, length):
        if not (0 < address <= 0xFFFFFFFF and 0 < length <= 0x40000):
            raise ValueError("Invalid 32-bit read address/length")
        buf = ctypes.create_string_buffer(length)
        count = ctypes.c_size_t()
        if not self.k.ReadProcessMemory(self.handle, address, buf, length, ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        if count.value != length:
            raise OSError("Short process read")
        return buf.raw

    def regions(self):
        """Yield readable committed 32-bit address ranges without changing them."""
        from ctypes import wintypes as W
        class MemoryInfo(ctypes.Structure):
            _fields_ = [("BaseAddress", ctypes.c_void_p),
                        ("AllocationBase", ctypes.c_void_p),
                        ("AllocationProtect", W.DWORD),
                        ("RegionSize", ctypes.c_size_t),
                        ("State", W.DWORD), ("Protect", W.DWORD), ("Type", W.DWORD)]
        self.k.VirtualQueryEx.argtypes = [W.HANDLE, ctypes.c_void_p,
                                         ctypes.POINTER(MemoryInfo), ctypes.c_size_t]
        self.k.VirtualQueryEx.restype = ctypes.c_size_t
        address = 0x10000
        while address < 0x100000000:
            info = MemoryInfo()
            got = self.k.VirtualQueryEx(self.handle, address, ctypes.byref(info), ctypes.sizeof(info))
            if not got:
                break
            start, size = int(info.BaseAddress or 0), int(info.RegionSize)
            end = min(start + size, 0x100000000)
            if end <= address:
                raise OSError("VirtualQueryEx did not advance")
            # MEM_COMMIT; exclude guard/no-access and execute-only pages.
            readable = info.Protect & 0xFF in (2, 4, 8, 0x20, 0x40, 0x80)
            if info.State == 0x1000 and readable and not info.Protect & 0x100:
                yield max(start, 0x10000), end
            address = end

    def engine(self):
        from ctypes import wintypes as W
        modules = (ctypes.c_void_p * 1024)()
        needed = W.DWORD()
        if not self.p.EnumProcessModulesEx(self.handle, modules, ctypes.sizeof(modules),
                                          ctypes.byref(needed), 1):
            raise ctypes.WinError(ctypes.get_last_error())
        if needed.value > ctypes.sizeof(modules):
            raise OSError("Module list exceeded bounded buffer")
        for pointer in modules[:needed.value // ctypes.sizeof(ctypes.c_void_p)]:
            name = ctypes.create_unicode_buffer(1024)
            if self.p.GetModuleFileNameExW(self.handle, pointer, name, len(name)):
                if Path(name.value).name.lower() == "empire.retail.dll":
                    return pointer, name.value
        raise OSError("32-bit empire.retail.dll not found in this PID")


def _task_groups_and_current(read, task, base):
    data = read(task, 0x50)
    if preferred(u32(data), base) != 0x115C1048:
        raise ValueError("Task is not the supported OG rank-fire task")
    group_count, current = u32(data, 0x38), u32(data, 0x40)
    if not (1 <= group_count <= 3 and current < group_count):
        raise ValueError("Invalid/transitional rank group fields")
    squad, mapping = u32(data, 4), u32(data, 0x48)
    squad_data = read(squad, 0x20)
    count, members = u32(squad_data, 0x18), u32(squad_data, 0x1C)
    if count > 4096:
        raise ValueError("Squad count exceeds bounded scan")
    pointers = read(members, count * 4) if count else b""
    groups = {group: [] for group in range(group_count)}
    for index in range(count):
        soldier = u32(pointers, index * 4)
        soldier_id = u32(read(soldier + 0x218, 4))
        if soldier_id > 0x10000:
            raise ValueError("Soldier ID exceeds bounded group-map lookup")
        group = u32(read(mapping + soldier_id * 4, 4))
        if group in groups:
            groups[group].append(soldier)
    return current, groups


def task_groups(read, task, base):
    """Return all valid rank cohorts with task_members' vtable/count/ID bounds.

    Reads the member-pointer array once, then only each soldier's four-byte ID
    and four-byte group-map entry. Unmapped IDs are omitted as in task_members.
    The result includes empty lists for valid groups with no remaining members.
    """
    return _task_groups_and_current(read, task, base)[1]


def task_members(read, task, base):
    current, groups = _task_groups_and_current(read, task, base)
    return current, groups[current]


def validate_task(read, address, base):
    """Stricter discovery validation; rejects transient/dead lookalikes."""
    data = read(address, 0x50)
    if preferred(u32(data), base) != 0x115C1048:
        raise ValueError("Not a rank task")
    groups, current = u32(data, 0x38), u32(data, 0x40)
    if not (1 <= groups <= 3 and current < groups):
        raise ValueError("Invalid group fields")
    squad, mapping = u32(data, 4), u32(data, 0x48)
    if any(p < 0x10000 or p & 3 for p in (squad, mapping)):
        raise ValueError("Invalid squad/map pointer")
    squad_data = read(squad, 0x20)
    count, array = u32(squad_data, 0x18), u32(squad_data, 0x1C)
    if not (1 <= count <= 4096 and array >= 0x10000 and not array & 3):
        raise ValueError("Invalid member array/count")
    members = read(array, count * 4)
    # Sample both ends and up to six middle/early members. Do not assume an
    # exact unit size, but demand actual soldier IDs and bounded group values.
    indexes = sorted(set([0, count - 1] + list(range(min(count, 6)))))
    for index in indexes:
        soldier = u32(members, index * 4)
        if soldier < 0x10000 or soldier & 3:
            raise ValueError("Invalid soldier pointer")
        soldier_id = u32(read(soldier + 0x218, 4))
        if soldier_id > 0x10000:
            raise ValueError("Invalid soldier ID")
        if u32(read(mapping + soldier_id * 4, 4)) >= groups:
            raise ValueError("Invalid sampled soldier group")
    return {"task": hex(address), "squad": hex(squad), "member_count": count,
            "group_count": groups, "current_group": current,
            "fired44": data[0x44], "first_cycle45": data[0x45]}


def scan_tasks(read, regions, base, max_bytes=2 * 1024**3, max_seconds=20,
               max_hits=4096, max_tasks=128):
    """Bounded batch scan. Pure read/region functions allow synthetic checks."""
    needle = struct.pack("<I", base + 0x15C1048)
    started, scanned, read_errors, hits = time.monotonic(), 0, 0, 0
    tasks, seen, limit = [], set(), None
    for start, end in regions:
        cursor, carry = start, b""
        while cursor < end:
            if time.monotonic() - started >= max_seconds:
                limit = "time"; break
            if scanned >= max_bytes:
                limit = "bytes"; break
            size = min(0x40000, end - cursor, max_bytes - scanned)
            try:
                block = read(cursor, size)
            except (OSError, ValueError):
                read_errors += 1; scanned += size; cursor += size; carry = b""
                continue
            if len(block) != size:
                raise OSError("Short batch read")
            combined = carry + block
            combined_start, offset = cursor - len(carry), 0
            while True:
                offset = combined.find(needle, offset)
                if offset < 0:
                    break
                address = combined_start + offset; offset += 1
                if address & 3 or address in seen:
                    continue
                seen.add(address); hits += 1
                try:
                    tasks.append(validate_task(read, address, base))
                except (OSError, ValueError, struct.error):
                    pass
                if hits >= max_hits or len(tasks) >= max_tasks:
                    limit = "candidate-count"; break
            scanned += size; cursor += size; carry = combined[-3:]
            if limit:
                break
        if limit:
            break
    return {"tasks": tasks, "bytes_examined_or_skipped": scanned,
            "unreadable_batches": read_errors, "vtable_matches_validated": hits,
            "limit_reached": limit, "elapsed_s": time.monotonic() - started,
            "complete_for_reported_readable_regions": limit is None and read_errors == 0,
            "note": "Read-only heuristic discovery; candidates can disappear or be stale."}


def selftest():
    memory = bytearray(0x5000)
    def put(address, value):
        struct.pack_into("<I", memory, address, value)
    def read(address, length):
        if address < 0 or address + length > len(memory):
            raise ValueError("fixture bounds")
        return bytes(memory[address:address + length])
    soldier, base = 0x1000, 0x50000000
    put(soldier + 0x2F8, base + 0x15DD1C0)
    put(soldier + 0x270, base + 0x179A0F0)
    put(soldier + 0xFC, base + 0x1799440)
    memory[soldier + 0x11F] = 1
    memory[soldier + 0x138] = 1
    memory[soldier + 0x144] = 1
    memory[soldier + 0x145] = 1
    struct.pack_into("<f", memory, soldier + 0x140, 12.5)
    memory[soldier + 0x384] = 1
    put(soldier + 0x474, 0x3000)
    put(0x3000, 152); put(0x3004, 0x3100)
    put(0x3164, 100); put(soldier + 0x1D8, 7)
    a = snapshot(read, soldier, base)
    assert a["ready"] is False and a["sequence_state"] == "STOP_STATE"
    assert a["clip_id"] == 152 and a["clip_remaining_ticks"] == 93
    assert a["movement_state"] == "FINISHED_STATE" and a["movement_finished"] == 1
    assert a["pending_pipe138"] == 1 and a["locked_until140"] == 12.5
    assert a["stopping144"] == 1 and a["bearing_speed_lock145"] == 1
    assert "world_tick" not in a  # A missing optional scope must not dereference zero.
    put(soldier + 0x28, 0x3500); put(0x3508, 0x3600); put(0x3650, 123)
    a = snapshot(read, soldier, base)
    assert a["world_tick"] == 123 and abs(a["world_time"] - 12.3) < 0.00001
    memory[soldier + 0x308] = 1
    assert snapshot(read, soldier, base)["ready"] is True
    memory[soldier + 0x308] = 0; put(soldier + 0x248, 17)
    assert snapshot(read, soldier, base)["ready"] is True
    put(soldier + 0x2F8, base + 0x1000)
    assert snapshot(read, soldier, base)["ready"] is None
    put(soldier + 0x474, 0)
    assert "clip_id" not in snapshot(read, soldier, base)
    # Exercise rank membership filtering with two IDs in different groups.
    task, squad, members, mapping = 0x100, 0x200, 0x300, 0x400
    put(task, base + 0x15C1048); put(task + 4, squad)
    put(task + 0x38, 2); put(task + 0x40, 1); put(task + 0x48, mapping)
    put(squad + 0x18, 2); put(squad + 0x1C, members)
    put(members, soldier); put(members + 4, 0x2000)
    put(soldier + 0x218, 0); put(0x2218, 1)
    put(mapping, 0); put(mapping + 4, 1)
    assert task_members(read, task, base) == (1, [0x2000])
    assert task_groups(read, task, base) == {0: [soldier], 1: [0x2000]}
    # Discovery requires realistic minimum pointers, unlike the tiny membership
    # fixture above. Place two task-like vtable matches, one with invalid fields.
    large = bytearray(0x80000)
    def put_large(address, value):
        struct.pack_into("<I", large, address, value)
    def read_large(address, size):
        if address < 0 or address + size > len(large):
            raise ValueError("fixture bounds")
        return bytes(large[address:address + size])
    task, squad, array, mapping, soldier = 0x3FFFC, 0x50000, 0x50100, 0x50200, 0x60000
    put_large(task, base + 0x15C1048); put_large(task + 4, squad)
    put_large(task + 0x38, 1); put_large(task + 0x48, mapping)
    put_large(squad + 0x18, 1); put_large(squad + 0x1C, array)
    put_large(array, soldier); put_large(soldier + 0x218, 0)
    put_large(0x20000, base + 0x15C1048)  # Invalid candidate must be rejected.
    report = scan_tasks(read_large, [(0x10000, len(large))], base)
    assert len(report["tasks"]) == 1 and report["tasks"][0]["task"] == hex(task)
    assert report["vtable_matches_validated"] == 2 and report["complete_for_reported_readable_regions"]
    limited = scan_tasks(read_large, [(0x10000, len(large))], base, max_bytes=0x10000)
    assert limited["limit_reached"] == "bytes" and not limited["complete_for_reported_readable_regions"]
    print("PASS snapshot decoding, readiness/clip/movement/world/group fields, batch task scan and limits")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pid", type=int)
    target = ap.add_mutually_exclusive_group()
    target.add_argument("--task", type=number)
    target.add_argument("--soldier", type=number)
    target.add_argument("--scan-tasks", action="store_true",
                        help="find plausible current rank tasks using read-only memory batches")
    ap.add_argument("--scan-mb", type=int, default=2048)
    ap.add_argument("--scan-seconds", type=float, default=20)
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--interval", type=float, default=0.05)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.selftest:
        selftest(); return
    if not args.pid or not (args.task or args.soldier or args.scan_tasks):
        ap.error("supply --pid and --task, --soldier OR --scan-tasks")
    if not args.scan_tasks and not args.out:
        ap.error("snapshot capture requires --out")
    if not (1 <= args.scan_mb <= 4096 and 0 < args.scan_seconds <= 120):
        ap.error("scan limits: --scan-mb 1..4096, --scan-seconds 0..120")
    if not (0 < args.seconds <= 3600 and 0.01 <= args.interval <= 10):
        ap.error("seconds must be 0..3600; interval 0.01..10")
    process = ProcessReader(args.pid)
    try:
        base, path = process.engine()
        expected = bytes.fromhex("80 b9 84 03 00 00 01")
        if process.read(base + 0x3CBE40, len(expected)) != expected:
            raise ValueError("Unsupported soldier readiness code prefix; refusing layout assumptions")
        if args.scan_tasks:
            report = scan_tasks(process.read, process.regions(), base,
                                args.scan_mb * 1024**2, args.scan_seconds)
            report.update(pid=args.pid, engine=path, engine_base=hex(base), read_only=True)
            encoded = json.dumps(report, indent=2)
            print(encoded)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                with args.out.open("x", encoding="utf-8") as output:
                    output.write(encoded + "\n")
            return
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create avoids silently overwriting an earlier capture.
        with args.out.open("x", encoding="utf-8") as output:
            output.write(json.dumps({"event": "metadata", "pid": args.pid, "engine": path,
                                     "engine_base": hex(base), "read_only": True,
                                     "non_atomic_sampling": True}) + "\n")
            started, previous, last_flush = time.monotonic(), None, time.monotonic()
            while time.monotonic() - started < args.seconds:
                current, soldiers = (None, [args.soldier])
                if args.task:
                    current, soldiers = task_members(process.read, args.task, base)
                snapshots = [snapshot(process.read, s, base) for s in soldiers]
                # Preserve all current-rank snapshots; identify the first known
                # unready member without treating unknown controller policy as ready.
                blocked = next((s["soldier"] for s in snapshots if s["ready"] is False), None)
                key = json.dumps([current, snapshots], sort_keys=True)
                if key != previous:
                    output.write(json.dumps({"event": "snapshot", "t_s": time.monotonic() - started,
                                             "current_group": current, "first_known_unready": blocked,
                                             "soldiers": snapshots}, allow_nan=False) + "\n")
                    previous = key
                if time.monotonic() - last_flush >= 0.5:
                    output.flush(); last_flush = time.monotonic()
                time.sleep(args.interval)
    finally:
        process.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
