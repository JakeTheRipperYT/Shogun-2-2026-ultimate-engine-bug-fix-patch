# Singleton group cleanup regression

Version0.1.16-single-group-cleanup-test corrects the lifecycle defect exposed by0.1.15 singleton retention.

## Reproduction and cause

A controlled live battle began with no engine groups. The first G created a working one-member locked group. G to ungroup removed its UI record but left its engine record with zero members. G to recreate reused internal ID0; the old empty record preceded the new live record. Native lookup101B3D90 selected the first matching ID,1041EBD0 rejected its zero count, and110E3020 chose empty command mode. The user confirmed the recreated unit became unresponsive.

The UI base removal10F97840 erases the last member before calling owner virtual+10 at10F97898. Both battle manager vtables resolve that callback to110DD2D0. Its old positive-count guard110DD318/110DD31C refused the zero count, so engine destruction was skipped while UI record destruction continued. Vanilla normally dissolved groups at one remaining member, which passed the old guard. Retaining a singleton made the one-to-zero path reachable in normal player grouping.

Plain-G lock/unlock uses group IDs; Ctrl+G can remove actual unit membership and recover from the stale lookup. No invariant tied to odd/even IDs was established. The earlier reported fresh-first-G failure was not reproduced in either controlled fresh attempt and should not be described as solved by inference.

## Focused correction

At110DD31D change opcode8E to8C, turning signed JLE into JL after comparison with zero. Permit teardown at count0; continue rejecting negative counts. Preserve lookup of the existing UI record, engine group existence checks, the supported land/naval mode dispatch and the exact destroy packet/ID. Keep both locked and unlocked singletons available. Existing group creation, movement, frame layout, packet protocol and group ID allocation remain intact.

The existing destroy command is sent while the UI record still exists, before its destructor frees the UI slot. Standard ordered command delivery performs teardown before a later recreation. Empty engine records already accumulated in a running battle are not rewritten; test the correction in a newly loaded battle. All data/model/localisation packs are identical to0.1.15.

## Verification

The build runs624 native fixtures at three ASLR bases:216 removal cases,360 owner-guard cases and48 same-ID recreation/selection cases. They execute real vector erase, owner guard, packet construction and land core removal/lookup/selection; naval owner dispatch is exercised and naval receiver ordering is audited separately. Same-ID recreation appends a prepared group instead of invoking the full constructor. Earlier group UI/command, installer, native engine and archive regressions also run. Controlled callbacks and command delivery fixtures do not establish live battle behavior. Player regression testing should repeat G create, G ungroup, G recreate, movement and unlock across several group numbers, plus Ctrl+G and multi-unit groups.
