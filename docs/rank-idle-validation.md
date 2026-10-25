# 0.1.7 trial validation — 2026-10-24

The trial was built from exact source commit349df1474d822486f242c4e6eb08ce3c9edb3a1c (working0.1.3), with initial rank-idle interruption as the only new gameplay change. No replacement packs or pack redirect are included.

## Package and installation

- Signed package SHA-256: `d769e96e8d39bfbe74f02f8f231d515bcc83febad208b7f18b0b5d0cc793f92b`.
- Tested/installed engine SHA-256: `3bc4d28b13b12038d28f48308276d4d3fd2c99274305acef8656f339a943a00b`.
- Exact signed embedded-package reconstruction matches the tested engine.
- Installed files and unchanged vanilla EXE/DLL were hash-verified.
- A read-only check of the running process confirmed the exact detour and90-byte adapter bytes were loaded.
- Previous working0.1.3 backup was copied and hash-verified at `F:\Codex\Shogun-2-OG-Patch-Backups\0.1.3-naval-test_before-rankidle_20261024_185505`.

## Checks passed

15 installer self-tests;10 yari branch cases;192 kneel-movement cases;28 naval factory cases;1554 rank guard/ABI/integration cases. Rank checks include integer-boundary animation IDs, all17 standing-idle IDs, excluded reload/stance clips, ESP/EBX/ESI/EDI/EBP preservation and real STOP/START evaluators. Clearing an idle does not bypass movement/time checks, and unloaded fixtures still route to RELOAD.

## First patched battle

The user reported that the fix appeared to work and chose another battle to double-check. The read-only trial capture independently shows one rank-task progression0→1→2, with each group reaching FIRE_STATE/animation130. The observed FIRE times were world137.8,142.9 and148.1. No standing-idle readiness blockers appeared in the captured samples.

Task discovery occurred after fired44 became1. Therefore this capture does **not** supply a patched initial-preparation duration to compare with the baseline's9.9 simulated seconds. No exact time saving or percentage improvement is claimed. Later-group preparation-to-fire-request handoffs were0.2 simulation seconds, consistent with the baseline's later handoffs.

Only the current rank's blocking member was retained in these samples. The trace does not directly verify previous ranks' post-fire kneeling or a complete repeated three-rank cycle. The user's additional battle check remains in progress. Keep this an experimental prerelease until broader gameplay checks are complete.
