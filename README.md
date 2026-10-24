# Shogun 2 — 2026 Ultimate Engine Bug Fix Patch

By JakeTheRipper. A separate project for original **32-bit Total War: SHOGUN 2**, Steam app 34330, independent of the native x64 reconstruction and CE remaster.

## Status

Current trial: **0.1.10-fear-values-test**. It retains the existing engine fixes and additive numeric fear correction. War Is Slaughter's three levels now contribute -4/-5/-6, Sword of Amaterasu -4, Dreaded Force -4, and Intimidating remains -4. Level-3 trait + Sword + Intimidating supplies -14 enemy morale within the existing fear range; adding Dreaded Force supplies -18 when all four rewards apply.

Thirteen existing float fields change relative to vanilla, retaining Brave/Cowardly progression and the previous fear-skill corrections. This build changes only five data fields relative to 0.1.9; its engine is identical. Install / Update streams a private data.pack, preserving its headers, index, length and unrelated bytes. Nearby units still take the strongest eligible enemy aura. See [current values](docs/fear-values-0.1.10.md) and [fear investigation](docs/fear-effect-stacking.md). Controlled battle validation remains pending; this is a test prerelease.

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
