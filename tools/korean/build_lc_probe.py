#!/usr/bin/env python3
"""Assemble an isolated LC/font test; does not patch a game disk."""
import argparse
import json
from pathlib import Path
import subprocess

from catalog import ROOT, digest, write_json
from font import load_font, subset


TEXT = ['한글 출력 시험 ABC 0123456789', '가나다라마바사아자차카타파하', '읽기 쓰기 저장 복원 디스크 교체']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'build/korean/lc-probe')
    p.add_argument('--without-lc', action='store_true')
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    chars, data = subset('\n'.join(TEXT), load_font())
    labels = {}
    for line in (ROOT / 'build/korean/english-baseline/chargen.lbl').read_text().splitlines():
        words = line.split()
        if len(words) == 3 and words[0] == 'al':
            labels[words[2].lstrip('.')] = int(words[1], 16)
    source = ['.setcpu "6502"', '.segment "CODE"',
        'entry: sei', 'cld', 'jsr lc_detect', 'bcs present', 'lda #$4e', 'jmp finish', 'present:',
        'lda $c080', 'lda $d000', 'cmp lc_saved_bank2', 'bne detect_corrupted',
        'lda $e000', 'cmp lc_saved_common', 'bne detect_corrupted',
        'lda $c088', 'lda $d000', 'cmp lc_saved_bank1', 'beq detect_preserved',
        'detect_corrupted: bit $c082', 'lda #$e1', 'jmp finish', 'detect_preserved: bit $c082',
        'lda #0', 'sta $26', 'lda #$20', 'sta $27', 'ldy #0',
        'clear_page: lda #0', 'clear_byte: sta ($26),y', 'iny', 'bne clear_byte',
        'inc $27', 'lda $27', 'cmp #$60', 'bne clear_page',
        'bit $c050', 'bit $c052', 'bit $c057', 'bit $c054']
    # Distinct bank addresses exercise bank selection and DFxx->E0xx crossing.
    for switch, base in [(0xc08b, 0xd000), (0xc083, 0xdf00)]:
        source += [f'lda ${switch:04x}', f'lda ${switch:04x}']
        for i, b in enumerate(data):
            source += [f'lda #${b:02x}', f'sta ${base+i:04x}']
        source.append('bit $c082')
    expected = []
    for page in (0, 1):
        inverse = 255 if page else 0
        source += [f'lda #{page}', 'sta $0346', f'lda #{inverse}', 'sta $0347']
        for row, text in enumerate(TEXT):
            for col, char in enumerate(text):
                glyph = chars.index(char)
                bank1 = (row + col) % 2 == 0
                address = (0xd000 if bank1 else 0xdf00) + glyph * 8
                source += [f'lda #{col}', 'sta $24', f'lda #{row}', 'sta $25',
                    f'lda #${address & 255:02x}', 'sta $1e', f'lda #${address >> 8:02x}', 'sta $1f',
                    f'ldx #{8 if bank1 else 0}', 'jsr lc_fetch_glyph',
                    'lda #<lc_glyph_scratch', 'sta $1e', 'lda #>lc_glyph_scratch', 'sta $1f',
                    f"jsr ${labels['locate_cursor_scanline']:04x}",
                    f"jsr ${labels['draw_eight_scanlines']:04x}"]
                for y, value in enumerate(data[glyph*8:glyph*8+8]):
                    scan = row * 12 + y
                    offset = (scan & 7)*0x400 + ((scan >> 3) & 7)*0x80 + (scan >> 6)*0x28
                    expected.append({'address': 0x2000 + page*0x2000 + offset + col,
                                     'value': value ^ inverse})
    source += ['lda #1', 'jsr $fca8',  # firmware WAIT must work after LC access
               'lda #$a5', 'finish: sta $02e0', 'done: jmp done',
               '.include "lc.s"']
    (out / 'probe.s').write_text('\n'.join(source)+'\n')
    (out / 'probe.cfg').write_text('MEMORY { MAIN: start=$6000, size=$4DFC, file=%O; }\n'
                                 'SEGMENTS { CODE: load=MAIN, type=rw; }\n')
    subprocess.run(['ca65', '-I', str(ROOT / 'src/korean'), str(out/'probe.s'), '-o', str(out/'probe.o')], check=True)
    subprocess.run(['ld65', '-C', str(out/'probe.cfg'), str(out/'probe.o'), '-o', str(out/'probe.bin'),
                    '-Ln', str(out/'probe.lbl')], check=True)
    write_json(out/'expected.json', {'expect_lc': not args.without_lc, 'bytes': expected})
    write_json(out/'build.json', {'kind': 'synthetic LC test, temporary $6000 fixture placement',
        'font_chars': chars, 'font_bytes': len(data), 'checked_hgr_bytes': len(expected),
        'lc_source_sha256': digest((ROOT/'src/korean/lc.s').read_bytes()),
        'probe_sha256': digest((out/'probe.bin').read_bytes())})
    print(out)


if __name__ == '__main__':
    main()
