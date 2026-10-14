#!/usr/bin/env python3
"""Synthetic full-pool message reader fixture, separate from game translation."""
import argparse
import struct
import subprocess
from pathlib import Path

from build_messages import build, labels
from catalog import ROOT, digest, write_json
from encoding import encode
from font import load_font, subset


def make_pool(texts, ids, size):
    data = bytearray([0xcc] * size)
    struct.pack_into('<H', data, 0, len(texts))
    cursor = 2 + len(texts)*2
    offsets = []
    for i, text in enumerate(texts):
        encoded = encode(text, ids)
        if i == len(texts)-1:
            cursor = size-len(encoded)  # last terminator at the final allowed byte
        offsets.append(cursor)
        struct.pack_into('<H', data, 2+i*2, cursor)
        data[cursor:cursor+len(encoded)] = encoded
        cursor += len(encoded)
    assert len(data) == size
    return bytes(data), offsets


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args=p.parse_args(); out=args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    runtime=build(out/'runtime'); symbols=labels(out/'runtime/messages.lbl')
    # Exercise native error entry points in the same conditional engine used by
    # startup disks. The English build remains the authority for fixed addresses.
    (out/'korean-bindings.inc').write_text('\n'.join(f'{name} = ${symbols[name]:04x}' for name in
        ('ko_print_script_string','ko_load_dispatch','ko_finish_startup'))+'\n')
    subprocess.run(['ca65','-g','-D','KOREAN=1','-I',str(out),str(ROOT/'src/interpreter.s'),
                    '-o',str(out/'interpreter.o')],check=True)
    subprocess.run(['ld65','-C',str(ROOT/'src/interpreter.cfg'),str(out/'interpreter.o'),
                    '-o',str(out/'interpreter.bin'),'-Ln',str(out/'interpreter.lbl')],check=True)
    engine=labels(out/'interpreter.lbl')
    native=labels(ROOT/'build/korean/english-baseline/interpreter.lbl')
    for name in ('print_script_string','print_engine_error','file_not_found','disk_error',
                 'input_without_cr','script_stack_overflow'):
        assert engine[name]==native[name],name
    # All 1024 valid common-region slots: exercise low byte 00/0A/8D/FF and FFFF.
    base=set('한글 출력 시험 읽기 쓰기 저장 복원 디스크 교체 끝')-{' '}
    for n in range(0xac00, 0xd7a4):
        if len(base)==1024: break
        base.add(chr(n))
    chars, font=subset(''.join(sorted(base)), load_font()); ids={c:i for i,c in enumerate(chars)}
    resident=['한글 출력 시험 ABC 0123456789\n'+('읽기 쓰기 저장 복원 디스크 교체 '*5),
              '끝'+chars[1023]]
    room=['', '']
    # Only use the deliberately selected 1024 glyphs, independent of catalog.
    room[0]='BANK 2: '+''.join(chars[i] for i in (0,10,13,59,141,255,256,511,1023))+'\n'+'가'*140
    room[1]='끝'+chars[256]
    resident_data,res_offsets=make_pool(resident,ids,4096)
    room_data,room_offsets=make_pool(room,ids,1024)
    (out/'font.bin').write_bytes(font);(out/'resident.bin').write_bytes(resident_data);(out/'room.bin').write_bytes(room_data)
    s=['.setcpu "6502"','.segment "CODE"','entry: sei','cld']
    s += [f'{name} = ${address:04x}' for name,address in symbols.items() if name in
          ('lc_detect','ko_print_message','ko_print_script_string','ko_room_size','ko_resident_size','ko_font_count')]
    s += ['jsr lc_detect','bcs lc_ok','lda #$4e','jmp finish','lc_ok:']
    for source,target,pages,switch in [(0x2000,0xe000,32,0xc083),(0x4000,0xd000,16,0xc08b),(0x5000,0xd000,4,0xc083)]:
        s += [f'lda ${switch:04x}',f'lda ${switch:04x}',f'lda #${source>>8:02x}','sta $07',
              f'lda #${target>>8:02x}','sta $09','lda #0','sta $06','sta $08',f'ldx #{pages}','jsr copy_pages','bit $c082']
    def word(label,value):
        s.extend([f'lda #${value&255:02x}',f'sta {label}',f'lda #${value>>8:02x}',f'sta {label}+1'])
    word('ko_room_size',1024);word('ko_resident_size',4096);word('ko_font_count',1024)
    s+=['jsr $b300','lda #0','sta $24','sta $25','sta $0346','sta $0347']
    cases=[]
    def call(mid,success,name,irq=False,wrapper=False,entry=None):
        n=len(cases)+1;cases.append({'number':n,'name':name,'expect_success':success,'interrupts_enabled':irq})
        s.extend([f'lda #{n}','sta $02e1','cli' if irq else 'sei',f'lda #{mid&255}',f'ldx #{mid>>8}',
                  f'jsr ${entry:04x}' if entry is not None else
                  'jsr ko_print_script_string' if wrapper else 'jsr ko_print_message'])
        # Native error entry points do not define a return carry flag.
        if success is not None:
            s.extend(['bcs :+' if success else 'bcc :+','jmp failed',':'])
        s.extend([
                  # Inspect I before any fixture SEI; reader must restore caller state.
                  'php','pla','and #4','beq :+' if irq else 'bne :+','jmp failed',':','sei',
                  'lda #1','jsr $fca8'])
    call(2,False,'room ID beyond count');call(0x8002,False,'resident ID beyond count')
    word('ko_room_size',1);call(0,False,'short room header');word('ko_room_size',1024)
    word('ko_room_size',1025);call(0,False,'oversized room');word('ko_room_size',1024)
    word('ko_resident_size',4097);call(0x8000,False,'oversized resident');word('ko_resident_size',4096)
    word('ko_font_count',1025);call(0,False,'font exceeds common region');word('ko_font_count',1024)
    def mutate(address, value):
        s.extend(['lda $c083','lda $c083',f'lda #{value}',f'sta ${address:04x}','bit $c082'])
    for name,patch in [
        ('offset points into header',[(0xd002,0),(0xd003,0)]),
        ('offset beyond pool',[(0xd002,0),(0xd003,4)]),
        ('oversized count',[(0xd000,0),(0xd001,8)]),
        ('unrecognized control byte',[(0xd000+room_offsets[0],13)]),
        ('unrecognized high opcode',[(0xd000+room_offsets[0],0xc0)]),
        ('glyph beyond font',[(0xd000+room_offsets[0],0x84),(0xd001+room_offsets[0],0)]),
        ('truncated glyph at final pool byte',[(0xd002,255),(0xd003,3),(0xd3ff,0x80)]),
        ('missing terminator at pool boundary',[(0xd002,255),(0xd003,3),(0xd3ff,ord('A'))])]:
        for addr,value in patch:mutate(addr,value)
        call(0,False,name,irq=True)
        for addr,_ in patch:mutate(addr,room_data[addr-0xd000])
    # Mark interpreter/state/stack-adjacent ownership outside test workspace.
    for addr in [0xd0,0xd1,0xd2,0xd3,0xd4,0xd5,0xda,0xdb,0xdc,0xdd,0xde,0xdf,0xe7,0xe8,0x601c,0x93ff,0x9bff]:
        s += ['lda #$5a',f'sta ${addr:04x}']
    s += ['lda #0','sta $26','lda #$20','sta $27','ldy #0',
          'clear_page: lda #0','clear_byte: sta ($26),y','iny','bne clear_byte',
          'inc $27','lda $27','cmp #$60','bne clear_page',
          'bit $c050','bit $c052','bit $c057','bit $c054']
    pixels=bytearray(16384)
    ascii_chars,ascii_font=subset(''.join(chr(i) for i in range(32,127)),load_font())
    bitmaps={c:ascii_font[i*8:i*8+8] for i,c in enumerate(ascii_chars)}
    bitmaps.update({c:font[i*8:i*8+8] for i,c in enumerate(chars)})
    def plot(text,page,row,col,inverse):
        def glyph(c):
            for y,value in enumerate(bitmaps[c]):
                scan=row*12+y
                offset=(scan&7)*1024+((scan>>3)&7)*128+(scan>>6)*40+col+page*8192
                pixels[offset]=value^inverse
        for c in text:
            if c=='\n':
                glyph(' ');col=0;row=min(row+1,15)
            else:
                glyph(c);col+=1
                if col==40:col=0;row=min(row+1,15)
        return row,col
    for page in (0,1):
        inverse=255 if page else 0
        s += [f'lda #{page}','sta $0346',f'lda #{inverse}','sta $0347']
        for mid,text,row,col in [(0x8000,resident[0],0,0),(0,room[0],6,0),
                                 (0x8001,resident[1],12,39),(1,room[1],15,39)]:
            s += [f'lda #{row}','sta $25',f'lda #{col}','sta $24']
            call(mid,True,f'page{page} ID{mid:04X}',irq=bool(page))
            endrow,endcol=plot(text,page,row,col,inverse)
            s += ['lda $24',f'cmp #{endcol}','beq :+','jmp failed',':',
                  'lda $25',f'cmp #{endrow}','beq :+','jmp failed',':']
        for script,text,row,col in [('~8001;\r',resident[1],11,1),
                                   ('~0001\r',room[1]+'\n',13,1),
                                   ('12345;\r','12345',14,1),
                                   ('OK>^\r','OK>^\n',14,10)]:
            for i,c in enumerate(script):
                s += [f'lda #{ord(c)|128}',f'sta ${0x02a0+i:04x}']
            s += [f'lda #{row}','sta $25',f'lda #{col}','sta $24']
            call(0x02a0,True,f'page{page} wrapper {script!r}',irq=True,wrapper=True)
            endrow,endcol=plot(text,page,row,col,inverse)
            s += ['lda $24',f'cmp #{endcol}','beq :+','jmp failed',':',
                  'lda $25',f'cmp #{endrow}','beq :+','jmp failed',':']
        for script in ['~000G\r','~0001X\r','~0001;X','~800F\r']:
            for i,c in enumerate(script):
                s += [f'lda #{ord(c)|128}',f'sta ${0x02a0+i:04x}']
            call(0x02a0,False,f'page{page} invalid wrapper {script!r}',wrapper=True)
        # Errors must remain printable while the room cache is invalid (for
        # example with save media inserted). Keep the original two extra CRs.
        word('ko_room_size',0)
        for name,address,script,text,row in [
            ('file_not_found',0x0350,'~8001\r',resident[1]+'\n\n\n',1),
            ('disk_error',0x0360,'~8001;\r',resident[1]+'\n\n',4),
            ('input_without_cr',0x0370,'INPUT ERROR\r','INPUT ERROR\n\n\n',7),
            ('script_stack_overflow',0x0380,'~8001\r',resident[1]+'\n\n\n',10)]:
            for i,c in enumerate(script):
                s += [f'lda #{ord(c)|128}',f'sta ${address+i:04x}']
            s += [f'lda #{row}','sta $25','lda #0','sta $24']
            call(0,None,f'page{page} engine {name}, room cache empty',irq=bool(page),entry=engine[name])
            endrow,endcol=plot(text,page,row,0,inverse)
            s += ['lda $24',f'cmp #{endcol}','beq :+','jmp failed',':',
                  'lda $25',f'cmp #{endrow}','beq :+','jmp failed',':']
        word('ko_room_size',1024)
    for addr in [0xd0,0xd1,0xd2,0xd3,0xd4,0xd5,0xda,0xdb,0xdc,0xdd,0xde,0xdf,0x601c,0x93ff,0x9bff]:
        s += [f'lda ${addr:04x}','cmp #$5a','beq :+','jmp failed',':']
    s += ['lda #$a5','jmp finish','failed: lda #$e1','finish: sta $02e0','done: jmp done',
          'copy_pages: ldy #0','copy_byte: lda ($06),y','sta ($08),y','iny','bne copy_byte',
          'inc $07','inc $09','dex','bne copy_pages','rts']
    (out/'probe.s').write_text('\n'.join(s)+'\n')
    (out/'probe.cfg').write_text('MEMORY { MAIN: start=$6800, size=$2800, file=%O; }\nSEGMENTS { CODE: load=MAIN, type=rw; }\n')
    subprocess.run(['ca65',str(out/'probe.s'),'-o',str(out/'probe.o')],check=True)
    subprocess.run(['ld65','-C',str(out/'probe.cfg'),str(out/'probe.o'),'-o',str(out/'probe.bin'),'-Ln',str(out/'probe.lbl')],check=True)
    (out/'expected-hgr.bin').write_bytes(pixels)
    write_json(out/'build.json',{'kind':'synthetic LC message reader fixture','runtime':runtime,'cases':cases,
        'font_glyphs':1024,'font_bytes':len(font),'resident_bytes':4096,'room_bytes':1024,
        'fixture_sha256':digest((out/'probe.bin').read_bytes()),'expected_hgr_sha256':digest(pixels),
        'interpreter_source_sha256':digest((ROOT/'src/interpreter.s').read_bytes()),
        'interpreter_sha256':digest((out/'interpreter.bin').read_bytes()),
        'native_error_addresses':{name:engine[name] for name in
            ('print_engine_error','file_not_found','disk_error','input_without_cr','script_stack_overflow')},
        'texts':{'resident':resident,'room':room}})
    print(out)


if __name__=='__main__':main()
