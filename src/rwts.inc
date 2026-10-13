; Native DOS high-memory RWTS and tail helpers, $B800-$BFFF.
; Reconstructed from supplied track0 sectors2-9; source authority for both disks.
; Initial nibble buffers are data, not game code. See docs/rwts.md.
        .setcpu "6502"

device_characteristics:= $003C
sector_buffer   := $003E
iob_pointer     := $0048
dos_close_all   := $A316
dos_close       := $A75B
dos_file_type   := $AA63
dos_file_address:= $AA70
dos_file_address_high:= $AA71
dos_run_intercepted:= $AAB7
dos_release_file_buffer:= $AE7E
dos_file_error  := $B385
dos_saved_stack := $B39B
dos_reload_entry:= $B744
rom_set_video   := $FE93
; GCR bytes index the inverse table from $BA00; legal codes start at $96.
gcr_decode_base := $BA00

.segment        "RWTS": absolute

; $B800: split ($3E/$3F) sector into 256 six-bit and 86 two-bit groups.
; Clobbers A/X/Y and both nibble buffers. Low two bits are rotated in place.
prenibble_sector:
        ldx     #$00
        ldy     #$02
prenibble_pair:
        dey
        lda     (sector_buffer),y
        lsr     a
        rol     auxiliary_nibbles,x
        lsr     a
        rol     auxiliary_nibbles,x
        sta     primary_nibbles,y
        inx
        cpx     #$56
        bcc     prenibble_pair
        ldx     #$00
        tya
        bne     prenibble_pair
        ldx     #$55
mask_auxiliary_nibbles:
        lda     auxiliary_nibbles,x
        and     #$3F
        sta     auxiliary_nibbles,x
        dex
        bpl     mask_auxiliary_nibbles
        rts

; $B82A: X=slot*16, buffers already prenibbled; C=1 means write protected.
; $C08D/$C08F switch Q6/Q7, $C08C samples the latch. PHA/PLA, NOP and
; tiny subroutines provide required bit-cell timing: preserve their cycles.
write_sector_data:
        sec
        stx     $27
        stx     $0678
        lda     $C08D,x
        lda     $C08E,x
        bmi     finish_sector_write
        lda     auxiliary_nibbles
        sta     $26
        lda     #$FF
        sta     $C08F,x
        ora     $C08C,x
        pha
        pla
        nop
        ldy     #$04
write_sync_gap:
        pha
        pla
        jsr     write_byte_delay
        dey
        bne     write_sync_gap
        lda     #$D5
        jsr     write_byte_clear_carry
        lda     #$AA
        jsr     write_byte_clear_carry
        lda     #$AD
        jsr     write_byte_clear_carry
        tya
        ldy     #$56
        bne     write_auxiliary_delta
write_auxiliary_next:
        lda     auxiliary_nibbles,y
write_auxiliary_delta:
        eor     primary_nibbles+255,y
        tax
        lda     gcr_write_codes,x
        ldx     $27
        sta     $C08D,x
        lda     $C08C,x
        dey
        bne     write_auxiliary_next
        lda     $26
        nop
write_primary_delta:
        eor     primary_nibbles,y
        tax
        lda     gcr_write_codes,x
        ldx     $0678
        sta     $C08D,x
        lda     $C08C,x
        lda     primary_nibbles,y
        iny
        bne     write_primary_delta
        tax
        lda     gcr_write_codes,x
        ldx     $27
        jsr     write_byte_latch
        lda     #$DE
        jsr     write_byte_clear_carry
        lda     #$AA
        jsr     write_byte_clear_carry
        lda     #$EB
        jsr     write_byte_clear_carry
        lda     #$FF
        jsr     write_byte_clear_carry
        lda     $C08E,x
finish_sector_write:
        lda     $C08C,x
        rts

write_byte_clear_carry:
        clc
write_byte_delay:
        pha
        pla
write_byte_latch:
        sta     $C08D,x
        ora     $C08C,x
        rts

; $B8C2: inverse 6-and-2 conversion into ($3E/$3F), ending at Y=$26.
; $26=0 means a complete 256-byte sector. Auxiliary bits are consumed.
postnibble_sector:
        ldy     #$00
postnibble_auxiliary_cycle:
        ldx     #$56
postnibble_byte:
        dex
        bmi     postnibble_auxiliary_cycle
        lda     primary_nibbles,y
        lsr     auxiliary_nibbles,x
        rol     a
        lsr     auxiliary_nibbles,x
        rol     a
        sta     (sector_buffer),y
        iny
        cpy     $26
        bne     postnibble_byte
        rts

; $B8DC: X=slot*16; locate D5 AA AD, decode XOR-linked GCR into buffers.
; Verify checksum and DE AA trailer; C clear on success, set on timeout/error.
read_sector_data:
        ldy     #$20
read_data_retry:
        dey
        beq     read_data_failed
read_data_wait_byte:
        lda     $C08C,x
        bpl     read_data_wait_byte
read_data_test_d5:
        eor     #$D5
        bne     read_data_retry
        nop
read_data_wait_aa:
        lda     $C08C,x
        bpl     read_data_wait_aa
        cmp     #$AA
        bne     read_data_test_d5
        ldy     #$56
read_data_wait_ad:
        lda     $C08C,x
        bpl     read_data_wait_ad
        cmp     #$AD
        bne     read_data_test_d5
        lda     #$00
read_auxiliary_next:
        dey
        sty     $26
read_auxiliary_nibble:
        ldy     $C08C,x
        bpl     read_auxiliary_nibble
        eor     gcr_decode_base,y
        ldy     $26
        sta     auxiliary_nibbles,y
        bne     read_auxiliary_next
read_primary_next:
        sty     $26
read_primary_nibble:
        ldy     $C08C,x
        bpl     read_primary_nibble
        eor     gcr_decode_base,y
        ldy     $26
        sta     primary_nibbles,y
        iny
        bne     read_primary_next
read_data_checksum:
        ldy     $C08C,x
        bpl     read_data_checksum
        cmp     gcr_decode_base,y
        bne     read_data_failed
read_data_epilogue_de:
        lda     $C08C,x
        bpl     read_data_epilogue_de
        cmp     #$DE
        bne     read_data_failed
        nop
read_data_epilogue_aa:
        lda     $C08C,x
        bpl     read_data_epilogue_aa
        cmp     #$AA
        beq     address_success
read_data_failed:
        sec
        rts

; $B944: scan D5 AA 96 and decode four 4-and-4 bytes.
; $2C=checksum, $2D=physical sector, $2E=track, $2F=volume; C reports failure.
read_address_header:
        ldy     #$FC
        sty     $26
address_retry:
        iny
        bne     address_wait_d5
        inc     $26
        beq     read_data_failed
address_wait_d5:
        lda     $C08C,x
        bpl     address_wait_d5
address_test_d5:
        cmp     #$D5
        bne     address_retry
        nop
address_wait_aa:
        lda     $C08C,x
        bpl     address_wait_aa
        cmp     #$AA
        bne     address_test_d5
        ldy     #$03
address_wait_96:
        lda     $C08C,x
        bpl     address_wait_96
        cmp     #$96
        bne     address_test_d5
        lda     #$00
address_save_checksum:
        sta     $27
address_first_4and4:
        lda     $C08C,x
        bpl     address_first_4and4
        rol     a
        sta     $26
address_second_4and4:
        lda     $C08C,x
        bpl     address_second_4and4
        and     $26
        sta     $2C,y
        eor     $27
        dey
        bpl     address_save_checksum
        tay
        bne     read_data_failed
address_checksum:
        lda     $C08C,x
        bpl     address_checksum
        cmp     #$DE
        bne     read_data_failed
        nop
address_epilogue:
        lda     $C08C,x
        bpl     address_epilogue
        cmp     #$AA
        bne     read_data_failed
address_success:
        clc
        rts

; $B9A0: A=target half-track, X=slot*16, $0478=current position.
; Accelerate/decelerate using delay tables and phase switches $C080..$C087.
seek_halftrack:
        stx     $2B
        sta     $2A
        cmp     $0478
        beq     seek_return
        lda     #$00
        sta     $26
seek_next_step:
        lda     $0478
        sta     $27
        sec
        sbc     $2A
        beq     seek_finished
        bcs     seek_step_inward
        eor     #$FF
        inc     $0478
        bcc     seek_limit_acceleration
seek_step_inward:
        adc     #$FE
        dec     $0478
seek_limit_acceleration:
        cmp     $26
        bcc     seek_limit_delay_index
        lda     $26
seek_limit_delay_index:
        cmp     #$0C
        bcs     seek_magnet_on
        tay
seek_magnet_on:
        sec
        jsr     select_stepper_phase
        lda     magnet_on_delays,y
        jsr     motor_delay
        lda     $27
        clc
        jsr     select_stepper_switch
        lda     magnet_off_delays,y
        jsr     motor_delay
        inc     $26
        bne     seek_next_step
seek_finished:
        jsr     motor_delay
        clc
select_stepper_phase:
        lda     $0478
select_stepper_switch:
        and     #$03
        rol     a
        ora     $2B
        tax
        lda     $C080,x
        ldx     $2B
seek_return:
        rts

        .byte   $AA,$A0,$A0
; $BA00: A=count of short delays; increments $46/$47 elapsed-delay counter.
; Clobbers A/X; the slot offset is saved/restored by callers.
motor_delay:
        ldx     #$11
motor_delay_inner:
        dex
        bne     motor_delay_inner
        inc     $46
        bne     motor_delay_tick
        inc     $47
motor_delay_tick:
        sec
        sbc     #$01
        bne     motor_delay
        rts

; Seek acceleration tables (12 entries each), followed by the 64 legal GCR codes.
magnet_on_delays:
        .byte   $01,$30,$28,$24,$20,$1E,$1D,$1C
        .byte   $1C,$1C,$1C,$1C
magnet_off_delays:
        .byte   $70,$2C,$26,$22,$1F,$1E,$1D,$1C
        .byte   $1C,$1C,$1C,$1C
gcr_write_codes:
        .byte   $96,$97,$9A,$9B,$9D,$9E,$9F,$A6
        .byte   $A7,$AB,$AC,$AD,$AE,$AF,$B2,$B3
        .byte   $B4,$B5,$B6,$B7,$B9,$BA,$BB,$BC
        .byte   $BD,$BE,$BF,$CB,$CD,$CE,$CF,$D3
        .byte   $D6,$D7,$D9,$DA,$DB,$DC,$DD,$DE
        .byte   $DF,$E5,$E6,$E7,$E9,$EA,$EB,$EC
        .byte   $ED,$EE,$EF,$F2,$F3,$F4,$F5,$F6
        .byte   $F7,$F9,$FA,$FB,$FC,$FD,$FE,$FF
.ifdef SIDE_B
; Side B cannot boot DOS. Its $BA69..$BA93 copy contains 43 residual bytes,
; not the live side-A stubs. Gameplay keeps side-A RWTS resident across swaps.
unused_side_b_stub_region:
        .byte   $B3,$B3,$A0,$E0,$B3,$C3,$C5,$B3
        .byte   $A0,$E0,$B3,$C3,$C5,$B3,$A0,$E0
        .byte   $B3,$B3,$C5,$AA,$A0,$82,$B3,$B3
        .byte   $C5,$AA,$A0,$82,$C5,$B3,$B3,$AA
        .byte   $88,$82,$C5,$B3,$B3,$AA,$88,$82
        .byte   $C5,$C4,$B3
.else
; Native patched register-return entries, not workspace copying routines.
; $BA69 returns X=$6E,Y=$36; $BA6D X=$8A,Y=$36; $BA72 X=$6F,Y=0.
; Their shared branches reach RTS without writing memory. Preserve native NOP.
native_after_save_stub:
        ldx     #$6E
        bne     native_return_y36
native_initialize_stub:
        ldx     #$8A
        nop
        bne     native_return_y36
native_before_save_stub:
        ldx     #$6F
        ldy     #$00
        beq     native_stub_return
native_return_y36:
        ldy     #$36
native_stub_return:
        rts

        .byte   $12
; Residual DOS decoder initializer fragment. Native stubs above bypass it.
; It changes the inverse lookup and its EOR immediate; no live caller observed.
dormant_decode_initializer:
        eor     gcr_decode_base,x
        sta     gcr_decode_base,x
        sty     decode_initializer_xor_mask
        ldy     #$3F
decode_initializer_next:
        ldx     gcr_write_codes,y
        txa
decode_initializer_xor:
        eor #$FF
decode_initializer_xor_mask := decode_initializer_xor+1
        sta     gcr_decode_base,x
        dey
        bpl     decode_initializer_next
        rts

.endif
        .byte   $B0,$88 ; legacy bytes, not an executed branch
; $BA96..$BAFF: inverse table for codes $96..$FF. Invalid indices retain
; their native byte, while the 64 legal indices map to $00..$3F.
gcr_read_codes:
        .byte   $00,$01,$98,$99,$02,$03,$9C,$04
        .byte   $05,$06,$A0,$A1,$A2,$A3,$A4,$A5
        .byte   $07,$08,$A8,$A9,$AA,$09,$0A,$0B
        .byte   $0C,$0D,$B0,$B1,$0E,$0F,$10,$11
        .byte   $12,$13,$B8,$14,$15,$16,$17,$18
        .byte   $19,$1A,$C0,$C1,$C2,$C3,$C4,$C5
        .byte   $C6,$C7,$C8,$C9,$CA,$1B,$CC,$1C
        .byte   $1D,$1E,$D0,$D1,$D2,$1F,$D4,$D5
        .byte   $20,$21,$D8,$22,$23,$24,$25,$26
        .byte   $27,$28,$E0,$E1,$E2,$E3,$E4,$29
        .byte   $2A,$2B,$E8,$2C,$2D,$2E,$2F,$30
        .byte   $31,$32,$F0,$F1,$33,$34,$35,$36
        .byte   $37,$38,$F8,$39,$3A,$3B,$3C,$3D
        .byte   $3E,$3F
; $BB00..$BBFF scratch: initial captured sector residue, overwritten by reads
; or prenibbling before use. Byte declarations are data, not hidden executable code.
primary_nibbles:
        .byte   $01,$0A,$11,$0A,$08,$20,$20,$0E
        .byte   $18,$06,$02,$31,$02,$09,$08,$27
        .byte   $22,$00,$12,$0A,$0A,$04,$00,$00
        .byte   $03,$2A,$00,$04,$00,$00,$22,$08
        .byte   $10,$28,$12,$02,$00,$02,$08,$11
        .byte   $0A,$08,$02,$28,$11,$01,$39,$22
        .byte   $31,$01,$05,$18,$20,$28,$02,$10
        .byte   $06,$02,$09,$02,$05,$2C,$10,$00
        .byte   $08,$2E,$00,$05,$02,$28,$18,$02
        .byte   $30,$23,$02,$20,$32,$04,$11,$02
        .byte   $14,$02,$08,$09,$12,$20,$0E,$2F
        .byte   $23,$30,$2F,$23,$30,$0C,$17,$2A
        .byte   $3F,$27,$23,$30,$37,$23,$30,$12
        .byte   $1A,$08,$30,$2F,$08,$30,$2F,$27
        .byte   $23,$30,$37,$23,$30,$3A,$22,$34
        .byte   $3C,$2A,$35,$08,$35,$2F,$2A,$2A
        .byte   $08,$35,$2F,$2A,$25,$08,$35,$2F
        .byte   $29,$10,$08,$31,$2F,$29,$11,$08
        .byte   $31,$2F,$29,$0F,$08,$31,$2F,$29
        .byte   $10,$11,$11,$11,$0F,$12,$12,$01
        .byte   $0F,$27,$23,$30,$2F,$23,$30,$1A
        .byte   $02,$2A,$08,$35,$2F,$2A,$37,$08
        .byte   $35,$2F,$2A,$2A,$08,$35,$2F,$2A
        .byte   $3A,$08,$35,$2F,$06,$2F,$23,$30
        .byte   $2F,$23,$30,$18,$12,$12,$01,$0F
        .byte   $27,$23,$30,$37,$23,$30,$1A,$3A
        .byte   $3A,$3A,$02,$2A,$3A,$3A,$12,$1A
        .byte   $27,$23,$30,$37,$23,$30,$18,$22
        .byte   $29,$3A,$24,$28,$25,$22,$25,$3A
        .byte   $24,$28,$25,$22,$25,$24,$24,$32
        .byte   $25,$34,$25,$24,$24,$32,$25,$34
        .byte   $25,$24,$28,$32,$28,$29,$21,$29
; $BC00..$BC55 scratch: overwritten by disk conversion, identical on both sides.
auxiliary_nibbles:
        .byte   $10,$A1,$45,$28,$21,$82,$80,$38
        .byte   $62,$19,$0B,$C5,$0B,$24,$21,$9C
        .byte   $88,$00,$48,$28,$2B,$10,$00,$03
        .byte   $0C,$A9,$01,$10,$01,$00,$88,$22
        .byte   $40,$A0,$48,$09,$01,$08,$21,$44
        .byte   $29,$22,$08,$A0,$45,$06,$E4,$8A
        .byte   $C4,$06,$16,$60,$80,$A0,$09,$40
        .byte   $18,$0A,$24,$0A,$16,$B0,$43,$00
        .byte   $20,$BB,$00,$14,$08,$A0,$60,$0A
        .byte   $C0,$8F,$0A,$83,$CA,$11,$44,$08
        .byte   $51,$0A,$20,$26,$4A,$80
; $BC56: X=slot*16, Y=sync count; $41=volume, $44=track, $3F=sector,
; $3E=$AA bit mask. Emit D5 AA 96, 4-and-4 fields/checksum, DE AA EB.
write_address_header:
        sec
        lda     $C08D,x
        lda     $C08E,x
        bmi     finish_address_write
        lda     #$FF
        sta     $C08F,x
        cmp     $C08C,x
        pha
        pla
write_address_header_sync:
        jsr     address_write_return
        jsr     address_write_return
        sta     $C08D,x
        cmp     $C08C,x
        nop
        dey
        bne     write_address_header_sync
        lda     #$D5
        jsr     write_4and4_delay_second
        lda     #$AA
        jsr     write_4and4_delay_second
        lda     #$96
        jsr     write_4and4_delay_second
        lda     $41
        jsr     write_4and4_byte
        lda     $44
        jsr     write_4and4_byte
        lda     sector_buffer+1
        jsr     write_4and4_byte
        lda     $41
        eor     $44
        eor     sector_buffer+1
        pha
        lsr     a
        ora     sector_buffer
        sta     $C08D,x
        lda     $C08C,x
        pla
        ora     #$AA
        jsr     write_4and4_delay
        lda     #$DE
        jsr     write_4and4_delay_second
        lda     #$AA
        jsr     write_4and4_delay_second
        lda     #$EB
        jsr     write_4and4_delay_second
        clc
finish_address_write:
        lda     $C08E,x
        lda     $C08C,x
address_write_return:
        rts

; $BCC4: emit A as a 4-and-4 pair; NOPs/subroutine calls are disk timing.
write_4and4_byte:
        pha
        lsr     a
        ora     sector_buffer
        sta     $C08D,x
        cmp     $C08C,x
        pla
        nop
        nop
        nop
        ora     #$AA
write_4and4_delay:
        nop
write_4and4_delay_second:
        nop
        pha
        pla
        sta     $C08D,x
        cmp     $C08C,x
        rts

; $BCDF..$BCFF: 33 residual bytes outside routines; no branch/call targets.
; Kept as documented native padding; they are not treated as instructions.
unused_legacy_bytes:
        .byte   $88,$A5,$E8,$91,$A0,$94,$88,$96
        .byte   $E8,$91,$A0,$94,$88,$96,$91,$91
        .byte   $C8,$94,$D0,$96,$91,$91,$C8,$94
        .byte   $D0,$96,$91,$A3,$C8,$A0,$A5,$85
        .byte   $A4
; $BD00 public RWTS: A=IOB high byte, Y=IOB low byte. Clobbers A/X/Y.
; Command at +12: 0 seek/null, 1 read, 2 write, 4 format. C=0 success.
; +13 holds errors ($10 protected, $20 volume, $40 seek, $08 format).
; Uses $26..$2F, $35, $3C..$3F, $46..$49 and slot-indexed text-page scratch.
rwts_entry:
        sty     iob_pointer
        sta     iob_pointer+1
        ldy     #$02
        sty     $06F8
        ldy     #$04
        sty     $04F8
        ldy     #$01
        lda     (iob_pointer),y
        tax
        ldy     #$0F
        cmp     (iob_pointer),y
        beq     rwts_select_read
        txa
        pha
        lda     (iob_pointer),y
        tax
        pla
        pha
        sta     (iob_pointer),y
        lda     $C08E,x
rwts_wait_old_motor:
        ldy     #$08
        lda     $C08C,x
rwts_test_old_motor:
        cmp     $C08C,x
        bne     rwts_wait_old_motor
        dey
        bne     rwts_test_old_motor
        pla
        tax
rwts_select_read:
        lda     $C08E,x
        lda     $C08C,x
        ldy     #$08
rwts_sample_motor:
        lda     $C08C,x
        pha
        pla
        pha
        pla
        stx     $05F8
        cmp     $C08C,x
        bne     rwts_save_motor_flags
        dey
        bne     rwts_sample_motor
rwts_save_motor_flags:
        php
        lda     $C089,x
        ldy     #$06
rwts_get_buffer:
        lda     (iob_pointer),y
        sta     $36,y
        iny
        cpy     #$0A
        bne     rwts_get_buffer
        ldy     #$03
        lda     (device_characteristics),y
        sta     $47
        ldy     #$02
        lda     (iob_pointer),y
        ldy     #$10
        cmp     (iob_pointer),y
        beq     rwts_select_drive
        sta     (iob_pointer),y
        plp
        ldy     #$00
        php
rwts_select_drive:
        ror     a
        bcc     rwts_select_drive_two
        lda     $C08A,x
        bcs     rwts_drive_flag
rwts_select_drive_two:
        lda     $C08B,x
rwts_drive_flag:
        ror     $35
        plp
        php
        bne     rwts_seek_request
        ldy     #$07
rwts_spinup_delay:
        jsr     motor_delay
        dey
        bne     rwts_spinup_delay
        ldx     $05F8
rwts_seek_request:
        ldy     #$04
        lda     (iob_pointer),y
        jsr     rwts_seek_by_device
        plp
        bne     rwts_dispatch_command
        ldy     $47
        bpl     rwts_dispatch_command
rwts_spinup_wait:
        ldy     #$12
rwts_spinup_wait_inner:
        dey
        bne     rwts_spinup_wait_inner
        inc     $46
        bne     rwts_spinup_wait
        inc     $47
        bne     rwts_spinup_wait
rwts_dispatch_command:
        ldy     #$0C
        lda     (iob_pointer),y
        beq     rwts_null_command
        cmp     #$04
rwts_test_format:
        beq     rwts_format_command
        ror     a
        php
        bcs     rwts_start_retries
        jsr     prenibble_sector
rwts_start_retries:
        ldy     #$30
        sty     $0578
rwts_retry_address:
        ldx     $05F8
        jsr     read_address_header
        bcc     rwts_check_track
rwts_count_retry:
        dec     $0578
        bpl     rwts_retry_address
rwts_recalibrate:
        lda     $0478
        pha
        lda     #$60
        jsr     rwts_save_track
        dec     $06F8
        beq     rwts_seek_failed
        lda     #$04
        sta     $04F8
        lda     #$00
        jsr     rwts_seek_by_device
        pla
rwts_seek_after_recalibration:
        jsr     rwts_seek_by_device
        jmp     rwts_start_retries

rwts_check_track:
        ldy     $2E
        cpy     $0478
        beq     rwts_check_volume
        lda     $0478
        pha
        tya
        jsr     rwts_save_track
        pla
        dec     $04F8
        bne     rwts_seek_after_recalibration
        beq     rwts_recalibrate
rwts_seek_failed:
        pla
        lda     #$40
rwts_error_from_stack:
        plp
        jmp     rwts_finish

rwts_null_command:
        beq     rwts_success
rwts_format_command:
        jmp     format_disk

rwts_check_volume:
        ldy     #$03
        lda     (iob_pointer),y
        pha
        lda     $2F
        ldy     #$0E
        sta     (iob_pointer),y
        pla
        beq     rwts_check_sector
        cmp     $2F
        beq     rwts_check_sector
        lda     #$20
        bne     rwts_error_from_stack
rwts_check_sector:
        ldy     #$05
        lda     (iob_pointer),y
        tay
        lda     logical_to_physical_sectors,y
        cmp     $2D
        bne     rwts_count_retry
        plp
        bcc     rwts_write_command
        jsr     read_sector_data
        php
        bcs     rwts_count_retry
        plp
        ldx     #$00
        stx     $26
        jsr     postnibble_sector
        ldx     $05F8
; Success falls through BIT $38: opcode $24 consumes the alternate-entry
; SEC opcode as its operand, preserving carry clear. Error callers enter SEC.
rwts_success:
        clc
        .byte   $24 ; BIT zp skips SEC at alternate entry
rwts_finish:
        sec
        ldy     #$0D
        sta     (iob_pointer),y
        lda     $C088,x
        rts

rwts_write_command:
        jsr     write_sector_data
        bcc     rwts_success
        lda     #$10
        bcs     rwts_finish
; Device characteristic +1 bit0 selects full/half-track seeking convention.
rwts_seek_by_device:
        pha
        ldy     #$01
        lda     (device_characteristics),y
        ror     a
        pla
        bcc     rwts_seek_wholetrack
        asl     a
        jsr     rwts_seek_wholetrack
        lsr     $0478
        rts

rwts_seek_wholetrack:
        sta     $2A
        jsr     slot_nibble_to_index
        lda     $0478,y
        bit     $35
        bmi     rwts_get_track
        lda     $04F8,y
rwts_get_track:
        sta     $0478
        lda     $2A
        bit     $35
        bmi     rwts_save_drive_one_track
        sta     $04F8,y
        bpl     rwts_call_seek
rwts_save_drive_one_track:
        sta     $0478,y
rwts_call_seek:
        jmp     seek_halftrack

slot_nibble_to_index:
        txa
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        tay
        rts

rwts_save_track:
        pha
        ldy     #$02
        lda     (iob_pointer),y
        ror     a
        ror     $35
        jsr     slot_nibble_to_index
        pla
        asl     a
        bit     $35
        bmi     rwts_save_drive_one_position
        sta     $04F8,y
        bpl     rwts_track_saved
rwts_save_drive_one_position:
        sta     $0478,y
rwts_track_saved:
        rts

; $BEAF: format tracks 0..34 and verify headers/data; C/status report errors.
; Native game does not invoke format; source retained for the DOS component.
format_disk:
        ldy     #$03
        lda     (iob_pointer),y
        sta     $41
        lda     #$AA
        sta     sector_buffer
        ldy     #$56
        lda     #$00
format_start_track:
        sta     $44
format_clear_auxiliary:
        sta     primary_nibbles+255,y
        dey
        bne     format_clear_auxiliary
format_clear_primary:
        sta     primary_nibbles,y
        dey
        bne     format_clear_primary
        lda     #$50
        jsr     rwts_save_track
        lda     #$28
        sta     $45
format_next_track:
        lda     $44
        jsr     rwts_seek_by_device
        jsr     format_track
        lda     #$08
        bcs     format_failed
        lda     #$30
        sta     $0578
format_verify_retry:
        sec
        dec     $0578
        beq     format_failed
        jsr     read_address_header
        bcs     format_verify_retry
        lda     $2D
        bne     format_verify_retry
        jsr     read_sector_data
        bcs     format_verify_retry
        inc     $44
        lda     $44
        cmp     #$23
        bcc     format_next_track
        clc
        bcc     format_motor_off
format_failed:
        ldy     #$0D
        sta     (iob_pointer),y
        sec
format_motor_off:
        lda     $C088,x
        rts

; $BF0D: write 16 physical sectors and adapt sync gap until all verify.
format_track:
        lda     #$00
        sta     sector_buffer+1
        ldy     #$80
        bne     format_track_sector
format_track_next_sector:
        ldy     $45
format_track_sector:
        jsr     write_address_header
        bcs     format_return
        jsr     write_sector_data
        bcs     format_return
        inc     sector_buffer+1
        lda     sector_buffer+1
        cmp     #$10
        bcc     format_track_next_sector
        ldy     #$0F
        sty     sector_buffer+1
        lda     #$30
        sta     $0578
format_clear_sector_flags:
        sta     format_sector_flags,y
        dey
        bpl     format_clear_sector_flags
        ldy     $45
format_gap_delay:
        jsr     format_return
        jsr     format_return
        jsr     format_return
        pha
        pla
        nop
        dey
        bne     format_gap_delay
        jsr     read_address_header
        bcs     format_last_sector_retry
        lda     $2D
        beq     format_read_sector
        lda     #$10
        cmp     $45
        lda     $45
        sbc     #$01
        sta     $45
        cmp     #$05
        bcs     format_last_sector_retry
        sec
        rts

format_read_retry:
        jsr     read_address_header
        bcs     format_count_retry
format_read_sector:
        jsr     read_sector_data
        bcc     format_mark_sector
format_count_retry:
        dec     $0578
        bne     format_read_retry
format_last_sector_retry:
        jsr     read_address_header
        bcs     format_last_sector_failed
        lda     $2D
        cmp     #$0F
        bne     format_last_sector_failed
        jsr     read_sector_data
        bcc     format_track
format_last_sector_failed:
        dec     $0578
        bne     format_last_sector_retry
        sec
format_return:
        rts

format_mark_sector:
        ldy     $2D
        lda     format_sector_flags,y
        bmi     format_count_retry
        lda     #$FF
        sta     format_sector_flags,y
        dec     sector_buffer+1
        bpl     format_read_retry
        lda     $44
        bne     format_track_success
        lda     $45
        cmp     #$10
        bcc     format_return
        dec     $45
        dec     $45
format_track_success:
        clc
        rts

; $BFA8: one verification flag per physical sector.
format_sector_flags:
        .byte   $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte   $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
; $BFB8: DOS .do logical-to-physical sector interleave (16 entries).
logical_to_physical_sectors:
        .byte   $00,$0D,$0B,$09,$07,$05,$03,$01
        .byte   $0E,$0C,$0A,$08,$06,$04,$02,$0F
; $BFC8: optional language-card reload helper, unused on baseline 48K II+.
dos_language_card_reload:
        jsr     rom_set_video
        lda     $C081
        lda     $C081
        lda     #$00
        sta     $E000
        jmp     dos_reload_entry

        .byte   $00,$00,$00
; $BFDC: clear file-type/address selection to A; DOS tail entry.
dos_reset_file_selection:
        sta     dos_file_type
        sta     dos_file_address
        sta     dos_file_address_high
        rts

; $BFE6: close file then save Y as DOS RUN-interception state.
dos_close_from_exec:
        jsr     dos_close
        sty     dos_run_intercepted
        rts

; $BFED: release buffer, restore DOS stack, close all and raise error 9.
dos_close_with_stack_recovery:
        jsr     dos_release_file_buffer
        ldx     dos_saved_stack
        txs
        jsr     dos_close_all
        tsx
        stx     dos_saved_stack
        lda     #$09
        jmp     dos_file_error


.assert prenibble_sector = $B800, error, "prenibble entry moved"
.assert read_sector_data = $B8DC, error, "data reader moved"
.assert read_address_header = $B944, error, "address reader moved"
.assert rwts_entry = $BD00, error, "public RWTS entry moved"
.assert write_address_header = $BC56, error, "address writer moved"
.assert * = $C000, error, "RWTS must occupy eight native pages"

