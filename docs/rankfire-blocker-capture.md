# Read-only rank-fire blocker capture

## Audit of saved evidence

Reviewed Grok's tracer and `F:\Codex\Shogun-2-Original-Upgrade-Patch\build\captures\rankfire\trace_20261024_103911.csv`. The CSV contains 21,654 soldier readiness events, 2,116 events named `range_los`, 2,076 `rf_canfire` events and 160 fire-dispatch events. It records no current clip ID, clip progress/length, sequence vtable/HSM state or byte+0x11F. Consequently it cannot prove which clip or STOP subcondition held the last soldier.

The old event name `range_los` refers to controller/action compatibility at FUN_1039ED40. The old `target` extra field is an action ID. Neither measures enemy range entry or line of sight. The later tracer's `ready_fail` probe logs only readiness/action changes, so it also needs more fields to answer the clip question.

## New tool

`tools/inspect-rankfire-blocker.py` reads a running OG process using `OpenProcess(QUERY_INFORMATION | VM_READ)` and `ReadProcessMemory`. It does not create debugger breakpoints, inject code, call game functions, stop its threads, or request process write permissions. It writes only the explicitly named capture file. No live process was sampled during development.

Run its fixture checks without the game:

```powershell
& 'C:\Users\CT-MK2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\tools\inspect-rankfire-blocker.py --selftest
```

For a live capture, first obtain the **current** process PID. Old CSV addresses are stale after a process restart and must not be reused. Discover current rank tasks without a debugger:

```powershell
& 'C:\Users\CT-MK2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\tools\inspect-rankfire-blocker.py --pid 12345 --scan-tasks --scan-mb 2048 --scan-seconds 20
```

This uses `VirtualQueryEx` to enumerate committed readable 32-bit pages, excludes guard/no-access/execute-only pages, and searches up to 256 KiB per `ReadProcessMemory` batch for the ASLR-adjusted rank-task vtable. Candidate objects must pass bounded task/group/squad/member-array checks and sampled soldier-ID/group-map checks. It prints task addresses and counts plus scanned/skipped bytes, unreadable batches and whether byte/time/candidate limits stopped the scan. Defaults are at most 2 GiB, 20 seconds, 4,096 candidate validations and 128 accepted tasks. `--scan-mb` accepts 1..4096 and `--scan-seconds` accepts up to 120; these are scan limits, not time estimates. An empty or incomplete result does not prove there are no rank tasks. Tasks may not exist until firing preparation begins, and short/transitional tasks can disappear during scanning. Pause the battle while it is experiencing the opening wait if a stable capture address is needed. Do not reuse discovered addresses across a process restart.

Then substitute a discovered **current** rank-task address in the capture command. From `work\og-patch`:

```powershell
& 'C:\Users\CT-MK2\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\tools\inspect-rankfire-blocker.py --pid 12345 --task 0xCURRENT_TASK --seconds 120 --out .\build\captures\rankfire\blocker-new.jsonl
```

Alternatively, use `--soldier 0xCURRENT_SOLDIER` instead of `--task`. The task option checks the rank-fire vtable and refreshes current-rank membership on each sample. The sampler discovers the ASLR engine base and checks the expected readiness code prefix. The address/code checks protect against obvious unsupported layouts, not every possible custom engine change. It exits on unreadable or invalid pointers instead of treating unreadable memory as zeros.

The JSONL records ready/active/entered flags, action ID, controller request type/mode/start flag, sequence ownership/vtable/completion/HSM state/type/mode, delay/start timestamp, byte+0x11F, goal/stance states, and clip ID/total/elapsed/remaining ticks. Movement fields include the HSM state at entity+0xFC (named states BEGIN through FINISHED), `pending_pipe138`, `locked_until140`, `stopping144`, and `bearing_speed_lock145`. The `movement_finished` alias is byte+0x11F: the original FINISHED state's enter sets it and exit clears it. When the entity's scope/world pointers are present, it also reads world tick+0x50 and its 0.1-second conversion; it does not dereference a missing optional scope. The capture therefore distinguishes a clip wait from unfinished movement or a bearing/speed lock.

It labels 141..157 as the verified standing-idle family. It preserves every current-rank member so a known false readiness result can be associated with its clip. Other controller compatibility policies remain `null`/unknown rather than being guessed. The tool does not call the virtual loaded predicate and therefore does not claim to measure loaded status. Discovery prints JSON to standard output; optional `--out` saves its report with exclusive create.

Interpret the movement and clip fields together: `FUN_103DDA00` advances an outstanding clip and returns before `FUN_103AA090` updates the movement HSM. An active clip can therefore coexist with `movement_finished == 0` and hold both STOP prerequisites; a zero movement-finished flag alone does not rule out the idle-clip mechanism. The one-second bearing/speed lock set through `FUN_10393680` can also be refreshed, so repeated snapshots of its expiry matter more than a single lock flag.

Sampling is read-only and non-atomic: a state change can occur between reads, and 50 ms sampling can miss short transitions. The first-known-unready field is a reconstructed snapshot, not proof of the actual native gate's precise failing instruction. Capture several stable consecutive samples before attributing a delay. Ctrl+C simply closes the read handle; there are no breakpoints to remove. The output path uses exclusive create and cannot overwrite an earlier capture.

Development checks: `--selftest` passes snapshot decoding, unknown-controller handling, clip metadata/progress, movement-state/flags/expiry decoding, optional world tick/time and null-scope handling, current-group membership filtering, rejection of an invalid vtable lookalike, acceptance of a synthetic rank task in batched memory, and explicit byte-limit reporting. These are synthetic decoder/discovery tests, not a live process capture or performance benchmark.

What remains to establish in battle: whether the actual blocking soldier has firearm STOP_STATE, an idle clip 141..157, byte+0x11F set and elapsed delay; whether clearing that clip while preserving the ready request shortens the first volley; and whether later ranked volleys and kneeling remain correct. This tool alone neither establishes range-entry time nor validates a gameplay fix.
