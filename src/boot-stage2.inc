; Track0/sector1, loaded/run at $B700. Side A's first stage enters here.
; Loads 27 remaining DOS pages, descending T2/S4..T0/S10 and $B500..$9B00.
; Native data also retains alternate DOS reload/write entry and IOB/DCT.
; X=slot nibble. Clobbers A/X/Y, flags, stack and DOS/ROM workspace.
        .setcpu "6502"
        .segment "BOOT2"
boot_stage2:
        stx boot_iob_slot
        stx last_slot
        lda #1
        sta last_drive
        sta boot_iob_drive
        lda dos_page_count
        sta pages_remaining
        lda #2
        sta boot_iob_track
        lda #4
        sta boot_iob_sector
        ldy boot_base_page
        dey
        sty boot_iob_buffer_high
        lda #1
        sta boot_iob_command
        txa
        lsr a
        lsr a
        lsr a
        lsr a
        tax
        lda #0
        sta $04f8,x ; ROM per-slot drive/track state
        sta $0478,x
        jsr transfer_dos_pages
        ldx #$ff
        txs
        stx boot_iob_volume
        jsr $fe93
        jsr $fe89
.ifdef SIDE_A
        jmp initialize_dos
.else
        jmp $9d84
.endif
; Alternate reload/write path retained; not entered in the fresh side-A trace.
reload_dos_pages:
        lda boot_base_page
        sec
        sbc boot_iob_buffer_high
        sta pages_remaining
        lda boot_base_page
        sta boot_iob_buffer_high
        dec boot_iob_buffer_high
        lda #2
        sta boot_iob_track
        lda #4
        sta boot_iob_sector
        lda #2
        sta boot_iob_command
        jsr transfer_dos_pages
        lda boot_base_page
        sta $b6fe
        clc
        adc #9
        sta boot_iob_buffer_high
        lda #10
        sta pages_remaining
        sec
        sbc #1
        sta $b6ff
        sta boot_iob_sector
        jsr transfer_dos_pages
        rts
.ifdef SIDE_A
initialize_dos:
        jsr $ba6d ; DOS I/O initialization
        jmp $9d84 ; DOS cold start
.else
        .res 6,0 ; side-B copy omits this trampoline
.endif
transfer_dos_pages:
        lda iob_pointer_high
        ldy iob_pointer_low
        jsr call_rwts_interrupt_masked
        ldy boot_iob_sector
        dey
        bpl next_sector_selected
        ldy #15
        nop
        nop
        dec boot_iob_track
next_sector_selected:
        sty boot_iob_sector
        dec boot_iob_buffer_high
        dec pages_remaining
        bne transfer_dos_pages
        rts
; A/Y=IOB high/low. RWTS at $BD00; returns carry while preserving interrupt state.
call_rwts_interrupt_masked:
        php
        sei
        jsr $bd00
        bcs rwts_failed
        plp
        clc
        rts
rwts_failed:
        plp
        sec
        rts
prepare_dos_file_iob:
        lda $b5bc
        sta boot_iob_buffer_high
        lda #0
        sta boot_iob_buffer_low
        lda $b5f9
        eor #$ff
        sta boot_iob_volume
        rts
clear_dos_page:
        lda #0
        tay
clear_dos_page_byte:
        sta ($42),y
        iny
        bne clear_dos_page_byte
        rts
        .byte 0
dos_page_count: .byte $1b
pages_remaining: .byte $02
        .byte $0a,$1b
iob_pointer_low: .byte $e8
iob_pointer_high: .byte $b7
        .byte 0
boot_base_page: .byte $b6
boot_iob:
        .byte 1
boot_iob_slot: .byte $60
boot_iob_drive: .byte 2
boot_iob_volume: .byte $fe
boot_iob_track: .byte 0
boot_iob_sector: .byte 1
        .word boot_dct
boot_iob_buffer_low: .byte 0
boot_iob_buffer_high: .byte $b7
        .byte 0,0
boot_iob_command: .byte 2
.ifdef SIDE_A
        .byte 3
.else
        .byte 1
.endif
        .byte $fe
last_slot: .byte $60
last_drive: .byte 2
        .byte 0,0
boot_dct: .byte 0,1,$ef,$d8
        .byte 0
.assert boot_iob=$b7e8,error,"native IOB address"
.assert *-boot_stage2=$100,error,"stage2 must be 256 bytes"
