; CHAR GEN allocated stream at $ADFC-$B6FB. See docs/chargen.md.
.setcpu "6502"
.segment "CHARGEN_HEADER"
        .word $1700,$08FB ; nominal legacy address/length, ignored by custom loader
.segment "CHARGEN_LEGACY"
; Uncalled editor fragment: starts with tail of inline text from an older program.
legacy_editor_text_tail:
        .byte $1F
        .asciiz "VTOC: "
legacy_editor_vtoc_action:
        lda #$17
        ldx #$C2
        jmp $1673 ; older editor entry, not current game interface
legacy_editor_video_action:
        jsr $18A7
        jsr $19BE
        jsr $1F00 ; older inline-text printer, consumes next zero-terminated string
        .asciiz "V-edit: "
        lda #$17
        ldx #$D8
        jsr $1673
        jmp $1715
legacy_editor_return:
        clc
        rts
; Key byte followed by legacy entry address; these are data, not instructions.
legacy_editor_command_table:
        .byte $08
        .word $0E83
        .byte $15
        .word $0E73
        .byte ';'
        .word $13FC
        .byte '+'
        .word $13C2
        .byte 'J'
        .word $085B
        .byte 'I'
        .word $083F
        .byte 'K'
        .word $0853
        .byte 'M'
        .word $0849
        .byte 'L'
        .word $0869
        .byte 'U'
        .word $0863
        .byte 'O'
        .word $09C7
        .byte '.'
        .word $09D2
        .byte ','
        .word $099A
        .byte '0'
        .word $113A
        .byte 'X'
        .word $1159
        .byte 'Q'
        .word $09F2
        .byte 'Z'
        .word $0A03
        .byte 'A'
        .word $0A12
        .byte $0D
        .word $0A54
        .byte ':'
        .word $0A5C
        .byte '-'
        .word $0A48
        .byte 'G'
        .word $0961
        .byte 'H'
        .word $0965
        .byte 'B'
        .word $095D
        .byte 'N'
        .word $09B1
        .byte 'T'
        .word $162B
        .byte 'Y'
        .word $096B
        .byte 'W'
        .word $0ED6
        .byte 'R'
        .word $0EC8
        .byte 'E'
        .word $108B
        .byte 'S'
        .word $0F22
        .byte 'C'
        .word $10E0
        .byte $03
        .word $10D3
        .byte 'D'
        .word $16CF
        .byte 'V'
        .word $16FE
        .byte 'F'
        .word $1130
        .byte 'P'
        .word $247D
        .byte '?'
        .word $0A3E
        .byte '/'
        .word $1C01
        .byte $11
        .word $2266
        .byte 0
; Key byte followed by legacy entry address; these are data, not instructions.
legacy_editor_command_table_2:
        .byte 'C'
        .word $1262
        .byte ' '
        .word $0AC2
        .byte 'F'
        .word $146C
        .byte 'G'
        .word $118A
        .byte 'L'
        .word $12E2
        .byte 'R'
        .word $2149
        .byte 'S'
        .word $154E
        .byte 'W'
        .word $0B52
        .byte $1B
        .word $172B
        .byte 0
; Key byte followed by legacy entry address; these are data, not instructions.
legacy_editor_command_table_3:
        .byte ' '
        .word $0B5C
        .byte 'E'
        .word $170F
        .byte 'F'
        .word $1A3F
        .byte 'M'
        .word $1A37
        .byte 'R'
        .word $1179
        .byte 'W'
        .word $117D
        .byte $1B
        .word $172B
        .byte 0
; Key byte followed by legacy entry address; these are data, not instructions.
legacy_editor_command_table_4:
        .byte $1B
        .word $1B66
        .byte ' '
        .word $1B56
        .byte 'I'
        .word $19D5
        .byte 'J'
        .word $19F2
; Same 28 mask bytes as INTRIN pixel masks; unused copy in editor residue.
legacy_editor_mask_tail:
        .byte $FC,$F3,$CF,$BF,$FF,$FF,$FF,$FF
        .byte $FF,$FF,$FE,$F9,$E7,$9F,$FF,$FF
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte $FF,$FF,$FF,$FF
.assert * = $AF00, error, "legacy fragment must occupy one page"
.segment "CHARGEN_LOOKUPS"
; Logical horizontal coordinate is doubled: 140 units cover 280 HGR pixels.
pixel_byte_bit_lookup:
        .repeat $100,I
        .if I < 140
        .byte (I/7)*8+(I .mod 7)
        .else
        .byte 7 ; native out-of-range entry
        .endif
        .endrepeat
hgr_scanline_low:
        .repeat $100,I
        .if I < 192
        .byte <((I&7)*$400+((I>>3)&7)*$80+(I>>6)*$28)
        .else
        .byte 0
        .endif
        .endrepeat
hgr1_scanline_high:
        .repeat $100,I
        .if I < 192
        .byte >($2000+(I&7)*$400+((I>>3)&7)*$80+(I>>6)*$28)
        .else
        .byte $F0 ; native invalid-row marker
        .endif
        .endrepeat
hgr2_scanline_high:
        .repeat $100,I
        .if I < 192
        .byte >($4000+(I&7)*$400+((I>>3)&7)*$80+(I>>6)*$28)
        .else
        .byte $F0
        .endif
        .endrepeat
.assert * = $B300, error, "lookup pages must precede renderer"
.include "renderer.s"
.segment "CHARGEN_FONT"
character_bitmaps:
        .incbin "font.bin" ; generated only from assets/decoded/font PNGs
.assert character_bitmaps = $B400, error, "font address moved"
.assert * = $B6FC, error, "CHAR GEN allocated stream must occupy nine sectors"
