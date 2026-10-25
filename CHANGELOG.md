# Changelog

## 0.1.12-unit-access-test

- Give Yari Samurai variants Yari Square via existing Spear Expertise/custom-battle unlocks; give Yari Ronin Rapid Advance.
- Add an isolated Ikko Warrior Nun variant to tier-3/4 Ikko temple recruitment and the Ikko custom-battle roster. Preserve the original unit, other clans' religion rules, costs, caps and combat stats.
- Preserve prior fixes; add independent unit-access and research-tier validation. Keep developer/compiler/test outputs on F:. See [details and testing limits](docs/unit-access-0.1.12.md).

## 0.1.11-collection-test

- Integrate only the selected collection fixes; see [scope and attribution](docs/selected-collection-0.1.11.md). Keep original ninja IDs and set all eight variants to 2 ammo. Preserve current progressive traits and fear values.
- Add signed schema-3 streaming reconstruction of private data, models and English localisation packs. Launcher checks all three; original game files remain intact.
- Extend private pack redirection with native path/access/ABI/ASLR checks. Add archive-wide and field-level validation plus installer upgrade, failure and uninstall checks. Gameplay validation remains pending.

## 0.1.10-fear-values-test

- Apply the user's revised War Is Slaughter/Bloodthirsty/Blood Soaked progression: -4/-5/-6 enemy morale.
- Sword of Amaterasu and the Dreaded Force effect bundle now each contribute -4. Both Intimidating levels remain -4.
- Retain the 0.1.9 engine unchanged, including numeric stacking. Preserve Brave/Cowardly progression, Legendary Menpo -1, ROTS Dreaded -1/-2, FOTS data and other reward effects.
- Exactly five float fields change relative to 0.1.9; thirteen guarded same-size writes reconstruct the private pack from vanilla. No pack headers, row counts, indexes or file sizes change.

## 0.1.9-fear-test

- Fix the shared enemy-morale effect's opposite signs: both Intimidating levels now contribute -4; ROTS Dreaded uses -1/-2. Trait, Sword and Legendary Menpo numeric values retain their existing negative sign. Other skill effects and FOTS source data stay unchanged.
- Replace the constructor's flat-four conversion for negative numeric bonuses with their absolute combined magnitude, added to innate fear. Zero and positive legacy fear flags keep vanilla behavior. Retain strongest-nearby-enemy selection, range, eligibility and separate horse fear.
- War Is Slaughter level 3 + Sword + Intimidating supplies -8, as selected by the user. This also makes the earlier -1/-2/-3 trait progression reach battle stats. The earlier Brave screenshot did not establish that enemy-morale magnitude worked.
- Private native execution covers 756 constructor/aura cases, alongside the inherited regression checks. Controlled battle comparison remains pending.

## 0.1.8-traits-test

- Port CE progressive general traits to OG: War Is Slaughter enemy morale -1/-2/-3, Brave local morale +1/+2/+3, Cowardly local morale -1/-2/-3. Exactly six level-2/3 floats change; level 1, Cowardly personal security, thresholds and FOTS rows remain unchanged.
- Install / Update builds a private data.pack from the supported vanilla pack using a signed streaming delta. Preserve every pack/table header, index and byte outside the six fields. No game packs are included in release assets.
- Add data.pack-only engine redirection with path, access, argument, stack and ASLR checks. The native launcher requires the generated private pack before launch.
- Retain the existing yari-wall, kneel-movement, naval and ranked-idle fixes. Campaign validation of this trait build is pending.
- Requires the updated installer ZIP for schema 2 packages. Private GitHub releases still require a signed-in download; the credential-free updater cannot access them.
