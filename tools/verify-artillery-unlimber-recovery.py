"""Verify emitted branch behavior and native callback ABI; not a gameplay test."""
from pathlib import Path
import hashlib
import itertools
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2')
r=json.loads((ROOT/'patches/engine/234-artillery-unlimber-recovery.json').read_text())
before=(GAME/'UltimatePatch/empire.retail.dll').read_bytes()
after=(ROOT/'build/artillery-unlimber-recovery.candidate.dll').read_bytes()
assert hashlib.sha256(before).hexdigest()==r['sourceSha256']
assert hashlib.sha256(after).hexdigest()==r['sha256']
expected=bytearray(before)
for w in r['writes']:
    pos=w['offset'];a=bytes.fromhex(w['expect']);b=bytes.fromhex(w['bytes'])
    assert len(a)==len(b) and before[pos:pos+len(a)]==a
    expected[pos:pos+len(b)]=b
assert bytes(expected)==after and len(after)==len(before)

def offset(va):
    pe=struct.unpack_from('<I',before,60)[0];op=struct.unpack_from('<H',before,pe+20)[0]
    for i in range(struct.unpack_from('<H',before,pe+6)[0]):
        vs,rv,rs,start=struct.unpack_from('<4I',before,pe+24+op+i*40+8)
        if rv<=va-0x10000000<rv+rs:return start+va-0x10000000-rv
    raise ValueError(hex(va))

# Exact original predicate instruction decoder, with loader-adjusted pointer immediates.
def eligibility(image,key,slide):
    code=image[offset(0x1015bd30):offset(0x1015bd30)+0x25]
    pc=0;equal=False
    while True:
        if code[pc:pc+3]==b'\x8b\x41\x38':eax=key;pc+=3
        elif code[pc]==0x3d:equal=eax==struct.unpack_from('<I',code,pc+1)[0]+slide;pc+=5
        elif code[pc]==0x74:
            delta=struct.unpack_from('<b',code,pc+1)[0];pc=pc+2+delta if equal else pc+2
        elif code[pc]==0x90:pc+=1
        elif code[pc:pc+2]==b'\xb0\x01':return True
        elif code[pc:pc+2]==b'\x32\xc0':return False
        else:raise AssertionError((pc,code[pc:pc+5].hex()))

predicate_cases=0
for key,slide in itertools.product([0x11796da4,0x11796da8,0x11796dac,0x11796de0,0x11796db0,0x11796dcc,0],[0,0x200000]):
    actual_key=key+slide
    assert eligibility(before,actual_key,slide)==(key not in [0x11796da4,0x11796da8,0x11796dac,0x11796de0])
    assert eligibility(after,actual_key,slide)==(key!=0x11796de0)
    predicate_cases+=1

code=bytes.fromhex(r['writes'][-1]['bytes']);cave=int(r['adapter'],0)
def emulate(entry,continuation,request,slide,seed):
    regs=[0x12340000+seed*17+i*0x101 for i in range(8)];regs[4]=0x900000
    original=list(regs);fsm=0x300034;state=fsm-0x34;vtable=0x115bf6a0+slide
    memory={regs[4]:0x11374d00+slide,regs[4]+4:fsm,fsm+0x0d:request,state:vtable,vtable+0x158:0x1017b440+slide}
    pc=entry-cave;virtual_calls=[]
    def push(v):regs[4]-=4;memory[regs[4]]=v
    def pop():v=memory[regs[4]];regs[4]+=4;return v
    for step in range(25):
        op=code[pc]
        if code[pc:pc+4]==b'\x8b\x44\x24\x04':regs[0]=memory[regs[4]+4];pc+=4
        elif code[pc:pc+4]==b'\x80\x78\x0d\x00':zero=memory[regs[0]+0x0d]==0;pc+=4
        elif code[pc:pc+2]==b'\x0f\x85':
            dest=pc+6+struct.unpack_from('<i',code,pc+2)[0];pc=pc+6 if zero else dest
        elif op==0x56:push(regs[6]);pc+=1
        elif code[pc:pc+4]==b'\x8b\x74\x24\x08':regs[6]=memory[regs[4]+8];pc+=4
        elif op==0xe9:
            target=cave+slide+pc+5+struct.unpack_from('<i',code,pc+1)[0]
            assert not request and target==continuation+slide
            assert regs[6]==fsm and regs[4]==original[4]-4 and memory[regs[4]]==original[6]
            assert all(regs[i]==original[i] for i in [1,2,3,5,7])
            # EAX and flags are overwritten immediately by original LEA/NEG/SBB.
            assert before[offset(continuation):offset(continuation)+3]==bytes.fromhex('8d 46 cc')
            assert not virtual_calls
            return
        elif code[pc:pc+3]==b'\x8d\x48\xcc':regs[1]=regs[0]-0x34;pc+=3
        elif code[pc:pc+2]==b'\x8b\x11':regs[2]=memory[regs[1]];pc+=2
        elif code[pc:pc+6]==b'\xff\x92\x58\x01\x00\x00':
            assert request and regs[1]==state
            fn=memory[regs[2]+0x158];assert fn==0x1017b440+slide
            push(cave+slide+pc+6)
            virtual_calls.append(fn)
            # Original virtual getter is MOV EAX,LIMBER_STATE; RET.
            assert before[offset(0x1017b440):offset(0x1017b440)+6]==bytes.fromhex('b8 e0 6d 79 11 c3')
            regs[0]=0x11796de0+slide
            assert pop()==cave+slide+pc+6
            pc+=6
        elif code[pc:pc+3]==b'\xc2\x04\x00':
            assert request and regs[0]==0x11796de0+slide and len(virtual_calls)==1
            assert pop()==0x11374d00+slide;regs[4]+=4
            assert regs[4]==original[4]+8 and all(regs[i]==original[i] for i in [3,5,6,7])
            # Adapter does not change native request, gun completion or model flags.
            assert memory[fsm+0x0d]==request
            return
        else:raise AssertionError((pc,hex(op)))
    raise AssertionError('No callback return/continuation')

callback_cases=0
for name,continuation in [('limbered_reform',0x100f9235),('unlimber',0x100f92e5)]:
    for request,slide,seed in itertools.product([0,1,2,255],[0,0x200000],[1,2,3]):
        emulate(int(r['entries'][name],0),continuation,request,slide,seed);callback_cases+=1

# Original pairing/re-limber logic and all previously accepted fixes are outside writes.
assert before[offset(0x10198ecd):offset(0x10198ed2)]==bytes.fromhex('5e c6 43 41 01')
assert before[offset(0x100f93b4):offset(0x100f93ba)]==bytes.fromhex('ff 90 58 01 00 00')
report=dict(status='passed',sha256=r['sha256'],sourceSha256=r['sourceSha256'],
    predicateCases=predicate_cases,callbackAbiCases=callback_cases,
    wholeImageDiffRestrictedToRecipe=True,normalUnlimberCallbacksPreserved=True,
    nativeLimberCompletionGuardPreserved=True,forcedGunCompletionFlags=False,
    scope='Byte-decoded predicates and callback adapters with virtual getter contract stub; no live game execution',
    gameplayTested=False)
(ROOT.parents[1]/'outputs/artillery-unlimber-recovery-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report))
