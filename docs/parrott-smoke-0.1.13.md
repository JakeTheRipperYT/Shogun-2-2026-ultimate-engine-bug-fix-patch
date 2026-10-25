# Parrott firing smoke, 0.1.13

The user reports no firing effect on FOTS Parrott guns and explicitly requested the same smoke as the Armstrong gun. The user also confirmed the 0.1.12 unit-access changes work in game.

Both Boshin_Art_Parrot_Guns and Boshin_Art_Parrot_Guns_MP use boshin_parrott_cannon, which maps to boshin_parrot_gun_shell. Its launch_particle_effect is null in vanilla. The otherwise corresponding Armstrong shell uses Cannon_common_shot_lrg, an existing particle_effects record.

Set only boshin_parrot_gun_shell.launch_particle_effect to Cannon_common_shot_lrg. Preserve its howitzer gun_type, audio, damage, reload, range, muzzle velocity, gravity, explosion, first-person effect and existing flight-trail fields. Its flight-trail fields already match Armstrong. This restores the requested firing smoke and does not introduce an additional continuous shell trail.

The selected Workshop collection also supplied this smoke reference but bundled unrelated gun_type/audio-category edits. Those edits are excluded. No particle assets, sound banks or engine code are replaced.

The independent archive verifier checks the effect exists, both Parrott variants resolve to the corrected projectile, all other projectile fields/rows match vanilla, and all earlier patch data remains as expected. Existing installer/native checks also run. Developer output, temporary files and prior-build backups stay on F:. Actual smoke appearance requires an in-game firing test.
