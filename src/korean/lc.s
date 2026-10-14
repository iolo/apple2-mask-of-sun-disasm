; Apple II+ 16K Language Card helpers, 6502 only.
; Must execute from main RAM with ROM visible on entry. Returns ROM visible,
; LC writes disabled (C082), preserves interrupt flag via PHP/SEI/PLP.
; Not reentrant. No ROM call is made with LC RAM mapped in.
; A/X/Y clobbered. Runtime placement remains pending the complete memory budget.
.setcpu "6502"
.segment "CODE"
.export lc_detect, lc_fetch_glyph, lc_glyph_scratch

lc_pointer = $1e                   ; borrowed renderer glyph pointer
lc_ram_bank2 = $c080
lc_rom_readonly = $c082
lc_write_bank2 = $c083
lc_ram_bank1 = $c088
lc_write_bank1 = $c08b

; Carry set on success. Preserve tested bytes in both banks and common RAM.
lc_detect:
        php
        sei
        lda lc_ram_bank2
        lda $d000
        sta lc_saved_bank2
        lda $e000
        sta lc_saved_common
        lda lc_ram_bank1
        lda $d000
        sta lc_saved_bank1
        lda lc_write_bank1
        lda lc_write_bank1
        lda #$55
        sta $d000
        lda lc_write_bank2
        lda lc_write_bank2
        lda #$aa
        sta $d000
        lda #$3c
        sta $e000
        lda #0
        sta lc_present
        lda $d000
        cmp #$aa
        bne lc_restore
        lda $e000
        cmp #$3c
        bne lc_restore
        lda lc_ram_bank1
        lda $d000
        cmp #$55
        bne lc_restore
        lda $e000
        cmp #$3c
        bne lc_restore
        inc lc_present
lc_restore:
        lda lc_write_bank1
        lda lc_write_bank1
        lda lc_saved_bank1
        sta $d000
        lda lc_write_bank2
        lda lc_write_bank2
        lda lc_saved_bank2
        sta $d000
        lda lc_saved_common
        sta $e000
        bit lc_rom_readonly
        plp
        lda lc_present
        cmp #1
        rts

; X=0: bank2 D000-DFFF, X=8: bank1 D000-DFFF; E000-FFFF common.
; $1E/$1F points at eight valid LC bytes; caller validates bank/address bounds.
; Copies to main RAM before the ordinary renderer can call firmware.
lc_fetch_glyph:
        php
        sei
        lda lc_ram_bank2,x
        ldy #7
lc_fetch_byte:
        lda (lc_pointer),y
        sta lc_glyph_scratch,y
        dey
        bpl lc_fetch_byte
        bit lc_rom_readonly
        plp
        rts

lc_saved_bank1: .byte 0
lc_saved_bank2: .byte 0
lc_saved_common: .byte 0
lc_present: .byte 0
lc_glyph_scratch: .res 8,0
