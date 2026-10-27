# SHOGUN 2 - Ultimate Engine Bug Fix Patch

By **JakeTheRipper**. A community gameplay patch for the **original Steam version of Total War: SHOGUN 2 on Windows**.

Fixes battle controls, formations, artillery aiming, projectile sounds, night reinforcements, morale and other gameplay problems. The original game files stay intact.

**[Download the installer ZIP](https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/download/v0.1.44-unified-launcher/Shogun2UltimatePatch_Installer.zip)** | [Release notes](https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/tag/v0.1.44-unified-launcher) | [Full changelog](CHANGELOG.md)

**Current version: 0.1.44.** Includes all previous fixes and a larger combined launcher for installation, updates, mod selection and Play. No earlier patch, separate mod pack or GitHub account is required. Requires .NET Framework 4.8.

Using **SHOGUN 2 Complete Edition**? Use [Remastered CE](https://github.com/JakeTheRipperYT/Remastered-CE) instead.

## Install in a few steps

1. Install the original **Total War: SHOGUN 2** through Steam and close the game.
2. [Download the installer ZIP](https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/download/v0.1.44-unified-launcher/Shogun2UltimatePatch_Installer.zip), right-click it, choose **Extract All**, and open the extracted folder.
3. Run **`Shogun2UltimatePatch_Setup.exe`**. Setup and mod controls appear together in one window.
4. Check **Game folder** on the left. Use **Browse...** to choose the folder containing **`Shogun2.exe`** if needed.
5. Leave **GitHub - latest release** selected and click **Install / Update**. Wait for completion.
6. On the right, select any optional mods you want, or leave them disabled. With **Steam running**, click **Play Ultimate Patch**.

The launcher builds the patch from your supported original game files. No game files need to be copied manually.

## Play after installing

Open **`Launch_Shogun2_Ultimate_Patch.exe`** in the SHOGUN 2 game folder. A copy is also inside **`UltimatePatch`**, next to the **`mods`** folder. The installed **`UltimatePatch_Launcher.exe`** opens the same combined interface.

The normal Steam shortcut runs the original engine. Use the patch launcher to apply the engine fixes. Saves and settings are shared with the original game.

## Optional mods

- Finds local `.pack` mods and Shogun 2 Workshop packs across Steam libraries. PNG thumbnails are excluded and equivalent Steam paths are deduplicated.
- Save profiles, change the order manually, or use **Auto-sort** for pack-declared dependencies. Packs without dependency declarations receive a consistent filename order; sorting cannot guarantee compatibility.
- Reports missing dependencies, dependency cycles, conflicting filenames and overlapping file paths.
- Selected optional packs are copied into a per-user cache without editing the original mod files. The original Steam mod script is restored after the game closes.
- **Movie-type packs already in the game's `data` folder load automatically**, so their checkboxes are locked. This is a pack-loading type, not a statement about the contents. Keep Steam's original game packs in place. Only relocate mods you installed yourself if you want to manage them from `UltimatePatch/mods`.

**Patch only** disables optional selections; existing movie-type packs in `data` retain the engine's automatic loading behavior. Steam Workshop subscriptions and downloads remain managed by Steam.

## What does the patch fix?

- **Single-unit groups:** keep one-unit groups working, including after ungrouping and regrouping.
- **Locked formations:** preserve the spacing you set when moving, rotating and dragging a locked formation.
- **Artillery:** aim cannons and mangonels at the centre of enemy formations while keeping normal range checks and projectile spread.
- **Firing and morale:** reduce unnecessary first-volley delays and correct how fear, traits and morale effects combine.
- **Units and recruitment:** correct missing abilities, recruitment options, ammunition values and naval behaviour. See the [full changelog](CHANGELOG.md).
- **Projectile sounds:** correct affected matchlock, bow and torch firing sounds that could incorrectly use cannon audio.
- **Night battles:** allow normally eligible nearby armies on either side to reinforce when their own leading general has night-battle ability, with matching deployment UI.
- **Battle tooltips:** keep status text together at the original tooltip size, including an ordinary space in **general nearby**.
- **Battle difficulty:** remove extra AI accuracy and reload bonuses on Hard and Very Hard while retaining other difficulty effects.

This remains a **test release**. The combined launcher, night reinforcement participation/deployment UI and tooltip correction have player confirmation. Installation integrity, launcher startup and focused checks pass. Broader campaign, battle-result, multiplayer and mod-combination testing continues; there is no universal crash-free guarantee. The multiplayer desync investigation is ongoing. Siege pathfinding remains a mitigation trial, and graphics/shader experiments are excluded. Engine and gameplay data are unchanged from 0.1.40.

## Update from an earlier version

**Download and run this new installer ZIP once if you use 0.1.40 or earlier.** Older installers safely reject the new combined-launcher package. There is no need to uninstall first.

After that, use **Install / Update** in the combined launcher. Keep **GitHub - latest release** selected for the newest published patch. User mods and profiles are retained through updates.

## Offline installation and repair

Choose **Offline... > Use included or installed release (offline)**, then **Install / Update**. The downloaded setup includes the complete 0.1.44 package. The installed launcher also retains its verified package for offline repair while the patch is installed.

The separate `.s2ub` release asset is an optional signed update package; it is not needed for a normal installation.

## Remove the patch or report an error

Close the game and click **Uninstall** in the combined launcher. Original game files, saves, user mods and profiles are kept.

If a launcher error occurs, details are written locally to **`%LOCALAPPDATA%/Shogun2UltimatePatch/launcher-errors.log`**. Include the error text, patch version and enabled-mod list when reporting a problem.
