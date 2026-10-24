# Guarded initial rank preparation candidate

Research update 2026-10-24. Candidate remains disabled. Live diagnosis was interrupted by the user's report that installed 0.1.6-bugfixpack-test.1 does not launch; recovery to the last working 0.1.3-naval-test takes priority. No new ranked-fire release has been installed.

## Movement condition resolved

Soldier+0x11F is **movement FINISHED_STATE**, not a wall-link flag. The movement HSM is constructed at soldier+0xF8 (103522C4 -> 10352440). Its FINISHED_STATE enter callback 10343A80 calls 1038AE30, setting HSM+0x27 to 1. Exit callback 10343AA0 calls 1038B170, clearing it. State table 115DB300's ID getter 10343A70 reads 11799090, pointing to the string FINISHED_STATE at 115B60D4. State object 11799440 points to that table. Native instructions/string references were independently re-read after the agent audit.

The firearm STOP gate therefore waits for **movement finished, no current clip, and elapsed delay**. The candidate preserves the movement and time checks.

## Narrow intervention

`patches/engine/080-rank-idle-first-volley.json` is generated with `enabled: false`. It detours only rank preparation 10188290 and calls native cancellation 103CA920 only when all these guards hold:

- Ranked task vtable 115C1048.
- First-cycle flag +45 equals 1 and fired flag +44 equals 0.
- Ordinary preparation argument is zero and current group +40 is zero.
- Nonnull soldier and current clip, with animation ID **141..157**.

The original request construction and first-cycle stance rules execute afterward. The 90-byte position-independent adapter occupies 115A0DA0..115A0DF9, disjoint from the naval adapter and pack redirect. It preserves all general registers and entry flags, replays the five-byte prologue and resumes at 10188295. The generator checks exact original SHA-256, expected bytes, executable section mapping and overlap with enabled recipes.

Native policy 103C2040/103E99A0 already considers these idle IDs interruptible. That general predicate also permits reload loops 133/134/138, so it must not replace the explicit idle whitelist. Named stance/aim/reload transitions remain excluded.

For ordinary idle IDs, native cancellation 103CA920 only clears soldier+474. Its additional cleanup is reserved for animation IDs 42B..432,435,436. Clip records are shared registry pointers (10368D10), not owned allocations. Do not free them or manually zero motion-event offsets, readiness, action or stance fields.

## Verification

`tools/test-rank-idle-candidate.c` ran **1,408 original/candidate real-entry cases** at distinct ASLR mappings: 704 per engine. All passed. The 34 expected cancellations occurred only in the guarded initial-preparation cases; other task classes, later cycles, fired/follow-up/current-rank guards, null clips, reloads and stance transitions were preserved. The native cancellation helper executed; only downstream request dispatch was intercepted. All other soldier/task fixture bytes and the type-5 request/stance data remained unchanged.

The private workspace candidate DLL additionally includes the currently enabled support/naval/pack recipes solely for overlap and entry testing. It is not a distributable release or a restored-game installation. Any eventual trial must be built on the selected working baseline; it must not silently reintroduce the broken data-pack release.

These cases verify guard/ABI behavior, not in-game benefit, clip-event visual continuity or synchronized later volleys. The existing battle CSV does not contain the actual blocker clip or movement fields. `tools/inspect-rankfire-blocker.py` now provides bounded read-only task discovery and sampling; its synthetic checks pass. See `docs/rankfire-blocker-capture.md` for commands and limits.

## Separate installed-build problem

Read-only inspection of the exact installed .1 package metadata found unsorted added blocks in data.pack and models.pack, an uppercase DB path and six replacement table headers differing from vanilla. The newer local .2 recipes correct those structural differences, but passing checks of .2 do not validate installed .1 or establish a successful launch. The precise launch-failure trigger has not been isolated. The user's requested recovery uses the verified 0.1.3 backup, without adopting .2 or enabling this candidate.
