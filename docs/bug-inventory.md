# OG bug inventory and acceptance

All inherited patch recipes remain disabled. None is an accepted fix for this project.

The user selected kneel-fire movement as the next bug after the yari-wall candidate. **0.1.2-kneel-test** retains recipe 050 and adds only **060 kneel-fire movement**. The latter removes a two-byte ability-specific movement veto while preserving later eligibility checks. See [kneel-fire evidence and test procedure](kneel-fire-movement.md) and [yari-wall findings](yari-wall-movement.md). Both have native validation; in-game before/after and regression results remain pending. No other bug is in progress.

| Candidate | Inherited evidence | Disposition |
| --- | --- | --- |
| 010 siege route reissue | Pending requests repeatedly replaced during wall movement | Historical experiment; notes report lockups persisted |
| 020 queue budget reset | Synchronous work shares queue counter | Historical experiment; notes report lockups persisted |
| 030 preserve pending routes | Reduced request churn | Historical experiment; notes report lockups persisted |
| 040 A* heuristic | Suspected cost escalation after 500 expansions | Unverified; reproduce on OG and compare correctness/performance |
| 900 route invalidation | Diagnostic experiment | Disabled; notes report no improvement |
| 901 higher route budget | Scheduling change | Disabled; performance tradeoff, not accepted root-cause fix |
| 950 counters | Instrumentation | Disabled; not a player fix |
| 000 text cave | Stub support | Disabled; enable only with reviewed dependent code |

The inherited siege-lockup-root-cause.md records evolving interpretations and unsuccessful experiments. Read all updates. CE observations and addresses require revalidation against supported OG binaries.

For each report record game build, EXE/DLL SHA-256, mods, save/replay or battle setup, exact steps, expected/observed behavior and severity. Reproduce on vanilla first. Test one candidate at a time, including changed orders, long battles, save/load and relevant multiplayer determinism. A fix requires a reproduced failure, reviewed byte changes, a passing before/after comparison and regression evidence.
