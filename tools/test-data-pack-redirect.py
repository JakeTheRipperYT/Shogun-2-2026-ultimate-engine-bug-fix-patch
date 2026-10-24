"""Exercise the exact single-data.pack redirect bytes at three ASLR bases.

Requires unicorn and pefile in the selected Python environment. Optional --dll
checks the built DLL's recipe bytes and relocation entries, then emulates those
actual bytes too. No game process/file is modified.
"""
from pathlib import Path
import argparse
import json
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP, UC_X86_REG_EIP

ROOT = Path(__file__).resolve().parents[1]
PREFERRED = 0x10000000
WRAPPER, STUB, TABLE, STRINGS, IAT = 0x115A0C4A, 0x115A0C40, 0x115A0D78, 0x11793AE8, 0x115A1144
REAL, RETURN, INPUT, STACK = 0x20000000, 0x20001000, 0x20002000, 0x2000F000
SHADOW = 'UltimatePatch\\data\\data.pack'
MASK = 0x530D0156


def emulate(writes, base, path, access=0x80000000, disposition=3, loader=False):
    delta = base - PREFERRED
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(0x115A0000 + delta, 0x2000)
    mu.mem_map(0x11793000 + delta, 0x1000)
    mu.mem_map(REAL, 0x10000)
    for address, data in writes.items():
        if 0x115A0000 <= address < 0x115A2000 or 0x11793000 <= address < 0x11794000:
            mu.mem_write(address + delta, data)
    mu.mem_write(IAT + delta, struct.pack('<I', REAL))
    # Real Win32 stdcall return, not just stopping at the IAT boundary.
    mu.mem_write(REAL, bytes.fromhex('b8 78 56 34 12 c2 1c 00'))
    mu.mem_write(RETURN, b'\xf4')
    if path is not None:
        mu.mem_write(INPUT, (path + '\0').encode('utf-16le'))
    args = [INPUT if path is not None else 0, access, 0x1122, 0x33445566, disposition, 0x02000080, 0x55667788]
    expected_registers = [0xB0B0, 0x5151, 0xD1D1, 0xEBEB]
    for register, value in zip((UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP), expected_registers):
        mu.reg_write(register, value)
    if loader:
        mu.mem_write(STACK, struct.pack('<I', RETURN))
        mu.reg_write(UC_X86_REG_ESP, STACK)
        mu.emu_start(STUB + delta, RETURN, count=100)
        assert mu.reg_read(UC_X86_REG_EBX) == WRAPPER + delta
        assert mu.reg_read(UC_X86_REG_ESP) == STACK + 4
        expected_registers[0] = WRAPPER + delta
    mu.mem_write(STACK, struct.pack('<8I', RETURN, *args))
    mu.reg_write(UC_X86_REG_ESP, STACK)
    seen = []

    def capture(uc, address, size, user):
        if address == REAL:
            sp = uc.reg_read(UC_X86_REG_ESP)
            frame = list(struct.unpack('<8I', uc.mem_read(sp, 32)))
            pointer = frame[1]
            output = None
            if pointer:
                data = bytearray()
                for i in range(2048):
                    pair = bytes(uc.mem_read(pointer + i * 2, 2))
                    if pair == b'\0\0':
                        break
                    data.extend(pair)
                else:
                    raise AssertionError('Output path not terminated')
                output = data.decode('utf-16le')
            seen.append((frame, output))

    mu.hook_add(UC_HOOK_CODE, capture)
    mu.emu_start(WRAPPER + delta, RETURN, count=10000)
    assert len(seen) == 1, 'Expected exactly one CreateFileW call'
    frame, output = seen[0]
    expected = path
    normalized = (path or '').replace('/', '\\').lower()
    if path is not None and disposition == 3 and not access & MASK:
        if normalized == 'data\\data.pack' or normalized.endswith('\\data\\data.pack'):
            expected = SHADOW
    assert output == expected, (base, path, access, disposition, output, expected)
    assert frame[0] == RETURN and frame[2:] == args[1:]
    assert mu.reg_read(UC_X86_REG_EIP) == RETURN
    assert mu.reg_read(UC_X86_REG_ESP) == STACK + 32, 'stdcall stack imbalance'
    assert mu.reg_read(UC_X86_REG_EAX) == 0x12345678, 'Win32 return changed'
    assert [mu.reg_read(r) for r in (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)] == expected_registers


def exercise(writes):
    cases = 0
    paths = [None, '', 'data.pack', 'data\\data.pack', 'DATA/DATA.PACK',
             'C:\\Games\\SHOGUN 2\\data\\data.pack', 'C:/Games/将軍/data/DATA.PACK',
             'data\\models.pack', 'data\\local_en.pack', 'data\\boot.pack',
             'C:\\Games\\data\\models.pack', 'C:\\Games\\data\\local_en.pack',
             'mydata\\data.pack', 'data\\xdata.pack', 'data\\data.pack.bak',
             'UltimatePatch\\data\\models.pack', 'UltimatePatch\\data\\local_en.pack']
    accesses = [0, 1, 0x80000000, 0xC0000000, 0x10000000, 2, 4, 0x10, 0x40, 0x100, 0x10000, 0x40000, 0x80000, 0x01000000, 0x02000000]
    for base in (0x10000000, 0x53000000, 0x6C000000):
        for path in paths:
            emulate(writes, base, path); cases += 1
        for access in accesses:
            emulate(writes, base, 'data\\data.pack', access=access); cases += 1
        for disposition in (1, 2, 3, 4, 5):
            emulate(writes, base, 'data\\data.pack', disposition=disposition); cases += 1
        emulate(writes, base, 'data\\data.pack', loader=True); cases += 1
    return cases


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dll', type=Path)
    args = ap.parse_args()
    recipe = json.loads((ROOT / 'patches/engine/090-data-pack-redirect.json').read_text())
    writes = {int(w['va'], 0): bytes.fromhex(w['bytes']) for w in recipe['writes'] if 'va' in w}
    assert len(writes[TABLE]) == 12, 'Exactly one redirect entry required'
    assert writes[STRINGS] == (SHADOW + '\0').encode('utf-16le')
    assert WRAPPER + len(writes[WRAPPER]) <= 0x115A0D20
    assert TABLE + len(writes[TABLE]) <= 0x115A0DA0
    count = exercise(writes)
    print('PASS', count, 'exact-recipe cases at three ASLR bases; data.pack only, write-access refusals, Win32 args/return/stack and nonvolatile registers')
    if args.dll:
        import pefile
        pe = pefile.PE(str(args.dll), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_BASERELOC']])
        assert pe.OPTIONAL_HEADER.ImageBase == PREFERRED
        for w in recipe['writes']:
            expected = bytes.fromhex(w['bytes'])
            actual = pe.__data__[int(w['offset'], 0):int(w['offset'], 0) + len(expected)] if 'offset' in w else pe.get_data(int(w['va'], 0) - PREFERRED, len(expected))
            assert actual == expected, w.get('va', w.get('offset'))
        ranges = [(va, va + len(data)) for va, data in writes.items()]
        for block in pe.DIRECTORY_ENTRY_BASERELOC:
            for relocation in block.entries:
                if relocation.type:
                    address = PREFERRED + relocation.rva
                    assert not any(address < end and start < address + 4 for start, end in ranges), hex(address)
        actual_writes = {va: pe.get_data(va - PREFERRED, len(data)) for va, data in writes.items()}
        count = exercise(actual_writes)
        print('PASS built DLL bytes/relocation exclusions and', count, 'actual-DLL cases at three ASLR bases')


if __name__ == '__main__':
    main()
