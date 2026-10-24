# Ranked fire readiness: resumed review, 2026-10-24

## Current state checked before continuing

Grok's relevant notes are under `F:\Codex\Shogun-2-Original-Upgrade-Patch\research`: `grokbot_fire_by_rank.md`, `grokbot_rank_fire_SUMMARY.md`, and `grokbot_rankfire_trace_RUN.md`. Reviewed their recorded results, archived recipes and the actual CSV `trace_20261024_103911.csv`.

The installed version is now **0.1.6-bugfixpack-test.1**, not the 0.1.3 stated in the older rank notes. All five installed file hashes match its installation record. Applying the current enabled recipes to the original DLL in memory reproduces the installed DLL exactly: 42 writes, SHA-256 `cedd4f06fcf6b0b051616051b459b90110bbf252fce13544a13bfc9d55cb8c94`. Enabled recipes are 000/050/060/070/090. Neither archived 080 rank experiment is enabled. Original EXE and DLL hashes remain unchanged.

Later datapack and installer work exists locally, including a built `.2` package. This review does not install it, alter that work, or claim to validate the merged pack's gameplay. `datapacks/bugfix-2026/PLAN.md` still says staged/not installed despite the installed record; treat that heading as historical. GitHub research branch was still at `b2481054ed7b0ebb83eca755f8543a06c918579e` when checked, so the newer local integration is not represented by that branch.

## Exactly what the ready check requires

`FUN_103CBE40(soldier)` is equivalent to:

```c
if (soldier.controllerActive384 != 1) return true;
if (soldier.readyLatch308 == 1) return true;
if (soldier.actionID248 == 0) return false;
return controller.virtual28(soldier.actionID248);
```

For controller vtable `0x115DD1C0`, virtual +0x28 is `FUN_1039ECE0`. It accepts action IDs **1, 2, 13, 14, 17, 18, 19, 20**; all other IDs fail, including zero and 4. This is a compatibility policy, not a distance/line-of-sight calculation. The old tracer labels `range_los` and `target` do not establish range entry: `+0x248` is a numeric action ID. Likewise, soldier action ID, request type, sequence mode and stance state are different enums.

The rank predicate `FUN_1017B980` requires this result for every soldier in the current rank. Loaded status is a separate group-zero gate, `FUN_10178840`; passing readiness alone does not prove a loaded gun or valid shot.

## How the latch becomes ready

1. The rank's preparation method `FUN_10188290` sends a type-5 request through `FUN_103DB8F0`. Its controller constructor calls `FUN_103506F0`, clearing controller+0x10, which aliases soldier+0x308. It also marks the controller active. Keeping an old ready latch does not preserve all the new request's stance side effects.
2. Before the new controller starts, `FUN_103A9FE0` reads the current sequence through `FUN_10382030`. It waits until **sequence+8 == 1**, then calls `FUN_10392740`. This flag belongs to a sequence object; it is not inherently a timer or proof that an idle clip finished.
3. After start, the update calls `FUN_1038A5E0(controller, sequence)`. When sequence+8 equals 1, this helper sets the ready latch. Sequence+0x18 values 0/1/2 are also copied to controller+0x1C. Thus sequence completion can unblock readiness without a nonzero action ID.
4. There is another setter in the soldier update at `0x103D6CB8`: active controller + virtual +0x24 accepting the current action ID sets the latch. For this controller that policy is `FUN_1038A9C0`, accepting 14, 17, 18, 19. The completed-action-12 branch at `0x103D6CF1` is another path. The latch does not exclusively mean one ready animation has played.

## Further sequence finding

The infantry start implementation `FUN_10391B50` (a soldier virtual +0x1B0 implementation) destroys the previous owned sequence and placement-constructs `FUN_103B9AE0` at soldier+0x250 for modes 0/1. The resulting vtable is `0x115E0FCC`. It is a replacement, not simply an extra item appended to a queue. There are other soldier implementations and a special branch; this finding should not be generalized to every entity class.

That sequence's update is **FUN_103EF1E0**. On its normal mode path it requests stance 8 or 9 through `FUN_103E3D40` and sets sequence+8 only after **soldier+0x1D0 becomes 18 (mode 0) or 19 (mode 1)**. Link/unit eligibility checks can postpone this path; there is also a special alternative completion branch through `FUN_103D8B20` and `FUN_103C9960`. These numeric stance values are verified, but their precise standing/kneeling animation names and the live blocking soldier's sequence class have not been captured.

Consequently, “finish the current animation” is too broad an explanation. At least this ready-sequence class waits for a requested stance state. Bypassing sequence+8 can disrupt the stance handoff, consistent with the reported failed kneeling experiments, although that causal explanation still needs a targeted live trace.

## Evidence and limits

- New native harness `tools/inspect-ranked-fire-readiness.c`: **222 results pass** against the original DLL: 207 flag/action combinations through the real controller callback, 12 completion/latch cases, and 3 current-rank integration cases. No readiness callback is mocked in this harness.
- Older group harness retains its controlled callbacks to test rank membership and loaded filtering. Corrected its action argument from an arbitrary pointer to a numeric ID.
- Re-read Grok's CSV: outer fire-state entry 33.9856; first per-soldier fire dispatch 43.8161; final identified blocker last false 43.6985 and next true 43.7948. Dispatch followed that true by **21.3 ms**. These are instrumented trace timestamps, not a clean benchmark or measured delay from actual enemy range entry.
- Grok records user-observed regressions: 0.1.4 fired sooner but staggered and stalled the second rank; 0.1.5 still broke second-rank kneeling and left some delayed shots. Both recipes stay archived.

Next useful capture: at the blocking soldier, log sequence vtable, sequence+8/+0x18/+0x1C, controller+0x40/+0x44/+0x70, ready latch, action ID and soldier stance+0x1D0. This separates waiting for the old sequence from waiting for the newly requested stance. Do not reuse the old `range_los` label as a range measurement or revive either failed bypass. No new gameplay patch, build, install or release is made by this research update.
