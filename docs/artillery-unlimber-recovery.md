# Obstructed artillery unlimber recovery — local trial 1

The reported failure is a permanent grey limber control after deploying mobile artillery near an obstacle, sometimes with guns unable to clear their horse carriages. This change provides cancellation/recovery through the original limber state. It does not force firing readiness or change collision/pathfinding.

## Original code path

`unlimber` is special ability `14h`, established from the original ability-name table at `115B3B98`. Group commands reach `1045FDB0` and the unit special-ability order path. The unrelated `BCQ_UNIT_ORDER_DEPLOY_ENGINE` is not the limber toggle; it was inspected and excluded.

`1015BE80`, case `14h`, calls the current artillery state's virtual eligibility method at slot `110h`. For the artillery state created by `1012DBD0` (primary vtable `115BF6A0`) this is `1015BD30`.

`1015BD30` rejects four state keys:

- `11796DA4`: LIMBERED_REFORM_STATE
- `11796DA8`: UNLIMBER_STATE
- `11796DAC`: UNLIMBERED_REFORM_STATE
- `11796DE0`: LIMBER_STATE

Names were resolved from the original state-object vtables and their name getters, not inferred from numeric IDs. The original request handler at virtual slot `64h`, native address `10198E50`, already accepts ability `14h` and records a re-limber request at state `+41h` during a live battle.

The UNLIMBER_STATE completion callback `100F92E0` calls `101B49A0`, which waits for every gun model's `+6F9h` limbered flag to clear. Its entry routine `101B4950` asks each gun to unlimber through `10316CC0`. That request uses the model's normal unlimber processing rather than immediately clearing the completion flag during a live battle.

The earlier LIMBERED_REFORM_STATE callback `100F9230` likewise waits for its preparation condition before entering UNLIMBER_STATE. Neither early callback checks the native re-limber request. UNLIMBERED_REFORM_STATE already checks `+41h` and returns virtual slot `158h`, the native LIMBER_STATE selector. A blocked transition can therefore be prevented from finishing while the predicate prevents the recovery order from being issued.

## Focused change

Three two-byte conditional branches in `1015BD30` are NOPed, permitting the native request handler during the three deployment phases. The LIMBER_STATE predicate remains unchanged, as do outer unit eligibility/gun-presence/routing checks.

Two five-byte callback prologues (`100F9230`, `100F92E0`) redirect to 76 bytes of handwritten x86 in previously zero padding at `11D8DA00`. Each adapter reads the existing request from the callback's FSM argument (`state+34h`, hence request at argument `+Dh`). With no request it replays the displaced prologue and resumes the original callback. With a request it calls the state's original virtual LIMBER_STATE selector and returns that key using the original RET 4 callback contract.

The generic native FSM (`11374CF0`) performs the old-state exit and new-state entry. LIMBER_STATE runs the original `10188A70` entry routine, which clears pending movement and dispatches normal gun/carriage limber operations, followed by the original `10188CC0` attachment-completion predicate. No per-model completion bits are forged. The already-cancellable later reform state is left untouched.

The intended recovery is to click Limber when an attempted deployment is blocked, let native limbering finish, move away, and deploy again. This is not an automatic obstacle-placement correction. Carriage movement still obeys normal engine rules.

## Verification and status

The original predicate was byte-decoded before and after the change: the three deployment keys become eligible, the limber key remains ineligible, and other keys retain their original result. Two callback adapters were byte-decoded across request/no-request values, two image bases and register seeds. All 14 predicate and 48 callback ABI cases pass. Native callback returns, vtable selectors and normal-path register liveness were checked against original instruction bytes.

Whole-image comparison permits only the six guarded write ranges (three branch edits, two prologues and one padding region). Original engine size and all unrelated bytes remain unchanged. The current source includes accepted Alt-drag, fear, agent-disembark and FOTS farm-hover changes; none is reconstructed or removed. No compiler, other project material, data-pack edit or backup is used.

Installed engine SHA256: `0d6e29bdfb3d2d9d35c21cb0cdf36f7a50aee3a7783e2f9af991523d654452ab`.

Recipe `234-artillery-unlimber-recovery.json` remains disabled for release packaging; the installed local overlay is now user-confirmed working. Explicit local overlay installation is recorded in `outputs/artillery-unlimber-recovery-installed.json`; static/ABI results are in `outputs/artillery-unlimber-recovery-verification.json`.

After launching the installed overlay, the user confirmed on 2026-11-07: "it's fixed, good job". This records successful user gameplay validation of the reported issue. The exact artillery type, obstacle and individual recovery steps were not specified; do not infer exhaustive coverage of every battery or deployment situation. Acceptance receipt: outputs/artillery-unlimber-recovery-user-acceptance.json.
