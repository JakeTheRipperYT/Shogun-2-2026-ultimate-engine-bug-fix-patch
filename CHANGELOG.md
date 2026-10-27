# Included changes - 0.1.44

## New since 0.1.40

- Combine setup, updates, mod profiles and Play in one larger window, with both panels always visible.
- Keep Uninstall and Cancel on separate full-width rows and keep controls within the window when resized.
- Discover local and Steam Workshop `.pack` mods, excluding PNG thumbnails and duplicate entries caused by equivalent Steam paths.
- Add named profiles, manual order controls, dependency-based Auto-sort and checks for missing dependencies, cycles, conflicting filenames and overlapping file paths.
- Stage selected mods without editing their originals and restore the original Steam mod script after the game closes. Correct native paired-comment syntax so generated mod commands reach the engine.
- Install the combined launcher next to `UltimatePatch/mods`, preserve user mods/profiles through updates, and retain a verified signed package for offline repair.
- Allow the installed launcher to update its managed files safely and open repair controls when managed engine files are missing.
- Add local error logging for startup and launcher operations.

Use the new installer ZIP once when updating from 0.1.40 or earlier; older installers safely reject this package. Movie-type packs already in game `data` keep the engine's automatic loading behavior.

The combined launcher has player confirmation. The installed files match the signed package and the original game files remain intact. Focused checks cover 34 mod-core cases, 37 compiled native-helper scenarios with simulated Windows APIs, 35 setup checks, 32 installed-launcher checks and 39 combined UI checks. Broader game/mod-combination stability remains under testing. Engine and gameplay data are byte-for-byte unchanged from 0.1.40.

## Previous update: 0.1.40

### New since 0.1.34

- Correct firing sound selection for affected matchlock, bow and torch projectiles that could incorrectly use cannon audio.
- Keep battle unit status text together at the original tooltip size, preserving fonts, positions, colours and ordinary spaces, including **general nearby**.
- Allow nearby land armies on either side to reinforce night battles when their own leading general has night-battle ability. The attacking army and direct target remain included; normal reinforcement range and alliance rules still apply.
- Make night reinforcement portraits, unit cards, exclusion tooltips and reinforcement totals match each army's eligibility. Preserve normal day, naval and artillery restrictions.

Night reinforcement participation and the deployment UI were confirmed in player testing. The tooltip correction was also confirmed. Wider campaign, battle-result and multiplayer testing remains ongoing; multiplayer desync investigation is separate.

## Full cumulative gameplay changelog

- Allow units in Yari Wall to accept movement orders while engaged in melee.
- Allow movement orders while Kneel Fire is enabled.
- Correct naval defender AI so defending fleets use the active attack behaviour and select an opposing fleet.
- Remove unnecessary standing-idle animation delays before the first Fire by Rank volley.
- Make fear contributions from traits, items and skills combine numerically instead of collapsing to a flat −4 penalty or cancelling one another.
- Set War Is Slaughter/Bloodthirsty/Blood Soaked enemy-morale penalties to −4/−5/−6.
- Set Sword of Amaterasu and Dreaded Force enemy-morale penalties to −4 each.
- Normalize both Intimidating levels to a −4 contribution and ROTS Dreaded levels to −1/−2.
- Make Brave morale bonuses progress through +1/+2/+3.
- Make Cowardly morale penalties progress through −1/−2/−3.
- Add Yari Square to ordinary, Hattori, dojo and multiplayer Yari Samurai: unlock through Spear Expertise in campaign and the existing default custom-battle unlock.
- Give Yari Ronin Rapid Advance.
- Add Warrior Nuns to Ikko Ikki recruitment at the Jodo Shinshu Fortified Monastery after Scholarship and at Honganji after Neo-Confucianism, with recruitment XP of 2 and 3 respectively.
- Add Warrior Nuns to the Ikko Ikki custom/multiplayer roster through an Ikko variant using the original unit’s combat stats, costs, caps, voices and appearance.
- Set ammunition to 2 for all eight existing Kisho Ninja variants, including clan, hero, multiplayer and FOTS variants.
- Correct Hattori and Tokugawa Kisho Ninja stats to melee attack 17, melee defence 11, accuracy 50 and loading skill 70.
- Add the six missing melee/ranged infantry fatigue rows: tired/very tired/exhausted movement, charge and melee penalties of −10%/−25%/−50%, and accuracy penalties of −5%/−10%/−15%.
- Give Hattori Matchlock Ashigaru, Ikko Ikki Matchlock Ashigaru and Hattori Matchlock Samurai the firearm officer instead of the katana officer.
- Apply the general’s bow-accuracy bonus to Bow Ronin, Hattori Bandits, Chosokabe Daikyu Samurai, Bow Cavalry and Takeda Bow Cavalry.
- Add missing Ikko monk recruitment XP bonuses to holy sites: Holy Site +1, Mountain Hermitage +1, Pilgrim Hostel +2, Fortified Monastery +1 and Great Soja Shrine +2.
- Correct ship bailing, flooding, sinking and hull-section critical thresholds across the affected naval roster.
- Correct the fire-risk modifier for standard, Mori and multiplayer Sengoku Bune to 1.0.
- Restore the missing Mori campaign ship-movement bonus.
- Restore Heavy Bune oar placement.
- Restore FOTS Parrott gun firing smoke using the Armstrong gun’s Cannon_common_shot_lrg effect for both Parrott variants.
- Correct the Oda banner model and its flower/umbrella textures.
- Replace twelve original-campaign and FOTS loading images with correctly proportioned 1920×1080 versions.
- Add colour formatting to 93 UI status strings while retaining their original wording.
- Add a separate OG launcher and patched bootstrap with Steam checks, duplicate-instance protection and argument forwarding.
- Make Install/Update reconstruct private data.pack, models.pack and English localisation packs from the player’s original files.
- Add signed reconstruction packages, installer compatibility checks, verified installation, rollback handling and ownership-protected uninstall.
- Add Mori Medium Bune recruitment at the Harbour, matching the ordinary variant’s earliest recruitment port.
- Increase Mori Nanban Trade Ship base campaign movement from **40 to 65**, matching the Nanban ship available to Otomo.
- Increase Ikko monk agent base movement from **20 to 30**, matching regular monks.
- Allow player battle groups containing one land unit or ship.
- Retain groups with one remaining member and show single-member group frames safely in compact UI mode.
- Remove the engine record when a group loses its last UI member, preventing stale group IDs from making recreated single-unit groups unresponsive.
- Raise the siege cached-route work threshold from 500 to 2000 per navigation update as a mitigation trial.
- Preserve deliberately overlapping player locked land-group formations when saving, moving and rotating their layouts.
- Preserve overlap through direct, copied and composite drag placement while retaining checks against other groups.
- Correct locked-group ownership lookup to prevent the battle-load crash introduced during the formation trial.
- Aim land siege equipment, including cannons and mangonels, at target formation centres with consistent native range and firing-arc checks.
- Restrict centre aiming to land siege equipment, retaining ordinary infantry, rocket, crew and naval targeting.
- Set Hard and Very Hard AI core marksmanship difficulty multipliers to 1.0 for land and naval units, including Legendary's Very Hard battle tier.
- Remove the matching AI loading-skill additions while preserving earned unit bonuses, player/Easy behavior and other difficulty effects.
- Prioritize weapon/projectile compatibility over unit preference in firing sound selection, preventing cross-weapon cannon audio on affected bow, matchlock and torch cases; preserve incoming sound selection.

- Keep the battle unit status line together using native no-wrap, with original tooltip size, positions, fonts, colours and ordinary spaces.

- Allow additional normally eligible land armies on either side to reinforce night battles when their own leading general has effective night-battle ability; preserve attacker and direct target.
- Display qualified night reinforcements consistently in deployment portraits, unit cards, exclusion tooltips and reinforcement totals while preserving day, naval and artillery restrictions.
