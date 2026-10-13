; Side A track0/sector0. Slot ROM loads at $0800 and enters $0801.
; A copy later resides at $B600; trailing DOS helpers execute there.
; Preserves native boot/I/O approach. X/zero-page/DOS workspace are clobbered.
        .setcpu "6502"
        .segment "BOOT"
boot_sector:
        .byte 1 ; slot-ROM page count
boot_entry:
        lda $27
        cmp #$09 ; ROM increments destination after reading $0800
        bne select_boot_sector
        lda $2b ; slot nibble, $60 in the accepted profile
        lsr a
        lsr a
        lsr a
        lsr a
        ora #$c0
        sta $3f
        lda #$5c
        sta $3e ; $C65C ROM sector-read entry for slot6
        clc
        lda destination_page
        adc remaining_sector
        sta destination_page
select_boot_sector:
        ldx remaining_sector
        bmi boot_stage1_done
        lda physical_sector_order,x
        sta $3d
        dec remaining_sector
        lda destination_page
        sta $27
        dec destination_page
        ldx $2b
        jmp ($3e)
boot_stage1_done:
        inc destination_page
        inc destination_page ; pointer becomes $B700
        jsr $fe89 ; SETKBD
        jsr $fe93 ; SETVID
        jsr $fb2f ; INIT text window
        ldx $2b
        jmp (stage2_pointer)
physical_sector_order:
        .byte $00,$0d,$0b,$09,$07,$05,$03,$01,$0e,$0c,$0a,$08,$06,$04,$02,$0f
        .byte 0 ; pending-read flag at resident $B65D
; These helpers are also loaded at $B65E–$B6B1. Names describe their visible
; operations; full DOS callers and file-manager conventions remain under analysis.
dos_load_and_clear_buffer:
        jsr $a764
        bcs dos_resume_input
        lda #0
        tay
        sta $b65d
        sta ($40),y
dos_resume_input:
        lda $b5c5
        jmp $a6d2
dos_advance_file_position:
        lda $b65d
        beq dos_clear_pending_read
        inc $b5bd
        bne dos_clear_pending_read
        inc $b5be
dos_clear_pending_read:
        lda #0
        sta $b65d
        jmp $a546
dos_process_saved_character:
        sta $b5bc
        jsr $a6a8
        jsr $a2ea
        jmp $a27d
dos_copy_file_position:
        ldy #$13
test_file_header_fields:
        lda ($42),y
        bne dos_mark_pending_read
        iny
        cpy #$17
        bne test_file_header_fields
        ldy #$19
copy_file_header_fields:
        lda ($42),y
        sta $b5a4,y
        iny
        cpy #$1d
        bne copy_file_header_fields
resume_dos_file_manager:
        jmp $a6bc
dos_mark_pending_read:
        ldx #$ff
        stx $b65d
        bne resume_dos_file_manager
        .res $d0-(*-boot_sector),0
; Diagnostic routine retained as readable code; no executed caller established.
resident_diagnostic:
        jsr $fc58
        lda #$c2
        jsr $fded
        lda #1
        jsr $fdda
        lda #$ad
        jsr $fded
        lda #0
        jsr $fdda
        rts
        .res $fd-(*-boot_sector),0
stage2_pointer: .byte 0
destination_page: .byte $b6 ; also high byte of stage2_pointer
remaining_sector: .byte 9
.assert *-boot_sector=$100,error,"boot sector must be 256 bytes"
