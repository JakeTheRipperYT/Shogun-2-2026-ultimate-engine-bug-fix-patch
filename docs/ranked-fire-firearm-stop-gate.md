# Ranked fire: firearm-specific STOP gate

Research continued 2026-10-24 against original OG Steam build 11306771. This supersedes the earlier explanation that every ordinary type-5 request waits in controller update `FUN_103A9FE0` before starting. It identifies and tests a narrower mechanism; the observed battle's dominant blocking clip/state still needs a targeted capture.

## Correct path and corrected assumptions

`FUN_10188290` builds request type 5. `FUN_101216C0` sets request+0x34 to zero; controller construction `FUN_10350F10` copies that to controller+0x54. The real owner lifecycle `FUN_103EFC70` invokes controller enter `FUN_103828B0`. With that zero handle, enter calls **FUN_10392740 immediately** and sets controller+0x70. The completion wait in the controller's update is a different path, reached when a preliminary handle was supplied. Its existence does not prove it delays these ordinary rank requests. Native constructor/lifecycle cases confirm entry starts with previous-sequence completion both false and true; only the final start implementation is a recording fixture in those two cases.

In `FUN_10392740`, the random-number branch changes a mode/stance boolean passed to the sequence. It has no timed retry/return that would make it a random startup delay.

`FUN_10391B50` chooses the actual sequence. It tests animation metadata+**0xC44**. The original named animation table at `0x11692640` has 24-byte rows, and row **130 is FIRE**; `130 * 24 + 20 == 0xC44` is the variant-count field used by the branch. When FIRE is available, the start path calls `FUN_103D95A0` -> `FUN_103B9B30`, producing **vtable 0x115E10D0**, derived from 0x115E1044. Its update is `FUN_103EF320`. The simpler 0x115E0FCC sequence examined previously is a fallback, not the FIRE-available path.

## Firearm state sequence

Original state names were resolved through each state table's ID getter, rather than inferred from neighboring strings:

| State object | Name | Key behavior for type 5 |
| --- | --- | --- |
| 0x1179A0F0 | STOP_STATE | Enter 0x103B2B80 -> FUN_103D3BF0 stops movement; evaluator 0x103B2BA0 polls FUN_103D3CE0 |
| 0x1179A0F4 | START_STATE | Evaluator 0x103B2C80 uses virtual +0x6C -> FUN_103D3D40; type 5 checks loaded status through soldier virtual +0xF8 |
| 0x1179A114 | RELOAD_STATE | Destination when that type-5 loaded check fails |
| 0x1179A11C | FINISH_STATE | Destination when that type-5 loaded check succeeds; enter FUN_103D35E0 requests standing/kneeling combat-ready mode |

The same sequence also contains TURN_STATE, GET_AMMO_STATE, MISFIRE_STATE, AIM_STATE, AIM_RELOAD_STATE, AIM_FINISHED_STATE, FIRE_STATE and WATCH_STATE. Those checks and transitions must not be globally bypassed.

For type 5, the STOP evaluator's alternate facing-abort predicate `FUN_103D3300` returns false in the normal no-special-target case. The STOP-to-START condition in **FUN_103D3CE0** is:

```c
soldier.byte11F != 0
    && soldier.currentClip474 == NULL
    && sequence.startTime74 + sequence.delay50 <= world.tick50 * 0.1f
```

Continued multi-agent tracing established that this is the embedded movement HSM's FINISHED_STATE flag (HSM at soldier+0xF8, flag+0x27; enter10343A80/1038AE30, exit10343AA0/1038B170). It is not a wall-link flag. See [the guarded candidate review](rank-idle-first-volley-candidate.md). In the ordinary rank request, the constructed delay field is zero. An outstanding clip can still block the transition despite zero requested delay.

## Why an idle clip can produce a long first-volley wait

`FUN_103C2030` is simply the test `soldier+0x474 == NULL`. `FUN_103D3BF0` calls the movement-stop helper, which does not itself clear that clip. The per-soldier update `FUN_103DDA00` sees an outstanding clip and advances it through **FUN_103F0370**. That function increments soldier+0x1D8 once per update, compares it with clip metadata+0x64, and calls `FUN_103CA920` to clear the clip when its ticks run out.

Thus a rank can be waiting on the remaining ticks of an already-playing clip, rather than on its own ready request's delay or a new aim timer. Because the rank gate requires everyone, one such soldier can hold the volley. This is a demonstrated mechanism, not proof of which clip the last soldier had in Grok's capture.

The named animation table identifies **141..151 as STAND_IDLE_1 through STAND_IDLE_11_TELESCOPE**, and **152..157 as STAND_TRAINED_IDLE_1..6**. Animation ID 4 is STAND_TO_COMBAT_READY, while **soldier action ID 4 is a different enum** and must not be used as an idle-clip detector. Aim, fire, reload and stance-transition animation IDs are distinct from these idle families.

## First-cycle stance guards matter

The rank preparation method does not unconditionally request kneeling for every non-last rank. Its request mode is:

```c
mode = (followup ? task.fired44 != 0 : task.firstCycle45 == 0)
       && soldierGroup < groupCount - 1;
```

The constructor's first-cycle value is 1. Initial ordinary preparation therefore requests mode 0. Later calls can request mode 1. Skipping preparation or forcing a mode can discard this distinction and disrupt rank handoff/kneeling.

## Original-code verification

`tools/inspect-ranked-fire-sequences.c` compiles as x86 C++ with `/O2 /W4 /WX`. **96 native cases pass**:

- Eight transition-table lookups, including standing-to-ready, kneeling, aim recovery and reload recovery, using the original matrix constructor and resolver.
- Six goal/state mappings and 16 completion cases for the separate fallback sequence.
- 48 actual rank request-construction cases covering group counts 1..3, firing/first-cycle flags and follow-up calls. Only downstream dispatch is intercepted in a private mapped copy.
- Two real type-5 constructor/owner-lifecycle cases, with a recording fixture at the final start implementation.
- Eight actual firearm STOP evaluator cases isolating the state flag, current clip and elapsed delay. All three conditions are necessary in these fixtures.
- Two actual firearm START evaluator cases showing loaded -> FINISH and unloaded -> RELOAD.
- Six idle progression cases (IDs 141 and 152, with 1/10/93 ticks). The real clip-advance/cancellation and STOP code wait for every remaining tick, then permit the transition. Event-free clip fixtures omit motion events; no hook is needed for these six cases. The supplied durations are synthetic, not extracted lengths or a measured explanation of the earlier 9.3-second battle trace.

No live game was attached, no patch build installed and neither failed rank recipe re-enabled. The source and cases establish what to measure next: firearm HSM state, current clip ID, total/elapsed clip ticks, byte+0x11F, sequence delay and loaded result at the rank's blocking soldier. A focused candidate could cancel only a verified idle clip on rank preparation while preserving reloads, stance transitions and all other gates; it is not yet a validated gameplay fix.
