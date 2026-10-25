"""Requested Yari ability links and isolated Ikko Warrior Nun recruitment.

Applied after the selected collection and existing trait/fear changes.
"""
SAMURAI=('Inf_Spear_Yari_Samurai','Inf_Spear_Yari_Samurai_Hattori',
         'Inf_Spear_Yari_Samurai_Dojo','Inf_Spear_Yari_Samurai_MP')
NUNS='Inf_Heavy_Warrior_Nuns'
IKKO=NUNS+'_Ikko_Ikki'
TEMPLES=('SHO_Ikko_Temple_3_Jodo_Shinshu_Fortified_Monastery',
         'SHO_Ikko_Temple_4_Jodo_Shinshu_Honganji')


def apply(c,packs,changes):
    source,(_,ix)=packs['data.pack']; cache={}
    def table(name):
        full=name+'_tables'
        if full not in cache:
            paths=[p for p in ix if p.startswith('db\\'+full+'\\')]
            if len(paths)!=1: raise ValueError('Unique original table '+full)
            path=paths[0];raw=changes['data.pack'].get(path,c.read(source,ix,path))
            prefix,fs,rows=c.decode(raw,full)
            if c.encode(prefix,fs,rows)!=raw:raise ValueError('Roundtrip '+full)
            cache[full]=(path,prefix,fs,rows)
        return cache[full][3]
    def add(rows,row,keys):
        matches=[r for r in rows if all(r[k]==row[k] for k in keys)]
        if matches:raise ValueError('Unexpected existing requested row '+str(row))
        rows.append(row)
    abilities=table('unit_to_unit_abilities_junctions')
    for unit in SAMURAI:add(abilities,dict(unit_name=unit,ability='pike_square_formation'),('unit_name','ability'))
    add(abilities,dict(unit_name='Inf_Spear_Yari_Ronin',ability='rapid_advance'),('unit_name','ability'))
    units=table('units'); original=next(r for r in units if r['key']==NUNS)
    if original['religion_requirement']!='rel_buddhist':raise ValueError('Unsupported Nun source religion')
    unit=dict(original,key=IKKO,religion_requirement='rel_ikko',
              unique_index=max(r['unique_index'] for r in units)+1,in_encyclopedia=False)
    add(units,unit,('key',))
    land=table('unit_stats_land'); add(land,dict(next(r for r in land if r['key']==NUNS),key=IKKO),('key',))
    uniforms=table('uniforms'); original_uniforms=[r for r in uniforms if r['Unit']==NUNS]
    if len(original_uniforms)!=1:raise ValueError('Unexpected original Nun uniform count')
    add(uniforms,dict(original_uniforms[0],Unit=IKKO,Uniform_Name='Default_Warrior_Nuns_Ikko_Ikki'),('Faction','Unit'))
    groups=table('units_to_groupings_military_permissions')
    add(groups,dict(unit=IKKO,military_group='ikko_ikki'),('unit','military_group'))
    permissions=table('units_to_exclusive_faction_permissions')
    add(permissions,dict(key=IKKO,faction='ikko_ikki',allowed=True),('key','faction'))
    recruitment=table('building_units_allowed'); next_key=max(r['key'] for r in recruitment)+1
    counterparts=('SHO_Buddhist_3_Temple_Complex','SHO_Buddhist_4_Legendary_Temple')
    for i,(building,original_building) in enumerate(zip(TEMPLES,counterparts)):
        row=next(r for r in recruitment if r['unit']==NUNS and r['building']==original_building)
        add(recruitment,dict(row,unit=IKKO,building=building,key=next_key+i),('key',))
    quality=table('cdir_unit_qualities'); originals=[r for r in quality if r['unit_key']==NUNS]
    if len(originals)!=7:raise ValueError('Unexpected Nun AI quality coverage')
    for r in originals:add(quality,dict(r,unit_key=IKKO),('config_key','group_key','unit_key'))
    for full,(path,prefix,fs,rows) in cache.items():
        raw=c.encode(prefix,fs,rows)
        if c.decode(raw,full)[2]!=rows:raise ValueError('Rebuilt roundtrip '+full)
        changes['data.pack'][path]=raw
    lp='text\\db\\units.loc';ls,(_,li)=packs['local_en.pack']
    version,rows=c.loc(changes['local_en.pack'].get(lp,c.read(ls,li,lp)))
    original_name=next(r for r in rows if r['key']=='units_on_screen_name_'+NUNS)
    add(rows,dict(original_name,key='units_on_screen_name_'+IKKO),('key',))
    changes['local_en.pack'][lp]=c.encode_loc(version,rows)
    return dict(squareUnits=list(SAMURAI),squareCampaignArt='shogun_military_spear_spear_expertise',
                squareMultiplayerArt='shogun_custom_battle_tech',rapidAdvanceUnit='Inf_Spear_Yari_Ronin',
                ikkoNunUnit=IKKO,ikkoNunIndex=unit['unique_index'],recruitmentKeys=[next_key,next_key+1],
                recruitmentTemples=list(TEMPLES),originalNunReligionPreserved=True,originalNunStatsPreserved=True)
