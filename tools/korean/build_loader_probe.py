#!/usr/bin/env python3
"""Build synthetic DOS resource fixtures and a streaming-loader harness."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

from build_messages import build, labels, bind_media_id
from catalog import ROOT, digest, write_json
from encoding import pool
from packages import package as frame_package, HEADER_BYTES
sys.path.insert(0,str(ROOT/'tools'))
from dos_disk import Disk, offset


def script(length):
    prefix=bytes(ord(c)|128 for c in '.P "~0000;\r')
    assert length>len(prefix)
    return prefix+bytes([0xa0])*(length-len(prefix)-1)+b'\0'


MEDIA_ID = bytes.fromhex('0123456789abcdef01234567')


def package(source, data=b'', lengths=None, magic=b'KOR2', identity=MEDIA_ID, sides=1):
    data=frame_package(source,data,identity=identity,sides=sides)
    return magic+struct.pack('<HH',*(lengths or struct.unpack_from('<HH',data,4)))+data[8:]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    runtime=build(out/'runtime');syms=labels(out/'runtime/messages.lbl')
    runtime=bind_media_id(out/'runtime',MEDIA_ID)
    original=(ROOT/'build/korean/english-baseline/mask-of-sun-a.dsk').read_bytes()
    image=bytearray(original);catalog=Disk(original).catalog();files={f['name']:f for f in catalog['files']}
    text='LOADED FROM DISK\nLC BANK 2 0123456789'
    data,_=pool([{'ko':text}],{});full_pool=data+bytes([0xcc])*(1000-len(data))
    cases=[]
    def case(name,file,source=None,data=b'',error=0,destination=0x6800,raw=None,volume=0,ts_patch=None,side=1,pool_only=False):
        n=len(cases)+1;f=files.get(file)
        item={'number':n,'name':name,'file':file,'error':error,'destination':destination,'volume':volume,
              'script_bytes':len(source or b''),'pool_bytes':len(data),'print_text':text if data and not error else None,
              'side':side,'pool_only':pool_only}
        item['interrupts_enabled']=bool(n%2)
        if source is not None:
            payload=raw if raw is not None else package(source,data)
            assert len(payload)<=f['allocated_bytes'],(file,len(payload),f['allocated_bytes'])
            padded=payload+bytes([0xce])*(f['allocated_bytes']-len(payload))
            for i,pair in enumerate(f['sectors']):
                start=offset(*pair);image[start:start+256]=padded[i*256:i*256+256]
            if ts_patch:
                start=offset(*f['ts_lists'][0])
                for pos,value in ts_patch.items():image[start+pos]=value
            (out/f'case-{n}-script.bin').write_bytes(source)
            (out/f'case-{n}-pool.bin').write_bytes(data)
            item['script_sha256']=digest(source);item['pool_sha256']=digest(data)
        cases.append(item)
    case('reject unaligned destination','ROOM 6.0',error=4,destination=0x6801)
    case('reject non-resource destination','ROOM 6.0',error=4,destination=0x2000)
    case('bad magic','ROOM 1.0',script(80),error=3,raw=package(script(80),magic=b'NOPE'))
    case('oversized room','ROOM 2.0',script(80),error=4,raw=package(script(80),lengths=(2049,0)))
    case('oversized library','ROOM 2.1',script(80),error=4,destination=0x7000,raw=package(script(80),lengths=(9217,0)))
    case('oversized room pool','ROOM 3.0',script(80),error=4,raw=package(script(80),lengths=(80,1025)))
    case('missing script EOF','ROOM 4.0',script(80)[:-1]+b'X',error=3)
    case('truncated stream after partial script','ROOM 5.0',script(600),error=5,ts_patch={14:0,15:0})
    cases[-1]['partial_script_bytes']=256-HEADER_BYTES
    case('truncated stream after partial LC pool','ROOM 9.0',script(271),full_pool,error=5,ts_patch={18:0,19:0})
    cases[-1]['partial_script_bytes']=271
    cases[-1]['partial_pool_bytes']=768-HEADER_BYTES-271
    case('second TS list rejected','ROOM 5.1',script(80),error=3,ts_patch={1:1,2:1})
    case('invalid TS track rejected','ROOM 6.1',script(80),error=3,ts_patch={12:35})
    case('empty TS list','ROOM 6.2',script(80),error=5,ts_patch={12:0,13:0})
    case('missing filename','KO ABSENT',error=2)
    case('real RWTS volume mismatch','ROOM 6.0',error=1,volume=1)
    cases[-1]['expected_rwts_error']=0x20
    case('wrong build rejected before script write','ROOM 8.0',script(80),error=6,
         raw=package(script(80),identity=bytes([0x77])*12))
    case('wrong side rejected before script write','ROOM 10.0',script(80),error=6,
         raw=package(script(80),sides=2))
    case('old KOR1 rejected','ROOM 11.0',script(80),error=3,raw=package(script(80),magic=b'KOR1'))
    case('B side resource accepted','ROOM 9.1',script(80),raw=package(script(80),sides=2),side=2)
    case('shared resource accepted on B','ROOM 9.2',script(80),raw=package(script(80),sides=3),side=2)
    case('restore pool rejects wrong build','ROOM 8.0',error=6,pool_only=True)
    case('restore pool rejects wrong side','ROOM 10.0',error=6,pool_only=True)
    case('unaligned script/pool split across eight sectors','ROOM 6.0',script(1023),full_pool)
    case('second room replaces cache','ROOM 7.0',script(271),data)
    case('maximum library stops exactly before code','LIBRARY',script(9216),destination=0x7000)
    case('resident-only room has no local pool','ROOM 7.1',script(80))
    # Reuse the valid disk file after the library/cache transitions.
    case('reload after empty pool','ROOM 6.0')
    cases[-1].update(script_bytes=1023,pool_bytes=len(full_pool),print_text=text,
                    script_sha256=digest(script(1023)),pool_sha256=digest(full_pool))
    (out/f'case-{len(cases)}-script.bin').write_bytes(script(1023));(out/f'case-{len(cases)}-pool.bin').write_bytes(full_pool)
    pixels=bytearray(8192)
    native_font=(ROOT/'build/korean/english-baseline/chargen.bin').read_bytes()
    row=col=0
    for char in text:
        code=32 if char=='\n' else ord(char)
        glyph=native_font[0xb300+code*8-0xadfc:0xb300+code*8-0xadfc+8]
        for y,value in enumerate(glyph):
            scan=row*12+y
            pos=(scan&7)*1024+((scan>>3)&7)*128+(scan>>6)*40+col
            pixels[pos]=value
        if char=='\n':row+=1;col=0
        else:
            col+=1
            if col==40:row+=1;col=0
    (out/'expected-hgr.bin').write_bytes(pixels)
    (out/'synthetic-a.dsk').write_bytes(image)
    # Intentionally invalid TS fixtures prevent a full catalog ownership audit.
    # Verify every mutated sector is within the explicitly selected fixture files/TS.
    allowed={tuple(pair) for c in cases if c['file'] in files for pair in
             (files[c['file']]['sectors']+files[c['file']]['ts_lists'])}
    changed=[]
    for track in range(35):
        for sector in range(16):
            pos=offset(track,sector)
            if image[pos:pos+256]!=original[pos:pos+256]:
                assert (track,sector) in allowed
                changed.append([track,sector])
    s=['.setcpu "6502"','.segment "CODE"']
    for name in ('lc_detect','ko_load_package','ko_load_pool','ko_load_error','ko_room_size','ko_font_count','ko_print_script_string'):
        s.append(f'{name} = ${syms[name]:04x}')
    s += ['entry: sei','cld','jsr lc_detect','bcs :+','lda #$4e','sta $02e0','jmp done',':',
          'lda $c08b','lda $c08b','lda #$d0','sta $1f','lda #0','sta $1e','ldy #0','lda #$69',
          'fill_bank1: sta ($1e),y','iny','bne fill_bank1','inc $1f','ldx $1f','cpx #$e0','bne fill_bank1',
          'lda $c083','lda $c083','lda #$d0','sta $1f','lda #$69',
          'fill_bank2_common: sta ($1e),y','iny','bne fill_bank2_common','inc $1f','bne fill_bank2_common','bit $c082',
          'jsr $b300','lda #0','sta $0346','sta $0347','sta ko_font_count','sta ko_font_count+1']
    for c in cases:
        # Deliberately seed a stale cache; any failure must clear its validity.
        s += [f'lda #{c["number"]}','sta $02e1','lda #$99','sta ko_room_size','sta ko_room_size+1',
              f'lda #{c["volume"]}','sta $0bae','lda #0','sta $02e4',
              f'lda #{c["side"]}','sta $601c',
              f'lda #{c["destination"]&255}','sta $ec',f'lda #{c["destination"]>>8}','sta $ed',
              'cli' if c['interrupts_enabled'] else 'sei',
              f'lda #<name_{c["number"]}',f'ldx #>name_{c["number"]}',
              'jsr ko_load_pool' if c['pool_only'] else 'jsr ko_load_package',
              'lda #0','rol a','sta $02e2','php','pla','and #4','sta $02e5','sei',
              'lda ko_load_error','sta $02e3']
        if c['print_text']:
            s += ['lda #0','sta $26','lda #$20','sta $27','ldy #0',
                  f'clear_{c["number"]}: lda #0',f'clear_byte_{c["number"]}: sta ($26),y','iny',f'bne clear_byte_{c["number"]}',
                  'inc $27','lda $27','cmp #$40',f'bne clear_{c["number"]}',
                  'lda #0','sta $24','sta $25','bit $c050','bit $c052','bit $c057','bit $c054',
                  'lda #4','ldx #$68','jsr ko_print_script_string','lda #0','rol a','sta $02e4']
        s += ['jsr checkpoint']
    s += ['lda #$a5','sta $02e0','done: jmp done','checkpoint: nop','rts']
    for c in cases:
        name=(c['file']+' '*10)[:10]
        s += [f'name_{c["number"]}: .byte '+','.join(str(ord(v)|128) for v in name)]
    (out/'probe.s').write_text('\n'.join(s)+'\n')
    (out/'probe.cfg').write_text('MEMORY { MAIN: start=$5000, size=$1000, file=%O; }\nSEGMENTS { CODE: load=MAIN, type=rw; }\n')
    subprocess.run(['ca65','-g',str(out/'probe.s'),'-o',str(out/'probe.o')],check=True)
    subprocess.run(['ld65','-C',str(out/'probe.cfg'),str(out/'probe.o'),'-o',str(out/'probe.bin'),'-Ln',str(out/'probe.lbl')],check=True)
    code_ranges=[(0x9400,syms['lc_saved_bank1']), (syms['ko_print_script_string'],syms['ko_room_size']),
                 (syms['ko_load_package'],syms['ko_package_header'])]
    write_json(out/'build.json',{'kind':'synthetic packages on a copied DOS disk; no translated game',
        'runtime':runtime,'cases':cases,'checkpoint':labels(out/'probe.lbl')['checkpoint'],
        'reader_symbols':{k:syms[k] for k in ['ko_room_size','ko_load_error']},
        'code_ranges':code_ranges,'disk_sha256':digest(image),'source_disk_sha256':digest(original),
        'changed_sectors':changed,'fixture_sha256':digest((out/'probe.bin').read_bytes())})
    print(out)


if __name__=='__main__':main()
