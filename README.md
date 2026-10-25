# Shogun 2 — 2026 Ultimate Engine Bug Fix Patch

By JakeTheRipper. For original **32-bit Total War: SHOGUN 2**, Steam app 34330, separate from CE and the x64 reconstruction.

## Current build

[0.1.34 — Neutral ranged battle difficulty](https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/tag/v0.1.34-neutral-ranged-difficulty) is a cumulative gameplay test release. It includes the prior engine/data fixes, locked formation corrections and siege-equipment centre aiming. Hard and Very Hard now give land/naval AI no extra core marksmanship or loading skill; other difficulty effects and earned unit bonuses remain.

[Full included changelog](CHANGELOG.md).

The siege work-budget adjustment remains a mitigation trial. Version 0.1.34 has passed native and installer checks; the new difficulty change still needs player battle testing. Graphics/shader experiments are disabled and are not included.

## Install and launch

1. Download `Shogun2UltimatePatch_Installer.zip` from the release while signed into a GitHub account with access, then extract it. The setup EXE is also available directly.
2. Run `Shogun2UltimatePatch_Setup.exe` and select your OG SHOGUN 2 installation.
3. Choose **Offline… → Use included release (offline)**, then **Install / Update**. The installer embeds the complete signed cumulative package; earlier patch builds are not required.
4. With Steam running, use `Launch_Shogun2_Ultimate_Patch.exe` in the game folder.

This repository is private. Its credential-free updater cannot retrieve private GitHub releases; use the included offline release or choose the downloaded `.s2ub` package. Do not copy a GitHub token into the launcher.

The installer verifies the supported vanilla inputs and reconstructs a separate patched engine and three data packs. Original game files remain intact. Release assets contain reconstruction instructions, replacement payloads and our launcher, not complete original game binaries or packs. Saves/settings are shared with OG.

## Verification

The shipped launcher passed 24 compiled-binary scenarios with simulated Windows APIs, including duplicate-game prevention, Steam checks, missing files, argument forwarding and launch failures. The installer passed 28 self-tests, including signature checks, safe update rollback and package selection. The gameplay build passed 240 native ranged difficulty cases, 147 centre-aim cases and inherited gameplay regressions. These checks do not claim a live Steam/game startup test or comprehensive multiplayer coverage.

Use `SHA256SUMS.txt` to compare release downloads. Keep a backup of the previous patch build before updating.
