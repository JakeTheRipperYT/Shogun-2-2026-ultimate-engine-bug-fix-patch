# Shogun 2 — 2026 Ultimate Engine Bug Fix Patch

By JakeTheRipper. A separate project for original **32-bit Total War: SHOGUN 2**, Steam app 34330, independent of the native x64 reconstruction and CE remaster.

## Status

Current trial: **0.1.13-parrott-smoke-test**. Restores the FOTS Parrott gun's missing firing smoke using the Armstrong gun's existing effect. Exactly one projectile field changes; ballistics, gun type and audio stay unchanged. See [smoke investigation](docs/parrott-smoke-0.1.13.md). The user confirmed the previous [Yari/Ikko unit access changes](docs/unit-access-0.1.12.md) work. All [selected collection fixes](docs/selected-collection-0.1.11.md), engine patches and current trait/fear values remain enabled. Smoke appearance awaits an in-game firing test.

[Full cumulative changelog](docs/full-changelog.md).

## Launcher and installer

The installer reconstructs a separate engine from the player's own files. Vanilla game files remain intact. The launcher checks Steam and running OG processes, sets app 34330, forwards arguments and starts the separate bootstrap with the game root as its working directory.

Installed files:

```
Launch_Shogun2_Ultimate_Patch.exe
Shogun2_UB.exe
UltimatePatch/empire.retail.dll
UltimatePatch/data/data.pack
UltimatePatch/data/models.pack
UltimatePatch/data/local_en.pack
UltimatePatch/install-state.json
```

Saves and settings are shared with OG; use backed-up test saves during development.

## Build

Requires Visual Studio C++ tools, the .NET Framework 4.8 targeting pack and Python 3. Pass -Python with the interpreter path if python.exe is unavailable.

```powershell
.\build.ps1 -Keygen -GameDir '<OG game directory>' # first build only
.\build.ps1 -GameDir '<OG game directory>' -CollectionPack '<Bug fix collection.pack>'
```

The private signing key is generated under ignored `build/keys/`. Back it up before cleaning that directory; never commit or distribute it. The matching public key is `installer/release-public.xml`. Build outputs go to `build/` and `dist/`; builds verify signatures and run installer self-tests.

The signed release contains reconstruction recipes, selected replacement payloads and our launcher, never complete original game packs. Install / Update builds three private packs from the player's supported originals using bounded streaming and verified source/result hashes. The developer build needs the collection pack; players only need the new installer. Earlier installers reject schema 3 safely, so download the updated installer ZIP once.

[Release staging](https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases) belongs to this repository only. It is currently private, so the credential-free player updater cannot access its releases. Download the test bundle while signed in, then use Offline with its included signed package.

See [bug inventory](docs/bug-inventory.md) and [provenance](docs/provenance.md). Release packages contain reconstruction instructions and our launcher; do not distribute game binaries or packs.
