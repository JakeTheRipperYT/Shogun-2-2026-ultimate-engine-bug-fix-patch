"""Handwritten x86 adapter on the current installed OG engine; no compiler."""
from pathlib import Path
import hashlib
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2')
SOURCE_SHA='a0a8df960eccc629ebd7b22c7c41071b6762472ef0f094696dce509eb683e631'
HOOK=0x108a7a52
CAVE=0x11d8d800

def offset(image,va):
    pe=struct.unpack_from('<I',image,0x3c)[0]
    count=struct.unpack_from('<H',image,pe+6)[0]
    op=struct.unpack_from('<H',image,pe+20)[0]
    base=struct.unpack_from('<I',image,pe+52)[0]
    for i in range(count):
        pos=pe+24+op+i*40
        vs,rva,raw,start=struct.unpack_from('<4I',image,pos+8)
        if rva<=va-base<rva+min(vs,raw):
            return start+va-base-rva
    raise ValueError(hex(va))

image=(GAME/'UltimatePatch/empire.retail.dll').read_bytes()
assert hashlib.sha256(image).hexdigest()==SOURCE_SHA
code=bytearray();fixups=[];labels={}
def raw(value): code.extend(bytes.fromhex(value))
def branch(op,target):
    raw(op);fixups.append((len(code),target));code.extend(b'\0'*4)
raw('9c 60 8b f1 85 f6')                 # Preserve flags/registers; ESI=fleet.
branch('0f 84','original')
raw('8d 8e bc 00 00 00')                # Existing carried-army link.
branch('e8',0x103e5960)                  # Native handle dereference, RET 0.
raw('85 c0');branch('0f 84','original')
raw('3b c6');branch('0f 84','original')   # Never transfer a container into itself.
raw('8b f8 8b 46 6c 8b 57 6c')         # EDI=army; source/destination agent counts.
raw('83 f8 03');branch('0f 87','original')
raw('83 fa 03');branch('0f 87','original')
raw('03 c2 83 f8 03');branch('0f 87','original')
raw('56 8b cf')                         # this=army, stack source=fleet.
branch('e8',0x105ff5d0)                  # Native transfer, RET 4, existing events.
labels['original']=CAVE+len(code)
raw('61 9d')                           # Original caller state restored.
branch('e9',0x105f2990)                  # Tail-call original unload, RET 0.
for pos,target in fixups:
    destination=labels[target] if isinstance(target,str) else target
    struct.pack_into('<i',code,pos,destination-(CAVE+pos+4))
original_call=bytes.fromhex('e8 39 af d4 ff')
assert image[offset(image,HOOK):offset(image,HOOK)+5]==original_call
assert image[offset(image,CAVE):offset(image,CAVE)+len(code)]==bytes(len(code))
writes=[dict(va=hex(HOOK),offset=offset(image,HOOK),expect=original_call.hex(' '),
             bytes=(b'\xe8'+struct.pack('<i',CAVE-HOOK-5)).hex(' ')),
        dict(va=hex(CAVE),offset=offset(image,CAVE),expect=bytes(len(code)).hex(' '),bytes=code.hex(' '))]
candidate=bytearray(image)
for w in writes:
    start=w['offset'];data=bytes.fromhex(w['bytes']);candidate[start:start+len(data)]=data
recipe=dict(id='agent-fleet-bulk-disembark',title='Bring fleet agents ashore with a bulk army landing',enabled=False,
    description='Before the existing successful army unload, transfer fleet agents to its carried army using the original native passenger routine. Guard null/self destinations and the three-agent capacity. Preserve all caller registers/flags and tail-call the unchanged unload. Normal agent-only disembarkation is untouched. Local trial pending gameplay verification.',
    sourceSha256=SOURCE_SHA,sha256=hashlib.sha256(candidate).hexdigest(),writes=writes,
    hook=hex(HOOK),adapter=hex(CAVE),adapterBytes=len(code),gameplayTested=False)
(ROOT/'patches/engine/232-agent-fleet-bulk-disembark.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf8')
(ROOT/'build/agent-fleet-bulk-disembark.candidate.dll').write_bytes(candidate)
print(json.dumps({k:v for k,v in recipe.items() if k!='writes'}))
