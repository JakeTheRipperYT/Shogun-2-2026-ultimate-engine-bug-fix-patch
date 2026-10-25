# Progressive general trait effects

This ports entries 10/11 of the Remastered-CE GitHub changelog into original OG data. It does not alter character trait acquisition, thresholds, campaign clan traits or Fall of the Samurai traits.

| Trait line | Effect | Levels 1 / 2 / 3 |
| --- | --- | --- |
| War Is Slaughter / Bloodthirsty / Blood Soaked | mod_unit_morale_enemy | -1 / -2 / -3 |
| Brave | mod_unit_morale_local | +1 / +2 / +3 |
| Cowardly | mod_unit_morale_local | -1 / -2 / -3 |

Vanilla OG has the level-1 value repeated at all three levels. Only six floats, the level-2 and level-3 morale values, change. Cowardly level 3's separate personal_security value remains -2.

`tools/build-trait-progression.py` reads original OG `data/data.pack`, verifies the source SHA-256 and length, parses the trait effect/trait level/effect definition tables, verifies all nine intended morale rows and the security penalty, and generates `patches/data/trait-progression.json`. The recipe contains six four-byte guarded writes inside the existing `db\trait_level_effects_tables\trait_level_effects` entry. The pack length, entire PFH3 header/index, table header/GUID, row count (335), row keys and unrelated entries stay unchanged. Both source and expected output hashes are calculated by streaming; the generator never writes a full game pack or modifies the installation.

Generate/check:

```powershell
python tools/build-trait-progression.py --game-dir "C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2"
python tools/build-trait-progression.py --game-dir "C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2" --check
```

Provenance: CE source `F:\Codex\Shogun2-CE\work\install_trait_progression.py` and corrected receipt `F:\Codex\Shogun2-CE\outputs\Shogun2_CE_trait_progression\compressed_correction_20261016_030217\receipt.json`; Remastered-CE changelog entries 10/11, retained in the 0.1.16 changelog. The initial CE attempt failed because it changed a compressed PFHs entry into raw data while retaining compression metadata. That container workaround is not ported: OG is an uncompressed PFH3 pack, and this recipe changes its existing float bytes in place without rebuilding table or archive metadata.

Independent decoded-table comparison confirms that the complete corrected 40,327-byte OG table is byte-identical to the retained corrected CE table, not just equal at the six intended values. Its SHA-256 is `9313d3c154e78280781447c13c5b2072c1ea923035e1aebacab537be62143a69`. The expected whole OG pack hash after the six writes is `73d47046bd097fbec2a1c2013426e573b617b8a6cab0aa084ab651778711c752`.

Build/install verification is recorded separately; matching rows and hashes does not by itself establish campaign gameplay testing.
