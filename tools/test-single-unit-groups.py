"""Execute actual OG player-group instructions in isolated x86 Unicorn fixtures.

No game process is opened. Engine virtual UI callbacks are controlled fixtures;
creator vector append and removal vector erase execute their actual DLL code.
--dll repeats against built bytes, at three relocated image bases.
This verifies instruction behavior and ABI, not gameplay or rendered appearance.
"""
import argparse
from collections import Counter
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

ROOT = Path(__file__).resolve().parents[1]
VANILLA = Path(r'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2\empire.retail.dll')
PREFERRED = 0x10000000
OBJ, VT, DATA, MGR, MVT, AUX = [0x20000000 + i * 0x1000 for i in range(6)]
STACK, STOP, CALLBACK = 0x21008000, 0x22000000, 0x22001000
REGS = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
SENTINELS = (0xB0B0B0B0, 0x51515151, 0xD1D1D1D1, 0xEBEBEBEB)
SITES = {0x11101A3A: 1, 0x11102DC8: 1, 0x10F89A46: 1,
         0x11223482: 1}


def pack(*values):
    return struct.pack('<' + 'I' * len(values), *values)


class Fixture:
    def __init__(self, pe, base):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.delta = base - PREFERRED
        # pefile applies HIGHLOW relocations to the actual image instructions.
        if not hasattr(pe, "fixture_image"):
            pe.fixture_image = pe.get_memory_mapped_image(ImageBase=base)
        self.image = pe.fixture_image
        self.pages = set()
        self.pe = pe
        for address, length in ((0x11101A30, 0x60), (0x11102DC5, 0x50),
                                (0x10F89A40, 0x50), (0x10F97840, 0x90),
                                (0x10098B40, 0x150), (0x10094080, 0x50),
                                (0x110E2120, 0x40), (0x10473340, 0xD0),
                                (0x11223470, 0x130), (0x11100570, 0x100), (0x10F9C360, 0x10)):
            self.code(address, length)
        self.map(OBJ, 0x6000)
        self.map(STACK - 0x8000, 0x10000)
        self.map(STOP, 0x2000)
        self.mu.mem_write(STOP, b'\xf4')
        self.mu.reg_write(UC_X86_REG_ESP, STACK)
        self.mu.reg_write(UC_X86_REG_EFLAGS, 0x202)
        for reg, value in zip(REGS, SENTINELS):
            self.mu.reg_write(reg, value)

    def map(self, address, length):
        for page in range(address & ~0xFFF, (address + length + 0xFFF) & ~0xFFF, 0x1000):
            if page not in self.pages:
                self.mu.mem_map(page, 0x1000)
                self.pages.add(page)

    def code(self, address, length):
        actual = address + self.delta
        page = actual & ~0xFFF
        end = (actual + length + 0xFFF) & ~0xFFF
        self.map(page, end - page)
        offset = page - PREFERRED - self.delta
        self.mu.mem_write(page, self.image[offset:offset + end - page])

    def write(self, address, *values):
        self.mu.mem_write(address, pack(*values))

    def read(self, address, count=1):
        return struct.unpack('<' + 'I' * count, self.mu.mem_read(address, 4 * count))

    def ret(self, size, result=0):
        sp = self.mu.reg_read(UC_X86_REG_ESP)
        address = self.read(sp)[0]
        self.mu.reg_write(UC_X86_REG_ESP, sp + 4 + size)
        self.mu.reg_write(UC_X86_REG_EAX, result)
        self.mu.reg_write(UC_X86_REG_EIP, address)

    def run(self, start, hook):
        self.mu.hook_add(UC_HOOK_CODE, hook)
        self.mu.emu_start(start + self.delta, STOP, count=10000)

    def abi(self, popped):
        assert self.mu.reg_read(UC_X86_REG_EIP) == STOP
        assert self.mu.reg_read(UC_X86_REG_ESP) == STACK + popped
        assert tuple(self.mu.reg_read(r) for r in REGS) == SENTINELS


def gate(pe, base, patched, naval, selected, groups, capacity):
    f = Fixture(pe, base)
    mu, d = f.mu, f.delta
    f.map(0x11BC8180 + d, 4)
    f.write(0x11BC8180 + d, OBJ)
    f.write(OBJ + 0x5B4, MGR)
    f.write(MGR + 0x40, groups)
    f.write(MGR + 0x50, capacity)
    f.write(DATA + 4, selected)
    f.write(STACK + 0x38, selected)
    mu.reg_write(UC_X86_REG_EBX, AUX)
    mu.reg_write(UC_X86_REG_ESI, AUX)
    mu.reg_write(UC_X86_REG_EDI, DATA)
    before = tuple(mu.reg_read(r) for r in REGS)
    seen = []
    enabled = selected >= (1 if patched else 2) and groups < capacity
    expected_arg = AUX + (0x150 if naval else 0x240)
    def hook(uc, address, size, user):
        if address in (0x11100570 + d, 0x11100650 + d):
            sp = uc.reg_read(UC_X86_REG_ESP)
            seen.append(address == 0x11100650 + d)
            assert sp == STACK - 8 and f.read(sp + 4)[0] == expected_arg
            assert tuple(uc.reg_read(r) for r in REGS) == before
            uc.emu_stop()
    f.run(0x11102DC5 if naval else 0x11101A30, hook)
    assert seen == [enabled], (naval, selected, groups, capacity, seen, enabled)


def creator(pe, base, patched, selected, group_id):
    f = Fixture(pe, base)
    f.write(OBJ, VT)
    f.write(OBJ + 0x28, selected)
    f.write(OBJ + 0x3C, 2, 0, DATA)
    f.write(VT + 0x20, CALLBACK)
    f.write(VT + 0x34, CALLBACK + 0x10)
    f.write(VT + 0x24, CALLBACK + 0x20)
    f.write(STACK, STOP, group_id & 0xFFFFFFFF)
    f.mu.reg_write(UC_X86_REG_ECX, OBJ)
    seen = []
    def hook(uc, address, size, user):
        if CALLBACK <= address <= CALLBACK + 0x20:
            sp = uc.reg_read(UC_X86_REG_ESP)
            seen.append(address - CALLBACK)
            assert uc.reg_read(UC_X86_REG_ECX) == OBJ
            if address == CALLBACK:
                assert f.read(sp + 4, 2) == (OBJ + 0x24, group_id & 0xFFFFFFFF)
                f.ret(8, 0xABCD)
            elif address == CALLBACK + 0x10:
                assert f.read(sp + 4, 4) == (OBJ, group_id, 0xABCD, OBJ + 0x24)
                f.ret(16, 0x12345678)
            else:
                assert f.read(sp + 4, 2) == (OBJ + 0x24, group_id & 0xFFFFFFFF)
                f.ret(8)
    f.run(0x10F89A40, hook)
    active = selected >= (1 if patched else 2)
    expected = ([0, 0x20] if group_id == -1 else [0, 0x10, 0x20]) if active else []
    assert seen == expected, (selected, group_id, seen)
    assert f.read(OBJ + 0x40)[0] == int(active and group_id != -1)
    if active and group_id != -1:
        assert f.read(DATA)[0] == 0x12345678  # Actual native10098B40 append.
    f.abi(8)


def retention(pe, base, patched, count, found, index, derived=False):
    f = Fixture(pe, base)
    members = [0x12340000 + 4 * i for i in range(count)]
    target = members[index] if found else 0xDEADBEEF
    f.write(OBJ, VT, MGR, max(count, 1), count, DATA, 7)
    if members:
        f.write(DATA, *members)
    f.write(MGR, MVT)
    f.write(MVT + 0x1C, CALLBACK)
    f.write(MVT + 0x14, CALLBACK + 0x10)
    f.write(MVT + 0x10, CALLBACK + 0x20)
    f.write(VT, CALLBACK + 0x30)
    if derived:
        f.map(target, 0x400)
        f.write(target + 0x318, AUX)
        f.write(AUX + 0x48, AUX + 0x100)
        f.write(AUX + 0x100, AUX + 0x200)
        f.write(AUX + 0x254, CALLBACK + 0x40)
        f.write(OBJ + 0x24, count, AUX + 0x600)
        f.write(OBJ + 0x30, 0xFFFFFFFF)  # No engine group: local vector erase only.
        if members:
            f.write(AUX + 0x600, *[0x56780000 + i for i in range(count)])
    f.write(STACK, STOP, target)
    f.mu.reg_write(UC_X86_REG_ECX, OBJ)
    seen = []
    def hook(uc, address, size, user):
        if CALLBACK <= address <= CALLBACK + 0x40:
            sp = uc.reg_read(UC_X86_REG_ESP)
            seen.append(address - CALLBACK)
            if address == CALLBACK:
                assert uc.reg_read(UC_X86_REG_ECX) == MGR
                assert f.read(sp + 4, 2) == (target, 0xFFFFFFFF)
                f.ret(8)
            elif address == CALLBACK + 0x10:
                assert f.read(sp + 4)[0] == OBJ + 8
                f.ret(4)
            elif address == CALLBACK + 0x20:
                assert f.read(sp + 4)[0] == 7
                f.ret(4)
            elif address == CALLBACK + 0x30:
                assert uc.reg_read(UC_X86_REG_ECX) == OBJ
                assert f.read(sp + 4)[0] == 1
                f.ret(4)
            else:
                assert uc.reg_read(UC_X86_REG_ECX) == AUX + 0x100
                f.ret(0, 0x56780000 + index)
    f.run(0x110E2120 if derived else 0x10F97840, hook)
    remaining = count - int(found)
    destroyed = found and remaining <= (0 if patched else 1)
    expected = ([0] + ([0x10] if remaining == 1 else []) + [0x20, 0x30]) if destroyed else ([0] if found else [])
    if derived and found and not destroyed:
        expected += [0x40]
        assert f.read(OBJ + 0x24)[0] == remaining
        if remaining:
            engine_members = [0x56780000 + i for i in range(count) if i != index]
            assert list(f.read(AUX + 0x600, remaining)) == engine_members
    assert seen == expected, (count, found, seen, expected)
    assert f.mu.reg_read(UC_X86_REG_EAX) == (2 if destroyed else 1 if found else 0)
    assert f.read(OBJ + 0xC)[0] == remaining
    if found and remaining:
        assert list(f.read(DATA, remaining)) == members[:index] + members[index + 1:]
    f.abi(8)


def renderer(pe, base, patched, count, compact):
    f = Fixture(pe, base)
    d, mu = f.delta, f.mu
    # One pointer in the last four bytes of a mapped page: array[1] is unmapped.
    cards = 0x23000FFC
    f.map(cards, 4)
    f.write(cards, AUX)
    f.write(DATA, 1, count, cards)
    f.write(OBJ + 4, MGR)
    f.write(OBJ + 0x44, MGR)
    f.write(STACK, STOP, DATA, compact)
    mu.reg_write(UC_X86_REG_ECX, OBJ)
    # Load the actual RX trampoline page referenced by the built JMP.
    if patched:
        hook_bytes = f.image[0x112234A0 - PREFERRED:0x112234A5 - PREFERRED]
        assert hook_bytes[0] == 0xE9
        target = 0x112234A5 + struct.unpack('<i', hook_bytes[1:])[0]
        f.code(target, 16)
    seen = []
    paths = []
    before_hook = []
    def hook(uc, address, size, user):
        if address == 0x10F9C360 + d:
            sp = uc.reg_read(UC_X86_REG_ESP)
            assert uc.reg_read(UC_X86_REG_ECX) == MGR
            seen.append(f.read(sp + 4)[0])
            f.ret(4)
        elif address == 0x112234A0 + d:
            before_hook.append((tuple(uc.reg_read(r) for r in REGS), uc.reg_read(UC_X86_REG_ESP)))
        elif address == 0x112234A5 + d:
            assert (tuple(uc.reg_read(r) for r in REGS), uc.reg_read(UC_X86_REG_ESP)) == before_hook[-1]
            expected_zf = (count == 1 or compact == 0) if patched else compact == 0
            assert bool(uc.reg_read(UC_X86_REG_EFLAGS) & 0x40) == expected_zf
        elif address in (0x112234BD + d, 0x11223584 + d):
            paths.append('simple' if address == 0x112234BD + d else 'compact')
            assert uc.reg_read(UC_X86_REG_ESP) == STACK - 0x60
            # Stop at actual dispatch before UI geometry/renderer callbacks.
            uc.emu_stop()
    f.run(0x11223470, hook)
    visible = count >= (1 if patched else 2)
    assert seen == [int(visible)]
    assert paths == ([('simple' if (compact == 0 or patched and count == 1) else 'compact')] if visible else [])
    if not visible:
        f.abi(12)


def exercise(path, patched):
    counts = Counter()
    for base in (0x10000000, 0x53000000, 0x6C000000):
        # Fresh PE per base because pefile relocation mutates internal image.
        pe = pefile.PE(str(path))
        for naval in (False, True):
            for selected in (0, 1, 2, 20):
                for groups, capacity in ((0, 0), (0, 1), (1, 1), (0, 2), (1, 2), (19, 20), (20, 20)):
                    gate(pe, base, patched, naval, selected, groups, capacity)
                    counts['ui_capacity'] += 1
        for selected in (0, 1, 2, 20):
            for group_id in (-1, 7):
                creator(pe, base, patched, selected, group_id)
                counts['creator'] += 1
        for count in (0, 1, 2, 3, 20):
            for derived in (False, True):
                retention(pe, base, patched, count, False, 0, derived)
                counts['retention'] += 1
            if count:
                for index in sorted(set((0, count - 1))):
                    for derived in (False, True):
                        retention(pe, base, patched, count, True, index, derived)
                        counts['retention'] += 1
        for count in (0, 1, 2, 3):
            for compact in (0, 1):
                renderer(pe, base, patched, count, compact)
                counts['renderer_dispatch'] += 1
    return dict(counts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vanilla', type=Path, default=VANILLA)
    ap.add_argument('--dll', type=Path, required=True)
    args = ap.parse_args()
    old, new = pefile.PE(str(args.vanilla)), pefile.PE(str(args.dll))
    assert old.OPTIONAL_HEADER.ImageBase == new.OPTIONAL_HEADER.ImageBase == PREFERRED
    for address, expected in SITES.items():
        assert old.get_data(address - PREFERRED, 1) == bytes([expected]), hex(address)
        assert new.get_data(address - PREFERRED, 1) == b'\0', hex(address)
    assert old.get_data(0x10F9787B - PREFERRED, 8) == bytes.fromhex('837f0c01772d7509')
    assert new.get_data(0x10F9787B - PREFERRED, 8) == bytes.fromhex('837f0c01732d7509')
    assert old.get_data(0x112234A0 - PREFERRED, 5) == bytes.fromhex('807c246800')
    hook = new.get_data(0x112234A0 - PREFERRED, 5)
    assert hook[0] == 0xE9
    target = 0x112234A5 + struct.unpack('<i', hook[1:])[0]
    section = next(s for s in new.sections if s.VirtualAddress <= target - PREFERRED < s.VirtualAddress + s.Misc_VirtualSize)
    assert section.Name.rstrip(b'\0') == b'.ubfix'
    assert section.Characteristics & 0xE0000000 == 0x60000000, 'Trampoline must be RX, not writable'
    for label, path, patched in [('vanilla', args.vanilla, False), ('built', args.dll, True)]:
        result = exercise(path, patched)
        print('PASS', label, sum(result.values()), 'actual-code cases at three ASLR bases:', result)
    print('LIMIT: controlled UI virtual callbacks; renderer tested through dispatch, no gameplay/visual assertion')


if __name__ == '__main__':
    main()




