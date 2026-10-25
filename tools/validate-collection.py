"""Independently validate selected OG collection artifacts against local originals.

Shares only the PFH3/DB/LOC codecs with the builder. Does not invoke selected()
or trust its audit/recipe output. Unchanged archive entries are streamed and
compared byte-for-byte; selected DB changes are reconstructed independently.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, re, struct

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('codec', ROOT/'tools/build-collection.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
NINJA_MAP = {
    'Inf_Special_Shinobi':'Inf_Special_Kisho_Ninjas',
    'Inf_Special_Shinobi_Hattori':'Inf_Special_Kisho_Ninjas_Hattori',
    'Inf_Special_Shinobi_Tokugawa':'Inf_Special_Kisho_Ninjas_Tokugawa',
    'Inf_Special_Shinobi_MP':'Inf_Special_Kisho_Ninjas_MP',
    'Inf_Special_Shinobi_Hero':'Sh_Inf_Special_Kisho_Ninja_Hero',
    'Inf_Special_Shinobi_Hero_MP':'Sh_Inf_Special_Kisho_Ninja_Hero_MP',
    'Boshin_Inf_Special_Shinobi':'Boshin_Inf_Special_Kisho_Ninjas',
    'Boshin_Inf_Special_Shinobi_MP':'Boshin_Inf_Special_Kisho_Ninjas_MP',
}
OFFICERS = {
    'Inf_Missile_Matchlock_Ashigaru_Hattori',
    'Inf_Missile_Matchlock_Ashigaru_Ikko_Ikki',
    'Inf_Missile_Matchlock_Samurai_Hattori',
}
BOW = {
    'Inf_Missile_Bow_Ronin', 'UP1_Inf_Missile_Bandits_Hattori',
    'UP1_Inf_Missile_Daikyu_Samurai_Chosokabe',
    'Cav_Missile_Bow_Cavalry', 'Cav_Missile_Bow_Cavalry_Takeda',
}

def require(condition, message):
    if not condition: raise ValueError(message)

def rows_equal(actual, expected, message):
    require(actual == expected, message)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-dir',type=Path,required=True)
    p.add_argument('--collection',type=Path,required=True)
    p.add_argument('--built-dir',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    originals={n:(a.game_dir/'data'/n,c.index(a.game_dir/'data'/n)[1])
               for n in ('data.pack','models.pack','local_en.pack')}
    mi=c.index(a.collection)[1]
    expected={n:{} for n in originals}; table_cache={}; details={}
    def source_table(name):
        table=name+'_tables'
        if table not in table_cache:
            pack,ix=originals['data.pack']
            paths=[x for x in ix if x.startswith('db\\'+table+'\\')]
            require(len(paths)==1,'Unique original table: '+table)
            path=paths[0]; raw=c.read(pack,ix,path)
            prefix,fields,rows=c.decode(raw,table)
            require(c.encode(prefix,fields,rows)==raw,'Original codec roundtrip: '+table)
            table_cache[table]=(path,prefix,fields,rows,raw)
        return table_cache[table]
    def mod_rows(name, fragment):
        paths=[x for x in mi if x.startswith('db\\'+name+'_tables\\') and x.split('\\')[-1]==fragment]
        require(len(paths)==1,'Unique collection fragment: '+fragment)
        return c.decode(c.read(a.collection,mi,paths[0]),name+'_tables')[2]
    def add_rows(name,new_rows):
        _,_,fields,rows,_=source_table(name)
        bykey={c.rowkey(r,fields):r for r in rows}
        for row in new_rows:
            key=c.rowkey(row,fields)
            if key in bykey:
                rows_equal(bykey[key],row,'Conflicting selected addition: '+repr(key))
            else:
                rows.append(row.copy()); bykey[key]=rows[-1]

    xp=mod_rows('building_effects_junction','iigsxpf_building_effects_junction')
    require(len(xp)==5 and all(r['effect']=='agent_XP_mod_ikko_monk' for r in xp),'Five Ikko monk XP rows')
    require(sorted(r['value'] for r in xp)==[1,1,1,2,2],'Ikko monk XP magnitudes')
    require(all(r['building'].startswith('SHO_Region_Specialty_Holy_Site_') for r in xp),'Ikko holy-site scope')
    add_rows('building_effects_junction',xp)
    fatigue=[r for r in mod_rows('fatigue_effects','fatigue_effects') if r['unit_category'] in ('infantry_melee','infantry_ranged')]
    require(len(fatigue)==6,'Six infantry fatigue rows')
    for r in fatigue:
        level=r['fatigue_level']; rank=('threshold_tired','threshold_very_tired','threshold_exhausted').index(level)
        for f in ('run_speed','charge_bonus','melee_penalty'):
            require(math.isclose(r[f],(-.1,-.25,-.5)[rank],abs_tol=1e-7),'Fatigue '+f)
        require(math.isclose(r['firing_accuracy'],(-.05,-.1,-.15)[rank],abs_tol=1e-7),'Fatigue firing accuracy')
    add_rows('fatigue_effects',fatigue)
    bow=mod_rows('effect_bonus_value_unit_record_junctions','zzz_bow_accuracy_bug_fix')
    require(len(bow)==5,'Five bow accuracy links')
    require({r['unit_record_key'] for r in bow}==BOW,'Bow accuracy unit scope')
    require(all(r['effect']=='general_bow_bonus' and r['bonus_value_id']=='accuracy_mod' for r in bow),'Bow accuracy link type')
    add_rows('effect_bonus_value_unit_record_junctions',bow)
    mori_link=[r for r in mod_rows('effect_bonus_value_basic_junction','effect_bonus_value_basic_junction') if r['effect']=='clan_trait_mori_ship_movement']
    require(len(mori_link)==1 and mori_link[0]['bonus_value_id']=='mod_ship_movement_campaign','Mori campaign movement link')
    add_rows('effect_bonus_value_basic_junction',mori_link)
    bundles=source_table('effect_bundles_to_effects_junctions')[3]
    mori=[r for r in bundles if r['effect_bundle_key']=='t_mori' and r['effect_key']=='clan_trait_mori_ship_movement']
    require(len(mori)==1 and mori[0]['value']==1,'Original Mori movement')
    mori[0]['value']=15.0

    land=source_table('unit_stats_land')[3]; land_bykey={r['key']:r for r in land}
    ninja_keys={k for k in land_bykey if re.search('kisho|ninja|shinobi',k,re.I)}
    require(ninja_keys==set(NINJA_MAP.values()),'Exactly eight existing ninja variants')
    for key in ninja_keys: land_bykey[key]['ammo']=2
    for suffix in ('Hattori','Tokugawa'):
        r=land_bykey['Inf_Special_Kisho_Ninjas_'+suffix]
        r.update(melee_attack=17,melee_defence=11,core_marksmanship=50,core_loading_skill=70)
    for key in OFFICERS: land_bykey[key]['officer']='officer_teppo'
    abilities=[]
    for r in mod_rows('unit_to_unit_abilities_junctions','unit_to_unit_abilities_junctions'):
        if r['unit_name'] in NINJA_MAP: abilities.append(dict(r,unit_name=NINJA_MAP[r['unit_name']]))
    require(len(abilities)==13,'Thirteen collection ninja ability links')
    add_rows('unit_to_unit_abilities_junctions',abilities)

    naval=source_table('unit_stats_naval')[3]; naval_bykey={r['key']:r for r in naval}
    sinking=mod_rows('unit_stats_naval','The_REAL_Sinking_Fix')
    fire=mod_rows('unit_stats_naval','unit_stats_naval')
    require(len(sinking)==58 and len(fire)==3,'Naval fragment row scope')
    require({r['key'] for r in fire}=={'Medium_Ship_Sengoku_Bune','Medium_Ship_Sengoku_Bune_MP','Medium_Ship_Sengoku_Bune_Mori'},'Sengoku Bune fire scope')
    for r in sinking: naval_bykey[r['key']].update(r)
    for r in fire:
        require(r['fire_risk_modifier']==1.0,'Sengoku Bune fire modifier')
        naval_bykey[r['key']]['fire_risk_modifier']=1.0
    overlap={r['key'] for r in sinking}&{r['key'] for r in fire}
    require(overlap=={'Medium_Ship_Sengoku_Bune','Medium_Ship_Sengoku_Bune_Mori'},'Known two conflicting ship rows')
    for key in overlap:
        r=naval_bykey[key]
        require(math.isclose(r['water_bail_out_modifier'],.1,abs_tol=1e-7),'Sinking bailing resolution')
        require(math.isclose(r['side_panels_above_water_1_top_critical'],.25,abs_tol=1e-7),'Sinking hull resolution')
    # Independently construct the three requested unit-access changes from vanilla.
    # Do not import or execute the builder's unit-access module.
    spear_units={'Inf_Spear_Yari_Samurai','Inf_Spear_Yari_Samurai_Hattori',
                 'Inf_Spear_Yari_Samurai_Dojo','Inf_Spear_Yari_Samurai_MP'}
    unit_abilities=source_table('unit_to_unit_abilities_junctions')[3]
    before_abilities=len(unit_abilities)
    add_rows('unit_to_unit_abilities_junctions',[dict(unit_name=k,ability='pike_square_formation') for k in ('Inf_Spear_Yari_Samurai','Inf_Spear_Yari_Samurai_Hattori','Inf_Spear_Yari_Samurai_Dojo','Inf_Spear_Yari_Samurai_MP')])
    add_rows('unit_to_unit_abilities_junctions',[dict(unit_name='Inf_Spear_Yari_Ronin',ability='rapid_advance')])
    require(len(unit_abilities)==before_abilities+5,'Five requested ability links')
    ability_defs=source_table('unit_abilities')[3]
    square=next(r for r in ability_defs if r['key']=='pike_square_formation')
    require(square['requires_effect_enabling'],'Campaign square remains effect-gated')
    require(not next(r for r in ability_defs if r['key']=='rapid_advance')['requires_effect_enabling'],'Rapid Advance remains ungated')
    effect_links=source_table('effect_bonus_value_unit_ability_junctions')[3]
    require(dict(effect='tech_enable_pike_square',bonus_value_id='enable',unit_ability='pike_square_formation') in effect_links,'Square enable effect')
    technology_effects=source_table('technology_effects_junction')[3]
    for tech in ('shogun_military_spear_spear_expertise','shogun_custom_battle_tech'):
        require(dict(technology=tech,effect='tech_enable_pike_square',value=1.0) in technology_effects,'Square campaign/custom-battle unlock')
    base_nun='Inf_Heavy_Warrior_Nuns'; ikko_nun=base_nun+'_Ikko_Ikki'
    units=source_table('units')[3]; base=next(r for r in units if r['key']==base_nun)
    require(base['religion_requirement']=='rel_buddhist','Original Nun religion stays Buddhist')
    require(base['mp_available_early'] and base['mp_available_middle'] and base['mp_available_late'],'Nun multiplayer eras')
    expected_unit=dict(base,key=ikko_nun,unique_index=max(r['unique_index'] for r in units)+1,
                       religion_requirement='rel_ikko',in_encyclopedia=False)
    add_rows('units',[expected_unit])
    add_rows('unit_stats_land',[dict(land_bykey[base_nun],key=ikko_nun)])
    uniform=source_table('uniforms')[3]; base_uniform=next(r for r in uniform if r['Unit']==base_nun)
    add_rows('uniforms',[dict(base_uniform,Unit=ikko_nun,Uniform_Name='Default_Warrior_Nuns_Ikko_Ikki')])
    add_rows('units_to_groupings_military_permissions',[dict(unit=ikko_nun,military_group='ikko_ikki')])
    add_rows('units_to_exclusive_faction_permissions',[dict(key=ikko_nun,faction='ikko_ikki',allowed=True)])
    recruits=source_table('building_units_allowed')[3]; first_key=max(r['key'] for r in recruits)+1
    temple_pairs=[('SHO_Buddhist_3_Temple_Complex','SHO_Ikko_Temple_3_Jodo_Shinshu_Fortified_Monastery'),
                  ('SHO_Buddhist_4_Legendary_Temple','SHO_Ikko_Temple_4_Jodo_Shinshu_Honganji')]
    building_tech=source_table('building_level_required_technology_junctions')[3]
    for i,(standard,ikko) in enumerate(temple_pairs):
        standard_tech={r['technology_key'] for r in building_tech if r['building_level_key']==standard}
        ikko_tech={r['technology_key'] for r in building_tech if r['building_level_key']==ikko}
        require(standard_tech==ikko_tech and len(ikko_tech)==1,'Equal temple technology tier')
        source=next(r for r in recruits if r['unit']==base_nun and r['building']==standard)
        add_rows('building_units_allowed',[dict(source,unit=ikko_nun,building=ikko,key=first_key+i)])
    quality=source_table('cdir_unit_qualities')[3]
    matching=[dict(r,unit_key=ikko_nun) for r in quality if r['unit_key']==base_nun]
    require(len(matching)==7,'Nun AI quality config coverage')
    add_rows('cdir_unit_qualities',matching)

    # Verify the exact requested single-field Parrott smoke restoration.
    projectiles=source_table('projectiles')[3]
    parrott=next(r for r in projectiles if r['key']=='boshin_parrot_gun_shell')
    armstrong=next(r for r in projectiles if r['key']=='boshin_armstrong_gun_shell')
    require(parrott['launch_particle_effect'] is None,'Vanilla Parrott smoke is missing')
    require(armstrong['launch_particle_effect']=='Cannon_common_shot_lrg','Armstrong firing smoke reference')
    require(dict(key='Cannon_common_shot_lrg') in source_table('particle_effects')[3],'Smoke effect exists')
    links=source_table('gun_type_to_projectiles')[3]
    require(any(r['gun_type']=='boshin_parrott_cannon' and r['shot_type']=='boshin_parrot_gun_shell' for r in links),'Parrott gun projectile mapping')
    for key in ('Boshin_Art_Parrot_Guns','Boshin_Art_Parrot_Guns_MP'):
        require(land_bykey[key]['gun_type']=='boshin_parrott_cannon','Campaign and MP use fixed projectile')
    require(parrott['projectile_trail_particle_effect']==armstrong['projectile_trail_particle_effect'] and parrott['trail']==armstrong['trail'],'Flight trails already match Armstrong')
    require(parrott['gun_type']=='howitzer','Original Parrott gun type remains unchanged')
    parrott['launch_particle_effect']='Cannon_common_shot_lrg'

    # Requested campaign parity: exactly one recruitment row and two base budgets.
    recruits=source_table('building_units_allowed')[3]
    medium='Medium_Ship_Medium_Bune';mori_medium=medium+'_Mori'
    harbour='SHO_Port_1_Harbour'
    require(not any(r['unit']==mori_medium and r['building']==harbour for r in recruits),'Mori Harbour source row missing')
    harbour_template=next(r for r in recruits if r['unit']==medium and r['building']==harbour)
    harbour_key=max(r['key'] for r in recruits)+1
    add_rows('building_units_allowed',[dict(harbour_template,unit=mori_medium,key=harbour_key)])
    require({r['building'] for r in recruits if r['unit']==medium}=={r['building'] for r in recruits if r['unit']==mori_medium},'Equal Medium Bune recruitment port sets')
    ship=next(r for r in units if r['key']=='Galleon_Caravel_Mori')
    reference=next(r for r in units if r['key']=='Galleon_Caravel')
    require(ship['campaign_action_points']==40 and reference['campaign_action_points']==65,'Original Nanban movement budgets')
    ship['campaign_action_points']=65
    agents=source_table('agents')[3]
    ikko=next(r for r in agents if r['key']=='ikko_monk');regular=next(r for r in agents if r['key']=='monk')
    require(ikko['move_points']==20 and regular['move_points']==30,'Original monk movement budgets')
    ikko['move_points']=30

    for table,(path,prefix,fields,rows,raw) in table_cache.items():
        new=c.encode(prefix,fields,rows)
        if new!=raw: expected['data.pack'][path]=new
        before={c.rowkey(r,fields):r for r in c.decode(raw,table)[2]}
        details[table]=dict(beforeRows=len(before),afterRows=len(rows),changedRows=sum(before.get(c.rowkey(r,fields))!=r for r in rows))

    # Preserve the separately authorized trait/fear recipe exactly, including all
    # trait values already present in 0.1.10 rather than Workshop's trait table.
    recipe=json.loads((ROOT/'patches/data/trait-progression.json').read_text(encoding='utf8'))
    pack,ix=originals['data.pack']
    for w in recipe['writes']:
        offset=int(w['offset'],0); before=bytes.fromhex(w['expect']); after=bytes.fromhex(w['bytes'])
        matches=[name for name,(start,size) in ix.items() if start<=offset and offset+len(after)<=start+size]
        require(len(matches)==1,'Trait entry bounds')
        name=matches[0]; relative=offset-ix[name][0]
        raw=bytearray(expected['data.pack'].get(name,c.read(pack,ix,name)))
        require(raw[relative:relative+len(before)]==before,'Trait original value')
        raw[relative:relative+len(after)]=after; expected['data.pack'][name]=bytes(raw)

    load=[x for x in mi if x.startswith('ui\\loading_screen_pictures\\') and x.endswith('.dds')]
    models=[x for x in mi if x.startswith('rigidmodels\\flags\\') or x=='rigidmodels\\naval\\heavy_bune\\placement.placement']
    require(len(load)==12 and len(models)==12,'Twelve loading and twelve model assets')
    require(sum(x.endswith('.dds') for x in models)==10,'Ten Oda textures')
    require('rigidmodels\\flags\\sho_char_flag_oda.rigid_model_v2' in models,'Oda flag model')
    for name in load:
        raw=c.read(a.collection,mi,name)
        require(raw[:4]==b'DDS ' and struct.unpack_from('<II',raw,12)==(1080,1920),'Loading dimensions')
        expected['data.pack'][name]=raw
    for name in models: expected['models.pack'][name]=c.read(a.collection,mi,name)
    locpath='text\\db\\random_localisation_strings.loc'
    pack,ix=originals['local_en.pack']
    version,original=c.loc(c.read(pack,ix,locpath)); rows=[r.copy() for r in original]
    bykey={r['key']:r for r in rows}; colours={}
    for r in c.loc(c.read(a.collection,mi,locpath))[1]:
        if '[[rgba:' not in r['text']: continue
        stripped=re.sub(r'\[\[/?rgba(?::[^\]]*)?\]\]','',r['text'])
        vanilla=bykey[r['key']]['text']
        require(stripped.casefold()==vanilla.casefold(),'Colour wording differs')
        text=r['text'] if stripped==vanilla else r['text'].replace(stripped,vanilla)
        require(re.sub(r'\[\[/?rgba(?::[^\]]*)?\]\]','',text)==vanilla,'Vanilla wording preserved')
        bykey[r['key']]['text']=text; colours[r['key']]=text
    require(len(colours)==93,'Exactly 93 colour-only edits')
    expected['local_en.pack'][locpath]=c.encode_loc(version,rows)

    unit_loc='text\\db\\units.loc'
    version,unit_names=c.loc(c.read(pack,ix,unit_loc))
    source_name=next(r for r in unit_names if r['key']=='units_on_screen_name_Inf_Heavy_Warrior_Nuns')
    unit_names.append(dict(source_name,key='units_on_screen_name_Inf_Heavy_Warrior_Nuns_Ikko_Ikki'))
    expected['local_en.pack'][unit_loc]=c.encode_loc(version,unit_names)

    receipts=[]; unchanged_bytes=0
    for packname,(source,oldix) in originals.items():
        built=a.built_dir/'data'/packname
        _,newix=c.index(built)
        require(set(newix)==set(oldix)|set(expected[packname]),'Archive path scope: '+packname)
        require(list(newix)==sorted(newix,key=str.lower),'Sorted archive index: '+packname)
        changed=[]; checked=0
        with source.open('rb') as before, built.open('rb') as after:
            for name,(offset,length) in newix.items():
                if name in expected[packname]:
                    actual=c.read(built,newix,name)
                    require(actual==expected[packname][name],'Selected entry differs: '+packname+'/'+name)
                    if name.startswith('db\\'):
                        table=name.split('\\')[1]
                        if table in c.SCHEMAS:
                            _,fs,rs=c.decode(actual,table)
                            require(len({c.rowkey(r,fs) for r in rs})==len(rs),'Duplicate DB keys: '+name)
                            require(not any(isinstance(v,str) and v in NINJA_MAP for r in rs for v in r.values()),'Unexpected replacement Shinobi reference: '+name)
                    changed.append(name); continue
                oldoffset,oldlength=oldix[name]
                require(length==oldlength,'Unexpected length change: '+name)
                before.seek(oldoffset); after.seek(offset); remaining=length
                while remaining:
                    size=min(1048576,remaining)
                    require(before.read(size)==after.read(size),'Unexpected entry change: '+packname+'/'+name)
                    remaining-=size; unchanged_bytes+=size
                checked+=1
        receipts.append(dict(pack=packname,length=built.stat().st_size,sha256=c.digest(built),unchangedEntries=checked,selectedEntries=changed))
        print('PASS',packname,checked,'unchanged entries;',len(changed),'selected entries',flush=True)
    report=dict(result='pass',packs=receipts,tables=details,ninjaVariants=sorted(ninja_keys),ninjaAmmo=2,
                colours=93,loadingImages=12,modelAssets=12,traitWrites=len(recipe['writes']),
                unchangedBytesCompared=unchanged_bytes,vanillaModified=False,
                campaignParity=dict(moriPort=harbour,moriRecruitmentKey=harbour_key,nanbanMovement=65,ikkoMonkMovement=30),
                parrottSmoke=dict(projectile='boshin_parrot_gun_shell',field='launch_particle_effect',effect='Cannon_common_shot_lrg',changedFields=1,combatStatsPreserved=True),
                unitAccess=dict(squareUnits=sorted(spear_units),campaignSquareArt='Spear Expertise',customBattleSquareDefault=True,rapidAdvance='Inf_Spear_Yari_Ronin',ikkoNun=ikko_nun,templeTier=3,templeTechnology='Scholarship',newAbilityLinks=5,newRecruitmentRows=2),
                excluded=['Lua scripts','Tercios','replacement ninja IDs','audio changes','unrelated localisation','collection general traits'],
                gameplayValidation='pending player testing')
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('PASS independent collection artifact validation:',a.report,flush=True)

if __name__=='__main__': main()
