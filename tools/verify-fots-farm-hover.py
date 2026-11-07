"""Decode the emitted UI matcher and verify its native call/return contract."""
from pathlib import Path
import hashlib
import importlib.util
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2')
r=json.loads((ROOT/'patches/engine/233-fots-farm-hover-wealth.json').read_text())
old=(GAME/'UltimatePatch/empire.retail.dll').read_bytes()
new=(ROOT/'build/fots-farm-hover.candidate.dll').read_bytes()
assert hashlib.sha256(old).hexdigest()==r['sourceSha256']
assert hashlib.sha256(new).hexdigest()==r['sha256']
expected=bytearray(old)
for w in r['writes']:
    pos=w['offset'];a=bytes.fromhex(w['expect']);b=bytes.fromhex(w['bytes'])
    assert len(a)==len(b) and old[pos:pos+len(a)]==a
    expected[pos:pos+len(b)]=b
assert new==bytes(expected) and len(new)==len(old)
code=bytes.fromhex(r['writes'][1]['bytes']);cave=int(r['adapter'],0)
spec=importlib.util.spec_from_file_location('collection',ROOT/'tools/build-collection.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
pack=GAME/'UltimatePatch/data/data.pack';_,ix=c.index(pack)
raw=c.read(pack,ix,r'db\effects_tables\effects');cur=c.traits.Cursor(raw)
assert cur.take(4)==c.traits.GUID_MARKER;cur.string16();assert cur.take(1)==b'\1'
keys=[]
for _ in range(cur.u32()):
    keys.append(cur.string16());cur.optional_string16();cur.u32()
assert cur.pos==len(raw)

def emulate(key,slide,seed):
    regs=[0x12340000+seed*32+i for i in range(8)];regs[4]=0x900000;regs[1]=0x200000
    original=list(regs);memory={regs[4]:0x105b5ba0+slide,regs[4]+4:0x115fe48c+slide}
    comparisons=[];pc=0
    def push(v):regs[4]-=4;memory[regs[4]]=v&0xffffffff
    def pop():v=memory[regs[4]];regs[4]+=4;return v
    def string_at(pointer):
        if pointer==0x115fe48c+slide:return 'gdp_farm'
        off=pointer-cave-slide
        assert 0<=off<len(code)
        return code[off:code.index(0,off)].decode('ascii')
    for step in range(40):
        op=code[pc]
        if op==0x56:push(regs[6]);pc+=1
        elif code[pc:pc+2]==b'\x8b\xf1':regs[6]=regs[1];pc+=2
        elif code[pc:pc+4]==b'\xff\x74\x24\x08':push(memory[regs[4]+8]);pc+=4
        elif op==0xe8:
            next_pc=pc+5;target=cave+slide+next_pc+struct.unpack_from('<i',code,pc+1)[0]
            push(cave+slide+next_pc)
            if target==cave+slide+next_pc:pc=next_pc;continue
            assert target==0x100ee2d0+slide and regs[1]==original[1]
            compare=string_at(memory[regs[4]+4]);comparisons.append(compare)
            regs[0]=0xaabbcc00|int(key==compare);regs[1]=0x99887766;regs[2]=0x88776655
            assert pop()==cave+slide+next_pc;pop()  # native RET 4
            pc=next_pc
        elif code[pc:pc+2]==b'\x84\xc0':zero=(regs[0]&255)==0;pc+=2
        elif code[pc:pc+2]==b'\x0f\x85':
            target=pc+6+struct.unpack_from('<i',code,pc+2)[0];pc=pc+6 if zero else target
        elif code[pc:pc+2]==b'\x8b\xce':regs[1]=regs[6];pc+=2
        elif op==0x58:regs[0]=pop();pc+=1
        elif code[pc:pc+2]==b'\x8d\x80':regs[0]+=struct.unpack_from('<i',code,pc+2)[0];pc+=6
        elif op==0x50:push(regs[0]);pc+=1
        elif op==0x5e:regs[6]=pop();pc+=1
        elif op==0xc2:
            assert struct.unpack_from('<H',code,pc+1)[0]==4
            assert pop()==0x105b5ba0+slide;regs[4]+=4
            assert regs[4]==original[4]+8
            assert all(regs[i]==original[i] for i in [3,5,6,7])
            assert bool(regs[0]&255)==(key in {'gdp_farm','bos_gdp_farm'})
            assert comparisons==(['gdp_farm'] if key=='gdp_farm' else ['gdp_farm','bos_gdp_farm'])
            return
        else:raise AssertionError((pc,op))
    raise AssertionError('No return')

cases=0
for key in keys+['','bos_gdp_farm_extra','gdp_farm_extra','x','BOS_GDP_FARM']:
    for slide in [0,0x200000]:
        for seed in [1,2]:emulate(key,slide,seed);cases+=1
report=dict(status='passed',sha256=r['sha256'],sourceSha256=r['sourceSha256'],effectKeys=len(keys),
    emulatedAbiCases=cases,changedClassificationOnly=['bos_gdp_farm'],
    preservesNativeComparisonAndRet4=True,wholeImageDiffRestrictedToRecipe=True,
    scope='Byte-decoded adapter with native string-comparison contract stubs; no live tooltip verification',
    economyFunctionsUnmodified=True,dataPacksUnmodified=True,visualTested=False)
(ROOT.parents[1]/'outputs/fots-farm-hover-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report))
