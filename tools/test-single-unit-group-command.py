"""Native x86 single-member battle-group command fixtures.

Usage: python test-single-unit-group-command.py ORIGINAL_DLL [CANDIDATE_DLL]
Dependencies: pefile, unicorn. Reads local DLLs; never starts or modifies a game.
Executes the real serializer/receiver with controlled typed-I/O and group callbacks.
This checks packet count handling, not complete battle/formation behavior.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                              UC_X86_REG_EDI, UC_X86_REG_ESI, UC_X86_REG_EBP,
                              UC_X86_REG_ESP, UC_X86_REG_EIP)

VANILLA_SHA='022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5'
BASE=0x10000000
STACK, DATA, ADD, STOP=0x30000000,0x31000000,0x32000000,0x33000000
PRESERVED=(UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)
SENTINELS=(0xb1b1b1b1,0x51515151,0xd1d1d1d1,0xbfbfbfbf)
COUNTS=(0,1,2,20)
SPANS=((0x102e6390,0x57),(0x102a5e40,0x178))

def require(condition, message):
    if not condition: raise AssertionError(message)

def read(u,address): return struct.unpack('<I',u.mem_read(address,4))[0]
def put(u,address,value): u.mem_write(address,struct.pack('<I',value))
def return_to_caller(u,cleanup=0):
    sp=u.reg_read(UC_X86_REG_ESP); target=read(u,sp)
    u.reg_write(UC_X86_REG_ESP,sp+4+cleanup); u.reg_write(UC_X86_REG_EIP,target)

def machine(image):
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    u.mem_map(BASE,(len(image)+4095)&~4095);u.mem_write(BASE,image)
    for address,length in ((STACK,0x10000),(DATA,0x10000),(ADD,0x1000),(STOP,0x1000)):
        u.mem_map(address,length)
    for register,value in zip(PRESERVED,SENTINELS):u.reg_write(register,value)
    return u

def serializer_case(image,count):
    u=machine(image);sp=STACK+0xf000
    payload,army,array,writer=DATA+0x100,DATA+0x200,DATA+0x300,DATA+0x400
    events=[]
    put(u,army+4,101);put(u,payload+4,army);put(u,payload+8,7)
    put(u,payload+0x10,count);put(u,payload+0x14,array)
    for i in range(count):
        member=DATA+0x1000+i*0x20
        put(u,member+4,1000+i);put(u,array+4*i,member)
    put(u,sp,STOP);put(u,sp+4,writer)
    u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_ECX,payload)
    stopped=[]
    def hook(u,address,size,user):
        if address==STOP:stopped.append(True);u.emu_stop();return
        if address in (0x10285a40,0x10285a00,0x10285c80):
            s=u.reg_read(UC_X86_REG_ESP);w=read(u,s+4);value=read(u,s+8)
            require(w==writer,'serializer writer argument')
            if address==0x10285a40:events.append(('army',read(u,value+4)))
            elif address==0x10285c80:events.append(('unit',read(u,value+4)))
            else:events.append(('u32',value))
            u.reg_write(UC_X86_REG_EAX,w);return_to_caller(u)
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x102e6390,STOP+1,count=10000)
    expected=[('army',101),('u32',7),('u32',count)]+[('unit',1000+i) for i in range(count)]
    require(stopped==[True] and events==expected,'serializer field sequence/count')
    require(u.reg_read(UC_X86_REG_EAX)&255==1,'serializer success return')
    require(u.reg_read(UC_X86_REG_ESP)==sp+8,'serializer stack cleanup')
    require(tuple(u.reg_read(r) for r in PRESERVED)==SENTINELS,'serializer nonvolatile registers')

def receiver_case(image,count):
    u=machine(image);sp=STACK+0xf000
    reader,army,group,vtable=DATA+0x100,DATA+0x200,DATA+0x300,DATA+0x400
    reads=[7,count];members=[];calls=[];state=[]
    put(u,group,vtable);put(u,vtable+0x70,ADD)
    put(u,sp,STOP);put(u,sp+4,reader);put(u,sp+8,DATA+0x9000)
    u.reg_write(UC_X86_REG_ESP,sp)
    def hook(u,address,size,user):
        s=u.reg_read(UC_X86_REG_ESP)
        if address==STOP:u.emu_stop();return
        if address==0x10284bc0:
            require(read(u,s+4)==reader,'receiver army reader')
            put(u,read(u,s+8),army);return_to_caller(u)
        elif address==0x10284b80:
            require(read(u,s+4)==reader and reads,'receiver group/count reader')
            put(u,read(u,s+8),reads.pop(0));return_to_caller(u)
        elif address==0x10166e40:
            require(u.reg_read(UC_X86_REG_ECX)==army and read(u,s+4)==7,'receiver factory arguments')
            calls.append('create');u.reg_write(UC_X86_REG_EAX,group);return_to_caller(u,4)
        elif address==0x10285730:
            require(read(u,s+4)==reader,'receiver member reader')
            member=DATA+0x1000+0x20*len(members)
            put(u,read(u,s+8),member);members.append(member);return_to_caller(u)
        elif address==ADD:
            require(u.reg_read(UC_X86_REG_ECX)==group,'receiver add this pointer')
            calls.append(('add',read(u,s+4)));return_to_caller(u,4)
        elif address==0x101ffa70:
            require(u.reg_read(UC_X86_REG_ECX)==group,'receiver state this pointer')
            state.append(True);u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x102a5e40,STOP+1,count=10000)
    require(calls==['create']+[('add',x) for x in members],'receiver add sequence')
    require(len(members)==count and state==[True] and not reads,'receiver exact member count/state emission')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('original',type=Path);p.add_argument('candidate',type=Path,nargs='?')
    p.add_argument('--report',type=Path)
    a=p.parse_args();paths=[a.original]+([a.candidate] if a.candidate else [])
    require(hashlib.sha256(a.original.read_bytes()).hexdigest()==VANILLA_SHA,'Unsupported original engine SHA256')
    original=pefile.PE(str(a.original));results=[]
    for index,path in enumerate(paths):
        pe=pefile.PE(str(path));require(pe.FILE_HEADER.Machine==0x14c and pe.OPTIONAL_HEADER.ImageBase==BASE,'Expected supported x86 engine')
        for va,length in SPANS:
            require(pe.get_data(va-BASE,length)==original.get_data(va-BASE,length),'Group command code unexpectedly modified')
        image=pe.get_memory_mapped_image()
        for count in COUNTS:serializer_case(image,count);receiver_case(image,count)
        results.append(dict(image='vanilla' if index==0 else 'candidate',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),serializerCases=4,receiverCases=4,counts=list(COUNTS)))
    report=dict(result='pass',cases=8*len(paths),images=results,
                scope='Real serializer/receiver code with controlled typed-I/O, factory, add and state callbacks; no game process used',
                limitation='Does not simulate full battle formation/lifetime or prove live multiplayer behavior; vanilla receiver accepts explicit empty packets, so UI empty-selection guard must remain')
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report))

if __name__=='__main__':main()
