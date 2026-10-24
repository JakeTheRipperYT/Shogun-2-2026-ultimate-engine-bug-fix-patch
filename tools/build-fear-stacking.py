"""Build progressive traits and the selected numeric fear reward values.

Only writes a JSON recipe. No game file or full pack is written.
"""
from pathlib import Path
import argparse,importlib.util,json,struct
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('traits',ROOT/'tools/build-trait-progression.py')
traits=importlib.util.module_from_spec(spec);spec.loader.exec_module(traits)
SKILLS=r'db\character_skill_level_to_effects_junctions_tables\character_skill_level_to_effects_junctions'
TARGETS={('general_intimidating',1):(1.0,-4.0),('general_intimidating',2):(1.0,-4.0),
         ('gem_general_dreaded',1):(1.0,-1.0),('gem_general_dreaded',2):(2.0,-2.0)}
def generate(pack):
    recipe=traits.generate(pack);index=traits.pack_index(pack)
    # Replace the previous Bloodthirsty progression, retaining Brave/Cowardly edits.
    raw_traits=traits.read_entry(pack,index,traits.TABLE)
    _,trait_rows=traits.table_rows(raw_traits,'trait-effects')
    blood=[]
    for level,amount in ((1,-4.0),(2,-5.0),(3,-6.0)):
        row=traits.only(trait_rows,key=f'S2_trait_general_bloodthirsty_{level}',effect='mod_unit_morale_enemy')
        assert row['value']==-1.0
        blood.append((index[traits.TABLE][0]+row['value_offset'],amount,level))
    positions={offset for offset,_,_ in blood}
    recipe['writes']=[w for w in recipe['writes'] if int(w['offset'],0) not in positions]
    for offset,amount,level in blood:
        recipe['writes'].append({'offset':hex(offset),'expect':struct.pack('<f',-1.0).hex(' '),'bytes':struct.pack('<f',amount).hex(' '),'note':f'Bloodthirsty level {level}: -1 -> {amount:g}'})
    # Same-size float writes to the two requested reward rows; consume every row.
    for table,version,count_expected,key_target in (
            ('ancillary_to_effects',0,562,'s2anc_artefact_myth_sword_amateratsu'),
            ('effect_bundles_to_effects_junctions',1,389,'p_dreaded_force')):
        name=f'db\\{table}_tables\\{table}';data=traits.read_entry(pack,index,name);cursor=traits.Cursor(data)
        assert cursor.take(4)==traits.GUID_MARKER;cursor.string16()
        if version:assert cursor.take(4)==traits.VERSION_MARKER and cursor.u32()==version
        assert cursor.take(1)==b'\1' and cursor.u32()==count_expected
        matches=0
        for _ in range(count_expected):
            key=cursor.string16();effect=cursor.string16();position=cursor.pos;value=struct.unpack('<f',cursor.take(4))[0]
            if key==key_target and effect=='mod_unit_morale_enemy':
                assert value==-1.0;matches+=1
                recipe['writes'].append({'offset':hex(index[name][0]+position),'expect':struct.pack('<f',value).hex(' '),'bytes':struct.pack('<f',-4.0).hex(' '),'note':f'{key_target}: -1 -> -4 enemy morale'})
        assert cursor.pos==len(data) and matches==1
    raw=traits.read_entry(pack,index,SKILLS);c=traits.Cursor(raw)
    assert c.take(4)==traits.GUID_MARKER;c.string16()
    assert c.take(4)==traits.VERSION_MARKER and c.u32()==1
    assert c.take(1)==b'\1';count=c.u32();assert count==740
    found=set();all_source_rows=[]
    for _ in range(count):
        key=c.string16();effect=c.string16();level=c.i32();position=c.pos
        value=struct.unpack('<f',c.take(4))[0];factionwide=c.take(1)[0];assert factionwide in (0,1)
        if effect!='mod_unit_morale_enemy':continue
        target=(key,level);assert target in TARGETS and target not in found
        expected,after=TARGETS[target];assert value==expected and not factionwide
        found.add(target);all_source_rows.append((key,level,after))
        recipe['writes'].append({'offset':hex(index[SKILLS][0]+position),'expect':struct.pack('<f',value).hex(' '),
                                 'bytes':struct.pack('<f',after).hex(' '),'note':f'{key} level {level}: {value:g} -> {after:g}; use negative numeric fear, retaining Intimidating magnitude 4'})
    assert c.pos==len(raw) and found==set(TARGETS)
    recipe['writes'].sort(key=lambda w:int(w['offset'],0))
    source,after=traits.streamed_hashes(pack,recipe['writes']);assert source==traits.SOURCE_SHA256
    recipe.update(id='trait-progression-and-fear',title='Progressive traits and additive numeric fear rewards',
                  description='User-selected values: War Is Slaughter/Bloodthirsty/Blood Soaked -4/-5/-6, Sword of Amaterasu -4, Dreaded Force bundle -4. Keep both Intimidating levels -4, ROTS Dreaded -1/-2, Legendary Menpo -1 and prior Brave/Cowardly progression. Paired engine adapter preserves their combined numeric magnitude. Other effects, FOTS data and every archive structure byte remain unchanged.',sha256=after)
    assert len(recipe['writes'])==13
    return recipe
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'patches/data/trait-progression.json');p.add_argument('--check',action='store_true');a=p.parse_args()
    pack=(a.game_dir/'data/data.pack').resolve();output=a.output.resolve()
    assert output!=pack and output.suffix.lower()=='.json'
    recipe=generate(pack)
    if a.check:assert json.loads(output.read_text(encoding='utf-8'))==recipe
    else:output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'verified' if a.check else 'generated','writes':len(recipe['writes']),'sourceSha256':recipe['sourceSha256'],'sha256':recipe['sha256'],'gameModified':False}))
if __name__=='__main__':main()
