#!/usr/bin/env python3
"""Exercise the actual packed native strings on dirty HGR pages, with no room pool."""
import argparse
import json
from pathlib import Path
import subprocess

from build_messages import labels
from catalog import ROOT, DEFAULT, digest, write_json
from encoding import decode
from font import load_font, subset


def build(media, output):
    output.mkdir(parents=True,exist_ok=False)
    built=json.loads((media/'startup-build.json').read_text())
    assert built['native_ui'] and built['full_synthetic']
    syms=labels(media/'runtime/messages.lbl')
    native=labels(media/'intrinsics.lbl');engine=labels(media/'interpreter.lbl')
    glyphs=json.loads((media/'encoding/glyphs.json').read_text())
    pool=(media/'encoding/resident-pool.bin').read_bytes()
    aliases=json.loads((media/'encoding/resident-aliases.json').read_text())
    messages={m['id']:m for m in json.loads(DEFAULT.read_text())['messages']}
    def text(mid):
        n=aliases[mid]&0x7fff;at=int.from_bytes(pool[2+n*2:4+n*2],'little')
        # decode() checks the exact body size, so walk token boundaries to END.
        end=at
        while pool[end]:end+=2 if pool[end]>=128 else 1
        return decode(pool[at:end+1],glyphs)
    font=(media/'encoding/hangul-font.bin').read_bytes()
    ascii_chars,ascii_font=subset(''.join(chr(i) for i in range(32,127)),load_font())
    bitmaps={c:ascii_font[i*8:i*8+8] for i,c in enumerate(ascii_chars)}
    bitmaps.update({c:font[i*8:i*8+8] for i,c in enumerate(glyphs)})
    (output/'font.bin').write_bytes(font.ljust(8192,b'\0'))
    (output/'resident.bin').write_bytes(pool.ljust(4096,b'\0'))
    (output/'room.bin').write_bytes(bytes([0xcc])*1024)
    s=['.setcpu "6502"','.segment "CODE"','entry: sei','cld','ldx #$ff','txs']
    for source,target,pages,switch in [(0x2000,0xe000,32,0xc083),(0x4000,0xd000,16,0xc08b),(0x5000,0xd000,4,0xc083)]:
        s += [f'lda ${switch:04x}',f'lda ${switch:04x}',f'lda #{source>>8}','sta $07',
              f'lda #{target>>8}','sta $09','lda #0','sta $06','sta $08',f'ldx #{pages}','jsr copy_pages','bit $c082']
    for name,value in [('ko_room_size',0),('ko_resident_size',4096),('ko_font_count',len(glyphs))]:
        s += [f'lda #{value&255}',f'sta ${syms[name]:04x}',f'lda #{value>>8}',f'sta ${syms[name]+1:04x}']
    s += ['jsr $b300',f'lda #{syms["ko_print_script_string"]&255}','sta $0344',
          f'lda #{syms["ko_print_script_string"]>>8}','sta $0345']
    cases=[]
    for page in (0,1):
        for record in built['native_ui_records']:
            mid=record['id'];address=record.get('address',0x02fc+record['offset'])
            entry=engine[['file_not_found','disk_error','input_without_cr','script_stack_overflow'][int(mid[-1])]] if mid.startswith('parms:') else syms['ko_print_script_string']
            cases.append(dict(page=page,id=mid,address=address,entry=entry,
                              clear=mid.startswith('runtime:'),extra_cr=2 if mid.startswith('parms:') else 0))
        for side in ('a','b'):
            cases.append(dict(page=page,id='native-media-'+side,entry=native['print_game_disk_prompt'],
                              address=0,clear=True,side=side,extra_cr=0))
    for n,c in enumerate(cases,1):
        page=c['page'];inverse=255 if page else 0
        pixels=bytearray([0xa5])*16384;row=12 if c['clear'] else 0;col=0
        def plot(value):
            nonlocal row,col
            def glyph(char):
                for y,value in enumerate(bitmaps[char]):
                    scan=row*12+y
                    at=(scan&7)*1024+((scan>>3)&7)*128+(scan>>6)*40+col+page*8192
                    pixels[at]=value^inverse
            for char in value:
                if char=='\n':glyph(' ');col=0;row=min(row+1,15)
                else:
                    glyph(char);col+=1
                    if col==40:col=0;row=min(row+1,15)
        if c['clear']:plot(' '*160);row=12;col=0
        if 'side' in c:
            mids=['intrinsic:disk_action_error_text','intrinsic:game_disk_prompt_text',
                  'intrinsic:disk_side_'+c['side']+'_text','intrinsic:drive_prompt_text','intrinsic:disk_prompt_ok_text']
        else:mids=[c['id']]
        for mid in mids:
            m=messages[mid];plot((m['source'] if m['status']=='excluded' else text(mid))+('\n' if m['layout']['newline'] else ''))
        plot('\n'*c['extra_cr'])
        c.update(number=n,end_row=row,end_column=col,inverse=inverse)
        (output/f'expected-{n}.bin').write_bytes(pixels)
        s += ['jsr dirty_pages',f'bit ${0xc054+page:04x}',f'lda #{n}','sta $02e1',f'lda #{page}','sta $0346',
              f'lda #{inverse}','sta $0347','lda #0','sta $24','sta $25',
              f'lda #{c["address"]&255}',f'ldx #{c["address"]>>8}']
        if c['clear'] and 'side' not in c:
            s += [f'jsr ${syms["ko_clear_message_rows"]:04x}']
        if 'side' in c:s += [f'lda #{1 if c["side"]=="a" else 2}','sta $601c']
        # Let the video scanout finish after the last write before screenshots.
        # This wait belongs only to the injected fixture, never to game code.
        s += [f'jsr ${c["entry"]:04x}','lda #120','jsr $fca8','jsr checkpoint']
    s += ['lda #$a5','sta $02e0','done: jmp done','checkpoint: nop','rts',
          'copy_pages: ldy #0','copy_byte: lda ($06),y','sta ($08),y','iny','bne copy_byte',
          'inc $07','inc $09','dex','bne copy_pages','rts',
          'dirty_pages: lda #0','sta $06','lda #$20','sta $07','ldx #64','ldy #0','lda #$a5',
          'dirty_byte: sta ($06),y','iny','bne dirty_byte','inc $07','dex','bne dirty_byte','rts']
    (output/'probe.s').write_text('\n'.join(s)+'\n')
    (output/'probe.cfg').write_text('MEMORY { MAIN: start=$6800, size=$2c00, file=%O; }\nSEGMENTS { CODE: load=MAIN, type=rw; }\n')
    subprocess.run(['ca65','-g',str(output/'probe.s'),'-o',str(output/'probe.o')],check=True)
    subprocess.run(['ld65','-C',str(output/'probe.cfg'),str(output/'probe.o'),'-o',str(output/'probe.bin'),'-Ln',str(output/'probe.lbl')],check=True)
    report=dict(media=str(media),cases=cases,checkpoint=labels(output/'probe.lbl')['checkpoint'],
                ko_room_size=syms['ko_room_size'],runtime_bytes=built['runtime']['bytes'],
                harness_sha256=digest((output/'probe.bin').read_bytes()),
                source_sha256=digest(Path(__file__).read_bytes()))
    write_json(output/'build.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--media',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    print(len(build(args.media.resolve(),args.output.resolve())['cases']))
