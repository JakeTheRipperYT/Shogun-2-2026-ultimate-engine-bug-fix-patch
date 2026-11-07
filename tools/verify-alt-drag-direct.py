"""Independent static inspection of the emitted image, using dumpbin's decode.

Checks PE bounds, untouched baseline bytes, relocation overlap, actual branch
destinations, position-independent entry setup, and stack balance across every
reachable path/loop. Does not claim native runtime or gameplay validation.
"""
from collections import deque
from pathlib import Path
import hashlib
import json
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build'
GAME = Path('C:/Program Files (x86)/Steam/steamapps/common/Total War SHOGUN 2')

# Callee argument cleanup, traced against OG. Cdecl calls have cleanup zero.
NATIVE = {
    0x102ACD20: 0, 0x10399F80: 4, 0x101CE380: 4, 0x10429DD0: 0,
    0x1042DFD0: 16, 0x101D10F0: 0, 0x100F04D0: 0, 0x110EEC30: 0,
    0x10BD12D0: 0, 0x10BD12A0: 4, 0x10419B40: 4, 0x100F7440: 0,
    0x10264600: 16, 0x10420ED0: 0, 0x10295A90: 8, 0x1029A6F0: 0,
    0x102E5C30: 4, 0x10090B10: 4, 0x101CF710: 0, 0x101CF760: 0,
    0x114FBC77: 0, 0x1037B430: 12, 0x1047ED90: 0, 0x1047ECA0: 0,
    0x1023D220: 4,
    0x10436690: 4,
    0x10BD4D70: 0,
}
REJOIN = {0x110F81E5: -112, 0x110F83E5: -12, 0x11101E16: -60,
          0x110FB986: -140, 0x110FAB3F: -4, 0x102E846B: -260}


def integer(s):
    return int(s[:-1], 16) if s.endswith('h') else int(s, 10)


def main():
    receipt = json.loads((BUILD / 'alt-drag-direct-x86-receipt.json').read_text())
    recipe = json.loads(Path(receipt['recipe']).read_text())
    candidate = Path(receipt['candidate']).read_bytes()
    baseline = (BUILD / 'backups/0.1.45-before-alt-drag-direct/UltimatePatch/empire.retail.dll').read_bytes()
    assert hashlib.sha256(baseline).hexdigest() == receipt['baseline_sha256']
    assert hashlib.sha256(candidate).hexdigest() == receipt['candidate_sha256']
    assert recipe['enabled'] is False
    native_audit = json.loads((BUILD / 'alt-drag-native-abi-audit.json').read_text())
    assert {int(row['va'], 16) for row in native_audit} == set(NATIVE)
    for row in native_audit:
        expected = NATIVE[int(row['va'], 16)]
        assert row['expected_cleanup'] == expected
        assert all(ret['cleanup'] == expected for ret in row['reachable_returns'])
        assert row['reachable_returns'] or int(row['va'], 16) in (0x1047ED90, 0x1047ECA0)
    reconstructed = bytearray(baseline)
    changed = set()
    for w in recipe['writes']:
        offset = int(w['offset'], 16)
        before, after = bytes.fromhex(w['expect']), bytes.fromhex(w['bytes'])
        assert bytes(reconstructed[offset:offset + len(before)]) == before
        assert len(before) == len(after)
        reconstructed[offset:offset + len(after)] = after
        changed.update(range(offset, offset + len(after)))
    assert int(recipe['append']['offset'], 16) == len(reconstructed)
    reconstructed.extend(bytes.fromhex(recipe['append']['bytes']))
    assert bytes(reconstructed) == candidate
    assert all(a == b or i in changed for i, (a, b) in enumerate(zip(baseline, candidate)))

    pe = struct.unpack_from('<I', candidate, 60)[0]
    assert struct.unpack_from('<H', candidate, pe + 4)[0] == 0x14C
    opt = pe + 24
    assert struct.unpack_from('<H', candidate, opt)[0] == 0x10B
    table = opt + struct.unpack_from('<H', candidate, pe + 20)[0]
    count = struct.unpack_from('<H', candidate, pe + 6)[0]
    sections = [struct.unpack_from('<IIII', candidate, table + 40 * i + 8) for i in range(count)]
    image_size = struct.unpack_from('<I', candidate, opt + 56)[0]
    for virtual_size, rva, raw_size, offset in sections:
        assert offset + raw_size <= len(candidate)
        assert rva + virtual_size <= image_size
    def file_offset(va):
        for _, rv, size, off in sections:
            if rv <= va - 0x10000000 < rv + size:
                return off + va - 0x10000000 - rv
        raise ValueError(hex(va))
    reloc_rva, reloc_size = struct.unpack_from('<II', candidate, opt + 96 + 5 * 8)
    for va, expected in (
        (0x102E846B, '8b 73 04 8b ce e8 5b 62 03 00'),
        (0x102E84CE, '5f 5e 5d b0 01 5b 81 c4 f4 00 00 00 c2 08 00'),
    ):
        expected = bytes.fromhex(expected)
        at = file_offset(va)
        assert candidate[at:at + len(expected)] == expected, 'Native movement sound tail changed'
    pos = file_offset(0x10000000 + reloc_rva)
    end = pos + reloc_size
    relocated = set()
    while pos < end:
        page, size = struct.unpack_from('<II', candidate, pos)
        assert size >= 8 and size % 2 == 0
        for at in range(pos + 8, pos + size, 2):
            slot = struct.unpack_from('<H', candidate, at)[0]
            if slot >> 12 == 3:
                f = file_offset(0x10000000 + page + (slot & 0xFFF))
                relocated.update(range(f, f + 4))
        pos += size
    # Hook bytes contain no relocated absolute operands. New code is relative.
    hook_offsets = {int(w['offset'], 16) for w in recipe['writes'][:5]}
    for off in hook_offsets:
        assert not relocated.intersection(range(off, off + 6))

    code = int(receipt['code_va'], 16)
    state = int(receipt['state_va'], 16)
    code_end = code + receipt['code_size']
    decoded = {}
    pattern = re.compile(r'^\s*([0-9A-F]{8}):\s+(?:[0-9A-F]{2} )+\s+([a-z][a-z0-9]*)\s*(.*?)\s*$')
    for line in (BUILD / 'alt-drag-direct-x86-inspection.asm').read_text().splitlines():
        m = pattern.match(line)
        if m and code <= int(m[1], 16) < code_end:
            decoded[int(m[1], 16)] = (m[2], m[3])
    assert code in decoded
    addresses = sorted(decoded)
    following = dict(zip(addresses, addresses[1:] + [code_end]))
    labels = {k: int(v, 16) for k, v in receipt['labels'].items()}
    ce_reference = json.loads((BUILD / 'ce-rotation-sensitivity-reference.json').read_text())
    expected_rate = bytes.fromhex(ce_reference['constants'][0]['bytes'])
    assert candidate[file_offset(state + 0x270):file_offset(state + 0x270) + 4] == expected_rate
    assert expected_rate == bytes.fromhex('89 9b d0 42')
    code_bytes = candidate[file_offset(code):file_offset(code) + receipt['code_size']]
    ui_mouse_source = bytes.fromhex('8d85') + struct.pack('<I', (0x11BBEAB0 - state) & 0xFFFFFFFF)
    assert code_bytes.count(ui_mouse_source) == 3, 'UI mouse X must supply start, delta and previous position'
    rotation_math = candidate[file_offset(labels['rotate_ce_math']):file_offset(labels['rotate_enter'])]
    assert bytes.fromhex('f30f5885') + struct.pack('<I', 0x260) in rotation_math
    assert bytes.fromhex('f30f5c85') + struct.pack('<I', 0x260) in rotation_math
    assert bytes.fromhex('f30f2cc0') in rotation_math
    for label in ('down', 'up', 'preview', 'mouse', 'key'):
        va = labels[label]
        at = file_offset(va)
        assert candidate[at:at + 8] == bytes.fromhex('9c60e8000000005d')
        assert candidate[at + 8:at + 10] == bytes.fromhex('81ed')
        immediate = struct.unpack_from('<I', candidate, at + 10)[0]
        for slide in (0, 0x13000000, 0x38000000):
            assert ((va + slide + 7 - immediate) & 0xFFFFFFFF) == state + slide

    summaries = {}
    native_calls = set()
    branches = 0
    def analyze(entry):
        nonlocal branches
        if entry in summaries:
            return summaries[entry]
        pending = deque([(entry, 0)])
        visited = {}
        endings = set()
        while pending:
            va, depth = pending.popleft()
            if va in visited:
                assert visited[va] == depth, f'inconsistent stack at {va:x}'
                continue
            visited[va] = depth
            assert va in decoded, f'branch into undecoded bytes: {va:x}'
            op, arg = decoded[va]
            nxt = following[va]
            if op == 'pushfd': depth -= 4
            elif op == 'popfd': depth += 4
            elif op == 'pushad': depth -= 32
            elif op == 'popad': depth += 32
            elif op == 'push': depth -= 4
            elif op == 'pop': depth += 4
            elif op in ('add', 'sub') and arg.startswith('esp,'):
                depth += integer(arg.split(',')[1]) * (1 if op == 'add' else -1)
            elif op == 'call':
                if arg == 'dword ptr [eax+0Ch]':
                    depth += 4  # native footprint returns through one argument
                elif arg == 'dword ptr [eax]':
                    pass  # existing GetForegroundWindow import: no arguments
                else:
                    target = int(arg, 16)
                    if target == nxt:
                        depth -= 4  # CALL/POP EIP acquisition, no RET
                    elif code <= target < code_end:
                        delta, cleanup = analyze(target)
                        assert delta == 0
                        depth += cleanup
                    else:
                        assert target in NATIVE, f'untraced external call {target:x}'
                        native_calls.add(target)
                        depth += NATIVE[target]
            elif op == 'ret':
                assert depth == 0, f'unbalanced RET at {va:x}: {depth}'
                endings.add((depth, integer(arg) if arg else 0))
                continue
            elif op.startswith('j'):
                target = int(arg, 16)
                branches += 1
                if target in REJOIN:
                    assert op == 'jmp' and depth == REJOIN[target], f'wrong native rejoin {va:x}'
                    endings.add((0, 8 if target == 0x102E846B else -1))
                else:
                    assert code <= target < code_end
                    pending.append((target, depth))
                if op == 'jmp': continue
            pending.append((nxt, depth))
        assert endings, f'no exit for {entry:x}'
        if entry not in (labels[k] for k in ('down', 'up', 'preview', 'mouse', 'key')):
            cleanup = 8 if entry == labels['movement_feedback'] else 0
            assert endings == {(0, cleanup)}, (hex(entry), endings)
            summaries[entry] = (0, cleanup)
            return (0, cleanup)
        return (0, 0)
    for label in ('down', 'up', 'preview', 'mouse', 'key'):
        analyze(labels[label])
    assert native_calls == set(NATIVE), 'Unexpected or missing native contracts'
    result = {'status': 'static-checks-passed-gameplay-not-tested',
              'candidate_sha256': receipt['candidate_sha256'],
              'decoded_instructions': len(decoded), 'native_call_contracts': len(native_calls),
              'branch_paths_checked': branches, 'stack_checked_helpers': len(summaries),
              'baseline_preserved_outside_guarded_writes': True, 'recipe_enabled': False,
              'checks': ['exact guarded reconstruction', 'baseline byte preservation',
                         'x86 PE section/image bounds', 'hook relocation exclusion',
                         'entry addressing under three ASLR slides',
                         'decoded control-flow and stack balance across loops/branches']}
    (BUILD / 'alt-drag-direct-x86-static-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
