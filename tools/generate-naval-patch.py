"""Generate the reviewed OG naval adapter recipe; never modifies the game DLL."""
from pathlib import Path
import argparse, hashlib, json, struct

parser=argparse.ArgumentParser()
parser.add_argument('--engine',type=Path,required=True)
args=parser.parse_args()
raw=args.engine.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5','Unsupported OG engine'
nt=struct.unpack_from('<I',raw,0x3c)[0];opt=nt+24
assert struct.unpack_from('<H',raw,nt+4)[0]==0x14c
base=struct.unpack_from('<I',raw,opt+28)[0]
table=opt+struct.unpack_from('<H',raw,nt+20)[0]
sections=[]
for i in range(struct.unpack_from('<H',raw,nt+6)[0]):
 s=table+i*40
 name=raw[s:s+8].rstrip(b'\0');vs,rva,size,offset=struct.unpack_from('<IIII',raw,s+8)
 sections.append((name,vs,rva,size,offset,s))
text=next(s for s in sections if s[0]==b'.text')
assert text[1]==0x159fc3e and text[2]==0x1000 and text[3]==0x159fe00
start=0x115a0d20;site=0x104d1636;constructor=0x101ca070
code=bytearray();labels={};fix=[]
def emit(h):code.extend(bytes.fromhex(h))
def label(name):labels[name]=start+len(code)
def rel(op,target):
 emit(op);at=len(code);code.extend(b'\0'*4);fix.append((at,target))
# Original ABI: ECX=group allocation; stack=(return, battleRef, parent).
# Save nonvolatile registers; default target from parent+144. Select the first
# opponent with ships, using exactly the attack factory's +30/+158/+15C/+48/+68.
emit('53 56 57 8b d9 8b 44 24 14 8b 90 44 01 00 00 8b 48 30')
emit('8b b9 58 01 00 00 8b b1 5c 01 00 00 85 ff')
rel('0f84','construct')
label('loop');emit('8b 0e 83 79 48 00');rel('0f85','target')
emit('83 c6 04 4f');rel('0f85','loop');rel('e9','construct')
label('target');emit('8b 51 68')
label('construct')
# Attack ctor expects (battleRef,parent,target) and ret 12. Restore the original
# wrapper's ABI with ret 8, preserving its caller's stack and EBX/ESI/EDI.
emit('52 50 ff 74 24 18 8b cb');rel('e8',constructor)
emit('5f 5e 5b c2 08 00')
for at,target in fix:
 if isinstance(target,str):target=labels[target]
 struct.pack_into('<i',code,at,target-(start+at+4))
def offset(va):
 rva=va-base
 for _,_,v,size,off,_ in sections:
  if v<=rva<v+size:return off+rva-v
 raise ValueError(hex(va))
assert raw[offset(start):offset(start)+len(code)]==bytes(len(code))
assert raw[offset(site):offset(site)+5]==bytes.fromhex('e855500700')
assert start-base+len(code)<=text[2]+text[3]
newvs=start-base+len(code)-text[2]
folder=Path(__file__).resolve().parents[1]/'patches/engine'
support={
 'id':'text-cave','title':'Map code padding for the naval defender adapter',
 'description':'Maps only through the naval adapter at VA 0x115A0D20. Historical siege stubs remain disabled and their reserved bytes stay zero. No other gameplay fix is enabled by this support recipe.',
 'enabled':True,'writes':[{'offset':hex(text[5]+8),'expect':struct.pack('<I',text[1]).hex(' '),'bytes':struct.pack('<I',newvs).hex(' '),'note':'Grow .text VirtualSize within existing executable raw padding; no file or section growth'}]}
patch={
 'id':'naval-defender-attack-group','title':'Naval AI: use the normal naval attack group for defenders (test candidate)',
 'description':'Redirect only defender factory FUN_104D15D0 call at 0x104D1636 from holding ctor FUN_10546690 to a position-independent adapter at 0x115A0D20. It selects default parent+144 or first opposing group with ships using analyzer parent+30, count+158, array+15C, group ships+48 and ID+68, matching native attacker factory FUN_104D09F0. Calls attack ctor FUN_101CA070, preserving the 0x4C allocation, ECX destination, battle reference, parent, nonvolatile registers and original ret-8 ABI. See docs/naval-defender-ai.md. Requires 000-text-cave; historical experiments remain disabled.',
 'enabled':True,'writes':[
  {'va':hex(start),'expect':bytes(len(code)).hex(' '),'bytes':code.hex(' '),'note':'Native x86 target/argument adapter; relative branches/call only'},
  {'va':hex(site),'expect':raw[offset(site):offset(site)+5].hex(' '),'bytes':(b'\xe8'+struct.pack('<i',start-site-5)).hex(' '),'note':'Only holding-group factory call redirected; allocator and other factory branches unchanged'}]}
for name,obj in [('000-text-cave.json',support),('070-naval-defender-ai.json',patch)]:
 (folder/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
print('Generated naval adapter:',len(code),'bytes; cave',hex(start),'new .text size',hex(newvs))
