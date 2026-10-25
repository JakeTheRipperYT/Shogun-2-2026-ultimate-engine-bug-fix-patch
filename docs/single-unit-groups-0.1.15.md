# Single-unit player battle groups

Version: 0.1.15-single-groups-test. Target: supported original 32-bit empire.retail.dll only.

## Behavior

Allow a land unit or ship to form a group by itself. Retain a group when removing members leaves one. Display its group frame with the existing ordinary one-row layout even when compact mode is selected. Reject empty selections, clean up empty groups and retain the maximum group capacity.

## Trace and focused changes

The OG pseudocode and native disassembly identify player UI manager vtable 1170D0F0. Its creator callback 110E0850 already accepts the selected member count. The Lua UICardManager scripting wrapper and script unit-controller checks are separate from this player path.

| Native address | Change | Purpose |
|---|---|---|
| 11101A3A | compare immediate 1 to 0 | Land grouping eligibility |
| 11102DC8 | compare immediate 1 to 0 | Naval grouping eligibility |
| 10F89A46 | compare immediate 1 to 0 | Actual card-group creator |
| 10F9787F | JA to JAE | Retain one remaining member; preserve original zero cleanup and flags |
| 11223482 | compare immediate 1 to 0 | Show a single-member group frame |
| 112234A0 | relative detour | Force singleton through ordinary frame layout |

The compact/odd-count frame path dereferences a second member. Simply lowering the visibility threshold is unsafe. The 16-byte adapter checks count == 1 and supplies the flags selecting the ordinary path. Other counts replay the original mode comparison. It changes no registers or stack and adds no absolute operands or relocations.

The adapter occupies a new RX, non-writable .ubfix section at RVA 01D88000, raw offset 01899400, using a 512-byte aligned append. A guarded section header, section count, SizeOfCode and SizeOfImage are updated. Existing imports, exports, resources, data directories and existing relocation descriptors remain intact. The recipe requires the exact vanilla SHA256 and guarded original bytes. ReleaseTool maps recipe addresses against the original image, limits the append to original EOF and rejects malformed, multiple or oversized appends. Installer reconstruction already supports an enlarged engine and verifies its hash before signing.

BCQ_ARMY_CREATE_UNIT_GROUP serializer 102E6390 and executor 102A5E40 already support a single member. Factory 10166E40, add/remove paths 1041DCC0/10472ED0, death pruning 1019F7A0 and army update 101B5230 retain nonempty groups. Existing loops support a count of one. No packet format, core movement logic, combat scoring or Lua script-controller minimum changes are needed. No UI Lua script is added.

## Verification and limits

- Generator checks the supported source hash, surrounding instructions, free section header, alignment, original EOF, no overlay/security directory, original data directory descriptors and nonoverlap with enabled recipes.
- Actual-code fixtures cover 288 vanilla and 288 candidate cases at three ASLR bases: land/naval capacity gates, full creator/vector append, base/derived removal/vector erase and renderer dispatch. Empty, singleton, multiple and boundary counts are included, with ABI checks.
- Command fixtures execute original serializer/receiver code for counts 0, 1, 2 and 20 against vanilla and candidate, with controlled typed I/O/factory callbacks. The vanilla receiver accepts explicit empty packets; UI empty-selection guards remain in place.
- Existing engine, private-pack, installer and archive checks run in the full build.

Controlled callbacks and renderer dispatch tests do not establish live battle behavior, geometry appearance or multiplayer compatibility. Player testing remains necessary for Ctrl+G/group button, numbered groups, lock/unlock, movement, adding/removing units, casualties, naval groups and compact UI. Original data, model and localisation packs are unchanged from 0.1.14.
