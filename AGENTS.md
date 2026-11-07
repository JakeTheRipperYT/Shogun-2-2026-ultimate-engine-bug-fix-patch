# Project instructions

## Current release authorization — 2026-11-07

The user authorized publishing the tested build after byte-for-byte installer
reconstruction checks, and explicitly authorized generating a replacement signing
key and rebuilding the installer/launcher to trust it. The missing original OG
private key cannot be recovered from published packages. CE uses a different key;
do not use CE material for this release.

Use build.ps1 and patches/release/current.json to compose the signed original
0.1.45 package plus the four accepted direct x86 engine overlays and eight fear
float edits. No engine compilation or historical collection reconstruction.
Preserve engine SHA256 0d6e29bdfb3d2d9d35c21cb0cdf36f7a50aee3a7783e2f9af991523d654452ab
and data.pack SHA256 a77c9e980635847f24d380e3abc227203d1c660f6f7c62026505b7458d257232.
The replacement private key stays in ignored build/keys/signing-key.xml; never
publish it. No backups unless the user explicitly asks. Older backup requirements
below are superseded. Release receipts belong in the project outputs folder.

## Mandatory current correction — 2026-11-06

Read the project-root AGENTS.md. Ask permission before using ANY information
from another project, including its symbols, notes, tooling or dependencies.
Only original-game DLL Ghidra exports and CE-edition Ghidra exports are expressly
allowed external reference material for this task. No restoration project use.
Trace and patch the original DLL directly using guarded binary recipes. Do not
compile code except for the launcher. The previous compiled Alt-drag approach
is REJECTED and must not be reused, built or installed. All new storage remains
inside the project on F:. Installed base is 0.1.45 with the direct x86 Alt-drag
local overlay revision 5 (2026-11-07), matching CE's exact rotation coefficient,
UI-coordinate stage and rounding. R3 added movement feedback and Ctrl+Alt rotation.
User explicitly approved reading CE's ORIGINAL DLL read-only for sensitivity and
input scaling; no other CE patch/reconstruction material is permitted.
R1 crashed; R2 corrected a missing native
stack argument and wrong ECX at 10436690. Earlier fixes remain byte-identical.
User says DON'T RESTORE, JUST FIX. No rollback/removal without user instruction.
Verify native call-site and callee instructions; inferred Ghidra prototypes can
omit stack arguments. User tested R5 and confirmed "perfect it works". Preserve this accepted build.

## Superseded restoration and Alt-drag scope (2026-11-06)

This source location was deleted and restored from our own historical branch
1868445b1531102a292061b77e894961e9f9d79a with the user's express approval.
Recover the EXACT signed 0.1.45 baseline before changing gameplay. Historical
recipes below are provenance, not the current enabled patch selection.
Implement Alt-left-drag translation and Ctrl rotation independently, without
reading, copying or adapting the other author's implementation. Keep existing
fixes and use this project's recipe/reconstruction/launcher workflow.
All new source, downloads, build products, logs, backups and temporary files
must stay within F:/Codex/Shogun-2-2026-Ultimate-Patch. Set TEMP/TMP there.
The user allows editing the managed patch in the existing Steam installation;
original game files, mods, profiles and saves must remain intact. No publishing
or game launch is authorized. Do not reuse rejected CE/weather/night builds.

This project targets original 32-bit SHOGUN 2 and is independent of the x64 reconstruction and CE remaster.

User requirement: work through legacy bugs **one at a time**. Do not batch fixes. Reproduce each bug on vanilla, make the smallest focused change, compare the same scenario, and check regressions before starting another fix. Do not enable historical experiments merely because recipes exist.

Keep vanilla files intact. Use workspace test outputs before any live installation. Never commit game binaries, game packs or private signing keys. Do not describe infrastructure builds or unverified candidates as released fixes.

Standing user instruction: after preparing and validating each new patch build, install it into the current OG installation unless the user explicitly says not to. Always retain a verified backup of the previous patch build (managed engine folder, root bootstrap, launcher and installation record) before replacing it. Store these backups on **F:** under `F:\Codex\Shogun-2-OG-Patch-Backups`, in a versioned/timestamped folder. This means the previous patch build, not a full vanilla-game backup. Keep these local binary backups out of GitHub and release assets. If the game is running, wait for it to close rather than replacing loaded files.

Current authorized exception: the user explicitly selected the collection bundle documented in docs/selected-collection-0.1.11.md. Implement that selection together; preserve existing ninja IDs and all ninja ammo 2. Do not expand to the excluded collection changes.

The user also explicitly authorized the three unit-access changes in docs/unit-access-0.1.12.md together. Preserve prior fixes and ninja ammo2. Canonical local workspace is on F:; all build/test temp files and retained artifacts must remain there.

Current focused task: user explicitly requests the Armstrong smoke effect for FOTS Parrott guns. Change only the missing launch_particle_effect reference; do not import collection gun_type/audio edits. User confirmed 0.1.12 works.

User-authorized 0.1.14 scope: Mori Medium Bune Harbour recruitment, Mori Nanban base campaign AP65, Ikko monk base AP30, as documented in docs/campaign-parity-0.1.14.md. Preserve all prior fixes and normal campaign bonus calculations.

User-authorized 0.1.15 scope: single-unit player battle groups, including land/naval UI eligibility, actual creator, nonempty group retention and safe singleton frame layout. Core battle group commands/movement already accept one. Preserve zero-selection/empty cleanup/max-capacity guards, scripting unit-controller limits and unrelated AI checks. See docs/single-unit-groups-0.1.15.md.

Current singleton regression correction: preserve both locked/unlocked singletons. Fix only owner zero-member teardown guard110DD31D (JLE to JL); retain record lookup, engine existence checks and negative-count rejection. Controlled live create/ungroup/recreate reproduced stale empty ID0 shadowing; initial fresh first-G failure was not reproduced in two controlled runs. See docs/single-unit-group-cleanup-0.1.16.md.
