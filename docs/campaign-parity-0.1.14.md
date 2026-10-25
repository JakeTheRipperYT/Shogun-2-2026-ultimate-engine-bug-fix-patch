# Mori recruitment and campaign movement parity, 0.1.14

The user requested three specific campaign corrections together.

## Mori Medium Bune

The standard Medium_Ship_Medium_Bune has recruitment at SHO_Port_1_Harbour, Trading Port, Military Port, Drydock, Nanban Trade Port and Nanban Quarter. Medium_Ship_Medium_Bune_Mori has the same higher-port links but lacks the Harbour row. Existing faction permissions already allow the Mori variant for Mori and exclude the ordinary variant.

Copy the ordinary Harbour recruitment row for the Mori variant, retaining XP0, conditions, faction and enabled-field representation. Append the new unique key after the existing Ikko Nun rows, preserving their keys and all existing unit IDs. Expected new key4722. Recruitment port sets then match exactly. Do not change technologies, ship costs, stats, existing higher-port links or faction permissions.

## Mori Nanban Trade Ship

Galleon_Caravel_Mori has campaign_action_points40; Galleon_Caravel, the Nanban ship available to Otomo, has65. Raise only the Mori unit's base budget to65. Preserve the existing Mori clan movement bonus, character bonuses, combat speed and all other ship fields. Actual travel distance can still vary with the normal campaign bonuses and fleet composition.

## Ikko monk agent

agents.ikko_monk.move_points is20, compared with agents.monk.move_points30. Raise the Ikko base budget to30. Preserve religion, costs, agent cap, line of sight, skill effects and other agents. Saved current-turn remaining points can reflect the existing turn state; the data change sets the normal movement budget.

## Construction and checks

The campaign-parity module runs after the existing unit-access module, preserving prior unit and recruitment identities. All earlier fixes, ninja ammo2, Hattori/Tokugawa melee attack17 and the Parrott smoke reference remain enabled. Engine, models and localisation are unchanged from0.1.13.

The independent verifier reconstructs the expected changes separately: one missing Harbour row, one existing ship movement field and one existing agent movement field. It also checks equal Medium Bune port sets, unique keys and all previous patch expectations, then compares untouched archive entries byte-for-byte. Build and compiler/test temporary files remain on F:. Previous-build backups remain on F:; only the live patch is retained in the C: game directory after verified rollback cleanup. In-game campaign recruitment and movement need player testing.
