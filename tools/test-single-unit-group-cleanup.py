"""Execute native singleton cleanup, destruction/recreation and selection regressions.

Requires Unicorn and pefile. No installed files/processes are changed. Original,
0.1.15 behavior reproduced in RAM, and actual --dll fixed bytes are tested at
three ASLR bases. Packet delivery and eligibility queries are controlled fixtures.
"""
import argparse
from collections import Counter
import importlib.util
import hashlib
import json
from pathlib import Path
import pefile
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EAX

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('groups', ROOT / 'tools/test-single-unit-groups.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
CACHE = {}


def make(path, base, mode, count, group_id, naval=False, exists=True, eligible=True):
    key = (str(path), base)
    if key not in CACHE:
        CACHE[key] = pefile.PE(str(path))
    f = g.Fixture(CACHE[key], base)
    d, mu = f.delta, f.mu
    for address, size in ((0x110DD2D0, 0xE0), (0x102EC440, 8), (0x10182650, 8),
                          (0x101825C0, 8), (0x110D0C10, 8), (0x110D0BB0, 8), (0x10254AA0, 0x20)):
        f.code(address, size)
    if mode == 'regression-0.1.15':
        mu.mem_write(0x10F9787F + d, b'\x73')
    f.write(g.OBJ, g.VT, g.MGR, max(count, 1), count & 0xFFFFFFFF, g.DATA, group_id)
    members = [0x12340000 + i * 4 for i in range(max(count, 0))]
    if members:
        f.write(g.DATA, *members)
    f.write(g.MGR, g.MVT)
    f.write(g.MGR + 0x40, int(exists), g.DATA + 0x200)
    f.write(g.DATA + 0x200, g.OBJ)
    f.write(g.MGR + 0x98, g.AUX)
    f.write(g.MVT + 0x10, 0x110DD2D0 + d)
    f.write(g.MVT + 0x14, g.CALLBACK + 0x10)
    f.write(g.MVT + 0x1C, g.CALLBACK)
    f.write(g.VT, g.CALLBACK + 0x20)
    f.write(g.AUX + 0x540, int(naval))
    f.write(g.AUX + 0x110, 0x24000000)
    f.map(0x24028000, 0x1000)
    f.write(0x24028048, 0x24100000)
    events, packets = [], []
    def hook(uc, address, size, user):
        sp = uc.reg_read(UC_X86_REG_ESP)
        if address == g.CALLBACK:
            assert f.read(sp + 4, 2) == (members[0], 0xFFFFFFFF)
            events.append('clear-unit-group-id'); f.ret(8)
        elif address == g.CALLBACK + 0x10:
            assert f.read(sp + 4)[0] == g.OBJ + 8
            events.append('ungroup-remaining-members'); f.ret(4)
        elif address == g.CALLBACK + 0x20:
            assert f.read(sp + 4)[0] == 1
            events.append('destroy-ui-record'); f.ret(4)
        elif address == 0x102EC440 + d:
            events.append('resolve-army'); f.ret(0, 0xABCDEF00)
        elif address in (0x10182650 + d, 0x101825C0 + d):
            assert f.read(sp + 4)[0] == group_id
            events.append('eligible-query'); f.ret(4, int(eligible))
        elif address in (0x110D0C10 + d, 0x110D0BB0 + d):
            assert address == (0x110D0BB0 if naval else 0x110D0C10) + d
            assert uc.reg_read(UC_X86_REG_ECX) == 0x24100000
            packet = f.read(f.read(sp + 4)[0], 3)
            assert packet == (0x115C4DE4 + d, 0xABCDEF00, group_id)
            packets.append(packet); events.append('engine-destroy-packet'); f.ret(4)
    f.hook = hook
    f.events, f.packets = events, packets
    return f


def invoke(f, address, obj, arg):
    f.write(g.STACK, g.STOP, arg & 0xFFFFFFFF)
    f.mu.reg_write(UC_X86_REG_ECX, obj)
    f.mu.reg_write(UC_X86_REG_ESP, g.STACK)
    f.run(address, f.hook)
    f.abi(8)
    return f.mu.reg_read(UC_X86_REG_EAX)


def removal(path, base, mode, count, group_id, naval):
    f = make(path, base, mode, count, group_id, naval)
    result = invoke(f, 0x10F97840, g.OBJ, 0x12340000)
    left = count - 1
    destroyed = left <= (1 if mode == 'vanilla' else 0)
    expected = destroyed and (left > 0 or mode == 'fixed')
    assert f.read(g.OBJ + 0xC)[0] == left
    assert result == (2 if destroyed else 1)
    assert len(f.packets) == int(expected), (mode, count, naval, f.events)
    return f, {'kind': 'removal', 'base': hex(base), 'mode': mode, 'initialCount': count,
               'groupId': group_id, 'naval': naval, 'packets': len(f.packets), 'events': f.events[:]}


def owner_guard(path, base, mode, count, exists, eligible, group_id, naval):
    f = make(path, base, mode, count, group_id, naval, exists, eligible)
    invoke(f, 0x110DD2D0, g.MGR, group_id)
    expected = exists and eligible and (count >= 0 if mode == 'fixed' else count > 0)
    assert len(f.packets) == int(expected), (mode, count, exists, eligible, f.events)
    return {'kind': 'owner-guard', 'base': hex(base), 'mode': mode, 'count': count,
            'groupId': group_id, 'naval': naval, 'exists': exists, 'eligible': eligible,
            'packets': len(f.packets)}


def recreate(path, base, mode, group_id, naval):
    # Start with the actual singleton removal / owner guard path above.
    f, result = removal(path, base, mode, 1, group_id, naval)
    for address, size in ((0x10169170, 0xA4), (0x10169280, 0x70), (0x100B5500, 0x140),
                          (0x101B3D90, 0x50), (0x10196A90, 0x10),
                          (0x1041EBD0, 0x30), (0x102FC880, 0x10)):
        f.code(address, size)
    old, new, vt = 0x25000000, 0x25001000, 0x25002000
    f.map(old, 0x3000)
    for obj, count in ((old, 0), (new, 1)):
        f.write(obj, vt)
        f.write(obj + 0x10, group_id)
        f.write(obj + 0x20, count, g.DATA + 0x500)
    f.write(vt + 0x6C, 0x10196A90 + f.delta)
    # Real army groups vector and deferred deletion vector, with capacity to
    # avoid allocator stubbing.10169170 enqueues deletion; no immediate dtor.
    f.write(g.MGR + 0x160, 4, 1, g.DATA + 0x300)
    f.write(g.DATA + 0x300, old)
    f.write(g.MGR + 0x178, 4, 0, g.DATA + 0x400)
    if f.packets:
        assert invoke(f, 0x10169170, g.MGR, group_id) & 0xFF == 1
        assert f.read(g.MGR + 0x164)[0] == 0
        assert f.read(g.MGR + 0x17C)[0] == 1
        assert f.read(g.DATA + 0x400)[0] == old
    # Append the new same-ID group with the actual native vector helper.
    invoke(f, 0x100B5500, g.MGR + 0x158, new)
    chosen = invoke(f, 0x101B3D90, g.MGR, group_id)
    assert chosen == (new if mode == 'fixed' else old)
    selection = g.AUX + 0x200
    f.write(selection + 4, 2, 0, g.DATA + 0x600)
    invoke(f, 0x1041EBD0, selection, chosen)
    selected = f.read(selection + 8)[0]
    assert selected == int(mode == 'fixed')
    if selected:
        assert f.read(g.DATA + 0x600)[0] == new
    result.update(kind='same-ID-recreate-selection', chosen='new-live' if chosen == new else 'stale-empty',
                  selected=selected, deferredDeletionCount=f.read(g.MGR + 0x17C)[0])
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vanilla', type=Path, required=True)
    ap.add_argument('--dll', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    args = ap.parse_args()
    old, new = pefile.PE(str(args.vanilla)), pefile.PE(str(args.dll))
    assert old.get_data(0x110DD31C - g.PREFERRED, 6) == bytes.fromhex('0f8e84000000')
    assert new.get_data(0x110DD31C - g.PREFERRED, 6) == bytes.fromhex('0f8c84000000')
    assert old.get_data(0x10F9787F - g.PREFERRED, 2) == bytes.fromhex('772d')
    assert new.get_data(0x10F9787F - g.PREFERRED, 2) == bytes.fromhex('732d')
    results = []
    for base in (0x10000000, 0x53000000, 0x6C000000):
        for mode in ('vanilla', 'regression-0.1.15', 'fixed'):
            path = args.dll if mode == 'fixed' else args.vanilla
            for group_id in (0, 1, 2, 3):
                for naval in (False, True):
                    for count in (1, 2, 3):
                        results.append(removal(path, base, mode, count, group_id, naval)[1])
                    for count, exists, eligible in ((-1, True, True), (0, True, True),
                                                     (1, True, True), (0, False, True), (0, True, False)):
                        results.append(owner_guard(path, base, mode, count, exists, eligible, group_id, naval))
                    if mode != 'vanilla':
                        results.append(recreate(path, base, mode, group_id, naval))
    counts = dict(Counter(r['kind'] for r in results))
    receipt = {'status': 'PASS', 'cases': len(results), 'counts': counts,
               'vanilla': str(args.vanilla), 'dll': str(args.dll),
               'vanillaSha256': hashlib.sha256(args.vanilla.read_bytes()).hexdigest(),
               'dllSha256': hashlib.sha256(args.dll.read_bytes()).hexdigest(),
               'actualInstructions': ['10F97840 removal', '10094080 erase', '110DD2D0 owner+10 guard',
                                      'land/naval destroy packet construction', '10169170 army removal',
                                      '10169280 member detach', '100B5500 append', '101B3D90 lookup',
                                      '1041EBD0/102FC880 selection'],
               'limitations': 'Engine eligibility and packet transport/UI callbacks are fixtures. Destruction enqueues the actual deferred deletion vector; immediate object destruction is not claimed. Same-ID recreation appends a prepared group, not the full game constructor. Gameplay/rendering remain player tests.',
               'results': results}
    args.report.write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('PASS', len(results), 'actual-code cleanup cases at three ASLR bases:', counts)
    print('Receipt:', args.report)


if __name__ == '__main__':
    main()

