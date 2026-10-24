# Shogun 2 — 2026 Ultimate Engine Bug Fix Patch

By JakeTheRipper. A separate project for original **32-bit Total War: SHOGUN 2**, Steam app 34330, independent of the native x64 reconstruction and CE remaster.

## Status

Current trial: **0.1.8-traits-test**. It retains the yari-wall, kneel-movement, naval and initial ranked-idle fixes, and ports the three progressive general-trait corrections from CE changelog entries 10/11: War Is Slaughter enemy morale -1/-2/-3, Brave morale +1/+2/+3, and Cowardly morale -1/-2/-3.

Only six existing float fields change in the player's original OG data table. Install / Update streams a private copy of vanilla data.pack into UltimatePatch, preserving its PFH3 header, index, table headers and length. The engine redirects only read-only opens of data/data.pack to this managed copy. See [trait details](docs/trait-progression.md), [rank trial details](docs/rank-idle-first-volley.md) and [live baseline evidence](docs/rank-fire-live-baseline.md). This remains a test prerelease pending campaign validation.

## Launcher and installer

The installer reconstructs a separate engine from the player's own files. Vanilla game files remain intact. The launcher checks Steam and running OG processes, sets app 34330, forwards arguments and starts the separate bootstrap with the game root as its working directory.

Installed files:

```
Launch_Shogun2_Ultimate_Patch.exe
Shogun2_UB.exe
UltimatePatch/empire.retail.dll
UltimatePatch/data/data.pack
UltimatePatch/install-state.json
```

Saves and settings are shared with OG; use backed-up test saves during development.

## Build

Requires Visual Studio C++ tools, the .NET Framework 4.8 targeting pack and Python 3. Pass -Python with the interpreter path if python.exe is unavailable.

```powershell
.\build.ps1 -Keygen -GameDir '<OG game directory>' # first build only
.\build.ps1 -GameDir '<OG game directory>'         # subsequent builds
```

The private signing key is generated under ignored `build/keys/`. Back it up before cleaning that directory; never commit or distribute it. The matching public key is `installer/release-public.xml`. Build outputs go to `build/` and `dist/`; builds verify signatures and run installer self-tests.

The signed release contains only reconstruction instructions and our launcher. It never includes the player's 2.56 GB data pack. Builds verify the six-field recipe against vanilla and reconstruct the pack with bounded memory. The updated installer also builds the table during Install / Update. Existing 0.1.7 installers reject the new package schema safely: download the updated installer ZIP once.

[Release staging](https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases) belongs to this repository only. It is currently private, so the credential-free player updater cannot access its releases. Download the test bundle while signed in, then use Offline with its included signed package.

See [bug inventory](docs/bug-inventory.md) and [provenance](docs/provenance.md). Release packages contain reconstruction instructions and our launcher; do not distribute game binaries or packs.
