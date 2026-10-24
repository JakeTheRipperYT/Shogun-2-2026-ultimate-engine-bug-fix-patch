# Shogun 2 — 2026 Ultimate Engine Bug Fix Patch

By JakeTheRipper. A separate project for original **32-bit Total War: SHOGUN 2**, Steam app 34330, independent of the native x64 reconstruction and CE remaster.

## Status

Current trial: **0.1.7-rankidle-test**, built from the verified 0.1.3 source baseline. It retains the yari-wall, kneel-movement and naval fixes, and adds only initial ranked-preparation cancellation of named standing idle clips. No replacement data packs or pack redirect are included.

The restored-build battle trace confirmed idle 155 blocking initial readiness. The signed trial passed 15 installer self-tests, the existing yari/kneel/naval native checks and 1,554 rank guard/ABI/STOP/START cases. Signed-package reconstruction matched the tested engine. Patched battle comparison is in progress; this is an experimental prerelease. See [trial details](docs/rank-idle-first-volley.md) and [live baseline evidence](docs/rank-fire-live-baseline.md).

## Launcher and installer

The installer reconstructs a separate engine from the player's own files. Vanilla game files remain intact. The launcher checks Steam and running OG processes, sets app 34330, forwards arguments and starts the separate bootstrap with the game root as its working directory.

Installed files:

```
Launch_Shogun2_Ultimate_Patch.exe
Shogun2_UB.exe
UltimatePatch/empire.retail.dll
UltimatePatch/install-state.json
```

Saves and settings are shared with OG; use backed-up test saves during development.

## Build

Requires Visual Studio C++ tools and the .NET Framework 4.8 targeting pack.

```powershell
.\build.ps1 -Keygen -GameDir '<OG game directory>' # first build only
.\build.ps1 -GameDir '<OG game directory>'         # subsequent builds
```

The private signing key is generated under ignored `build/keys/`. Back it up before cleaning that directory; never commit or distribute it. The matching public key is `installer/release-public.xml`. Build outputs go to `build/` and `dist/`; builds verify signatures and run installer self-tests.

[Release staging](https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases) belongs to this repository only. It is currently private, so the credential-free player updater cannot access its releases. Download the test bundle while signed in, then use Offline with its included signed package.

See [bug inventory](docs/bug-inventory.md) and [provenance](docs/provenance.md). Release packages contain reconstruction instructions and our launcher; do not distribute game binaries or packs.
