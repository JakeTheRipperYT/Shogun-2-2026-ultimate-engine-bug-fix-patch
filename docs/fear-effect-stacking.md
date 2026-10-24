# Numeric fear rewards: investigation and trial

The user selected numeric trait/item bonuses, retaining Intimidating's vanilla four-point penalty. Target behavior: War Is Slaughter/Bloodthirsty/Blood Soaked contributes 1/2/3, Sword of Amaterasu contributes 1, and Intimidating contributes 4. On one general, level-3 trait + Sword + Intimidating therefore supplies eight points of enemy morale reduction. Legendary Menpo contributes its existing numeric one point too.

## Original failure

Vanilla `trait_level_effects` gives each Bloodthirsty level `mod_unit_morale_enemy=-1`. Sword and Legendary Menpo also use -1. Both Intimidating skill levels use +1 for that same effect. ROTS Dreaded uses +1/+2. All these sources map through `effect_bonus_value_unit_record_junctions` to `scares_men` (bonus ID 8) on 24 original general unit records. They do not directly subtract from enemy base morale.

The original unit-stat constructor at preferred VA `0x10152B23..0x10152B43` tests the combined bonus. Zero leaves innate fear unchanged; any nonzero value replaces it with the negated `ume_concerned_unit_frightened` setting, normally four. Thus the mixed signs can cancel, and an uncancelled -1/-2/-3 still becomes four. The earlier progressive-trait screenshot verified Brave's +2 effect, not Bloodthirsty's battle magnitude.

The underlying query at `0x10BCF460` selects category 0x10/unit record/bonus ID 8. Its numeric lookup at `0x10BD5EE0` reads the aggregate's floating value and rounds it. The unchanged battle fear routine at `0x10158100` considers eligible nearby enemies, takes the largest positive enemy fear strength, and emits morale reason 0x2D with its negative magnitude. Its separate horse-fear reason is 0x2C. This routine does not sum auras from different enemy units.

## Focused correction

- Keep existing negative numeric trait, ancillary and effect-bundle values. The six prior trait-progression float edits remain intact.
- Change only four skill floats: both Intimidating levels +1 to -4, ROTS Dreaded +1/+2 to -1/-2. Every vanilla contributor to this shared effect now uses the same sign, preserving numeric descriptions. FOTS source rows remain unchanged.
- In the constructor, negative values add their absolute magnitude to innate fear. Zero retains the original path. Positive legacy flags retain the original KV conversion, including positive FOTS fear flags. Saturate numeric overflow.
- Preserve range, eligible/routing filters, strongest-nearby-enemy selection, horse fear and other morale effects. Do not multiply penalties by every nearby general.

The adapter uses 71 zero bytes at `0x11793B30..0x11793B76`, disjoint from existing adapters and the shadow-pack path. Recipe090 owns the shared `.rdata` VirtualSize mapping through `0x11793B7F`. Recipe100 marks the original read-only section executable (RX, never writable), writes only this verified padding and the 33-byte constructor hook, and has no overlapping HIGHLOW relocations. It overwrites no original function in the padding area. Engine recipes retain the strict original-byte and no-overlap checks.

`build-fear-stacking.py` validates the original skill table's exact schema, all 740 rows, the four known target rows and their values, then combines these same-size edits with the existing six trait edits. The private pack is streamed from vanilla and keeps every other archive byte and all headers/indexes unchanged. No original pack or binary is distributed.

## Validation and remaining scope

`test-fear-stacking.c` executes original and candidate code in distinct native Windows x86 private mappings. Each constructor runs 122 source-combination, innate, zero, positive-flag and overflow cases. Each full fear receiver runs 256 magnitude/eligibility/horse-isolation cases. These 756 cases reproduce the old collapse/cancellation consequence and verify the selected arithmetic without modifying a live game.

Controlled campaign/battle comparison is still required after installation. The native fixtures supply the combined numeric bonus; they do not prove campaign acquisition, save compatibility or all mod interactions. Loading the old general in a newly started battle is necessary to construct new battle stats. Existing positive third-party contributions mixed with negative numeric rewards are outside this vanilla-source correction.

The full 0.1.9 build passed 22 installer self-tests, all inherited native engine checks, 2,250 redirect cases, the 756 new fear cases, and 114 recipe plus 114 built-DLL redirect emulation cases. The complete 2,565,173,720-byte data pack was independently compared: exactly 16 bytes differ, all within the ten authorized float fields; every unrelated byte and every pack/table header/index byte remains identical.

Final hashes:

- Engine: `d69acf4d81c519ed9fc98480389bcccc21ada4aa773f8ab9484ce916cb04d2e8`.
- Private reconstructed data pack: `bade4ee874f0195ce612200a2c8d39159de65d0f1b4f0cdc98467f495c38eef8`.
- Signed package: `77908ff4d130abc7249919c9add797b3926e0b3addc7fd65b3b9c9beae24f574`.
- Installer ZIP: `f4ee9494bd6ea76b0d4ac69ad5f65894e150e7521ca38b171d0096acb99451f2`.
