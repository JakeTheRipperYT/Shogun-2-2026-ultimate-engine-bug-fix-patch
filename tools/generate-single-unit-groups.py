"""Generate the guarded OG singleton-unit-group candidate; never writes a DLL.

Adds one RX .ubfix section containing a relative, relocation-free frame adapter.
Other enabled recipes must own disjoint original bytes and may not append data.
"""
from pathlib import Path
import argparse, hashlib, json, struct

SOURCE_SHA256='022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5'
ROOT=Path(__file__).resolve().parents[1]
HOOK=0x112234A0
RESUME=0x112234A5
SITES=((0x11101A3A,'Allow one selected land unit; preserve zero-selection/capacity rejection'),
       (0x11102DC8,'Allow one selected ship; preserve zero-selection/capacity rejection'),
       (0x10F89A46,'Allow UICardManager creation from one selected card; preserve empty rejection'),
       (0x11223482,'Show group frame for one card; preserve empty-frame hide path'))

def align(value,boundary):
    if boundary<=0 or boundary&(boundary-1):raise ValueError('Invalid PE alignment')
    return (value+boundary-1)&~(boundary-1)

def parse(raw):
    if raw[:2]!=b'MZ':raise ValueError('Not a PE image')
    nt=struct.unpack_from('<I',raw,0x3c)[0]
    if raw[nt:nt+4]!=b'PE\0\0' or struct.unpack_from('<H',raw,nt+4)[0]!=0x14c:raise ValueError('Expected OG x86 PE')
    count=struct.unpack_from('<H',raw,nt+6)[0];optional=nt+24
    optional_size=struct.unpack_from('<H',raw,nt+20)[0]
    if optional_size!=0xe0 or struct.unpack_from('<H',raw,optional)[0]!=0x10b:raise ValueError('Unexpected optional header')
    section_table=optional+optional_size;sections=[]
    for i in range(count):
        offset=section_table+40*i
        size,rva,raw_size,raw_offset=struct.unpack_from('<4I',raw,offset+8)
        sections.append(dict(name=raw[offset:offset+8].rstrip(b'\0').decode('ascii'),size=size,rva=rva,rawSize=raw_size,rawOffset=raw_offset,header=offset,flags=struct.unpack_from('<I',raw,offset+36)[0]))
    return dict(nt=nt,optional=optional,count=count,table=section_table,base=struct.unpack_from('<I',raw,optional+28)[0],sections=sections)

def offset(pe,va):
    rva=va-pe['base']
    for s in pe['sections']:
        if s['rva']<=rva and rva-s['rva']<s['rawSize']:return s['rawOffset']+rva-s['rva']
    raise ValueError('VA outside original raw sections '+hex(va))

def generate(engine,enable=True):
    raw=engine.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError('Unsupported original OG engine SHA-256')
    pe=parse(raw);opt=pe['optional'];header=pe['table']+pe['count']*40
    section_align,file_align=struct.unpack_from('<II',raw,opt+32)
    original_image_size=struct.unpack_from('<I',raw,opt+56)[0]
    headers_size=struct.unpack_from('<I',raw,opt+60)[0]
    old_code_size=struct.unpack_from('<I',raw,opt+4)[0]
    if pe['count']!=6 or header!=0x348 or pe['base']!=0x10000000:raise ValueError('Unsupported original PE layout')
    if file_align!=0x200 or section_align!=0x1000 or original_image_size!=0x1D88000:raise ValueError('Unsupported original PE alignment/image size')
    if len(raw)!=0x1899400 or max(s['rawOffset']+s['rawSize'] for s in pe['sections'])!=len(raw):raise ValueError('Unexpected EOF/overlay; refuse append')
    if any(struct.unpack_from('<II',raw,opt+96+4*8)):raise ValueError('Unexpected security/certificate directory')
    if header+40>headers_size or raw[header:header+40]!=bytes(40):raise ValueError('No zero-filled spare section header')
    if any(s['name']=='.ubfix' for s in pe['sections']):raise ValueError('New section already exists')
    new_rva=align(max(s['rva']+max(s['size'],s['rawSize']) for s in pe['sections']),section_align)
    raw_pointer=align(len(raw),file_align)
    if new_rva!=original_image_size or new_rva!=0x1D88000 or raw_pointer!=len(raw):raise ValueError('Unexpected append placement')
    new_va=pe['base']+new_rva
    # count==1 sets ZF and bypasses compact-mode comparison. >=2 replays it.
    # The original MOV-only bridge preserves flags until its JNE at112234B7.
    stub=bytes.fromhex('83 7d 04 01 74 05 80 7c 24 68 00')+b'\xe9'+struct.pack('<i',RESUME-(new_va+16))
    if len(stub)!=16:raise ValueError('Unexpected frame stub length')
    raw_size=align(len(stub),file_align);payload=stub+bytes(raw_size-len(stub))
    section=struct.pack('<8s6I2HI',b'.ubfix\0\0',len(stub),new_rva,raw_size,raw_pointer,0,0,0,0,0x60000020)
    if len(section)!=40:raise ValueError('Invalid new section header')
    writes=[]
    def add(at,after,note,va=False,expected=None):
        pos=offset(pe,at) if va else at;before=raw[pos:pos+len(after)]
        if len(before)!=len(after) or expected is not None and before!=expected:raise ValueError('Original byte guard failed '+hex(at))
        writes.append({('va' if va else 'offset'):hex(at),'expect':before.hex(' '),'bytes':after.hex(' '),'note':note})
    for va,note in SITES:add(va,b'\0',note,True,b'\1')
    add(0x10F9787F,b'\x73','Retain >=1 members using JAE; original CMP flags and zero-removal cleanup remain unchanged',True,b'\x77')
    add(0x110DD31D,b'\x8c','Permit zero-member UI record engine teardown; signed JL still rejects invalid negative counts; record and engine-existence guards remain',True,b'\x8e')
    # Guard surrounding instructions, not only the immediate being changed.
    contexts=((0x11101A36,'83 7c 24 38 01 76 21'),(0x11102DC5,'83 7f 04 01 76 21'),
              (0x10F89A43,'83 7e 28 01 76 3e'),(0x110DD318,'83 78 0c 00 0f 8e 84 00 00 00'),(0x10F9787B,'83 7f 0c 01 77 2d 75 09'),
              (0x1122347F,'83 7d 04 01 8b 4b 04 77 0f'),
              (HOOK,'80 7c 24 68 00'),(RESUME,'8b 45 08 8b 38 8b 43 44 8b c8 89 7c 24 14 89 44 24 24 0f 85 c7 00 00 00'))
    for va,expected in contexts:
        expect=bytes.fromhex(expected)
        if raw[offset(pe,va):offset(pe,va)+len(expect)]!=expect:raise ValueError('Instruction context differs '+hex(va))
    add(HOOK,b'\xe9'+struct.pack('<i',new_va-HOOK-5),'Relative detour to one-card ordinary-frame adapter; displaced CMP replayed for >=2',True,bytes.fromhex('80 7c 24 68 00'))
    add(pe['nt']+6,struct.pack('<H',pe['count']+1),'Append exactly one owned .ubfix code section')
    add(opt+4,struct.pack('<I',old_code_size+raw_size),'Account for new aligned code section in SizeOfCode')
    add(opt+56,struct.pack('<I',align(new_rva+len(stub),section_align)),'Map the appended section in SizeOfImage')
    add(header,section,'New 16-byte RX/non-writable .ubfix section, one 512-byte raw page')
    ranges=[];combined=bytearray(raw);own=bytearray(raw)
    for w in writes:
        at=int(w['offset'],0) if 'offset' in w else offset(pe,int(w['va'],0));data=bytes.fromhex(w['bytes'])
        if any(at<start+size and start<at+len(data) for start,size in ranges):raise ValueError('Internal recipe overlap')
        ranges.append((at,len(data)));own[at:at+len(data)]=data
    folder=ROOT/'patches/engine';existing=[]
    for path in sorted(folder.glob('*.json')):
        if path.name=='110-single-unit-groups.json':continue
        other=json.loads(path.read_text(encoding='utf-8-sig'))
        if not other.get('enabled',True):continue
        if 'append' in other:raise ValueError('Another enabled recipe already owns engine growth: '+path.name)
        for w in other['writes']:
            at=int(w['offset'],0) if 'offset' in w else offset(pe,int(w['va'],0));data=bytes.fromhex(w['bytes']);before=bytes.fromhex(w['expect'])
            if len(data)!=len(before) or raw[at:at+len(before)]!=before:raise ValueError('Other recipe original guard failed '+path.name)
            if any(at<start+size and start<at+len(data) for start,size in ranges):raise ValueError('Overlap with enabled recipe '+path.name)
            if any(at<start+size and start<at+len(data) for start,size in existing):raise ValueError('Existing enabled recipes overlap')
            existing.append((at,len(data)));combined[at:at+len(data)]=data
    for w in writes:
        at=int(w['offset'],0) if 'offset' in w else offset(pe,int(w['va'],0));data=bytes.fromhex(w['bytes']);combined[at:at+len(data)]=data
    own.extend(payload);combined.extend(payload)
    after=parse(combined);new_section=after['sections'][-1]
    if len(combined)!=len(raw)+512 or after['count']!=7 or new_section['name']!='.ubfix' or new_section['flags']!=0x60000020:raise ValueError('Rebuilt section validation failed')
    if new_section['rva']!=new_rva or new_section['rawOffset']!=len(raw) or new_section['rawSize']!=512 or new_section['size']!=16:raise ValueError('Rebuilt section bounds differ')
    # All original data directories, import/IAT/export/resource/debug/relocation RVAs
    # retain their existing descriptors. No new absolute operand needs relocation.
    if combined[opt+96:opt+224]!=raw[opt+96:opt+224]:raise ValueError('Original data directory descriptors changed')
    for name in ('.rsrc','.reloc','_RDATA'):
        s=next(s for s in pe['sections'] if s['name']==name)
        # Existing090 intentionally edits old IAT-operand relocations; this recipe
        # itself may not change any original bytes in these sections.
        if own[s['rawOffset']:s['rawOffset']+s['rawSize']]!=raw[s['rawOffset']:s['rawOffset']+s['rawSize']]:raise ValueError('Single-group patch touched original '+name)
    recipe=dict(id='single-unit-groups',title='Allow single-unit battle groups',
        description='Allow one-card land/naval groups through actual creator/UI gates; retain nonempty one-card groups after removal; show their group frame using the ordinary single-row path even in compact mode. Zero selections/empty groups remain rejected or removed, the original zero-removal callback path is preserved, existing max-group checks and multi-unit compact layout remain unchanged. New 16-byte relative frame adapter resides in its own RX .ubfix section; no absolute operand or relocation added. Zero-member teardown reaches the existing engine-destroy command before UI ID reuse; preserve negative-count and ownership/existence checks. Requires guarded recipe append support. Corrected cleanup pending player regression testing.',
        enabled=enable,sourceSha256=SOURCE_SHA256,writes=writes,
        append=dict(offset=hex(len(raw)),bytes=payload.hex(' ')))
    result=dict(enabled=enable,writes=len(writes),thresholdImmediates=len(SITES),retentionBranchChanges=1,appendedBytes=len(payload),section='.ubfix',sectionHeader=hex(header),sectionRva=hex(new_rva),sectionVa=hex(new_va),sectionRaw=hex(raw_pointer),stubBytes=stub.hex(' '),stubSha256=hashlib.sha256(stub).hexdigest(),newSizeOfImage=hex(align(new_rva+len(stub),section_align)),ownEngineSha256=hashlib.sha256(own).hexdigest(),allEnabledEngineSha256=hashlib.sha256(combined).hexdigest(),length=len(combined),gameFilesModified=False)
    return recipe,result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--engine',type=Path,required=True);ap.add_argument('--disable',action='store_true');ap.add_argument('--check',action='store_true');a=ap.parse_args()
    recipe,result=generate(a.engine,not a.disable);output=ROOT/'patches/engine/110-single-unit-groups.json'
    if a.check:
        if json.loads(output.read_text(encoding='utf8'))!=recipe:raise ValueError('Checked-in recipe differs from generated candidate')
    else:output.write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))

if __name__=='__main__':main()
