# Project instructions

This project targets original 32-bit SHOGUN 2 and is independent of the x64 reconstruction and CE remaster.

User requirement: work through legacy bugs **one at a time**. Do not batch fixes. Reproduce each bug on vanilla, make the smallest focused change, compare the same scenario, and check regressions before starting another fix. Do not enable historical experiments merely because recipes exist.

Keep vanilla files intact. Use workspace test outputs before any live installation. Never commit game binaries, game packs or private signing keys. Do not describe infrastructure builds or unverified candidates as released fixes.

Standing user instruction: after preparing and validating each new patch build, install it into the current OG installation unless the user explicitly says not to. Always retain a verified backup of the previous patch build (managed engine folder, root bootstrap, launcher and installation record) before replacing it. Store these backups on **F:** under `F:\Codex\Shogun-2-OG-Patch-Backups`, in a versioned/timestamped folder. This means the previous patch build, not a full vanilla-game backup. Keep these local binary backups out of GitHub and release assets. If the game is running, wait for it to close rather than replacing loaded files.

Current authorized exception: the user explicitly selected the collection bundle documented in docs/selected-collection-0.1.11.md. Implement that selection together; preserve existing ninja IDs and all ninja ammo 2. Do not expand to the excluded collection changes.
