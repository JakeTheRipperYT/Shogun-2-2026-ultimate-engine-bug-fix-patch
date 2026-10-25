# Yari abilities and Ikko Warrior Nuns, 0.1.12

Requested scope: add campaign-unlockable Yari Square to Yari Samurai and default availability in multiplayer, give Yari Ronin Rapid Advance, and allow Ikko Ikki to recruit Warrior Nuns at the normal campaign technology tier and select them in multiplayer.

## Ability links

Add pike_square_formation to Inf_Spear_Yari_Samurai, _Hattori, _Dojo and _MP. Keep requires_effect_enabling true: the existing tech_enable_pike_square effect unlocks it through shogun_military_spear_spear_expertise (Spear Expertise) in campaign and shogun_custom_battle_tech for custom battles. This uses the same existing formation and unlock path as Yari Heroes. It does not remove the campaign research requirement or change formation statistics. Avatar Conquest battle availability should be checked in game; this does not alter veteran skill trees.

Add rapid_advance to Inf_Spear_Yari_Ronin. This existing ability is ungated and retains its original duration, cooldown and effects. No Ronin combat statistics change.

## Ikko access without changing other clans

The original Inf_Heavy_Warrior_Nuns is restricted to rel_buddhist and the japan military group. Ikko Ikki uses rel_ikko and its own military group, and lacks Warrior Nun recruitment rows in its temple chain. Changing only the roster link would leave campaign recruitment blocked by religion.

Add Inf_Heavy_Warrior_Nuns_Ikko_Ikki as an isolated copy of the ordinary campaign/custom-battle Warrior Nuns. It uses rel_ikko, the ikko_ikki military group and an explicit Ikko faction permission. Preserve unit costs, upkeep, campaign cap 4, custom-battle cap 1, all three multiplayer era flags, exact combat stats, voices and the original model/uniform filenames. Keep the original unit and all other clans' religion rules unchanged. Copy the seven original AI quality links. A single English name alias displays the existing name “Warrior Nuns”; description and recruitment movie reuse their original references. The internal copy has no duplicate encyclopedia listing. The original Avatar Warrior Nuns and their entitlement/upgrade records remain unchanged.

Add recruitment at:

| Building | Matching standard building | Required art | Recruitment XP |
| --- | --- | --- | --- |
| Jodo Shinshu Fortified Monastery | Temple Complex | Scholarship | 2 |
| Jodo Shinshu Honganji | Legendary Temple | Neo-Confucianism | 3 |

Both pairs already require identical arts; no technologies or building requirements are changed. No availability is added at the two earlier Ikko temple tiers. Recruitment inherits the original row's other fields, including its existing enabled flag representation.

## Construction and validation

The unit-access module runs after the selected collection integration and current trait/fear changes. Schema 3 still reconstructs private data, models and English localisation packs from supported originals. The engine and launcher behavior are unchanged from 0.1.11. Build/test temp, developer packs, logs and release downloads stay in the F: workspace.

The independent archive verifier does not call the unit-access module. It reconstructs expected changes separately, checks Spear Expertise/custom-battle effect relationships, equal temple research tiers, exact cloned stats and original religion preservation, unique DB keys, and all entries outside the selected scope. Prior collection and trait/fear expectations are retained. Automated checks cannot establish battle UI availability or existing-save campaign recruitment; those require player testing.
