# Kneel-fire movement — OG test candidate

Version **0.1.2-kneel-test** retains the yari-wall candidate and adds one new fix: permit movement eligibility while kneel fire remains enabled. The increment changes exactly two engine bytes relative to 0.1.1. Full in-game verification remains pending.

## Evidence from CE and OG

CE's existing fix removes `75 55` at RVA 0x224C4D, the immediate rejection after querying ability 0x39 in FUN_180224C30. Its other eligibility checks and the firing drill remain intact.

Existing OG pseudocode in F:/Ghidra/Exports/OG_Pseudocode/empire.retail.dll/functions/function_1015c3f0.c exposes the same structure. The OG ability name table at VA 0x115B3D60 points to `kneel_fire_ability` and stores ID 0x39. Its movement eligibility entry:

```text
1015C3F0 push esi
1015C3F1 mov esi,ecx
1015C3F3 mov eax,[esi+0xED4]
1015C3F9 lea ecx,[esi+0xED4]
1015C3FF push 0x39
1015C401 mov eax,[eax+4]
1015C404 call eax
1015C406 test al,al
1015C408 jne 1015C44F
1015C40A mov eax,[esi+0x14]
```

The rejected path returns false at 0x1015C44F. The continuation reads the battle phase and uses FUN_10180600 to test phases 5 through 8. For those phases, it retains the current action's virtual eligibility at +0xDC, if an action exists, and the final helper FUN_1015CB40. Outside those phases it returns true, as vanilla already does when kneel fire is inactive.

Only `75 45` at VA **0x1015C408**, RVA **0x15C408**, is replaced with `90 90`. The ability query remains; only its immediate movement veto is removed. No kneel-fire ability flags, firing drill, animations, reload timers, fire-by-rank behavior, combat stats or shared helper implementation are patched.

## Native verification

tools/test-kneel-eligibility.c maps the actual original/patched x86 DLL without initializing the game. It executes the real entry, phase helper and remaining branches. Controlled fixtures supply the ability query, action eligibility and final eligibility result. These are branch tests, not a game simulation.

Each mapping runs 96 combinations: kneel fire on/off; phases 0,5,6,7,8,9; action present/absent; action allows/denies; final helper allows/denies. All **192 cases** pass. Callback counts also verify that the phase/action/final checks run only where expected. Vanilla rejects all kneel-active cases; patched follows exactly the same downstream checks as kneel-inactive vanilla. The action and final helper can still reject movement. The test is integrated into build.ps1.

The existing ten yari-wall branch checks and all fifteen installer self-tests pass. Signed reconstruction is verified. Only recipes 050 and 060 are enabled; every historical experiment/diagnostic remains disabled.

Supported input is OG Steam build 11306771. Engine SHA-256:

```
Vanilla:     022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5
Yari only:   cf8288cbc7dcde2a9add0f5220675a441a809b125d595e2e8113ffc1b0814c66
Yari+kneel:  17df5605f2c34a1538a3184a28f82fcc9f484f455f4112a6ec33d7abe6ac82d2
```

## In-game test before acceptance

Compare the same matchlock battle on vanilla, 0.1.1 and 0.1.2. Enable kneel fire, let the unit fire, then issue a short move order while leaving the ability enabled. Repeat during aiming, firing, reload and after a halt. Test a second destination, turning, ability off/on and return to firing after movement. Verify that the firing drill still works and that disabled/busy-unit restrictions are respected. Repeat with an ordinary matchlock control and check that the yari-wall behavior from 0.1.1 has not regressed.

No live installation or battle test has been performed by this validation. Save/load, long-battle and multiplayer behavior remain unverified. Do not describe this candidate as an in-game-confirmed fix until those results are recorded.
