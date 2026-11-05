# Foundation validation — 2026-10-24

OG Steam build 11306771. This is an infrastructure baseline, with zero engine patches enabled.

- Native launcher compiled with MSVC /W4 /WX.
- Signed package built and signature verified using this project's dedicated key.
- All 15 inherited installer self-tests passed: traversal, byte output verification, package tampering, advertised-version mismatch, failed-update rollback, successful publication, uninstall ownership checks, preservation of unrelated files, version ordering, release selection, download URL restriction and cancellation.
- Build-only reconstruction from the real OG installation succeeded in an isolated workspace directory.
- Reconstructed engine matches the original SHA-256 exactly (zero writes).
- Original EXE/DLL hashes unchanged after reconstruction.
- Installer preview rendered and visually inspected; controls and labels fit.

Input hashes:

```
shogun2.exe       0ab284186e0be3fbcde34e2f800e3c0328008f3219490c7c25e822add837c4a9
empire.retail.dll 022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5
```

Self-tests used a workspace TEMP directory because directory moves were denied in the sandbox's default temporary directory. No test assertions were removed.

Not yet verified: a real game launch through the new bootstrap, live installation into the game directory, multiplayer, any engine fix, or player access to online releases (repository currently private). No game files installed or modified; no GitHub release published.
