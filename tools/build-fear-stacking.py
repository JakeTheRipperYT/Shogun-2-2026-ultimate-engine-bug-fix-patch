"""Build the existing trait delta plus four focused fear-skill value fixes.

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
                  description='Keep the six validated progressive trait float changes. Normalize both Intimidating levels to -4 and ROTS Dreaded levels to -1/-2 so every vanilla mod_unit_morale_enemy contribution has a consistent sign. The paired engine adapter preserves the numeric sum in battle instead of replacing it with flat fear. Sword/Mask remain -1, other traits/skills, FOTS and all archive structure remain unchanged.',sha256=after)
    assert len(recipe['writes'])==10
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
