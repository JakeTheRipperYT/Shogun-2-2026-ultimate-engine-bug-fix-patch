"""Generate a guarded OG fear-magnitude constructor adapter; no game writes."""
from pathlib import Path
import argparse,hashlib,json,struct
import pefile
SOURCE='022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5'
HOOK,END,CAVE=0x10152b23,0x10152b44,0x11793b30
def main():
    p=argparse.ArgumentParser();p.add_argument('--engine',type=Path,required=True);p.add_argument('--enable',action='store_true');a=p.parse_args()
    raw=a.engine.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE
    pe=pefile.PE(data=raw,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase
    def get(va,n):return pe.get_data(va-base,n)
    original=get(HOOK,END-HOOK)
    assert original.hex()=='85c0741d8bcee832eba7008d882c190000e867b806008b00f7d88984249c000000',original.hex()
    code=bytearray();labels={};branches=[]
    def emit(b):code.extend(bytes.fromhex(b))
    def rel(op,va):emit(op);code.extend(struct.pack('<i',va-(CAVE+len(code)+4)))
    def branch(op,label):emit(op);branches.append((len(code),label));code.append(0)
    emit('85 c0');branch('74','end');branch('78','numeric')
    # Positive values retain the complete legacy flag-to-KV conversion (including FOTS).
    emit('8b ce');rel('e8',0x10bd1660);emit('8d 88 2c 19 00 00');rel('e8',0x101be3a0)
    emit('8b 00 f7 d8 89 84 24 9c 00 00 00');branch('eb','end')
    labels['numeric']=len(code)
    # Negative values are explicit numeric penalties. Preserve innate fear and saturate overflow.
    emit('99 31 d0 29 d0');branch('79','abs_ok');emit('48');labels['abs_ok']=len(code)
    emit('03 84 24 9c 00 00 00');branch('71','sum_ok');emit('b8 ff ff ff 7f');labels['sum_ok']=len(code)
    emit('89 84 24 9c 00 00 00');labels['end']=len(code);rel('e9',END)
    for at,label in branches:
        distance=labels[label]-(at+1);assert -128<=distance<=127;code[at]=distance&255
    rdata=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.rdata')
    assert CAVE>=base+rdata.VirtualAddress+rdata.Misc_VirtualSize
    assert CAVE+len(code)<=base+rdata.VirtualAddress+rdata.SizeOfRawData
    assert get(CAVE,len(code))==bytes(len(code))
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_BASERELOC']])
    for b in pe.DIRECTORY_ENTRY_BASERELOC:
        for x in b.entries:
            if x.type:assert not (CAVE-3<=base+x.rva<CAVE+len(code) or HOOK-3<=base+x.rva<END)
    writes=[{'va':hex(HOOK),'expect':original.hex(' '),'bytes':(b'\xe9'+struct.pack('<i',CAVE-HOOK-5)+b'\x90'*(len(original)-5)).hex(' '),'note':'Retain original ESI restoration; adapt only the scares_men constructor conversion.'},
            {'va':hex(CAVE),'expect':get(CAVE,len(code)).hex(' '),'bytes':code.hex(' '),'note':'Zero unchanged; positive flags use original KV behavior; negative explicit morale magnitudes add to innate fear with signed-overflow saturation.'}]
    # Adapter090 owns the shared VirtualSize write; require its mapped extent.
    # Make this original read-only section RX, never writable.
    root=Path(__file__).resolve().parents[1]
    redirect=json.loads((root/'patches/engine/090-data-pack-redirect.json').read_text())
    assert redirect['enabled']
    virtual_size=next(w for w in redirect['writes'] if w.get('offset')==hex(rdata.get_file_offset()+8))
    assert bytes.fromhex(virtual_size['expect'])==raw[rdata.get_file_offset()+8:rdata.get_file_offset()+12]
    assert struct.unpack('<I',bytes.fromhex(virtual_size['bytes']))[0]>=CAVE+len(code)-base-rdata.VirtualAddress
    writes[:0]=[{'offset':hex(rdata.get_file_offset()+36),'expect':struct.pack('<I',rdata.Characteristics).hex(' '),'bytes':struct.pack('<I',rdata.Characteristics|0x20000000).hex(' '),'note':'Allow execution of the PIC adapter in existing read-only .rdata padding; retain read-only protection (RX, not writable).'}]
    ranges=[(HOOK,END),(CAVE,CAVE+len(code))]
    for file in (root/'patches/engine').glob('*.json'):
        if file.name=='100-fear-effect-stacking.json':continue
        r=json.loads(file.read_text(encoding='utf-8-sig'))
        if not r.get('enabled'):continue
        for w in r['writes']:
            start=int(w['va'],0) if 'va' in w else base+pe.get_rva_from_offset(int(w['offset'],0));stop=start+len(bytes.fromhex(w['bytes']))
            assert not any(start<hi and lo<stop for lo,hi in ranges),(file.name,w)
    recipe={'id':'fear-effect-stacking','title':'Numeric enemy-morale rewards stack on one general without cancelling',
            'description':'Preserve signed negative scares_men magnitude when constructing unit stats; add to innate fear. Zero and positive legacy flags retain vanilla semantics. Requires matching data sign normalization: Intimidating -4, Dreaded -1/-2; trait/item negatives unchanged. Keep strongest nearby enemy, fear range, horse fear, immunity/routing eligibility and other morale effects unchanged. Experimental until controlled battle comparison.',
            'enabled':bool(a.enable),'writes':writes}
    out=root/'patches/engine/100-fear-effect-stacking.json';out.write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'recipe':str(out),'enabled':a.enable,'caveBytes':len(code),'gameModified':False}))
if __name__=='__main__':main()
