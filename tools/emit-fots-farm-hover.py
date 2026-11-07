"""Recognize FOTS farm wealth in the existing province-aware card formatter."""
from pathlib import Path
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2')
SOURCE='4894baf06e8ab4db3f5d1f741c45f7040a759ebf7112c8902ab35cb5855cbf51'
HOOK=0x105b5b9b
CAVE=0x11d8d900
COMPARE=0x100ee2d0

def offset(image,va):
    pe=struct.unpack_from('<I',image,60)[0];op=struct.unpack_from('<H',image,pe+20)[0]
    base=struct.unpack_from('<I',image,pe+52)[0]
    for i in range(struct.unpack_from('<H',image,pe+6)[0]):
        pos=pe+24+op+i*40;vs,rv,rs,off=struct.unpack_from('<4I',image,pos+8)
        if rv<=va-base<rv+min(vs,rs):
            assert struct.unpack_from('<I',image,pos+36)[0]&0x20000000
            return off+va-base-rv
    raise ValueError(hex(va))

image=(GAME/'UltimatePatch/empire.retail.dll').read_bytes()
assert hashlib.sha256(image).hexdigest()==SOURCE
code=bytearray();fixups=[];labels={}
def raw(s):code.extend(bytes.fromhex(s))
def branch(op,target):
    raw(op);fixups.append((len(code),target));code.extend(b'\0'*4)
raw('56 8b f1 ff 74 24 08')       # Save ESI; retain effect key and original argument.
branch('e8',COMPARE)               # Original exact gdp_farm comparison, RET 4.
raw('84 c0');branch('0f 85','done')
raw('8b ce e8 00 00 00 00')       # ECX=effect key; obtain own code address.
pic=CAVE+len(code)
raw('58 8d 80');string_delta=len(code);raw('00 00 00 00')
raw('50');branch('e8',COMPARE)      # Exact bos_gdp_farm comparison, RET 4.
labels['done']=CAVE+len(code)
raw('5e c2 04 00')                # Restore ESI; consume original caller argument.
string_va=CAVE+len(code)
code.extend(b'bos_gdp_farm\0')
struct.pack_into('<i',code,string_delta,string_va-pic)
for pos,target in fixups:
    dest=labels[target] if isinstance(target,str) else target
    struct.pack_into('<i',code,pos,dest-(CAVE+pos+4))
old=b'\xe8'+struct.pack('<i',COMPARE-HOOK-5)
assert image[offset(image,HOOK):offset(image,HOOK)+5]==old
assert image[offset(image,CAVE):offset(image,CAVE)+len(code)]==bytes(len(code))
writes=[dict(va=hex(HOOK),offset=offset(image,HOOK),expect=old.hex(' '),bytes=(b'\xe8'+struct.pack('<i',CAVE-HOOK-5)).hex(' ')),
        dict(va=hex(CAVE),offset=offset(image,CAVE),expect=bytes(len(code)).hex(' '),bytes=code.hex(' '))]
candidate=bytearray(image)
for w in writes:
    start=w['offset'];data=bytes.fromhex(w['bytes']);candidate[start:start+len(data)]=data
recipe=dict(id='fots-farm-hover-wealth',title='Use contextual farm wealth in FOTS building hover cards',enabled=False,
    description='Recognize bos_gdp_farm alongside gdp_farm in the existing building-effect card query. Retain the native contextual wealth calculation and generic no-context behavior. No economy, fertility multiplier, building data or other effect keys changed. Local trial pending visual comparison.',
    sourceSha256=SOURCE,sha256=hashlib.sha256(candidate).hexdigest(),hook=hex(HOOK),adapter=hex(CAVE),
    adapterBytes=len(code),codeBytes=labels['done']+4-CAVE,stringVa=hex(string_va),writes=writes,gameplayTested=False)
(ROOT/'patches/engine/233-fots-farm-hover-wealth.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf8')
(ROOT/'build/fots-farm-hover.candidate.dll').write_bytes(candidate)
print(json.dumps({k:v for k,v in recipe.items() if k!='writes'}))
