# Shogun 2 — 2026 Ultimate Engine Bug Fix Patch

By JakeTheRipper. A separate project for original **32-bit Total War: SHOGUN 2**, Steam app 34330, independent of the native x64 reconstruction and CE remaster.

## Status

Current development build: **0.1.2-kneel-test**, retaining the [yari-wall movement candidate](docs/yari-wall-movement.md) and adding only [kneel-fire movement](docs/kneel-fire-movement.md). Native checks pass; in-game verification remains pending. Historical experiments and diagnostics remain disabled. Test builds are staged as prereleases in the private repository.

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
