# Four item fear values

User-authorized item changes on 2026-11-07:

| Item | Effect | Previous installed value | New value |
| --- | --- | ---: | ---: |
| Main-campaign Legendary Menpo | mod_unit_morale_enemy | -1 | -4 |
| FOTS Accordion | bos_enemy_morale_mod | +1 | -4 |
| FOTS Prussian Spiked Helmet | bos_enemy_morale_mod | +1 | -4 |
| FOTS Legendary Menpo | bos_enemy_morale_mod | +1 | -4 |

The existing shared fear constructor interprets negative totals numerically. Positive totals retain the vanilla enabling-flag conversion. Four negative points preserve each FOTS item's standalone four-point magnitude and permit numeric stacking on one general. Nearby general auras still use the strongest eligible source.

Main-campaign Sword of Amaterasu remains -4. Main-campaign skill/trait rewards and the ROTS Dreaded skill remain unchanged.

The established `build-fear-stacking.py` generator and `patches/data/trait-progression.json` include the four item edits. The item revision expanded the original-based recipe from 13 to 17 writes; the character revision below expands it to 21. Do not reconstruct the current installed build from this historical source tree: installation applies guarded float edits to the current managed pack, retaining all later fixes and the accepted Alt-drag engine.

`apply-fear-item-local-overlay.py` prepares a hash-verified full managed-patch backup inside this project, locates the exact installed ancillary records, and applies the four floats only after confirming the game is closed. It verifies the entire pack against its backup, allowing only those four fields, and records the updated hash as a local data overlay without changing the signed base package or existing engine overlay. Receipt: `outputs/fear-items-minus4-installed.json`.

Follow-up finding: FOTS `bos_general_4_dread` and `S2_boshin_general_bloodthirsty_1/2/3` originally retain +1 flags. The user explicitly authorized converting them, then requested tiered Bloodthirsty levels. Final requested values: Dread -4, Bloodthirsty -4/-5/-6 to match the main-campaign progression. The three trait levels are replacements, not cumulative tiers.

The `--fots-characters` mode of the same local installer applies these four character fields, with a fresh full verified backup and full-pack byte comparison. It preserves the earlier item overlay metadata as `previousOverlay`. Receipt: `outputs/fots-character-fear-tiered-installed.json`. No DLL changes or compilation are needed.

Static pack/byte verification is distinct from controlled battle testing; gameplay confirmation remains pending.
