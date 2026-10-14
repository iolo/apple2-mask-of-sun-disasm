; Streaming KOR2 resource loader, MOS6502, main-RAM code.
; A/X -> ten high-bit filename bytes. EC/ED = $6800 (room) or $7000 (library).
; Uses native slot6/drive1 RWTS and IOB, B700 TS scratch, 0700 sector buffer.
; C=1 complete script+pool; C=0 failure, ko_load_error describes failure.
; 1 I/O, 2 missing name, 3 malformed metadata/magic, 4 bounds, 5 short stream.
; No error prompts/unwinding here: caller must not run a partially loaded script.
; Always invalidates room pool first; publishes its size only on success.
; Clobbers A/X/Y, native loader/RWTS ZP plus renderer pointer 1E/1F.
; Main RAM/ROM on entry, LC present, D=0, no reentrant use. Preserves IRQ mask
; around each LC write and restores ROM before any RWTS call or return.
.setcpu "6502"
.segment "CODE"
.export ko_load_package, ko_load_pool, ko_load_error, ko_media_id

ko_load_pool:
        sta $ea
        stx $eb
        lda #1
        bne ko_load_mode
ko_load_package:
        sta $ea
        stx $eb
        lda #0
ko_load_mode:
        sta ko_pool_only
        lda #0
        sta ko_room_size
        sta ko_room_size+1
        sta ko_load_error
        lda $ec
        bne ko_early_bounds
        sta ko_destination
        lda $ed
        sta ko_destination+1
        cmp #$68
        beq ko_room_destination
        cmp #$70
        bne ko_early_bounds
        lda #$24                ; library ends before extension code at 9400
        bne ko_store_limit
ko_early_bounds:
        jmp ko_load_bounds
ko_room_destination:
        lda #8
ko_store_limit:
        sta ko_script_pages
        jsr ko_open_file
        bcs :+
        jmp ko_load_return
:       ldx #0
ko_header_loop:
        stx ko_header_index
        jsr ko_stream_byte
        bcc ko_load_return
        ldx ko_header_index
        sta ko_package_header,x
        inx
        cpx #24
        bne ko_header_loop
        ldx #3
ko_magic_loop:
        lda ko_package_header,x
        cmp ko_package_magic,x
        bne ko_load_format
        dex
        bpl ko_magic_loop
        ; Reject mismatched builds before touching main script or LC payload.
        ldx #11
ko_identity_loop:
        lda ko_package_header+8,x
        cmp ko_media_id,x
        bne ko_load_identity
        dex
        bpl ko_identity_loop
        lda ko_package_header+21
        ora ko_package_header+22
        ora ko_package_header+23
        bne ko_load_format
        lda ko_package_header+20
        beq ko_load_identity
        cmp #4
        bcs ko_load_identity
        ; Same convention as native print_game_disk_prompt: GE(12) >= 2 is B.
        lda $601c
        cmp #2
        lda #1
        bcc :+
        asl a
:       and ko_package_header+20
        beq ko_load_identity
        lda ko_package_header+5
        cmp ko_script_pages
        bcc ko_script_upper_ok
        bne ko_load_bounds
        lda ko_package_header+4
        bne ko_load_bounds
ko_script_upper_ok:
        lda ko_package_header+4
        ora ko_package_header+5
        beq ko_load_bounds      ; EOF must exist
        lda ko_package_header+7
        cmp #4
        bcc ko_pool_upper_ok
        bne ko_load_bounds
        lda ko_package_header+6
        bne ko_load_bounds
ko_pool_upper_ok:
        jmp ko_load_script
ko_load_format:
        lda #3
        bne ko_load_failure
ko_load_bounds:
        lda #4
        bne ko_load_failure
ko_load_identity:
        lda #6
ko_load_failure:
        sta ko_load_error
ko_load_return:
        bit $c082
        clc
        rts
ko_load_script:
        lda ko_package_header+4
        sta ko_remaining
        lda ko_package_header+5
        sta ko_remaining+1
        lda ko_pool_only
        sta ko_skip_main
        lda #0
        sta ko_copy_lc
        jsr ko_copy_stream
        lda #0
        sta ko_skip_main
        bcc ko_load_return
        lda ko_transfer_byte
        bne ko_load_format      ; final script byte must be EOF
        lda ko_package_header+6
        sta ko_remaining
        lda ko_package_header+7
        sta ko_remaining+1
        ora ko_remaining
        beq ko_package_complete
        lda #0
        sta ko_destination
        lda #$d0
        sta ko_destination+1
        lda #1
        sta ko_copy_lc
        jsr ko_copy_stream
        bcc ko_load_return
ko_package_complete:
        lda ko_package_header+6
        sta ko_room_size
        lda ko_package_header+7
        sta ko_room_size+1
        sec
        rts

ko_copy_stream:
        jsr ko_stream_byte
        bcc ko_copy_failed
        sta ko_transfer_byte
        lda ko_skip_main
        bne ko_copy_decrement
        lda ko_destination
        sta $1e
        lda ko_destination+1
        sta $1f
        php
        sei
        lda ko_copy_lc
        beq ko_copy_main
        tax
        dex                     ; 1 -> bank2, 9 -> bank1
        lda $c083,x
        lda $c083,x
ko_copy_main:
        ldy #0
        lda ko_transfer_byte
        sta ($1e),y
        bit $c082
        plp
        inc ko_destination
        bne ko_copy_decrement
        inc ko_destination+1
ko_copy_decrement:
        lda ko_remaining
        bne ko_copy_low
        dec ko_remaining+1
ko_copy_low:
        dec ko_remaining
        lda ko_remaining
        ora ko_remaining+1
        bne ko_copy_stream
        sec
        rts
ko_copy_failed:
        clc
        rts

; Open native DOS catalog and retain its single TS list at B700.
ko_open_file:
        ldy #9
ko_copy_name:
        lda ($ea),y
        sta ko_filename,y
        dey
        bpl ko_copy_name
        lda #0
        sta $0bb3
        lda #$b7
        sta $0bb4
        lda #35                 ; bound corrupt catalog cycles
        sta ko_catalog_remaining
        lda #17
        ldx #0
        jsr ko_read_sector
        bcs ko_open_failed
ko_next_catalog:
        lda $b701
        beq ko_file_missing
        ldx $b702
        dec ko_catalog_remaining
        beq ko_open_format
        jsr ko_read_sector
        bcs ko_open_failed
        ldy #$0e
ko_catalog_entry:
        sty ko_catalog_index
        lda $b6fd,y
        beq ko_next_entry
        cmp #$ff
        beq ko_next_entry
        ldx #0
ko_compare_name:
        lda $b700,y
        cmp ko_filename,x
        bne ko_next_entry
        iny
        inx
        cpx #10
        bne ko_compare_name
        ldy ko_catalog_index
        lda $b6fd,y
        ldx $b6fe,y
        jsr ko_read_sector
        bcs ko_open_failed
        lda $b701               ; do not silently ignore a second TS list
        ora $b702
        ora $b705
        ora $b706
        bne ko_open_format
        lda #12
        sta ko_ts_index
        lda #1
        sta ko_need_sector
        lda #0
        sta $0bb3
        lda #7
        sta $0bb4
        sec
        rts
ko_next_entry:
        lda ko_catalog_index
        cmp #$e0
        beq ko_next_catalog
        clc
        adc #35
        tay
        jmp ko_catalog_entry
ko_file_missing:
        lda #2
        bne ko_open_error
ko_open_format:
        lda #3
ko_open_error:
        sta ko_load_error
ko_open_failed:
        clc
        rts

; Carry follows native RWTS here: set=error. The stream API inverts it.
ko_read_sector:
        cmp #35
        bcs ko_bad_sector
        cpx #16
        bcs ko_bad_sector
        sta $0baf
        stx $0bb0
        lda #1
        sta $0bb7
        lda #$0b
        ldy #$ab
        jsr $bd00
        bcc ko_sector_ok
        lda #1
        sta ko_load_error
        sec
ko_sector_ok:
        rts
ko_bad_sector:
        lda #3
        sta ko_load_error
        sec
        rts

ko_stream_byte:
        lda ko_need_sector
        beq ko_buffer_byte
        ldy ko_ts_index
        beq ko_stream_short
        lda $b700,y
        beq ko_stream_short
        iny
        ldx $b700,y
        iny
        sty ko_ts_index
        jsr ko_read_sector
        bcs ko_stream_failed
        lda #0
        sta ko_need_sector
        sta ko_buffer_index
ko_buffer_byte:
        ldx ko_buffer_index
        lda $0700,x
        inc ko_buffer_index
        bne ko_byte_ready
        inc ko_need_sector
ko_byte_ready:
        sec
        rts
ko_stream_short:
        lda #5
        sta ko_load_error
ko_stream_failed:
        clc
        rts

ko_package_magic: .byte "KOR2"
ko_package_header: .res 24,0
ko_media_id: .res 12,0       ; bound to actual media by the host builder
ko_header_index: .byte 0
ko_script_pages: .byte 0
ko_destination: .word 0
ko_remaining: .word 0
ko_copy_lc: .byte 0
ko_transfer_byte: .byte 0
ko_filename: .res 10,0
ko_catalog_remaining: .byte 0
ko_catalog_index: .byte 0
ko_ts_index: .byte 0
ko_need_sector: .byte 0
ko_buffer_index: .byte 0
ko_load_error: .byte 0
ko_pool_only: .byte 0
ko_skip_main: .byte 0
