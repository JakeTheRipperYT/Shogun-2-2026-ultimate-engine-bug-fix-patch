"""Build signed-package input recipes from selected collection changes and local originals.

No game file is written. Players need only the signed release, not the Workshop pack.
PFH3 archives are composed from source slices and replacement entry payloads.
Schema metadata is the selected OG field layout from RPFM's schema_sho2.ron.
"""
from pathlib import Path
import argparse, base64, hashlib, importlib.util, json, re, struct

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = json.loads((ROOT/'tools/collection-schemas.json').read_text(encoding='utf8'))
spec = importlib.util.spec_from_file_location('traits', ROOT/'tools/build-trait-progression.py')
traits = importlib.util.module_from_spec(spec); spec.loader.exec_module(traits)
NINJA = {
    'Inf_Special_Shinobi':'Inf_Special_Kisho_Ninjas',
    'Inf_Special_Shinobi_Hattori':'Inf_Special_Kisho_Ninjas_Hattori',
    'Inf_Special_Shinobi_Tokugawa':'Inf_Special_Kisho_Ninjas_Tokugawa',
    'Inf_Special_Shinobi_MP':'Inf_Special_Kisho_Ninjas_MP',
    'Inf_Special_Shinobi_Hero':'Sh_Inf_Special_Kisho_Ninja_Hero',
    'Inf_Special_Shinobi_Hero_MP':'Sh_Inf_Special_Kisho_Ninja_Hero_MP',
    'Boshin_Inf_Special_Shinobi':'Boshin_Inf_Special_Kisho_Ninjas',
    'Boshin_Inf_Special_Shinobi_MP':'Boshin_Inf_Special_Kisho_Ninjas_MP',
}

def index(path):
    with path.open('rb') as f:
        header = f.read(32)
        magic, flags, deps, dep_size, count, size = struct.unpack_from('<4s5I', header)
        if magic != b'PFH3' or deps or dep_size: raise ValueError('Unsupported PFH3 header')
        raw = f.read(size)
    c=0; offset=32+size; entries={}
    for _ in range(count):
        length=struct.unpack_from('<I',raw,c)[0]; c+=4+(8 if flags&0x40 else 0)
        end=raw.index(b'\0',c); name=raw[c:end].decode('ascii'); c=end+1
        if name in entries: raise ValueError('Duplicate archive path')
        entries[name]=(offset,length); offset+=length
    if c!=size or offset!=path.stat().st_size: raise ValueError('Archive bounds')
    return header,entries

def read(path, entries, name): return traits.read_entry(path,entries,name)

def value(c, typ):
    if typ.startswith('Optional'):
        flag=c.take(1)[0]
        if flag not in (0,1): raise ValueError('Optional flag')
        return value(c,typ[8:]) if flag else None
    if typ=='StringU16': return c.string16()
    if typ=='StringU8': return c.take(struct.unpack('<H',c.take(2))[0]).decode('utf8')
    if typ=='Boolean':
        x=c.take(1)[0]
        if x not in (0,1): raise ValueError('Boolean')
        return bool(x)
    fmt={'I32':'i','I16':'h','I64':'q','F32':'f','F64':'d'}[typ]
    return struct.unpack('<'+fmt,c.take(struct.calcsize(fmt)))[0]

def string16(s):
    b=s.encode('utf-16le'); return struct.pack('<H',len(b)//2)+b

def encoded(x,typ):
    if typ.startswith('Optional'): return b'\0' if x is None else b'\1'+encoded(x,typ[8:])
    if typ=='StringU16': return string16(x)
    if typ=='StringU8':
        b=x.encode('utf8'); return struct.pack('<H',len(b))+b
    if typ=='Boolean': return bytes([int(x)])
    return struct.pack('<'+{'I32':'i','I16':'h','I64':'q','F32':'f','F64':'d'}[typ],x)

def decode(raw, table):
    c=traits.Cursor(raw); version=0
    if raw[:4]==traits.GUID_MARKER: c.take(4); c.string16()
    if raw[c.pos:c.pos+4]==traits.VERSION_MARKER: c.take(4); version=c.u32()
    if c.take(1)!=b'\1': raise ValueError('Table enabled flag')
    prefix=raw[:c.pos]; count=c.u32(); fs=SCHEMAS[table][str(version)]
    rows=[{f['name']:value(c,f['type']) for f in fs} for _ in range(count)]
    if c.pos!=len(raw): raise ValueError('Table trailing bytes '+table)
    return prefix,fs,rows

def encode(prefix,fs,rows):
    return prefix+struct.pack('<I',len(rows))+b''.join(encoded(r[f['name']],f['type']) for r in rows for f in fs)

def rowkey(row,fs): return tuple(row[f['name']] for f in fs if f['key'])

def loc(raw):
    c=traits.Cursor(raw)
    if c.take(6)!=b'\xff\xfeLOC\0': raise ValueError('LOC magic')
    version=c.u32(); rows=[dict(key=c.string16(),text=c.string16(),tooltip=bool(c.take(1)[0])) for _ in range(c.u32())]
    if c.pos!=len(raw): raise ValueError('LOC bounds')
    return version,rows

def encode_loc(version, rows):
    return b'\xff\xfeLOC\0'+struct.pack('<II',version,len(rows))+b''.join(string16(r['key'])+string16(r['text'])+bytes([r['tooltip']]) for r in rows)

def selected(game, collection):
    packs={name:(game/'data'/name,index(game/'data'/name)) for name in ('data.pack','models.pack','local_en.pack')}
    _,mi=index(collection); changes={name:{} for name in packs}; audit=[]
    tables={}
    def table(name):
        name=name+'_tables'
        if name not in tables:
            matches=[p for p in packs['data.pack'][1][1] if p.startswith('db\\'+name+'\\')]
            if len(matches)!=1: raise ValueError(('Expected one original table',name,matches))
            path=matches[0]; raw=read(packs['data.pack'][0],packs['data.pack'][1][1],path)
            prefix,fs,rows=decode(raw,name)
            if encode(prefix,fs,rows)!=raw: raise ValueError('DB roundtrip '+name)
            tables[name]=(path,prefix,fs,rows,raw)
        return tables[name][2:4]
    def modrows(fragment):
        path=next(p for p in mi if p.startswith('db\\'+fragment[0]+'_tables\\') and p.split('\\')[-1]==fragment[1])
        return decode(read(collection,mi,path),fragment[0]+'_tables')[2]
    def merge(name, rows):
        fs,dest=table(name); existing={rowkey(r,fs):r for r in dest}
        for row in rows:
            k=rowkey(row,fs)
            if k in existing:
                if existing[k]!=row: raise ValueError(('Conflicting addition',name,k))
            else: dest.append(row.copy()); existing[k]=dest[-1]
    merge('building_effects_junction',modrows(('building_effects_junction','iigsxpf_building_effects_junction')))
    merge('fatigue_effects', [r for r in modrows(('fatigue_effects','fatigue_effects')) if r['unit_category'] in ('infantry_melee','infantry_ranged')])
    merge('effect_bonus_value_unit_record_junctions',modrows(('effect_bonus_value_unit_record_junctions','zzz_bow_accuracy_bug_fix')))
    merge('effect_bonus_value_basic_junction', [r for r in modrows(('effect_bonus_value_basic_junction','effect_bonus_value_basic_junction')) if r['effect']=='clan_trait_mori_ship_movement'])
    _,bundles=table('effect_bundles_to_effects_junctions')
    mori=[r for r in bundles if r['effect_bundle_key']=='t_mori' and r['effect_key']=='clan_trait_mori_ship_movement']
    assert len(mori)==1
    mori[0]['value']=15.0
    _,land=table('unit_stats_land'); byunit={r['key']:r for r in land}
    # Preserve existing IDs, models, audio and recruitment. Only port actual stat differences.
    ninja_fields=('core_marksmanship','core_loading_skill','melee_attack','melee_defence')
    for r in modrows(('unit_stats_land','unit_stats_land')):
        if r['key'] not in NINJA: continue
        dest=byunit[NINJA[r['key']]]
        for field in ninja_fields: dest[field]=r[field]
    ninjas=[r for r in land if re.search('kisho|ninja|shinobi',r['key'],re.I)]
    assert len(ninjas)>=7
    for r in ninjas: r['ammo']=2
    officers=modrows(('unit_stats_land','zzz_matchlock_officer_fix'))
    assert len(officers)==3
    for r in officers: byunit[r['key']]['officer']=r['officer']
    abilities=[]
    for r in modrows(('unit_to_unit_abilities_junctions','unit_to_unit_abilities_junctions')):
        if r['unit_name'] in NINJA: abilities.append(dict(r,unit_name=NINJA[r['unit_name']]))
    merge('unit_to_unit_abilities_junctions',abilities)
    _,naval=table('unit_stats_naval'); ships={r['key']:r for r in naval}
    # Apply fire risk independently; sinking fragment controls conflicting bailing/hull values.
    for r in modrows(('unit_stats_naval','unit_stats_naval')):
        ships[r['key']]['fire_risk_modifier']=r['fire_risk_modifier']
    for r in modrows(('unit_stats_naval','The_REAL_Sinking_Fix')): ships[r['key']].update(r)
    for r in modrows(('unit_stats_naval','unit_stats_naval')):
        ships[r['key']]['fire_risk_modifier']=r['fire_risk_modifier']
    for name,(path,prefix,fs,rows,raw) in tables.items():
        new=encode(prefix,fs,rows)
        if decode(new,name)[2]!=rows: raise ValueError('Rebuilt table roundtrip')
        if new!=raw:
            changes['data.pack'][path]=new
            oldrows=decode(raw,name)[2]; before={rowkey(r,fs):r for r in oldrows}
            audit.append(dict(path=path,beforeRows=len(oldrows),afterRows=len(rows),changes=[dict(key=rowkey(r,fs),before=before.get(rowkey(r,fs)),after=r) for r in rows if before.get(rowkey(r,fs))!=r]))
    # Overlay existing, separately validated trait/fear byte writes on entries, not archive offsets.
    fear=json.loads((ROOT/'patches/data/trait-progression.json').read_text(encoding='utf8'))
    _,di=packs['data.pack'][1]
    for w in fear['writes']:
        offset=int(w['offset'],0); expect=bytes.fromhex(w['expect']); after=bytes.fromhex(w['bytes'])
        matches=[p for p,(start,size) in di.items() if start<=offset and offset+len(after)<=start+size]
        assert len(matches)==1; p=matches[0]; start=di[p][0]; relative=offset-start
        raw=bytearray(changes['data.pack'].get(p,read(packs['data.pack'][0],di,p)))
        # Rebuilt bundle table keeps row ordering/header, so existing float offsets remain stable.
        assert raw[relative:relative+len(expect)]==expect
        raw[relative:relative+len(after)]=after; changes['data.pack'][p]=bytes(raw)
    for p in mi:
        if p.startswith('ui\\loading_screen_pictures\\') and p.endswith('.dds'):
            raw=read(collection,mi,p); assert struct.unpack_from('<II',raw,12)==(1080,1920)
            assert p in di; changes['data.pack'][p]=raw
        elif p.startswith('rigidmodels\\flags\\') or p=='rigidmodels\\naval\\heavy_bune\\placement.placement':
            changes['models.pack'][p]=read(collection,mi,p)
    assert sum(p.startswith('ui\\') for p in changes['data.pack'])==12
    assert len(changes['models.pack'])==12
    lp='text\\db\\random_localisation_strings.loc'
    version,rows=loc(read(packs['local_en.pack'][0],packs['local_en.pack'][1][1],lp)); original={r['key']:r.copy() for r in rows}
    targets={r['key']:r for r in rows}; color_count=0
    for r in loc(read(collection,mi,lp))[1]:
        if '[[rgba:' not in r['text']: continue
        old=targets[r['key']]
        # Require exact original wording, allowing only colour markup and reset tokens.
        stripped=re.sub(r'\[\[/?rgba(?::[^\]]*)?\]\]','',r['text'])
        text=r['text']
        if stripped!=old['text']:
            # One supplied line also capitalizes Death; preserve vanilla spelling.
            if stripped.casefold()!=old['text'].casefold() or text.count(stripped)!=1:
                raise ValueError(('Colour edit includes wording',r['key'],old['text'],stripped))
            text=text.replace(stripped,old['text'])
        old['text']=text; color_count+=1
    assert color_count==93
    changes['local_en.pack'][lp]=encode_loc(version,rows)
    assert loc(changes['local_en.pack'][lp])[1]==rows
    unit_spec=importlib.util.spec_from_file_location('unit_access',ROOT/'tools/unit-access.py')
    unit_access=importlib.util.module_from_spec(unit_spec);unit_spec.loader.exec_module(unit_access)
    import types
    unit_audit=unit_access.apply(types.SimpleNamespace(**globals()),packs,changes)
    return packs,changes,dict(unitAccess=unit_audit,tables=audit,ninjaAmmo={r['key']:r['ammo'] for r in ninjas},colorRows=color_count,assets=[p for c in changes.values() for p in c if not p.startswith(('db\\','text\\'))])

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def compose(source,header,entries,changes):
    if struct.unpack_from('<I',header,4)[0]&0x40: raise ValueError('Timestamp source not supported')
    names=sorted(set(entries)|set(changes),key=str.lower)
    ix=b''.join(struct.pack('<I',len(changes[n]) if n in changes else entries[n][1])+n.encode('ascii')+b'\0' for n in names)
    header=bytearray(header); struct.pack_into('<II',header,16,len(names),len(ix))
    segments=[]
    def literal(raw):
        if raw: segments.append(dict(data=base64.b64encode(raw).decode('ascii')))
    literal(bytes(header)+ix)
    for n in names:
        if n in changes: literal(changes[n]); continue
        offset,length=entries[n]
        if not length: continue
        if segments and 'offset' in segments[-1] and segments[-1]['offset']+segments[-1]['length']==offset: segments[-1]['length']+=length
        else: segments.append(dict(offset=offset,length=length))
    h=hashlib.sha256(); size=0
    with source.open('rb') as f:
        for s in segments:
            if 'data' in s:
                raw=base64.b64decode(s['data']); h.update(raw); size+=len(raw)
            else:
                f.seek(s['offset']); remaining=s['length']; size+=remaining
                while remaining:
                    raw=f.read(min(1048576,remaining))
                    if not raw: raise ValueError('Source truncated')
                    h.update(raw); remaining-=len(raw)
    return dict(id='selected-collection-'+source.stem,enabled=True,title='Selected collection fixes: '+source.name,kind='stream-compose',source='data/'+source.name,destination='data/'+source.name,sourceSha256=digest(source),length=size,sha256=h.hexdigest(),segments=segments)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--game-dir',type=Path,required=True); p.add_argument('--collection',type=Path,required=True); p.add_argument('--output',type=Path,default=ROOT/'build/collection-recipes'); a=p.parse_args()
    packs,changes,audit=selected(a.game_dir,a.collection); a.output.mkdir(parents=True,exist_ok=True)
    receipts=[]
    for name,(path,(header,entries)) in packs.items():
        recipe=compose(path,header,entries,changes[name]); destination=a.output/(path.stem+'.json')
        destination.write_text(json.dumps(recipe,separators=(',',':'))+'\n',encoding='utf8')
        receipt={k:v for k,v in recipe.items() if k!='segments'}; receipt.update(changedEntries=list(changes[name]),segments=len(recipe['segments']))
        receipts.append(receipt); print(json.dumps(receipt),flush=True)
    audit.update(packs=receipts,collectionSha256=digest(a.collection),vanillaModified=False)
    (a.output/'audit.txt').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')

if __name__=='__main__': main()

