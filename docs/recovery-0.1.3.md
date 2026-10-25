# Recovery to working OG build — 2026-10-24

User reported that installed 0.1.6-bugfixpack-test.1 did not launch and requested reinstallation of the last working version. Restored **0.1.3-naval-test** from the pre-data-pack backup after verifying its eight recorded file hashes.

Before replacement, all eleven current managed/root patch files, including approximately 6.4 GB of reconstructed packs, were copied to and SHA-256 verified at:

`F:\Codex\Shogun-2-OG-Patch-Backups\0.1.6-bugfixpack-test.1_before-restore_20261024_184233`

Restoration used:

`F:\Codex\Shogun-2-OG-Patch-Backups\20261024_132748_0.1.3-naval-test-pre-0.1.6`

All eight restored files match that backup. Restored engine hash: `29bd5cac6520322a203f7702d21431f99436198e9a46941b0f0704ad66bddd6d`. Original vanilla EXE and DLL hashes were also verified unchanged. The restored managed folder contains no replacement data packs or rank-fire experiment. The broken version remains archived on F:; no failed-build copy was retained in the game directory.

Launcher exited with code 0. The resulting Shogun2_UB process was observed running and responding, and read-only module enumeration confirmed the managed engine was loaded. This is process/load evidence; the battle and menu still require player observation. A read-only ranked-task watcher was armed for the user's test. No live memory writes or debugger breakpoints were used.

The current local workspace contains newer data-pack/installer work. It was preserved for review and must not be silently included in the next ranked-fire trial. The exact .1 package contains unsorted added pack-index blocks, an uppercase DB path and altered replacement DB headers. These are demonstrated structural differences and possible failure causes; the individual launch-failure trigger has not been isolated. Local .2 static checks do not establish that .1 or .2 launches successfully.
