"""Static image diff and byte-decoded ABI emulation, not a live gameplay test."""
from pathlib import Path
import hashlib
import itertools
import json
import struct

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2')
recipe=json.loads((ROOT/'patches/engine/232-agent-fleet-bulk-disembark.json').read_text())
before=(GAME/'UltimatePatch/empire.retail.dll').read_bytes()
after=(ROOT/'build/agent-fleet-bulk-disembark.candidate.dll').read_bytes()
assert hashlib.sha256(before).hexdigest()==recipe['sourceSha256']
assert hashlib.sha256(after).hexdigest()==recipe['sha256']
assert len(before)==len(after)
expected=bytearray(before)
for w in recipe['writes']:
    off=w['offset'];old=bytes.fromhex(w['expect']);new=bytes.fromhex(w['bytes'])
    assert before[off:off+len(old)]==old and len(old)==len(new)
    expected[off:off+len(new)]=new
assert bytes(expected)==after
code=bytes.fromhex(recipe['writes'][1]['bytes'])
CAVE=int(recipe['adapter'],0)
NATIVE_GET=0x103e5960
NATIVE_MOVE=0x105ff5d0
NATIVE_UNLOAD=0x105f2990

# Decode/execute the actual emitted instructions. Native calls are contract stubs.
def run(source_count,destination_count,mode,slide,seed):
    registers=[0x12340000+seed*31+i*0x101 for i in range(8)]
    registers[4]=0x900000
    fleet=0 if mode=='null-fleet' else 0x200000
    army={'null-army':0,'same':fleet}.get(mode,0x300000)
    registers[1]=fleet
    original=list(registers)
    flags=(0x246 if seed%2 else 0x293)
    original_flags=flags
    memory={registers[4]:0x108a7a57+slide,fleet+0x6c:source_count,army+0x6c:destination_count}
    if army==fleet:
        memory[fleet+0x6c]=source_count
    transfers=[]
    pc=0;zero=False;above=False
    def push(v):
        registers[4]-=4;memory[registers[4]]=v&0xffffffff
    def pop():
        v=memory[registers[4]];registers[4]+=4;return v
    for step in range(100):
        op=code[pc]
        if op==0x9c:push(flags);pc+=1
        elif op==0x60:
            saved_sp=registers[4]
            for i in [0,1,2,3]:push(registers[i])
            push(saved_sp)
            for i in [5,6,7]:push(registers[i])
            pc+=1
        elif op==0x61:
            for i in [7,6,5]:registers[i]=pop()
            pop()
            for i in [3,2,1,0]:registers[i]=pop()
            pc+=1
        elif op==0x9d:flags=pop();pc+=1
        elif code[pc:pc+2] in (b'\x8b\xf1',b'\x8b\xf8',b'\x8b\xcf'):
            dest,src={b'\x8b\xf1':(6,1),b'\x8b\xf8':(7,0),b'\x8b\xcf':(1,7)}[code[pc:pc+2]]
            registers[dest]=registers[src];pc+=2
        elif code[pc:pc+2]==b'\x8d\x8e':registers[1]=registers[6]+struct.unpack_from('<I',code,pc+2)[0];pc+=6
        elif code[pc:pc+2] in (b'\x85\xf6',b'\x85\xc0'):
            zero=registers[6 if code[pc+1]==0xf6 else 0]==0;flags^=0x44;pc+=2
        elif code[pc:pc+2]==b'\x3b\xc6':zero=registers[0]==registers[6];flags^=0x41;pc+=2
        elif code[pc:pc+2] in (b'\x8b\x46',b'\x8b\x57'):
            dest,src=(0,6) if code[pc+1]==0x46 else (2,7)
            registers[dest]=memory[registers[src]+code[pc+2]];pc+=3
        elif code[pc:pc+2] in (b'\x83\xf8',b'\x83\xfa'):
            a=registers[0 if code[pc+1]==0xf8 else 2];v=code[pc+2]
            above=a>v;zero=a==v;flags^=0x41;pc+=3
        elif code[pc:pc+2]==b'\x03\xc2':registers[0]=(registers[0]+registers[2])&0xffffffff;flags^=0x44;pc+=2
        elif op==0x56:push(registers[6]);pc+=1
        elif op==0x0f:
            condition={0x84:zero,0x87:above}[code[pc+1]]
            target=pc+6+struct.unpack_from('<i',code,pc+2)[0]
            pc=target if condition else pc+6
        elif op==0xe8:
            next_pc=pc+5;target=CAVE+slide+next_pc+struct.unpack_from('<i',code,pc+1)[0]
            push(CAVE+slide+next_pc)
            if target==NATIVE_GET+slide:
                assert registers[1]==fleet+0xbc
                registers[0]=army;registers[1]=0xabcdef01;registers[2]=0xabcdef02;flags^=0x41
                assert pop()==CAVE+slide+next_pc
            elif target==NATIVE_MOVE+slide:
                assert registers[1]==army and memory[registers[4]+4]==fleet
                transfers.append((fleet,army,source_count))
                memory[army+0x6c]=source_count+destination_count;memory[fleet+0x6c]=0
                registers[0]=0xdeadbeef;registers[1]=0xabcdef03;registers[2]=0xabcdef04;flags^=0x44
                assert pop()==CAVE+slide+next_pc
                assert pop()==fleet  # native RET 4
            else:raise AssertionError(hex(target))
            pc=next_pc
        elif op==0xe9:
            target=CAVE+slide+pc+5+struct.unpack_from('<i',code,pc+1)[0]
            assert target==NATIVE_UNLOAD+slide
            assert registers==original and flags==original_flags
            assert memory[registers[4]]==0x108a7a57+slide
            should_transfer=mode=='normal' and source_count<=3 and destination_count<=3 and source_count+destination_count<=3
            assert bool(transfers)==should_transfer,(source_count,destination_count,mode)
            if should_transfer:
                assert memory[army+0x6c]==source_count+destination_count<=3 and memory[fleet+0x6c]==0
            return
        else:raise AssertionError((pc,hex(op)))
    raise AssertionError('Adapter did not terminate')

cases=0
for src,dst,mode,slide,seed in itertools.product([0,1,2,3,4,0xffffffff],[0,1,2,3,4],['normal','null-fleet','null-army','same'],[0,0x200000],[1,2]):
    run(src,dst,mode,slide,seed);cases+=1
report=dict(status='passed',emulatedAbiCases=cases,scope='Actual wrapper instruction decoding with native contract stubs; not native engine execution',
    sourceSha256=recipe['sourceSha256'],sha256=recipe['sha256'],adapterBytes=len(code),
    wholeImageDiffRestrictedToRecipe=True,originalUnloadArgumentsAndRegistersPreserved=True,
    capacity=3,gameplayTested=False)
(ROOT.parents[1]/'outputs/agent-fleet-adapter-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report))
