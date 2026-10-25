"""Mori harbour recruitment and campaign movement parity corrections."""
def apply(c,packs,changes):
    source,(_,ix)=packs['data.pack'];cache={}
    def table(name):
        full=name+'_tables'
        paths=[p for p in ix if p.startswith('db\\'+full+'\\')]
        if len(paths)!=1:raise ValueError('Unique source table '+full)
        path=paths[0];raw=changes['data.pack'].get(path,c.read(source,ix,path))
        prefix,fs,rows=c.decode(raw,full)
        if c.encode(prefix,fs,rows)!=raw:raise ValueError('Roundtrip '+full)
        cache[full]=(path,prefix,fs,rows)
        return rows
    recruits=table('building_units_allowed')
    standard='Medium_Ship_Medium_Bune';mori=standard+'_Mori';harbour='SHO_Port_1_Harbour'
    original=next(r for r in recruits if r['unit']==standard and r['building']==harbour)
    if any(r['unit']==mori and r['building']==harbour for r in recruits):raise ValueError('Mori Harbour row unexpectedly present')
    row=dict(original,unit=mori,key=max(r['key'] for r in recruits)+1)
    recruits.append(row)
    standard_ports={r['building'] for r in recruits if r['unit']==standard}
    mori_ports={r['building'] for r in recruits if r['unit']==mori}
    if standard_ports!=mori_ports:raise ValueError('Mori port tiers still differ')
    units=table('units')
    ship=next(r for r in units if r['key']=='Galleon_Caravel_Mori')
    reference=next(r for r in units if r['key']=='Galleon_Caravel')
    if ship['campaign_action_points']!=40 or reference['campaign_action_points']!=65:raise ValueError('Unsupported Nanban movement baseline')
    ship['campaign_action_points']=reference['campaign_action_points']
    agents=table('agents');ikko=next(r for r in agents if r['key']=='ikko_monk');monk=next(r for r in agents if r['key']=='monk')
    if ikko['move_points']!=20 or monk['move_points']!=30:raise ValueError('Unsupported monk movement baseline')
    ikko['move_points']=monk['move_points']
    for full,(path,prefix,fs,rows) in cache.items():
        raw=c.encode(prefix,fs,rows)
        if c.decode(raw,full)[2]!=rows:raise ValueError('Rebuilt roundtrip '+full)
        changes['data.pack'][path]=raw
    return dict(moriMediumBunePort=harbour,recruitmentKey=row['key'],nanbanMovementBefore=40,nanbanMovementAfter=65,ikkoMonkMovementBefore=20,ikkoMonkMovementAfter=30)
