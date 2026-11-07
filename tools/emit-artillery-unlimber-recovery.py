"""Guarded original-x86 transition recovery; handwritten bytes, no compiler."""
from pathlib import Path
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2')
SOURCE='7108a609c97bf6c448905eeba1ecc2b14b3b6cf86dff9ec93c816bf35eb3ddd5'
CAVE=0x11d8da00

def offset(image,va):
    pe=struct.unpack_from('<I',image,60)[0];op=struct.unpack_from('<H',image,pe+20)[0]
    base=struct.unpack_from('<I',image,pe+52)[0]
    for i in range(struct.unpack_from('<H',image,pe+6)[0]):
        pos=pe+24+op+i*40;vs,rv,rs,start=struct.unpack_from('<4I',image,pos+8)
        if rv<=va-base<rv+min(vs,rs):
            assert struct.unpack_from('<I',image,pos+36)[0]&0x20000000
            return start+va-base-rv
    raise ValueError(hex(va))

image=(GAME/'UltimatePatch/empire.retail.dll').read_bytes()
assert hashlib.sha256(image).hexdigest()==SOURCE
code=bytearray();fixups=[];labels={};entries={}
def raw(s):code.extend(bytes.fromhex(s))
def branch(op,target):
    raw(op);fixups.append((len(code),target));code.extend(b'\0'*4)

for name,original in [('limbered_reform',0x100f9230),('unlimber',0x100f92e0)]:
    entries[name]=CAVE+len(code)
    raw('8b 44 24 04')                 # Native callback argument: FSM at state+34h.
    raw('80 78 0d 00')                 # Existing native re-limber request at state+41h.
    branch('0f 85',name+'_recover')
    raw('56 8b 74 24 08')             # Replay the displaced original five-byte prologue.
    branch('e9',original+5)
    labels[name+'_recover']=CAVE+len(code)
    raw('8d 48 cc 8b 11')             # Recover actual state object and its own vtable.
    raw('ff 92 58 01 00 00')          # Existing virtual LIMBER_STATE selector, RET 0.
    raw('c2 04 00')                   # Same callback ABI: one argument, RET 4.
for pos,target in fixups:
    target=labels[target] if isinstance(target,str) else target
    struct.pack_into('<i',code,pos,target-(CAVE+pos+4))

writes=[]
def add(va,expected,replacement,note):
    expected=bytes.fromhex(expected) if isinstance(expected,str) else expected
    replacement=bytes.fromhex(replacement) if isinstance(replacement,str) else replacement
    pos=offset(image,va)
    assert image[pos:pos+len(expected)]==expected and len(expected)==len(replacement)
    writes.append(dict(va=hex(va),offset=pos,expect=expected.hex(' '),bytes=replacement.hex(' '),note=note))

# Only these three deploy phases become cancellable. Keep LIMBER_STATE blocked
# until its native carriage-attachment completion test succeeds.
add(0x1015bd38,'74 18','90 90','Allow recovery request during LIMBERED_REFORM_STATE')
add(0x1015bd3f,'74 11','90 90','Allow recovery request during UNLIMBER_STATE')
add(0x1015bd46,'74 0a','90 90','Allow recovery request during UNLIMBERED_REFORM_STATE')
for name,original in [('limbered_reform',0x100f9230),('unlimber',0x100f92e0)]:
    add(original,'56 8b 74 24 08',b'\xe9'+struct.pack('<i',entries[name]-original-5),
        'Honor existing re-limber request before waiting for obstructed deployment; normal path preserved')
add(CAVE,bytes(len(code)),bytes(code),'PIC recovery adapters; return existing native LIMBER_STATE token')
candidate=bytearray(image)
for write in writes:
    start=write['offset'];value=bytes.fromhex(write['bytes']);candidate[start:start+len(value)]=value
recipe=dict(id='artillery-unlimber-recovery',title='Recover artillery from obstructed unlimber transitions',enabled=False,
    description='Permit the native limber-order handler during the three deployment phases. In the two earlier phases honor its existing re-limber request before blocked formation/animation completion. UNLIMBERED_REFORM already handles that request. Preserve native FSM exit/entry, LIMBER_STATE cleanup and attachment completion, unit eligibility, routing and gun counts. No forced gun-ready flags or collision bypass.',
    sourceSha256=SOURCE,sha256=hashlib.sha256(candidate).hexdigest(),adapter=hex(CAVE),
    adapterBytes=len(code),entries={k:hex(v) for k,v in entries.items()},writes=writes,gameplayTested=False)
(ROOT/'patches/engine/234-artillery-unlimber-recovery.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf8')
(ROOT/'build/artillery-unlimber-recovery.candidate.dll').write_bytes(candidate)
print(json.dumps({k:v for k,v in recipe.items() if k!='writes'}))
