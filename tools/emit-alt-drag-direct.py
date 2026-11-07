"""Direct x86 byte recipe, independently traced from the permitted OG DLL.

This does not invoke a compiler/assembler or import another project's code.
Opcode blocks below are handwritten. Native calls retain OG's own projection,
preview, selection serialization and movement implementations. CE exports were
used only to identify the gesture's behaviour, not for bytes/layouts/ABIs.

Produces a DISABLED experimental recipe and a workspace inspection image only.
Never installs, launches the game, signs packages or updates version metadata.
"""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('C:/Program Files (x86)/Steam/steamapps/common/Total War SHOGUN 2')
BASE_HASH = 'a306512f3e571266f810392285b80caa1d15d525ddf9576b229b2fd9a669147d'
OG_HASH = '022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5'
CODE = 0x11D8A000
STATE = 0x11D8D000

# Offsets in new private gesture storage, NOT offsets transplanted from CE.
OWNER, MODEL, SIDE = 0, 4, 8
AX, AZ, TX, TZ, PX, PZ = 0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20
LASTX, ANGLE, CTRL, VALID, CANCEL = 0x24, 0x28, 0x2C, 0x30, 0x34
STARTX, STARTY, MOVED, COS, SIN = 0x38, 0x3C, 0x40, 0x44, 0x48
WORLD, RECT, SNAP = 0x4C, 0x60, 0x90
BG, BU, CG, CU, EMPTY, FINDER, TMP = 0xD4, 0xE0, 0xEC, 0xF8, 0x104, 0x148, 0x18C
MINX, MINZ, MAXX, MAXZ = 0x1A0, 0x1A4, 0x1A8, 0x1AC
PACKET, SINGLE, PROXY = 0x1C0, 0x238, 0x23C
PROJECTED = 0x244
MOUSEX, MOUSEY, SENT = 0x240, 0x248, 0x24C
ABS, HALF, TURN, TOLERANCE = 0x250, 0x260, 0x264, 0x268
DRAG_THRESHOLD, ROTATION_SCALE = 0x26C, 0x270
OG_UI_MOUSE_X = 0x11BBEAB0
# User-approved read-only CE original-DLL reference: 182352CA8 = these float bits.
# Applied to OG's own UI-coordinate stream, not normalized hardware coordinates.
CE_ROTATION_RATE_BITS = 0x42D09B89


def u32(x):
    return struct.pack('<I', x & 0xFFFFFFFF)


class Bytes:
    def __init__(self):
        self.data = bytearray()
        self.labels = {}
        self.fixups = []
        self.notes = []

    @property
    def va(self):
        return CODE + len(self.data)

    def label(self, name):
        assert name not in self.labels
        self.labels[name] = self.va

    def raw(self, h, note=''):
        b = bytes.fromhex(h) if isinstance(h, str) else h
        if note:
            self.notes.append((self.va, len(b), note))
        self.data.extend(b)

    def branch(self, opcode, target):
        self.raw(opcode)
        self.fixups.append((len(self.data), target))
        self.raw(b'\0' * 4)

    def call(self, target):
        self.branch('e8', target)

    def jmp(self, target):
        self.branch('e9', target)

    def jcc(self, cc, target):
        self.branch('0f ' + cc, target)

    def mem(self, opcode, displacement):
        self.raw(opcode)
        self.raw(u32(displacement))

    def lea(self, reg, offset):
        self.mem({'eax': '8d 85', 'ecx': '8d 8d', 'edx': '8d 95',
                  'esi': '8d b5', 'edi': '8d bd'}[reg], offset)

    def load(self, reg, offset):
        self.mem({'eax': '8b 85', 'ecx': '8b 8d', 'edx': '8b 95',
                  'esi': '8b b5', 'edi': '8b bd'}[reg], offset)

    def store(self, reg, offset):
        self.mem({'eax': '89 85', 'ecx': '89 8d', 'edx': '89 95',
                  'esi': '89 b5', 'edi': '89 bd', 'ebx': '89 9d'}[reg], offset)

    def imm(self, offset, value):
        self.mem('c7 85', offset)
        self.raw(u32(value))

    def xmm_load(self, reg, offset):
        self.raw(bytes([0xF3, 0x0F, 0x10, 0x85 | (reg << 3)]) + u32(offset))

    def xmm_store(self, reg, offset):
        self.raw(bytes([0xF3, 0x0F, 0x11, 0x85 | (reg << 3)]) + u32(offset))

    def xmm_mem(self, op, reg, offset):
        self.raw(bytes([0xF3, 0x0F, op, 0x85 | (reg << 3)]) + u32(offset))

    def xmm_reg(self, op, dest, source):
        self.raw(bytes([0xF3, 0x0F, op, 0xC0 | (dest << 3) | source]))

    def setup(self):
        # PUSHFD/PUSHAD first: original ECX is [ESP+24], args start +40.
        self.raw('9c 60 e8 00 00 00 00 5d', 'save flags/registers; obtain EIP')
        return_eip = self.va - 1
        self.raw('81 ed')
        self.raw(u32(return_eip - STATE))
        self.raw('8b 5c 24 18', 'EBX = original ECX; EBP = private gesture state')

    def finish(self):
        for at, target in self.fixups:
            dest = self.labels[target] if isinstance(target, str) else target
            self.data[at:at + 4] = u32(dest - (CODE + at + 4))
        return bytes(self.data)


def emit():
    e = Bytes()

    # Entry detours preserve normal behaviour by replaying exact OG prologues.
    e.label('down')
    e.setup()
    e.call('start')
    e.raw('84 c0')
    e.jcc('84', 'down_original')
    e.raw('61 9d c3')
    e.label('down_original')
    e.raw('61 9d 83 ec 68 53 55')
    e.jmp(0x110F81E5)

    e.label('up')
    e.setup()
    e.mem('39 9d', OWNER)
    e.jcc('85', 'up_original')
    e.raw('83 7c 24 28 00')  # original cancel argument, after saved flags/regs
    e.jcc('85', 'up_cleanup')
    e.call('validate_selection')
    e.raw('84 c0')
    e.jcc('84', 'up_cleanup')
    e.call('preview_active')
    e.mem('83 bd', VALID)
    e.raw('00')
    e.jcc('84', 'up_cleanup')
    e.mem('83 bd', MOVED)
    e.raw('00')
    e.jcc('84', 'up_cleanup')
    e.call('send_targets')
    e.label('up_cleanup')
    e.call('clear_ui')
    e.call('free_state')
    e.raw('61 9d c2 04 00')
    e.label('up_original')
    e.raw('61 9d 53 8b d9 56 57')
    e.jmp(0x110F83E5)

    e.label('preview')
    e.setup()
    e.mem('83 bd', OWNER)
    e.raw('00')
    e.jcc('84', 'preview_original')
    e.mem('39 9d', OWNER)
    e.jcc('85', 'preview_new_battle')
    e.raw('8b 83 10 01 00 00 8b 40 08')
    e.mem('39 85', MODEL)
    e.jcc('85', 'preview_new_battle')
    e.call('validate_selection')
    e.raw('84 c0')
    e.jcc('85', 'preview_go')
    # Selection changed while left remains held: consume its eventual release.
    e.imm(CANCEL, 1)
    e.call('clear_ui')
    e.raw('61 9d c3')
    e.label('preview_new_battle')
    # Current UI may belong to a new battle; never dereference the old owner.
    e.call('free_state')
    e.jmp('preview_original')
    e.label('preview_go')
    e.call('preview_active')
    e.raw('61 9d c3')
    e.label('preview_original')
    e.raw('61 9d 83 ec 38 55 8b e9')
    e.jmp(0x11101E16)

    e.label('mouse')
    e.setup()
    e.raw('83 eb 18')  # callback ECX is full UI + 0x18 in OG
    e.mem('39 9d', OWNER)
    e.jcc('85', 'mouse_original')
    e.raw('8b 44 24 28 8b 00 83 f8 05')
    e.jcc('84', 'mouse_cancel')
    e.raw('83 f8 06')
    e.jcc('84', 'mouse_cancel')
    e.raw('83 f8 04')
    e.jcc('85', 'mouse_original')
    e.mem('83 bd', CANCEL)
    e.raw('00')
    e.jcc('84', 'mouse_original')
    e.jmp('mouse_consume')
    e.label('mouse_cancel')
    e.imm(CANCEL, 1)
    e.call('clear_ui')
    e.label('mouse_consume')
    e.raw('61 9d c2 0c 00')
    e.label('mouse_original')
    e.raw('61 9d 81 ec 8c 00 00 00')
    e.jmp(0x110FB986)

    # Hook AFTER OG's CMP at AB33. Replay preserves its flags for native JNE.
    e.label('key')
    e.setup()
    e.raw('83 eb 18')
    e.mem('39 9d', OWNER)
    e.jcc('85', 'key_original')
    e.raw('8b 4c 24 34 6a 00', 'live keyboard argument; Escape physical key')
    e.call(0x10BD12A0)
    e.raw('84 c0')
    e.jcc('84', 'key_original')
    e.imm(CANCEL, 1)
    e.label('key_original')
    e.raw('61 9d 53 8b 5c 24 10')
    e.jmp(0x110FAB3F)

    e.label('clear_ui')
    e.raw('c6 83 98 05 00 00 00 c6 83 64 01 00 00 00')
    e.raw('8d 8b cc 0c 00 00')
    e.call(0x110EEC30)
    e.raw('c3')

    e.label('free_state')
    for v in (BG, BU, CG, CU):
        e.load('eax', v + 8)
        e.raw('85 c0')
        e.jcc('84', f'free_skip_{v}')
        e.raw('50')
        e.call(0x100F04D0)
        e.raw('83 c4 04')
        e.label(f'free_skip_{v}')
    e.lea('ecx', SNAP)
    e.call(0x101D10F0)
    e.lea('edi', 0)
    e.raw('33 c0 b9 94 00 00 00 fc f3 ab c3', 'zero owned state; constants start at +250')

    e.label('ground')
    e.raw('8b 8b 30 01 00 00 85 c9')
    e.jcc('84', 'false')
    e.raw('8b 49 0c 85 c9')
    e.jcc('84', 'false')
    e.lea('eax', WORLD)
    e.raw('50')
    e.call(0x10399F80)
    e.raw('b0 01 c3')

    e.label('read_mouse')
    # 10BD4A10 writes normalized float coordinates to this native mouse state.
    # UI+550h/+554h are also floats, not integer pixel counters.
    e.call(0x10BD4D70)
    e.raw('f3 0f 10 00 f3 0f 10 48 04')
    e.xmm_store(0, MOUSEX)
    e.xmm_store(1, MOUSEY)
    e.raw('c3')

    e.label('alt_held')
    e.raw('6a 37')
    e.call(0x10BD12A0)
    e.raw('84 c0')
    e.jcc('85', 'modifier_true')
    e.raw('6a 74')
    e.call(0x10BD12A0)
    e.raw('c3')
    e.label('ctrl_alt_held')
    e.raw('6a 1c')
    e.call(0x10BD12A0)
    e.raw('84 c0')
    e.jcc('85', 'ctrl_held_check_alt')
    e.raw('6a 69')
    e.call(0x10BD12A0)
    e.raw('84 c0')
    e.jcc('84', 'false')
    e.label('ctrl_held_check_alt')
    e.jmp('alt_held')
    e.label('modifier_true')
    e.raw('b0 01 c3')

    e.label('validate_selection')
    e.mem('39 9d', OWNER)
    e.jcc('85', 'false')
    e.raw('8b 83 10 01 00 00 85 c0')
    e.jcc('84', 'false')
    e.raw('8b 40 08')
    e.mem('39 85', MODEL)
    e.jcc('85', 'false')
    e.raw('8b 83 b4 05 00 00 85 c0')
    e.jcc('84', 'false')
    e.raw('05 b0 00 00 00')
    # Compare pointer sequences, not mutable UI vector storage addresses.
    for off in (4, 0x10):
        e.raw('50')
        e.raw(bytes([0x8B, 0x48, off + 4]))
        e.mem('3b 8d', SNAP + off + 4)
        e.jcc('85', f'validate_bad_pop_{off}')
        e.raw(bytes([0x8B, 0x70, off + 8]))
        e.load('edi', SNAP + off + 8)
        e.raw('fc f3 a7 58')
        e.jcc('85', 'false')
        e.jmp(f'validate_next_{off}')
        e.label(f'validate_bad_pop_{off}')
        e.raw('58')
        e.jmp('false')
        e.label(f'validate_next_{off}')
    for off in (0x20, 0x2C, 0x34, 0x3C):
        e.raw(bytes([0x83, 0x78, off, 0]))
        e.jcc('85', 'false')
    e.raw('b0 01 c3')

    e.label('start')
    e.call('alt_held')
    e.raw('84 c0')
    e.jcc('84', 'false')
    e.raw('80 bb 65 01 00 00 00')
    e.jcc('85', 'false')
    e.raw('8b 83 40 0d 00 00 85 c0')
    e.jcc('84', 'start_no_script_controller')
    e.raw('83 78 18 00')
    e.jcc('85', 'false')
    e.label('start_no_script_controller')
    e.raw('8b 83 10 01 00 00 80 b8 3c 83 02 00 00')
    e.jcc('84', 'start_native_preview_allowed')
    e.raw('83 b8 40 80 02 00 01')
    e.jcc('84', 'false')
    e.label('start_native_preview_allowed')
    e.raw('8d 8b 0c 01 00 00')
    e.call(0x102ACD20)
    e.raw('83 f8 05')
    e.jcc('85', 'false')
    e.call('ground')
    e.raw('84 c0')
    e.jcc('84', 'false')
    e.raw('8b b3 b4 05 00 00 85 f6')
    e.jcc('84', 'false')
    e.raw('81 c6 b0 00 00 00 8b 46 08 03 46 14 85 c0')
    e.jcc('84', 'false')
    for off in (0x20, 0x2C, 0x34, 0x3C):
        e.raw(bytes([0x83, 0x7E, off, 0]))
        e.jcc('85', 'false')
    # An abandoned gesture is freed before replacing its snapshot.
    e.raw('56')
    e.call('free_state')
    e.raw('5e')
    e.store('ebx', OWNER)
    e.raw('8b 83 10 01 00 00 8b 40 08')
    e.store('eax', MODEL)
    # Actual OG bytes: ECX=selection, [ESP+4]=battle model, RET 4.
    # Ghidra's inferred declaration omits this stack argument.
    e.raw('50 8b ce')
    e.call(0x10436690)
    e.raw('84 c0')
    e.jcc('84', 'start_failed')
    e.raw('56')
    e.lea('ecx', SNAP)
    e.call(0x101CE380)
    e.lea('ecx', SNAP)
    e.call(0x10429DD0)
    e.store('eax', SIDE)
    e.lea('eax', BU)
    e.raw('50')
    e.lea('eax', BG)
    e.raw('50 6a 00')
    e.load('eax', MODEL)
    e.raw('50')
    e.lea('ecx', SNAP)
    e.call(0x1042DFD0)
    e.load('eax', BG + 4)
    e.mem('03 85', BU + 4)
    e.raw('85 c0')
    e.jcc('84', 'start_failed')
    e.imm(MINX, 0x7F800000)
    e.imm(MINZ, 0x7F800000)
    e.imm(MAXX, 0xFF800000)
    e.imm(MAXZ, 0xFF800000)
    e.lea('ecx', BG)
    e.call('bounds')
    e.lea('ecx', BU)
    e.call('bounds')
    for lo, hi, pivot in ((MINX, MAXX, PX), (MINZ, MAXZ, PZ)):
        e.xmm_load(0, lo)
        e.xmm_mem(0x58, 0, hi)
        e.xmm_mem(0x59, 0, HALF)
        e.xmm_store(0, pivot)
    e.call('ground')
    e.raw('84 c0')
    e.jcc('84', 'start_failed')
    for src, dest in ((WORLD, AX), (WORLD + 8, AZ)):
        e.load('eax', src)
        e.store('eax', dest)
    e.call('read_mouse')
    e.load('eax', MOUSEX)
    e.store('eax', STARTX)
    e.lea('eax', OG_UI_MOUSE_X - STATE)
    e.raw('8b 00')
    e.store('eax', LASTX)
    e.load('eax', MOUSEY)
    e.store('eax', STARTY)
    # Ctrl+Alt may already be held when the left-button gesture starts.
    e.call('ctrl_alt_held')
    e.raw('0f b6 c0')
    e.store('eax', CTRL)
    # OG native position finder defaults, as constructed in 1042DFD0.
    for off, val in ((8, 0x40A00000), (0x24, 0xBF800000), (0x34, 1), (0x38, 1)):
        e.imm(FINDER + off, val)
    e.lea('eax', 0x11A63748 - STATE)
    e.raw('0f b7 00')
    e.store('eax', FINDER + 0x20)
    e.raw('b0 01 c3')
    e.label('start_failed')
    e.call('free_state')
    e.label('false')
    e.raw('32 c0 c3')

    e.label('bounds')
    e.raw('8b 71 08 8b 79 04 c1 e7 05 03 fe')
    e.label('bounds_loop')
    e.raw('3b f7')
    e.jcc('84', 'bounds_end')
    e.raw('8b 0e 8b 01')
    e.lea('edx', RECT)
    e.raw('52 ff 50 0c', 'native ordered footprint rectangle, same ABI used by 1041CDF0')
    # centre = origin + half depth * depth-axis; extents encompass all corners.
    e.raw('f3 0f 10 40 1c f3 0f 59 40 10 f3 0f 10 48 20 f3 0f 59 48 10')
    e.raw('0f 28 d0 0f 28 d9')
    e.xmm_mem(0x59, 0, HALF)
    e.xmm_mem(0x59, 1, HALF)
    e.raw('f3 0f 58 00 f3 0f 58 48 04')
    e.mem('0f 54 95', ABS)
    e.mem('0f 54 9d', ABS)
    e.raw('f3 0f 10 60 14 f3 0f 59 60 0c f3 0f 10 68 18 f3 0f 59 68 0c')
    e.mem('0f 54 a5', ABS)
    e.mem('0f 54 ad', ABS)
    e.xmm_reg(0x58, 2, 4)
    e.xmm_reg(0x58, 3, 5)
    e.xmm_mem(0x59, 2, HALF)
    e.xmm_mem(0x59, 3, HALF)
    e.raw('0f 28 e0 0f 28 e9')
    e.xmm_reg(0x5C, 0, 2)
    e.xmm_reg(0x5C, 1, 3)
    e.xmm_reg(0x58, 4, 2)
    e.xmm_reg(0x58, 5, 3)
    for reg, op, off in ((0, 0x5D, MINX), (1, 0x5D, MINZ), (4, 0x5F, MAXX), (5, 0x5F, MAXZ)):
        e.xmm_mem(op, reg, off)
        e.xmm_store(reg, off)
    e.raw('83 c6 20')
    e.jmp('bounds_loop')
    e.label('bounds_end')
    e.raw('c3')

    e.label('preview_active')
    e.call('clear_ui')
    e.imm(VALID, 0)
    e.mem('83 bd', CANCEL)
    e.raw('00')
    e.jcc('85', 'preview_end')
    # Existing OG USER32 IAT slot; compare the same HWND used by 10BD12A0.
    e.lea('eax', 0x115A15E0 - STATE)
    e.raw('ff 10')
    e.lea('edx', 0x11B30F48 - STATE)
    e.raw('3b 02')
    e.jcc('85', 'preview_cancel')
    e.call(0x10BD12D0)
    e.raw('84 c0')
    e.jcc('84', 'preview_cancel')
    e.raw('80 bb 65 01 00 00 00')
    e.jcc('85', 'preview_cancel')
    e.call('ground')
    e.raw('84 c0')
    e.jcc('84', 'preview_end')
    e.call('read_mouse')
    for current, saved in ((MOUSEX, STARTX), (MOUSEY, STARTY)):
        e.xmm_load(0, current)
        e.xmm_mem(0x5C, 0, saved)
        e.mem('0f 54 85', ABS)
        e.mem('0f 2e 85', DRAG_THRESHOLD)
        e.jcc('82', f'no_move_{saved}')
        e.imm(MOVED, 1)
        e.label(f'no_move_{saved}')
    e.call('ctrl_alt_held')
    e.raw('84 c0')
    e.jcc('84', 'translate')
    e.mem('83 bd', CTRL)
    e.raw('00')
    e.jcc('84', 'rotate_enter')
    e.label('rotate_ce_math')
    e.lea('eax', OG_UI_MOUSE_X - STATE)
    e.raw('f3 0f 10 00')
    e.xmm_mem(0x5C, 0, LASTX)
    e.xmm_mem(0x59, 0, ROTATION_SCALE)
    # Match CE's angle conversion: round to nearest, ties away from zero.
    e.raw('0f 57 c9 0f 2f c1')
    e.jcc('86', 'rotate_round_negative')
    e.xmm_mem(0x58, 0, HALF)
    e.jmp('rotate_round_done')
    e.label('rotate_round_negative')
    e.xmm_mem(0x5C, 0, HALF)
    e.label('rotate_round_done')
    e.raw('f3 0f 2c c0')
    e.mem('66 01 85', ANGLE)
    e.label('rotate_enter')
    e.imm(CTRL, 1)
    e.jmp('gesture_updated')
    e.label('translate')
    e.mem('83 bd', CTRL)
    e.raw('00')
    e.jcc('84', 'translate_plain')
    for world, offset, anchor in ((WORLD, TX, AX), (WORLD + 8, TZ, AZ)):
        e.xmm_load(0, world)
        e.xmm_mem(0x5C, 0, offset)
        e.xmm_store(0, anchor)
    e.imm(CTRL, 0)
    e.label('translate_plain')
    for world, anchor, offset in ((WORLD, AX, TX), (WORLD + 8, AZ, TZ)):
        e.xmm_load(0, world)
        e.xmm_mem(0x5C, 0, anchor)
        e.xmm_store(0, offset)
    e.label('gesture_updated')
    e.lea('eax', OG_UI_MOUSE_X - STATE)
    e.raw('8b 00')
    e.store('eax', LASTX)
    e.mem('0f bf 85', ANGLE)
    e.raw('50 db 04 24')
    e.mem('d8 8d', TURN)
    e.raw('d9 fb')
    e.mem('d9 9d', COS)
    e.mem('d9 9d', SIN)
    e.raw('83 c4 04')
    e.imm(PROJECTED, 1)
    for src, dest in ((BG, CG), (BU, CU)):
        e.lea('eax', src)
        e.raw('50')
        e.lea('ecx', dest)
        e.call(0x10419B40)
        e.lea('ecx', dest)
        e.call('transform')
    e.mem('83 bd', PROJECTED)
    e.raw('00')
    e.jcc('84', 'preview_end')
    # Initialize OG's own proxy with an empty selection, then populate it with
    # the transformed target vectors through the unchanged native expansion.
    e.raw('6a 48')
    e.call(0x100F7440)
    e.raw('83 c4 04 85 c0')
    e.jcc('84', 'preview_end')
    e.store('eax', PROXY)
    e.raw('8b c8 6a 00 6a 00')
    e.lea('edx', EMPTY)
    e.raw('52')
    e.load('edx', MODEL)
    e.raw('52')
    e.call(0x10264600)
    e.load('edx', SIDE)
    e.raw('89 10')
    e.lea('ecx', SNAP)
    e.call(0x10420ED0)
    e.load('esi', PROXY)
    e.raw('88 46 15')
    e.lea('eax', CU)
    e.raw('50')
    e.lea('eax', CG)
    e.raw('50 8b ce')
    e.call(0x10295A90)
    e.raw('8b ce')
    e.call(0x1029A6F0)
    e.raw('88 46 12 8b ce')
    e.load('eax', MODEL)
    e.raw('50')
    e.call(0x102E5C30)
    e.raw('84 c0')
    e.jcc('84', 'preview_invalid')
    e.raw('56 8d 8b cc 0c 00 00')
    e.call(0x10090B10)
    e.raw('c6 83 98 05 00 00 01')
    e.imm(VALID, 1)
    e.jmp('preview_end')
    e.label('preview_invalid')
    e.raw('8d 4e 30')
    e.call(0x101CF710)
    e.raw('8d 4e 18')
    e.call(0x101CF760)
    e.raw('6a 48 56')
    e.call(0x114FBC77)
    e.raw('83 c4 08')
    e.label('preview_end')
    e.raw('c3')
    e.label('preview_cancel')
    e.imm(CANCEL, 1)
    e.raw('c3')

    e.label('transform')
    e.raw('8b 71 08 8b 79 04 c1 e7 05 03 fe')
    e.label('transform_loop')
    e.raw('3b f7')
    e.jcc('84', 'transform_end')
    e.lea('eax', TMP)
    e.raw('50 8d 4e 04')
    e.call(0x10399F80)
    e.xmm_load(0, TMP)
    e.xmm_load(1, TMP + 8)
    e.xmm_mem(0x5C, 0, PX)
    e.xmm_mem(0x5C, 1, PZ)
    e.raw('0f 28 d0 0f 28 d9')
    e.xmm_mem(0x59, 0, COS)
    e.xmm_mem(0x59, 1, COS)
    e.xmm_mem(0x59, 2, SIN)
    e.xmm_mem(0x59, 3, SIN)
    e.xmm_reg(0x58, 0, 3)
    e.xmm_reg(0x5C, 1, 2)
    for reg, pivot, offset, finder in ((0, PX, TX, FINDER), (1, PZ, TZ, FINDER + 4)):
        e.xmm_mem(0x58, reg, pivot)
        e.xmm_mem(0x58, reg, offset)
        e.xmm_store(reg, finder)
        e.raw(bytes([0x66, 0x0F, 0x7E, 0xC0 | (reg << 3)]))
        e.raw('25 00 00 80 7f 3d 00 00 80 7f')
        e.jcc('84', 'transform_bad')
    e.mem('66 8b 85', ANGLE)
    e.raw('66 01 46 18 6a 01')
    e.lea('eax', FINDER)
    e.raw('50 8d 46 04 50')
    e.load('eax', MODEL)
    e.raw('8b 88 b8 00 00 00')
    e.call(0x1037B430)
    # A projected/clamped target must not silently deform the captured block.
    e.lea('eax', TMP)
    e.raw('50 8d 4e 04')
    e.call(0x10399F80)
    for world, target in ((TMP, FINDER), (TMP + 8, FINDER + 4)):
        e.xmm_load(0, world)
        e.xmm_mem(0x5C, 0, target)
        e.mem('0f 54 85', ABS)
        e.mem('0f 2e 85', TOLERANCE)
        e.jcc('87', 'transform_bad')
        e.jcc('8a', 'transform_bad')
    e.raw('83 c6 20')
    e.jmp('transform_loop')
    e.label('transform_end')
    e.raw('c3')
    e.label('transform_bad')
    e.imm(PROJECTED, 0)
    e.raw('c3')

    e.label('send_targets')
    e.imm(SENT, 0)
    # Native queue copies the packet synchronously through 102E6F00.
    for vec, resolver, voff in ((CG, 0x1047ED90, 8), (CU, 0x1047ECA0, 0x14)):
        e.load('esi', vec + 8)
        e.load('edi', vec + 4)
        e.raw('c1 e7 05 03 fe 57')
        e.label(f'send_loop_{vec}')
        e.raw('3b 34 24')
        e.jcc('84', f'send_end_{vec}')
        e.raw('8b ce')
        e.call(resolver)
        e.raw('85 c0')
        e.jcc('84', f'send_next_{vec}')
        e.store('eax', SINGLE)
        e.raw('56')
        e.lea('edi', PACKET)
        e.raw('33 c0 b9 1d 00 00 00 fc f3 ab')
        e.lea('eax', 0x115CFFDC - STATE)
        e.store('eax', PACKET)
        e.lea('eax', 0x115C4DA0 - STATE)
        e.store('eax', PACKET + 4)
        e.imm(PACKET + voff, 1)
        e.imm(PACKET + voff + 4, 1)
        e.lea('eax', SINGLE)
        e.store('eax', PACKET + voff + 8)
        e.lea('edi', PACKET + 0x48)
        e.raw('83 c6 04 b9 05 00 00 00 fc f3 a5 5e')
        e.raw('0f b7 46 18')
        e.store('eax', PACKET + 0x5C)
        e.raw('8b 46 1c')
        e.store('eax', PACKET + 0x60)
        e.raw('0f b6 83 8c 05 00 00')
        e.store('eax', PACKET + 0x70)
        e.imm(PACKET + 0x6C, 9)
        e.lea('eax', PACKET)
        e.raw('50 8b 83 10 01 00 00 8b 88 48 80 02 00')
        e.call(0x1023D220)
        e.raw('84 c0')
        e.jcc('84', f'send_next_{vec}')
        e.mem('ff 85', SENT)
        e.label(f'send_next_{vec}')
        e.raw('83 c6 20')
        e.jmp(f'send_loop_{vec}')
        e.label(f'send_end_{vec}')
        e.raw('58')
    e.mem('83 bd', SENT)
    e.raw('00')
    e.jcc('84', 'send_done')
    e.raw('6a 00 6a 00')
    e.call('movement_feedback')
    e.label('send_done')
    e.raw('c3')

    e.label('movement_feedback')
    # Re-enter the EXACT native regular-movement feedback tail. Its native
    # frame is F4h locals plus saved EBX/EBP/ESI/EDI; epilogue ends RET 8.
    # EBX there is the UI input context (full UI+10Ch), whose +4 is battle view.
    # The tail creates its own request and plays event 12Eh once, unchanged.
    e.raw('81 ec f4 00 00 00 53 55 56 57 81 c3 0c 01 00 00')
    e.jmp(0x102E846B)
    code = e.finish()
    assert len(code) < STATE - CODE
    return e, code


def main():
    original = (GAME / 'empire.retail.dll').read_bytes()
    live = (GAME / 'UltimatePatch/empire.retail.dll').read_bytes()
    if hashlib.sha256(live).hexdigest() == BASE_HASH:
        baseline = live
    else:
        state = json.loads((GAME / 'UltimatePatch/install-state.json').read_text())
        overlay = state['localOverlay']
        assert overlay['id'] == 'alt-drag-direct-x86'
        assert overlay['baseEngineSha256'] == BASE_HASH
        assert overlay['engineSha256'] == hashlib.sha256(live).hexdigest(), 'Unrecognized live change'
        baseline = (ROOT / 'build/backups/0.1.45-before-alt-drag-direct/UltimatePatch/empire.retail.dll').read_bytes()
    assert hashlib.sha256(original).hexdigest() == OG_HASH, 'OG source hash mismatch'
    assert hashlib.sha256(baseline).hexdigest() == BASE_HASH, 'Verified baseline reference changed'
    pe = struct.unpack_from('<I', baseline, 60)[0]
    opt = pe + 24
    table = opt + struct.unpack_from('<H', baseline, pe + 20)[0]
    count = struct.unpack_from('<H', baseline, pe + 6)[0]
    sections = []
    for i in range(count):
        pos = table + 40 * i
        name = baseline[pos:pos + 8].rstrip(b'\0').decode()
        vs, rva, raw, offset = struct.unpack_from('<IIII', baseline, pos + 8)
        sections.append((name, pos, vs, rva, raw, offset))
    cave = next(s for s in sections if s[0] == '.ubfix')
    _, header, _, cave_rva, old_raw, cave_file = cave
    assert cave_rva == 0x1D88000 and cave_file + old_raw == len(baseline)

    def offset(va):
        r = va - 0x10000000
        for _, _, _, rv, size, off in sections:
            if rv <= r < rv + size:
                return off + r - rv
        raise ValueError(hex(va))

    e, code = emit()
    writes = []
    def add(off, data, note):
        assert off + len(data) <= len(baseline)
        writes.append({'offset': hex(off), 'expect': baseline[off:off + len(data)].hex(' '),
                       'bytes': data.hex(' '), 'note': note})

    hooks = ((0x110F81E0, '83 ec 68 53 55', 'down'),
             (0x110F83E0, '53 8b d9 56 57', 'up'),
             (0x11101E10, '83 ec 38 55 8b e9', 'preview'),
             (0x110FB980, '81 ec 8c 00 00 00', 'mouse'),
             (0x110FAB3A, '53 8b 5c 24 10', 'key'))
    for va, expected, label in hooks:
        before = bytes.fromhex(expected)
        at = offset(va)
        assert baseline[at:at + len(before)] == before, f'Guard mismatch {va:x}'
        assert original[at:at + len(before)] == before, f'Original guard mismatch {va:x}'
        dest = e.labels[label]
        add(at, b'\xe9' + u32(dest - va - 5) + b'\x90' * (len(before) - 5),
            f'OG x86 {label}; handwritten detour; no CE addresses/layouts')
    add(header + 8, u32(0x6000), 'Extend established .ubfix virtual range')
    add(header + 16, u32(0x6000), 'Extend established .ubfix raw storage')
    add(header + 36, u32(0xE0000020), 'Private gesture state shares the extended patch section')
    add(opt + 56, u32(cave_rva + 0x6000), 'Updated aligned image size')
    appended = bytearray(0x6000 - old_raw)
    code_at = CODE - 0x10000000 - cave_rva - old_raw
    state_at = STATE - 0x10000000 - cave_rva - old_raw
    appended[code_at:code_at + len(code)] = code
    for off in range(ABS, ABS + 16, 4):
        struct.pack_into('<I', appended, state_at + off, 0x7FFFFFFF)
    struct.pack_into('<II', appended, state_at + HALF, 0x3F000000, 0x38C90FDB)
    struct.pack_into('<f', appended, state_at + TOLERANCE, 0.05)
    struct.pack_into('<fI', appended, state_at + DRAG_THRESHOLD, 0.002, CE_ROTATION_RATE_BITS)
    recipe = {'id': 'alt-drag-direct-x86', 'title': 'Direct OG x86 Alt-drag investigation candidate',
              'enabled': False, 'sourceSha256': OG_HASH, 'inputSha256': BASE_HASH,
              'description': 'Handwritten x86 binary recipe. Experimental, not runtime validated or installed.',
              'writes': writes, 'append': {'offset': hex(len(baseline)), 'bytes': appended.hex(' ')}}
    path = ROOT / 'patches/engine/231-alt-drag-direct-x86.json'
    path.write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf-8')
    candidate = bytearray(baseline)
    for w in writes:
        at = int(w['offset'], 16)
        expect, after = bytes.fromhex(w['expect']), bytes.fromhex(w['bytes'])
        assert candidate[at:at + len(expect)] == expect
        candidate[at:at + len(after)] = after
    candidate.extend(appended)
    out = ROOT / 'build/alt-drag-direct-x86-inspection.dll'
    out.write_bytes(candidate)
    receipt = {'status': 'experimental-not-runtime-validated-not-installed',
               'baseline_sha256': BASE_HASH, 'original_sha256': OG_HASH,
               'candidate_sha256': hashlib.sha256(candidate).hexdigest(),
               'candidate': str(out), 'recipe': str(path), 'code_va': hex(CODE),
               'state_va': hex(STATE), 'code_size': len(code),
               'labels': {k: hex(v) for k, v in e.labels.items()},
               'notes': [{'va': hex(a), 'size': n, 'note': t} for a, n, t in e.notes]}
    (ROOT / 'build/alt-drag-direct-x86-receipt.json').write_text(
        json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('status', 'code_size', 'candidate_sha256', 'recipe')}))


if __name__ == '__main__':
    main()
