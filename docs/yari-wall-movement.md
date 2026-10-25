# Yari-wall movement — first isolated OG candidate

Version 0.1.1-yari-test. The intended fix allows movement orders while a yari-wall unit is engaged in melee, preserving the formation. No other bug fix is enabled. This is a test candidate, not an in-game-verified release.

## Mapping the CE change to OG

CE's handler at RVA 0x268860 returns 1 before processing movement when unit+0x1128 state's +0x874 is nonzero. Its tested patch changes `74 0D` to `EB 0D` at RVA 0x268882. The OG compiler emits a different branch and helper calls, so CE bytes/addresses were not reused.

Existing OG pseudocode under F:/Ghidra/Exports/OG_Pseudocode/empire.retail.dll establishes:

- FUN_101672B0 maps ability 6 to formation type 3.
- Constructor FUN_101255F0 sets formation type 3 and installs vtable 0x115C0430.
- That table's slot +0x28 points to 0x10198560, matching CE's table 0x1821938F0 slot +0x50.
- FUN_10095790 returns context+8 (unit); FUN_1017BEE0 tests its argument+0x10 for nonzero.

The OG export omits a separately named function at 0x10198560. Disassembly of the original DLL supplies the missing handler and verifies its table entry:

```text
10198560 push ecx
10198561 push ebx
10198562 mov ebx,ecx
10198564 call 10095790
10198569 mov ecx,[eax+0xB9C]
1019856F add ecx,0x74C
10198575 call 1017BEE0
1019857A cmp al,1
1019857C jne 10198583
1019857E pop ebx
1019857F pop ecx
10198580 ret 8
10198583 push esi
10198584 push edi
```

After 0x10198583 the handler reads the movement request, obtains formation heading/speed and calls FUN_101542E0. The change is `75 05` to `EB 05` at VA 0x1019857C (RVA 0x19857C): always reach the same continuation. It does not alter the engagement check helper, speed, damage, formation ability or any other handler.

## Verification

Supported local input: Steam build 11306771.

```
Original engine 022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5
Patched engine  cf8288cbc7dcde2a9add0f5220675a441a809b125d595e2e8113ffc1b0814c66
```

The signed reconstruction package applies one engine write changing one byte. All other recipes, including diagnostics and text-cave support, are disabled.

tools/test-yari-branch.c compiles as x86 C++ (/TP) and runs the actual original/patched entry plus its two real helper functions in private, uninitialized DLL mappings. Only the continuation is replaced in memory with a sentinel return. Engagement values 0, 1, 3, -1 and INT_MAX produce ten passing checks: vanilla reaches movement only for zero; patched reaches it for all cases. This reproduces the control-flow defect, not a full battle. The test preserves the real ret-8 calling convention and is included in build.ps1 unless -SkipTests is used.

All 15 installer self-tests and signature verification also pass. Build-only reconstruction is verified separately. Original installed EXE/DLL remain unchanged. No game was launched and no live installation was performed.

## Required in-game comparison before acceptance

1. On vanilla OG with mods disabled, put yari ashigaru in yari wall, engage an enemy frontally, then issue a short movement order. Record whether it is ignored while formation stays enabled.
2. Repeat the same battle with this candidate through the Ultimate launcher. The order should reach movement handling without requiring yari wall to be toggled off.
3. Compare unengaged movement, turning, halt, changed destinations, ability on/off, attacking and withdrawing under pressure. Check losses and spacing for unintended behavior; no speed/stat change is intended.
4. Include long-yari ashigaru and a unit without yari wall as controls. Do not mix different patched engines in multiplayer; determinism has not been tested.

Record vanilla and patched results before calling the bug fixed or starting the next bug. If the behavior regresses, use the normal Steam launch for vanilla and uninstall the candidate with its installer.
