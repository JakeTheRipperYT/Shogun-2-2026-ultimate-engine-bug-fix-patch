# Revised fear rewards: 0.1.10

The user explicitly requested the following numeric enemy-morale values, superseding the 0.1.9 choices:

| Source | Value |
| --- | --- |
| War Is Slaughter / Bloodthirsty / Blood Soaked | -4 / -5 / -6 |
| Sword of Amaterasu | -4 |
| Dreaded Force (`p_dreaded_force` effect bundle) | -4 |
| Intimidating, either current skill level | -4, unchanged |

Dreaded Force is the effect bundle, not the ROTS Dreaded skill. That separate skill retains -1/-2. Legendary Menpo retains -1, and Sword's separate inspire modifier stays at its prior value. Brave/Cowardly progression, other traits, skill effects and FOTS data remain unchanged.

The engine is byte-identical to 0.1.9. Its negative numeric contributions stack on the same source general; the strongest eligible nearby enemy aura remains the receiver rule. Level-3 trait + Sword + Intimidating yields fourteen points, or eighteen when Dreaded Force also applies. Fear range and horse fear stay unchanged.

`build-fear-stacking.py` reconstructs the recipe from the supported original pack. It validates the complete trait, ancillary, skill and effect-bundle table layouts and expected source values, then replaces only the intended floats. Exactly five fields differ from 0.1.9; the full recipe contains thirteen writes relative to vanilla. Every archive/table header, row count, key, index and file length is preserved. All unrelated bytes must compare identical.

This is a test prerelease. Existing native tests exercise the unchanged constructor and aura implementation; controlled battle confirmation of the revised rewards remains pending. Begin a new battle to construct updated battle stats.

Build validation passed: 22 installer self-tests and all existing native engine checks, including 756 fear constructor/aura cases. Full comparison of all 2,565,173,720 bytes against the verified 0.1.9 private pack found exactly five changed bytes, one in each of the five requested float fields, and no other differences. The existing Intimidating -4 values are unchanged.

- Engine SHA-256 (unchanged): `d69acf4d81c519ed9fc98480389bcccc21ada4aa773f8ab9484ce916cb04d2e8`.
- Data pack SHA-256: `c48510bc7ad4a98d411f486922e432bea64e253b9e9832a48c1d9dc40c6a91c4`.
- Signed package SHA-256: `23986a2c76b1023ac3ed8a1b2dbd5976cf995933b54c29276d48e26230b8f7d1`.
- Installer ZIP SHA-256: `90e46691c1e2d65090a6c352f7e98ba756d84d18fa249e5b2563ea45d40f3754`.
