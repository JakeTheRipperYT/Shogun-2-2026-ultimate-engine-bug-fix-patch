# Naval defender AI — OG test candidate

**0.1.3-naval-test** retains the yari-wall and kneel-fire movement candidates and adds only the naval-defender group correction previously used in CE. Full naval-battle behavior remains unverified.

## CE fix and OG mapping

The CE fix redirects one call in defender factory FUN_180633F40, at 0x180633FD1, from holding-group constructor FUN_1806B8750 to the ordinary naval attack-group constructor FUN_1802B5A80 through a target-selection adapter. The 0x78 allocation remains unchanged. Native attacker factory FUN_180633760 supplies the target-selection rule.

Existing OG pseudocode and original-DLL disassembly establish corresponding functions:

| Role | OG preferred VA |
| --- | --- |
| Defender factory | 0x104D15D0 |
| Holding constructor | 0x10546690 |
| Normal naval attack constructor | 0x101CA070 |
| Existing attacker factory | 0x104D09F0 |
| Defender constructor call changed | 0x104D1636 |

The holding constructor creates two behavior components (0x74 allocations); the attack constructor uses two 0x5EC components plus the shared 0x74 component. Both use the same group base constructor FUN_101CA140. The native attacker and defender factories allocate **0x4C** for their respective naval group objects. The correction preserves that allocation.

The defender factory checks parent+0x64, handles the land-group branch separately, then checks naval availability at parent+0x14. If allocation succeeds it calls the holding constructor, passing ECX=allocation and stack arguments battleRef=parent+4 and parent. The call becomes a relative call to the new adapter at **0x115A0D20**. Allocation, allocation-failure handling and group registration remain original.

## Adapter behavior and calling convention

The 87-byte adapter chooses the same target as the original attacker factory:

1. Default target = parent+0x144.
2. Analyzer = parent+0x30; opponent count at analyzer+0x158, pointer array at +0x15C.
3. Select the first opposing group with nonzero ship count at group+0x48, using its ID at +0x68. If none exists, retain the default.
4. Call normal attack constructor FUN_101CA070 with ECX=original allocation and (battleRef,parent,target).

The holding constructor takes two stack arguments and returns with ret 8. The attack constructor takes three and returns with ret 12. The adapter supplies the third argument, preserves EBX/ESI/EDI and the constructor's EAX result, then uses ret 8 for its original caller. Directly swapping constructors would not preserve this ABI.

All adapter branches and its constructor call are relative; no absolute engine addresses require new relocation entries. The adapter uses previously zero executable padding. Recipe 000 grows .text VirtualSize from 0x159FC3E to 0x159FD77, entirely within existing raw section size 0x159FE00. File length, section count, characteristics and image size are unchanged. Disabled historical siege stubs remain zero; no historical gameplay experiment is enabled.

tools/generate-naval-patch.py reproduces recipes 000 and 070 from the supported original DLL, checks its SHA-256, verifies the original call and empty padding, and writes recipe JSON only. It never changes the input DLL.

## Validation and limits

tools/test-naval-factory.c runs the actual original and patched defender factories in separate uninitialized private DLL mappings at distinct load bases. It controls allocation, constructors and registration with fixtures. The patched factory executes the actual adapter. Twenty-eight scenarios pass (14 per engine), covering inactive factory, no ships, land-only and mixed groups, no opponents, empty opponents, first/later eligible targets, multiple eligible targets, naval/land allocation failures, constructor arguments, return values and registration. This tests factory control flow and adapter ABI, not the behavior of a live attacking fleet.

All ten yari-wall branch checks, 192 kneel-fire eligibility checks, fifteen installer self-tests and signed-package verification pass. Exact delta checks retain prior movement bytes and restrict new writes to the .text size field, one factory call and 87 adapter bytes. Isolated installer reconstruction must match the generated engine hash. No installed game files are changed by these tests.

Supported OG input: Steam build 11306771.

```
Vanilla engine: 022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5
0.1.2 engine:   17df5605f2c34a1538a3184a28f82fcc9f484f455f4112a6ec33d7abe6ac82d2
0.1.3 engine:   29bd5cac6520322a203f7702d21431f99436198e9a46941b0f0704ad66bddd6d
```

## In-game comparison

Compare vanilla/0.1.2 with 0.1.3 using the same naval battle: player attacks, AI defends, with no mods. Record whether the AI leaves its holding behavior and engages without waiting for the player to approach. Repeat with multiple opposing fleets, different ship classes, reinforcements and a longer battle. Compare AI-attacker behavior and a land battle as controls, then recheck both movement fixes. Campaign naval battles, retreat/disengagement, save/load and multiplayer remain unverified. Do not describe this as an in-game-confirmed fix before results are recorded.
