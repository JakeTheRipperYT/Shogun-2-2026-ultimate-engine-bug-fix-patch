# OG fire by rank — first-volley startup mechanisms

Research date: 2026-10-24. User target: **fire the first volley much earlier when an enemy enters range**, rather than increasing sustained rate of fire. This investigation creates no gameplay patch or new installer build. Installed 0.1.3-naval-test remains unchanged.

## Confirmed mechanisms

| Mechanism | Original OG address | Verified role |
| --- | --- | --- |
| Drill name mapping | FUN_10178690 | Numeric drill 5 is rank_fire; 6 is kneel_fire |
| Ability mapping | Name table 0x115B3BA8 | rank_fire ability ID 7; distinct from drill number 5 |
| Effective drill selection | FUN_10178620 | Reads the selected unit drill with special-state/override fallbacks |
| Firing-task dispatcher | FUN_10177780 | Case 5 allocates a 0x58 task and selects rank constructor FUN_101295D0 |
| Ranked task construction | FUN_101295D0 | Installs vtable 0x115C1048; caps generated group count at 3 |
| Group allocation/mapping | FUN_101540F0; FUN_10171570 | Builds soldier-ID-to-group mapping through formation interface; this is formation-based, not simply one global timer |
| First group loaded | FUN_10178840 | Requires every soldier mapped to group 0 to pass entity virtual +0xF8 |
| Current group ready | FUN_1017B980 | Requires every soldier mapped to current group to pass FUN_103CBE40 |
| Soldier controller readiness | FUN_103CBE40; FUN_1039ED40 | Consults active controller/action state and virtual readiness; an active controller with no action rejects readiness |
| Group fire dispatch | FUN_1019A760 | Collects the selected group, prepares shot data and dispatches through task virtual +0x80 |
| Ranked individual preparation | FUN_101883F0 | Rank vtable +0x80; prepares a per-soldier firing action through FUN_103DB8F0 |
| Ranked individual follow-up | FUN_10188290 | Rank vtable +0x84; constructs action type 5 through FUN_101216C0 and FUN_103DB8F0 |
| Group advance/wrap | FUN_1014ED40; FUN_1014ED50 | Increments current group and wraps it when it reaches group count |

Task fields verified from native code: +4 squad pointer; +0x38 group count; +0x40 current group; +0x48 group map indexed by soldier ID at entity+0x218. Squad+0x18 is member count; +0x1C is member pointer array. Do not confuse the rank ability ID, firing-drill ID and action IDs.

## Named states and actual callbacks

The original DLL contains named state definitions, located independently by string/global/getter/callback cross-references:

| State | Callback table | Relevant callback |
| --- | --- | --- |
| WAIT_FOR_FIRST_GROUP_LOADED_STATE | 0x115B6EC8 | Evaluator 0x100FA8D0 calls FUN_10178840 |
| WAIT_FOR_GROUP_ALL_LOADED_AND_READY_STATE | 0x115B6B20 | Enter 0x100FA760 calls FUN_1019A9A0; evaluator 0x100FA780 calls FUN_1017B980 |
| ORDER_GROUP_FIRE_STATE | 0x115B6C4C | Enter 0x100FA7C0 calls FUN_1019A760 |
| WAIT_FOR_GROUP_FIRE_COMPLETED_STATE | 0x115B6C60 | Evaluator 0x100FA810 calls FUN_1017B9D0 |
| ADVANCE_GROUP_STATE | 0x115B6E20 | Enter 0x100FA850 increments group; exit 0x100FA870 handles wrap |

These definitions and transition getters are shared by multiple firing-drill task types. Patching their shared readiness predicate globally would affect other drills. A candidate must be guarded for vtable 0x115C1048 or implemented in a rank-specific virtual slot. The complete live state sequence and residence time after range entry have not been captured yet.

## The two proven barriers

The first-loaded predicate scans the squad but filters only mapping value zero. It rejects immediately when any member of that group reports not loaded. It does not use the current-group field.

The current-ready predicate scans the squad and filters mapping == current group. It returns false on the first member whose controller is unready. Consequently, this stage is governed by the **slowest eligible soldier**, not the first soldier ready to shoot. A late animation/action transition can hold up otherwise-ready soldiers. This establishes the mechanism; it does not establish that it is the dominant cause in the user's battle.

FUN_103CBE40 checks entity+0x384 and entity+0x308. Where the controller is active, it requires entity+0x248 action to exist, then asks the controller at entity+0x2F0 for readiness via virtual +0x28. Other native cases take a ready fallback. It would be incorrect to replace this helper with an unconditional true result: it is shared and represents meaningful action/controller restrictions.

## Base OG data values

Read directly, without modifying packs, from data.pack: db/_kv_rules_tables/_kv_rules in the installed OG game:

| Key | Base value |
| --- | --- |
| fire_volley_gun_min_threshold | 0.025 |
| fire_volley_max_aim_delay_ashigaru | 0.5 |
| fire_volley_max_aim_delay_samurai | 0.25 |
| firing_drill_rank_fire_reload_modifier | 0.0 |

Registry FUN_10D01B80 binds these keys. Registration objects are at settings+0x276C, +0x27CC, +0x282C and +0x204C respectively. Float registration copies to object+0x5C. These names/values are confirmed; the exact use of every parameter in the rank-specific first-shot path and live mod precedence are not fully established. The threshold's name/value alone does not prove it overrides the rank synchronization gate. A zero reload modifier does not mean the engine has zero reload time.

## Original-engine checks performed

tools/inspect-ranked-fire-gates.c compiles as x86 C++ and maps the original engine with DONT_RESOLVE_DLL_REFERENCES. It executes the actual unmodified group predicates, filtering helper and controller-readiness helper. Fixtures provide only the loaded and final controller-readiness replies; no game is initialized and no code or game file is patched.

All 12 scenarios / 24 predicate results pass:

- All members of the first rank loaded/ready permits both gates.
- One current-rank unready soldier blocks the readiness gate.
- A different rank's unready soldier is ignored by that gate.
- One group-zero unloaded soldier blocks the loaded gate; a later rank's unloaded soldier does not.
- Changing current group changes readiness filtering, while first-loaded still filters group zero.
- Missing action in an active controller blocks readiness; inactive controller follows native fallback.
- Empty/missing groups pass these predicates vacuously. That alone does not establish a valid firing task; other states handle squad validity.

Supported original engine SHA-256: 022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5. Installed patched engine remains 29bd5cac6520322a203f7702d21431f99436198e9a46941b0f0704ad66bddd6d (0.1.3).

## Next experiment

Measure the live first-volley sequence with a stationary, loaded matchlock unit and an enemy entering range: time of valid target/range entry, rank-task creation, first-loaded state, current-ready state, fire dispatch and first muzzle shot. Distinguish time before task creation from time spent inside these gates.

If controller synchronization dominates, test a **rank-specific, first-volley-only** readiness policy while preserving loaded status, target validity, range/line-of-fire, aim/reload restrictions and subsequent ranked cycling. Do not simply change every all-ready test to any-ready: it can desynchronize volleys, and a shared predicate would change other drills. The task's +0x44/+0x45 flags and first-cycle identity need further verification before relying on them as a first-volley guard.

If delay occurs before rank-task creation, investigate target acquisition/range polling instead; changing the group gate would miss the problem. The exact range-entry/acquisition scheduling path is not yet proven. No measured seconds saved or gameplay improvement is claimed at this stage.

Earlier CE any-ready and standing-animation experiments were reverted. Their files supplied research leads only; neither has been copied into this OG patch.
