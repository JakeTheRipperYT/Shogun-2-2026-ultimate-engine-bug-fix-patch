# Restored-build live rank-fire baseline — 2026-10-24

After the requested recovery to 0.1.3-naval-test, the user loaded the test battle and reported the enemy entering range and two volleys firing. The game was sampled using process query/read access only. No breakpoints, suspension, injection, live memory writes or engine patch changes were used.

Evidence file: `outputs/OG-rankfire-restored-baseline-movement-live.jsonl` in the task workspace. It contains one discovered rank task, 160 changed snapshots and task expiration. PID58684 loaded the managed restored engine at base58840000. The discovered task946944 initially had group0, fired44=0 and first-cycle45=1. Its squad had160 soldiers split into groups67/67/26.

## Initial preparation observed

The initial type-5 sequence start field was world time173.2. The first sampled front-rank blocker appears at world176.0, so the first2.8 simulation seconds were not sampled. All67 soldiers first report ready at recorder time99.235. A type-0 fire-request sequence is then observed with start time183.1 at recorder99.344: approximately **9.9 simulated seconds from preparation start to fire-request start**. This is not an enemy-range-to-muzzle measurement.

Two unambiguous idle blockers:

| Soldier ID | World time | Observed block |
| --- | --- | --- |
| 2 |176.9..177.4|type5, STOP_STATE, idle155 STAND_TRAINED_IDLE_4, total77ticks, remaining6..1|
| 2 |177.5|clip cleared; next sample177.6 is FINISH_STATE with ready transition62|
| 3 |179.5..180.2|type5, STOP_STATE, idle155, remaining8..1|
| 3 |180.3|clip cleared; next sample180.4 is FINISH_STATE with transition62|

There are14 idle-bearing STOP blocker snapshots and two following no-clip STOP snapshots. In these windows, movement is already FINISHED, byte11F=1, requested delay is zero, controller_started=1, and pipe/stopping/bearing-lock flags are zero. The idle clip is therefore a demonstrated blocking condition, not an inference from a slow all-ready gate alone.

Ready transition62 is **STAND_TRAINED_TO_COMBAT_READY**, lasting17ticks. It appears in43 opening type-5 blocker snapshots and must remain intact. The last visible soldier58 was first sampled during this transition; its earlier clip is unknown. All73 type-5 blocker snapshots have movement finished, zero requested delay and no movement locks.

## Scope and limits

The task traverses groups0→1→2 once. Later group2 samples show type0 TURN_STATE / movement FINAL_TURN_STATE with no clip, until task expiration. The user's two visible volleys are consistent with the first two rank discharges; this capture does not prove two full three-rank cycles.

Only the first known unready soldier is retained in each watcher snapshot, so visible waits must not be added together to predict savings. Reads are non-atomic; short one-update differences between sequence completion, stance and ready latch are expected. No range/LOS calculation, loaded virtual call or muzzle event was measured.

The evidence supports an initial-preparation, named-idle-only cancellation trial while retaining transition62, movement completion, loading/reloading and later rank handoff. The guarded native prototype passes1554 cases, but the patched battle still needs the same observation and regression check.
