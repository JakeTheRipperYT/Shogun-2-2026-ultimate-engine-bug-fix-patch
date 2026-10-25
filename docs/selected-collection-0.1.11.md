# Selected collection integration, 0.1.11

The user selected this bundle from [Bug fix collection, Workshop 3804538920](https://steamcommunity.com/sharedfiles/filedetails/?id=3804538920). The current engine patches and thirteen progression/fear edits remain enabled. This is a test prerelease; archive checks and native tests do not establish in-game visual or campaign behavior.

| Selection | Implemented change |
| --- | --- |
| UI text colours | 93 existing strings receive colour markup; original wording and tooltip flags remain. Even the supplied capitalization change to “Death” is excluded. |
| Loading screens | Twelve 1920×1080 replacements across the original and Boshin loading sets. |
| Oda banner | Replacement flag model and its ten flower/umbrella textures. |
| Ships | Sinking/bailing/hull corrections from the 58-row sinking fragment, plus fire-risk correction for all three Sengoku Bune variants. On overlapping rows, sinking values take precedence over the other fragment's original bailing/hull values. The Mori campaign-movement bonus also gains its missing link and value 15. |
| Kisho Ninja | Retain all eight original unit IDs, names, recruitment and saved-unit references. Hattori/Tokugawa receive attack 17, defence 11, accuracy 50 and loading 70. All eight variants, including multiplayer, heroes and Boshin, use ammunition 2. Remapped collection ability links are already present on the original IDs, so none need adding. |
| Infantry fatigue | Add six missing melee/ranged infantry rows: tired/very tired/exhausted speed, charge and melee penalties −10/−25/−50%; accuracy −5/−10/−15%. |
| Heavy Bune | Add the collection's missing oar placement file. |
| Matchlock officers | Hattori Matchlock Ashigaru, Ikko Ikki Matchlock Ashigaru and Hattori Matchlock Samurai use officer_teppo; their audio and other statistics remain vanilla. |
| Bow accuracy | Add five missing general_bow_bonus accuracy links for Bow Ronin, Hattori Bandits, Chosokabe Daikyu and both Bow Cavalry variants. |
| Ikko monk XP | Five holy-site recruitment XP links, using the supplied 1/1/2/1/2 bonuses. |

Excluded: campaign Lua, Tercios changes, collection general-trait values, sound banks and sound/voice fields, unrelated Uesugi recruitment edits, non-colour localisation, and replacement Shinobi IDs. Existing War Is Slaughter −4/−5/−6, Sword −4, Dreaded Force −4 and Intimidating −4 remain intact.

## Construction and isolation

The developer build reads supported original data.pack, models.pack and English local_en.pack, and the local collection pack. Minimal selected schema layouts come from RPFM's schema_sho2.ron. Every decoded original table must re-encode byte-exactly before editing. Original GUID/version headers are retained, counts updated, and archive indexes rebuilt in sorted order with matching body order. No foreign version markers or wholesale collection tables are imported.

Schema 3 signed recipes reconstruct private copies under UltimatePatch/data using source slices and replacement payloads. They verify original and result SHA-256 values and stream multi-gigabyte packs with bounded buffers. The player installer includes the required reconstruction payload; players do not need the Workshop collection or Python. The developer build requires the collection via -CollectionPack or OGPATCH_COLLECTION. Earlier installers reject schema 3; download the new installer ZIP.

The existing read-only CreateFileW adapter now recognizes exactly data/data.pack, data/models.pack and data/local_en.pack. Write/create requests and other paths retain original behavior. Its enlarged table and new strings occupy checked unused padding, preserving the ranked-fire and fear adapters. The native launcher requires all three packs before starting. Steam's original binaries and packs remain unchanged.

## Validation

Build receipts live under ignored build/: collection-build.log, self-test.txt, collection-validation.json and native test reports. The independent archive verifier checks every untouched entry against vanilla, enumerates field-level DB differences, verifies retained traits against the previous guarded recipe, preserves all original ninja IDs and checks exclusions. Installer tests cover schema-2 upgrades, three-pack publication, failed reconstruction rollback and ownership-protected uninstall. Native redirect, fear, rank-fire, yari, kneel and naval tests run before packaging.

## Attribution

Collection assembled by JakeTheRipper. Workshop credits include ValerBOSS (loading images), DPFLH and KamiHo (Oda banner), The_Yogi (Heavy Bune oars), Jomar Reyes (matchlock officers), markeason (bow accuracy), Egalregent (sinking) and Mneu (Ikko recruitment XP). Refer to the collection's page for its complete credits. No new ownership or licence is asserted over contributor assets or game data.
