#!/usr/bin/env python3
"""Build complete synthetic media and a compact all-resource RWTS harness."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from build_messages import labels
from catalog import ROOT, digest, write_json
from encoding import decode
from packages import split
from startup_disk import Disk, file_bytes


def check_synthetic_pool(data, glyphs, test_glyph):
    """Independent body whitelist check on the final, sealed disk payload."""
    if not data:return
    count=int.from_bytes(data[:2],'little')
    offsets=sorted({int.from_bytes(data[2+2*i:4+2*i],'little') for i in range(count)})
    assert offsets and offsets[0]==2+2*count
    for first,end in zip(offsets,offsets[1:]+[len(data)]):
        assert set(decode(data[first:end],glyphs))<=set('X \n'+test_glyph)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    media=out/'media'
    subprocess.run([sys.executable,str(ROOT/'tools/korean/startup_disk.py'),
                    '--full-synthetic','--output',str(media)],check=True)
    built=json.loads((media/'startup-build.json').read_text())
    encoding=json.loads((media/'encoding/encoding.json').read_text())
    glyphs=json.loads((media/'encoding/glyphs.json').read_text())
    check_synthetic_pool((media/'encoding/resident-pool.bin').read_bytes(),glyphs,encoding['synthetic_test_glyph'])
    syms=labels(media/'runtime/messages.lbl')
    files={}
    retained=[]
    for side in ('a','b'):
        image=(media/f'synthetic-{side}.dsk').read_bytes()
        baseline=(ROOT/f'build/korean/english-baseline/mask-of-sun-{side}.dsk').read_bytes()
        originals={f['name']:f for f in Disk(baseline).catalog()['files']}
        catalog=Disk(image).catalog()
        assert {f['name'] for f in catalog['files']}==set(originals)
        resource_names={f['name'] for f in encoding['files'] if f['side']==side}
        for f in catalog['files']:
            files[side,f['name']]=(image,f)
            if f['name'] not in resource_names|{'START','INTRIN.OBJ','ADVEN INTERP.OBJ'}:
                assert file_bytes(image,f)==file_bytes(baseline,originals[f['name']])
                retained.append({'side':side,'name':f['name'],'sha256':digest(file_bytes(image,f))})
    cases=[]
    for f in sorted(encoding['files'],key=lambda f:(f['side'],f['name'])):
        image,actual=files[f['side'],f['name']]
        payload=file_bytes(image,actual)[:f['package_bytes']]
        assert payload==(media/'encoding'/f['package']).read_bytes()
        assert payload[8:20].hex()==built['media_id']
        script,pool=split(payload)
        check_synthetic_pool(pool,glyphs,encoding['synthetic_test_glyph'])
        n=len(cases)+1
        (out/f'case-{n}-script.bin').write_bytes(script)
        (out/f'case-{n}-pool.bin').write_bytes(pool)
        cases.append({'number':n,'side':f['side'],'name':f['name'],
                      'destination':0x7000 if f['name']=='LIBRARY' else 0x6800,
                      'script_bytes':len(script),'pool_bytes':len(pool),
                      'script_sha256':digest(script),'pool_sha256':digest(pool),
                      'early_track_sectors':[pair for pair in actual['sectors']+actual['ts_lists'] if pair[0]<3]})
    assert len(cases)==86
    s=['.setcpu "6502"','.segment "CODE"']
    for name in ('ko_load_package','ko_load_error'):
        s.append(f'{name} = ${syms[name]:04x}')
    s+=['entry: sei','cld','ldx #$ff','txs','lda #0','sta $02e0','sta $02e1',
        'next: inc $02e1','lda record','sta $ea','lda record+1','sta $eb',
        'ldy #10','lda ($ea),y','sta $ed','iny','lda ($ea),y','sta $601c',
        'lda #0','sta $ec','lda record','ldx record+1','jsr ko_load_package',
        'lda #0','rol a','sta $02e2','lda ko_load_error','sta $02e3','jsr checkpoint',
        'clc','lda record','adc #12','sta record','bcc :+','inc record+1',
        ': lda $02e1',f'cmp #{len(cases)}','bne next','lda #$a5','sta $02e0',
        'done: jmp done','checkpoint: nop','rts','record: .word records','records:']
    for c in cases:
        name=bytes(ord(ch)|128 for ch in c['name'].ljust(10)[:10])
        s.append('.byte '+','.join(str(b) for b in name+bytes([c['destination']>>8,1 if c['side']=='a' else 2])))
    (out/'reader.s').write_text('\n'.join(s)+'\n')
    (out/'reader.cfg').write_text('MEMORY { MAIN: start=$5000, size=$1000, file=%O; }\nSEGMENTS { CODE: load=MAIN, type=rw; }\n')
    subprocess.run(['ca65','-g',str(out/'reader.s'),'-o',str(out/'reader.o')],check=True)
    subprocess.run(['ld65','-C',str(out/'reader.cfg'),str(out/'reader.o'),'-o',str(out/'reader.bin'),'-Ln',str(out/'reader.lbl')],check=True)
    shutil.copyfile(media/'synthetic-b.dsk',out/'reader-b.dsk')
    code_ranges=[(0x9400,syms['lc_saved_bank1']),
                 (syms['ko_print_script_string'],syms['ko_room_size']),
                 (syms['ko_load_pool'],syms['ko_package_header']),
                 (syms['ko_load_dispatch'],0x9400+built['runtime']['bytes'])]
    report={'kind':'all-resource synthetic media reader; no game logic execution',
            'build':built,'cases':cases,'retained_native_files':retained,
            'checkpoint':labels(out/'reader.lbl')['checkpoint'],'code_ranges':code_ranges,
            'reader_symbols':{k:syms[k] for k in ['ko_room_size','ko_load_error','ko_media_id']},
            'reader_sha256':digest((out/'reader.bin').read_bytes()),
            'synthetic_b_sha256':digest((out/'reader-b.dsk').read_bytes()),
            'shape_source_catalog_sha256':encoding['catalog_sha256'],
            'synthetic_pool_body_whitelist_verified':True}
    write_json(out/'build.json',report)
    print(json.dumps({'resources':len(cases),'retained_native_files':len(retained),
                      'free_sectors':{s:built['game_'+s]['free_sectors'] for s in ('a','b')}}))


if __name__=='__main__':main()
