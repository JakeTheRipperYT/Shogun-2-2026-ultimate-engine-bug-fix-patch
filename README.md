# Shogun 2 — 2026 Ultimate Engine Bug Fix Patch

By JakeTheRipper. A separate project for original **32-bit Total War: SHOGUN 2**, Steam app 34330, independent of the native x64 reconstruction and CE remaster.

## Status

Current trial: **0.1.9-fear-test**. It retains the previous engine and progressive trait fixes, and fixes cancellation and lost magnitude when fear rewards are combined on a general. War Is Slaughter contributes -1/-2/-3, Sword of Amaterasu -1, and Intimidating retains -4. The level-3 trait + Sword + Intimidating combination therefore supplies -8 enemy morale within the existing fear range.

Ten existing float fields change: the previous six trait values plus four fear-skill sign/value corrections. Install / Update streams a private copy of vanilla data.pack, preserving its headers, index, length and every unrelated byte. The engine preserves numeric fear rewards instead of collapsing them to a flat four; positive legacy flags retain their original behavior. Nearby units still take the strongest eligible enemy aura. See [fear investigation and validation](docs/fear-effect-stacking.md) and [trait details](docs/trait-progression.md). Controlled battle validation remains pending; this is a test prerelease.

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
