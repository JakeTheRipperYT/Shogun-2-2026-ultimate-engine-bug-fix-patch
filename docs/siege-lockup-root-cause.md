# Siege lock-up: root cause (original Shogun 2, Steam build 11306771)

**Symptom:** during wall assaults, player units stop responding to move and dock orders for 10–85 s. Attack orders still work.

**Cause:** soldiers on wall/ladder links re-issue their move target **every tick**. Each re-issue throws away the route request that is still waiting in the pathfinder queue and appends a new one at the **tail**. Once the queue holds more work than one update can solve, those soldiers never reach the front. The queue becomes a livelock rather than a slow FIFO, which is the "overflow".

## The chain, with addresses (VA, image base 0x10000000)

1. **Link flag.** `Entity+0x11f` = the soldier is on a constrained link (ladder or wall link). While it's set, the soldier keeps a fixed facing and skips ground collision and avoidance (`FUN_103941c0`, `FUN_103a6650`, `FUN_10383080`).

2. **Per-tick re-issue.** Action vtable `0x115E0E90` (enter `0x103E8280`, update `FUN_103EE240`, ctor `FUN_103B9410`, installed into `Entity+0x250` by Entity virtual `FUN_103D93C0`).
   Each update, if the soldier hasn't reached `action+0x1c`, `Entity+0x11f == 1` and `action+0x46 == 1` (set from the ctor parameter `+0x2a`), it calls
   `FUN_103DF290` (Entity::SetMoveTarget) with the same destination.
   - Call site 1 (`FUN_103EE240`, first `FUN_103df290` call): **no cooldown.**
   - Call site 2 (end of `FUN_103EE240`): throttled by `action+0x4c = 10` ticks. CA added a cooldown here but not at call site 1.

3. **SetMoveTarget always resubmits.** `FUN_103DF290` copies the destination and options (route class at options `+0x14` → `Entity+0x448`), sets the movement state `Entity+0x3BC = 1` and immediately runs the state machine `FUN_103DF3F0`. It never compares the new target with the current one.

4. **Reuse only helps after completion.** In state 1, `FUN_103DF3F0` first tries `FUN_10378C70`. That reuses the previous request (`holder+0xC`, holder = `Entity+0x3C0`) only if it is **ready and successful** (`req+0x20/+0x21`). Before the queue backs up this absorbs about 6,000 re-issues per second (Pathfinder counter `+0x6A4`).

5. **A pending request is thrown away and requeued at the tail.** If the previous request is still waiting, `FUN_10385FD0` (route submit) creates a new class-2 request appended at `Pathfinder+0x14C` (tail). `FUN_1039F9F0` then stores it in the holder and releases the old one through `FUN_1039EE40`. Its refcount `+8` drops to 0, and `FUN_1037EC90` unlinks it from the pending list (`Pathfinder+0x148/+0x14C/+0x150`) and frees it.

6. **The queue is served from the head under a work budget.** `FUN_103AAC30` (Pathfinder::Update) solves pending requests from `Pathfinder+0x148` in order. After the first one it stops once `Pathfinder+0x470 >= 500` (`cmp` at `0x103AAEA4`). Single solves cost up to about 22,000 work units.

Result: when climbing starts, reuse stops working because the requests can't complete in time. Every soldier on a link then cancels and re-appends its request each tick, so the head of the queue is never reached. Defenders docked on the walls are on the same links, so their move and dock orders join the loop and freeze. Attack orders use different actions that don't re-issue, so they keep working.

## Measured (read-only sampler, experiment build, 633 s siege)

| Phase | Pending routes | Queued/s | Reused/s |
|---|---|---|---|
| Approach | 0–150 | 15–75 | ~6,000 |
| Climbing starts | 2,300 → 7,386 | 400 → 1,500 | collapses to ~300–800 |
| Rest of the assault | 2,000–5,500 | 300–1,600 | 1,000–5,000 |

## Why the CE budget raise (500 → 2000) only partly helps

A bigger budget clears more of the queue per update. Some requests then finish before their owner re-issues, and once finished they can be reused, so the livelock breaks sooner. It doesn't remove the cancel-and-requeue behaviour, so a large enough wave still causes it.

## Fix direction

Don't throw away a route that is still in flight. At `FUN_103EE240` call site 1 (and site 2), skip the re-issue while the soldier is waiting for its route (`Entity+0x3BC == 2`, request at `Entity+0x3CC` not ready). A more general alternative: make `FUN_103DF290` return early when the destination is unchanged and a request is still pending. Either way the request keeps its place and is served in normal FIFO order. Re-issues while following (states 3/4) keep using the cheap reuse path.

Ruled out: the wall navigation-version bump in the soldier event handler `FUN_103DCE90` (`0x103DD561`). Disabling it changed neither the backlog nor the lock-ups.

## Update: the actual overflow is a shared work counter

The re-issue fix above didn't stop the lock-up in play. The overflow comes from how the queue's budget is counted:

- `Pathfinder::Update` (`FUN_103AAC30`) serves the queue while `Pathfinder+0x470 < 500`, always serving at least one request.
- `Pathfinder+0x470` is the solver's running total (`solver = Pathfinder+0x36C`, total at `+0x104`). Every solve in `FUN_10386D90` adds its cost (`solver+0xC8`).
- **Synchronous** class-0 solves made during the frame (`FUN_10385FD0`, immediate re-solves of stale routes) use the **same solver and the same counter**.
- The counter is reset only at the **end** of the update (`0x103AAF09`).

So the frame's synchronous work spends the queue's budget before the queue runs. The sampler read the counter at **4–63** before climbing and **2,800–22,158** during it, which is far above anything the loop alone can produce. From then on the queue gets **one request per update** regardless of its length, and it overflows. Raising the limit to 2000 (Remastered CE) only made that less frequent, because the synchronous work still often exceeded 2000.

**Fix (`patches/engine/020-route-budget-reset.json`):** zero `Pathfinder+0x470` immediately before the queue loop (stub at `0x115A0C70`, called from `0x103AAE93`), so the 500 budget counts queue work only.

## Update 2: requests are replaced faster than the queue can reach them

The budget reset didn't stop the lock-ups either. The Pathfinder's own counters (`queued +0x6B0`, solves `+0x69C/+0x6A0`, cache hits `+0x698`) show why:

| Assault phase | Queued/s | Solved/s | Removed without being solved/s |
|---|---|---|---|
| Before climbing | ~20 | ~25 | 0 |
| Climbing (pre-fix) | 600–1,540 | 44–490 | up to ~1,300 |
| Climbing (budget fix) | 800–1,600 | 170–500 | 700–1,260 |

Even counting every cache hit as a removal, 400–800 requests a second leave the queue without being solved. The only way that happens is the soldier being **re-targeted while still waiting**: `SetMoveTarget` (`FUN_103DF290`) releases the pending request and appends a new one at the tail.

CE capture v4 at the 3,460-request peak shows who is waiting: every request belongs to a different soldier (200 requests = 200 distinct start and end points in one unit). Each goes from the ground (y ≈ 0.5 m) to that soldier's own spot on the wall-walk (y ≈ 11.9 m). They are all AI units under the wall command, while the AI issues only about 1.5 new unit commands a second for the whole army.

**The math:** about 3,000–5,000 soldiers wait on these routes. Each crosses dynamic climbing links, so none can be cached or reused, and the queue solves 200–500 a second. That makes the wait **10–20 s**. Unit re-forms (casualty compaction, the round-robin squad regroup every ~5 s per unit) re-target every waiting member, usually to the same or a neighbouring slot. That replaces each request about **every 5 s**. Requests are replaced faster than the queue can reach them, so almost nothing completes. The queue churns at full speed and every unit near the walls, including the player's, stalls. A bigger budget (CE 2000) only shortens the wait toward the replacement interval.

**Fix (`patches/engine/030-keep-pending-route.json`):** hook `SetMoveTarget`. If a soldier is waiting (state 2) on a pending request whose end region matches the new destination's region and whose end point is within 5 m of it, keep the request and its place in the queue instead of replacing it. Every other call runs unchanged.

Ruled out along the way: AI unit-order spam (about 1.5 commands/s for 40 units), the regroup's order-sensitive member comparison on its own (only about 160 re-targets/s at the round-robin rate), and one soldier holding several requests (each pending request is a distinct soldier).

## Update 3: the solve-cost explosion is a broken A* heuristic

None of the three stubs above (re-issue, budget reset, keep-pending) changed lock-up length in play. The keep-pending capture shows why: inflow and churn fell sharply, but solves stayed at about 40–200 a second and the backlog never drained. The queue is limited by **solve cost**, which matches Remastered CE, where a 4× budget gave about a 30× shorter lock-up.

`PathSearch::HeuristicCostTo` (`FUN_1038F0E0`):

```
if (ctx->expansions(+0xCC) < 500)  h = dist * 1.5;
else                               h = ((dist + node.additive) * node.multiplier)^2;
```

After 500 expansions the heuristic switches to metres squared, scaled by the candidate node's own cost multiplier. Climbing links carry large multipliers, so their heuristic explodes. For a goal on the wall-walk, the climbing nodes are the only way up, so the search avoids exactly the nodes it needs, floods the ground beneath the target to the 3,000-expansion cap, and the solver retries. Wall-top routes are the only ones that routinely pass 500 expansions, so this hits sieges specifically: each one costs thousands of work units against the 500-per-update budget.

**Fix (`patches/engine/040-astar-heuristic.json`):** NOP the `jae` at `0x1038F12A`, so the heuristic is always `dist * 1.5`. Patches 000–030 are disabled so this change can be judged on its own.
