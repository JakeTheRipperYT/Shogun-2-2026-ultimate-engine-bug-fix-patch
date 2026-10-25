"""Generate a DISABLED rank-first-volley idle interrupt candidate, never a DLL.

Requires the exact supported vanilla OG engine. Refuses cave/hook overlap with
enabled recipes and requires the existing 000 recipe to map the whole stub.
Only this generator's 080 JSON is written. No game file is changed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ORIGINAL_SHA256 = '022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5'
CAVE = 0x115A0DA0
CAVE_CAPACITY = 96
HOOK = 0x10188290
RESUME = HOOK + 5
VTABLE = 0x115C1048
CANCEL = 0x103CA920
ORIGINAL_HOOK = bytes.fromhex('83 ec 50 8b c1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    args = parser.parse_args()
    raw = args.engine.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('Unsupported original OG engine SHA-256')
    nt = struct.unpack_from('<I', raw, 0x3C)[0]
    opt = nt + 24
    if struct.unpack_from('<H', raw, nt + 4)[0] != 0x14C:
        raise ValueError('Expected original x86 PE')
    base = struct.unpack_from('<I', raw, opt + 28)[0]
    table = opt + struct.unpack_from('<H', raw, nt + 20)[0]
    sections = []
    for i in range(struct.unpack_from('<H', raw, nt + 6)[0]):
        at = table + i * 40
        vs, rva, size, offset = struct.unpack_from('<IIII', raw, at + 8)
        sections.append((raw[at:at + 8].rstrip(b'\0'), vs, rva, size, offset, at))
    text = next(s for s in sections if s[0] == b'.text')

    def offset(va):
        rva = va - base
        for _, _, section_rva, size, file_offset, _ in sections:
            if section_rva <= rva < section_rva + size:
                return file_offset + rva - section_rva
        raise ValueError('VA outside raw section data: ' + hex(va))

    code = bytearray()
    labels = {}
    jumps = []

    def emit(value):
        code.extend(bytes.fromhex(value))

    def branch(opcode, target='restore'):
        emit(opcode)
        jumps.append((len(code), target))
        emit('00')

    def relative(opcode, target):
        emit(opcode)
        code.extend(struct.pack('<i', target - (CAVE + len(code) + 4)))

    # Entry ESP points to return address; pushfd + pushad occupy 36 bytes.
    # ECX remains the firing task until replaced with the soldier for cancellation.
    emit('9c 60')
    relative('e8', CAVE + len(code) + 5)  # call next; no absolute addresses/relocs
    anchor = CAVE + len(code)
    emit('5a 81 c2')                    # pop edx; add edx, vtable - anchor
    code.extend(struct.pack('<I', (VTABLE - anchor) & 0xFFFFFFFF))
    emit('39 11'); branch('75')         # [task] must be ranked-fire vtable
    emit('80 79 45 01'); branch('75')    # first cycle
    emit('80 79 44 00'); branch('75')    # no rank has fired yet
    emit('80 7c 24 2c 00'); branch('75') # ordinary preparation, not follow-up
    emit('83 79 40 00'); branch('75')    # current firing group zero
    emit('8b 4c 24 28 85 c9'); branch('74')  # soldier argument; defensive null guard
    emit('8b 81 74 04 00 00 85 c0'); branch('74')
    emit('8b 00 2d 8d 00 00 00 83 f8 10'); branch('77') # clip ID 141..157 inclusive
    relative('e8', CANCEL)              # native ordinary-clip cancellation
    labels['restore'] = len(code)
    emit('61 9d')                       # restore every GPR and entry EFLAGS
    code.extend(ORIGINAL_HOOK)          # replay sub esp,50; mov eax,ecx
    relative('e9', RESUME)
    for at, target in jumps:
        distance = labels[target] - (at + 1)
        if not -128 <= distance <= 127:
            raise ValueError('Short branch overflow')
        code[at] = distance & 0xFF
    if len(code) != 90 or len(code) > CAVE_CAPACITY:
        raise ValueError('Unexpected candidate size: ' + str(len(code)))
    if raw[offset(HOOK):offset(HOOK) + 5] != ORIGINAL_HOOK:
        raise ValueError('Hook bytes differ')
    if raw[offset(CAVE):offset(CAVE) + CAVE_CAPACITY] != bytes(CAVE_CAPACITY):
        raise ValueError('Reserved cave is not entirely original zero padding')

    folder = Path(__file__).resolve().parents[1] / 'patches' / 'engine'
    targets = [(offset(CAVE), offset(CAVE) + len(code)), (offset(HOOK), offset(HOOK) + 5)]
    mapped_size = text[1]
    for path in sorted(folder.glob('*.json')):
        recipe = json.loads(path.read_text(encoding='utf-8-sig'))
        if not recipe.get('enabled'):
            continue
        for write in recipe['writes']:
            at = int(write['offset'], 0) if 'offset' in write else offset(int(write['va'], 0))
            payload = bytes.fromhex(write['bytes'])
            end = at + len(payload)
            if any(at < stop and begin < end for begin, stop in targets):
                raise ValueError('Candidate overlaps enabled recipe ' + path.name)
            if at == text[5] + 8 and len(payload) == 4:
                mapped_size = struct.unpack('<I', payload)[0]
    if CAVE + len(code) > base + text[2] + mapped_size:
        raise ValueError('Current enabled recipes do not map the whole cave')
    hook = b'\xe9' + struct.pack('<i', CAVE - HOOK - 5)
    patch = {
        'id': 'rank-idle-first-volley',
        'title': 'DISABLED candidate: interrupt standing idle clips before the first ranked volley',
        'description': 'Research candidate, not a validated gameplay fix. Detour only rank preparation FUN_10188290; require task vtable 0x115C1048, first-cycle flag +45 == 1, fired flag +44 == 0, ordinary followup argument == 0 and current group +40 == 0. For a nonnull soldier whose current clip at +474 has animation ID 141..157 (standing/trained-standing idle families), call native FUN_103CA920. Restore all GPRs/EFLAGS and replay the full original five-byte prologue. Existing type-5 request, stance flags, loading, time/STOP conditions and later firing cycles are unchanged. Stub is 90 PIC bytes at 0x115A0DA0; requires current 000 text mapping and does not overlap naval/pack redirect data. Live blocking clip identity and battle regressions remain unverified. See docs/ranked-fire-firearm-stop-gate.md.',
        'enabled': False,
        'writes': [
            {'va': hex(CAVE), 'expect': bytes(len(code)).hex(' '), 'bytes': code.hex(' '),
             'note': 'PIC guard/cancel adapter; no absolute addresses or new relocations'},
            {'va': hex(HOOK), 'expect': ORIGINAL_HOOK.hex(' '), 'bytes': hook.hex(' '),
             'note': 'Whole original prologue replaced by relative jump; adapter resumes at 0x10188295'}
        ]
    }
    destination = folder / '080-rank-idle-first-volley.json'
    destination.write_text(json.dumps(patch, indent=2) + '\n', encoding='utf-8')
    print('Generated DISABLED rank-idle candidate:', len(code), 'bytes at', hex(CAVE))
    print('Hook:', hook.hex(' '))
    print('Stub:', code.hex(' '))
    print('Confirmed no overlap with current enabled recipes; no engine file modified.')


if __name__ == '__main__':
    main()
