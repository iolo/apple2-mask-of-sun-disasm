; Candidate interpreter bridge. Native non-resource files retain their loader.
; Caller A/X filename, EC/ED destination; resource errors retry before returning.
.setcpu "6502"
.segment "CODE"
.export ko_load_dispatch, ko_finish_startup, ko_wait_game_media
ko_load_dispatch:
        sta $ea
        stx $eb
        lda $ec
        bne ko_native_load
        lda $ed
        cmp #$68
        beq ko_resource_load
        cmp #$70
        beq ko_resource_load
ko_native_load:
        lda $ea
        ldx $eb
        jmp ko_native_file_loader
ko_resource_load:
        sta ko_retry_page
        ldy #9
ko_save_retry_name:
        lda ($ea),y
        sta ko_retry_name,y
        dey
        bpl ko_save_retry_name
ko_resource_retry:
        lda #0
        sta $ec
        lda ko_retry_page
        sta $ed
        lda #<ko_retry_name
        ldx #>ko_retry_name
        jsr ko_load_package
        bcs ko_resource_ready
        ; Synthetic UI integration uses the same wrapper as reviewed references.
        .ifdef KOREAN_NATIVE_UI
        jsr ko_clear_message_rows
        .else
        lda #0
        sta $24
        lda #12
        sta $25
        .endif
        lda #<ko_media_text
        ldx #>ko_media_text
        .ifdef KOREAN_NATIVE_UI
        jsr ko_print_script_string
        .else
        jsr ko_native_print_script_string
        .endif
ko_wait_game_media:
        lda $c000
        bpl ko_wait_game_media
        bit $c010
        cmp #$8d
        bne ko_wait_game_media
        jmp ko_resource_retry
ko_resource_ready:
        ; Preserve the native loader's next-destination-page result.
        lda ko_package_header+4
        cmp #1
        lda ko_package_header+5
        adc ko_retry_page
        sta $ed
        rts
ko_finish_startup:
        jmp $b300
.ifdef KOREAN_NATIVE_UI
; Clear all message cells before variable-width media instructions. The original
; English prompts used trailing spaces. Keep picture rows 0-11 and the other HGR
; page untouched. Preserve the caller's A/X string pointer and Y.
ko_clear_message_rows:
        pha
        txa
        pha
        lda #0
        sta $24
        lda #12
        sta $25
        ldx #160
ko_clear_message_cell:
        lda #$a0
        jsr $fded
        dex
        bne ko_clear_message_cell
        lda #0
        sta $24
        lda #12
        sta $25
        pla
        tax
        pla
        rts
.endif
ko_retry_page: .byte 0
ko_retry_name: .res 10,$a0
ko_media_text:
        .byte $c9,$ce,$d3,$c5,$d2,$d4,$a0,$c7,$c1,$cd,$c5,$a0,$c4,$c9,$d3,$cb,$a0
        .byte $c1,$af,$c2,$a0,$c1,$ce,$c4,$a0,$d0,$d2,$c5,$d3,$d3,$a0,$d2,$c5,$d4,$d5,$d2,$ce,$ae,$8d
