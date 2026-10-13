; ULTRA high-resolution character output, loaded as part of CHAR GEN.
; Original allocated-file offsets $0504-$0603 -> CPU $B300-$B3FF.
; Character bitmaps begin at $B400, encoded from assets/decoded/font PNGs.
;
; Install: call renderer_install; sets ROM COUT vector $36 and $0348 draw vector.
; COUT: A = high-bit Apple character; preserves X/Y via absolute $001C/$001D,
; clobbers A, flags and $1E/$1F/$26/$27. Not reentrant. Cursor is $24 column
; and $25 text row. Page byte $0346: 0 -> HGR1, nonzero -> HGR2.
; Background byte $0347 is written before XORing a glyph. Glyph high bits
; therefore retain the asset's original artifact-color behavior.
;
; This module preserves the original rendering. It does not scroll; row 15
; clamps. Higher-level scripts clear/rewrite the three dialogue rows.
.setcpu "6502"
.segment "RENDERER"

saved_x = $1C
saved_y = $1D
glyph_pointer = $1E
cursor_column = $24
cursor_row = $25
scanline_pointer = $26
cout_vector = $36
draw_page = $0346
background = $0347
draw_vector = $0348
scanline_low = $B000
scanline_hgr1_high = $B100
scanline_hgr2_high = $B200
rom_backspace = $FC10

.export renderer_install, renderer_cout, renderer_draw_glyph
renderer_install:
        jmp install_vectors
current_scanline:
        .byte $00                 ; mutable workspace, not a BRK instruction
install_vectors:
        lda #<renderer_cout
        sta cout_vector
        lda #>renderer_cout
        sta cout_vector+1
        lda #<renderer_draw_glyph
        sta draw_vector
        lda #>renderer_draw_glyph
        sta draw_vector+1
        rts

renderer_cout:
        stx a:saved_x              ; original absolute encoding, 3 bytes
        sty a:saved_y
        cmp #$88                  ; backspace
        bne check_return
        jmp backspace
check_return:
        cmp #$8D                  ; CR erases cursor cell, then advances row
        beq carriage_return
        cmp #$8A                  ; LF advances without erasing
        beq line_feed
        cmp #$A0
        bcs printable
        jmp restore_registers     ; other control characters are ignored
printable:
        jsr renderer_draw_glyph
        jsr advance_column
        jmp restore_registers

; A = character, cursor/page/background as above. Clobbers A/X/Y and pointers.
; Does not advance cursor. Callers using $0348 must preserve their own registers.
renderer_draw_glyph:
        jsr locate_glyph
        jsr locate_cursor_scanline
        jsr draw_eight_scanlines
        rts

locate_glyph:
        and #$7F
        sta glyph_pointer
        lda #$00
        sta glyph_pointer+1
        asl glyph_pointer
        rol glyph_pointer+1
        asl glyph_pointer
        rol glyph_pointer+1
        asl glyph_pointer
        rol glyph_pointer+1
        lda glyph_pointer+1
        adc #$B3                  ; printable ASCII maps to $B400-$B6FF
        sta glyph_pointer+1
        rts

draw_eight_scanlines:
        ldx #$00
draw_scanline:
        txa
        tay
        lda (glyph_pointer),y
        ldy cursor_column
        pha
        lda background
        sta (scanline_pointer),y
        pla
        eor (scanline_pointer),y
        jmp store_scanline
reserved_patch_bytes:
        .byte $00,$00,$00,$00     ; unreachable jump-over patch space
store_scanline:
        sta (scanline_pointer),y
        jsr next_scanline
        inx
        cpx #$08
        bne draw_scanline
        rts

backspace:
        jsr rom_backspace
erase_after_backspace:
        jsr erase_cursor_cell
        jmp restore_registers
carriage_return:
        jsr erase_cursor_cell
line_feed:
        jsr next_text_row
        jmp restore_registers
restore_registers:
        ldx a:saved_x
        ldy a:saved_y
        rts
erase_cursor_cell:
        lda #$A0
        jsr renderer_draw_glyph
        rts

advance_column:
        inc cursor_column
        ldy cursor_column
        cpy #40
        bcc clamp_row
next_text_row:
        ldy #$00
        sty cursor_column
        inc cursor_row
clamp_row:
        ldy cursor_row
        cpy #16
        bcc row_in_bounds
        ldy #15
        sty cursor_row
row_in_bounds:
        rts

locate_cursor_scanline:
        jsr clamp_row
        lda text_row_scanline,y
        tay
        sta current_scanline
locate_scanline:
        lda scanline_low,y
        sta scanline_pointer
        lda draw_page
        bne select_hgr2
        lda scanline_hgr1_high,y
        sta scanline_pointer+1
        bne scanline_found        ; all HGR1 high addresses are nonzero
select_hgr2:
        lda scanline_hgr2_high,y
        sta scanline_pointer+1
scanline_found:
        rts
next_scanline:
        ldy current_scanline
        iny
        sty current_scanline
        jmp locate_scanline

text_row_scanline:
        .byte 0,12,24,36,48,60,72,84,96,108,120,132,144,156,168,180
renderer_tail:
        .byte $B0,$B0,$8D,$00,$00,$00,$00,$37,$FF
        ; $B3F7-$B3FF outside reachable routines; meaning remains unconfirmed.
        ; Retained as native CHAR GEN tail, explicitly not disassembled code.
.assert * - renderer_install = $100, error, "renderer must fit its original page"
