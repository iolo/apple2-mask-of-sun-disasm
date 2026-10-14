; Transient startup code at $5000, discarded by INITIAL's HGR page-2 clear.
; Do not place it in world RAM: INITIAL leaves some GE/room flags untouched.
; Loaded by DOS EXEC START after the interpreter/PARMS, before CALL engine_entry.
; Boot bindings and expected asset headers are generated from this build's bytes.
.setcpu "6502"
.segment "CODE"
.include "boot-bindings.inc"
.export bootstrap_entry, boot_no_lc_wait, boot_wait_media
bootstrap_entry:
        sei
        cld
        ldx #$ff
        txs
        jsr $fe93               ; restore ROM video output while loading assets
        lda #<$9400
        sta ko_destination
        lda #>$9400
        sta ko_destination+1
        lda #<runtime_bytes
        sta ko_remaining
        lda #>runtime_bytes
        sta ko_remaining+1
        lda #0
        sta ko_copy_lc
        lda #<runtime_header
        sta $e0
        lda #>runtime_header
        sta $e1
        lda #<runtime_filename
        ldx #>runtime_filename
        jsr boot_load_asset
        bcs :+
        jmp boot_asset_error
:       jsr runtime_lc_detect
        bcs :+
        jmp boot_no_lc
:       lda #0
        sta runtime_resident_size
        sta runtime_resident_size+1
        sta runtime_font_count
        sta runtime_font_count+1
        lda #<$e000
        sta ko_destination
        lda #>$e000
        sta ko_destination+1
        lda #<font_bytes
        sta ko_remaining
        lda #>font_bytes
        sta ko_remaining+1
        lda #1
        sta ko_copy_lc
        lda #<font_header
        sta $e0
        lda #>font_header
        sta $e1
        lda #<font_filename
        ldx #>font_filename
        jsr boot_load_asset
        bcs :+
        jmp boot_asset_error
:       lda #<$d000
        sta ko_destination
        lda #>$d000
        sta ko_destination+1
        lda #<resident_bytes
        sta ko_remaining
        lda #>resident_bytes
        sta ko_remaining+1
        lda #9                  ; bank1, distinct from room pool in bank2
        sta ko_copy_lc
        lda #<resident_header
        sta $e0
        lda #>resident_header
        sta $e1
        lda #<resident_filename
        ldx #>resident_filename
        jsr boot_load_asset
        bcs :+
        jmp boot_asset_error
:       lda #<resident_bytes
        sta runtime_resident_size
        lda #>resident_bytes
        sta runtime_resident_size+1
        lda #<font_glyphs
        sta runtime_font_count
        lda #>font_glyphs
        sta runtime_font_count+1
        ; INITIAL leaves GE(12) undefined. The Korean loader checks it before
        ; accepting ROOM 1.0's A-only package, so cold RAM must not select B.
        ; Restore later replaces this byte with the saved world's disk side.
        lda #0
        sta $601c               ; GE(12): initial game side A
        jmp $0800               ; normal engine initialization; resets stack

boot_load_asset:
        sta $ea
        stx $eb
        jsr ko_open_file
        bcc boot_asset_failed
        ldy #0
boot_check_header:
        sty boot_header_index
        jsr ko_stream_byte
        bcc boot_asset_failed
        ldy boot_header_index
        cmp ($e0),y
        bne boot_asset_failed
        iny
        cpy #16
        bne boot_check_header
        jmp ko_copy_stream
boot_asset_failed:
        clc
        rts
boot_asset_error:
        bit $c082
        bit $c051
        jsr $fe93
        ldx #0
boot_error_text_loop:
        lda boot_error_text,x
        beq boot_wait_media
        ora #$80
        jsr $fded
        inx
        bne boot_error_text_loop
boot_wait_media:
        lda $c000
        bpl boot_wait_media
        bit $c010
        cmp #$8d
        bne boot_wait_media
        jmp bootstrap_entry
boot_no_lc:
        bit $c051
        ldx #0
boot_no_lc_text:
        lda boot_no_lc_message,x
        beq boot_no_lc_wait
        ora #$80
        jsr $fded
        inx
        bne boot_no_lc_text
boot_no_lc_wait:
        jmp boot_no_lc_wait
boot_header_index: .byte 0
boot_error_text: .byte 13,"INSERT STARTUP DISK AND PRESS RETURN.",13,0
boot_no_lc_message: .byte 13,"16K LANGUAGE CARD REQUIRED.",13,"RESET TO RESTART.",13,0
runtime_filename: .byte $cb,$cf,$ae,$d2,$d5,$ce,$d4,$c9,$cd,$c5
font_filename: .byte $cb,$cf,$ae,$c6,$cf,$ce,$d4,$a0,$a0,$a0
resident_filename: .byte $cb,$cf,$ae,$d4,$c5,$d8,$d4,$a0,$a0,$a0
.include "boot-headers.inc"
.include "loader.s"
