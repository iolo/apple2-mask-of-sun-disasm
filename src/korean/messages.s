; Candidate Korean message reader, MOS6502, executes from main RAM.
; Dependencies: lc.s and generated native renderer symbol aliases.
; A/X = message ID low/high; bit15 selects resident (bank1), else room (bank2).
; C=1 success, C=0 malformed ID/pool/stream/glyph. Always returns ROM visible
; and LC writes disabled. Caller appends the original script CR if required.
; Clobbers A/X/Y, renderer ZP $1C-$1F/$24-$27/$33, private mutable workspace.
; Direct reader does not borrow interpreter ZP or alter script/condition pointers.
; Caller must have decimal mode clear. Not reentrant.
; Loader must set pool sizes and font count only after complete validated loads.
.setcpu "6502"
.segment "CODE"
.export ko_print_message, ko_room_size, ko_resident_size, ko_font_count
.export ko_print_script_string

; A/X = original high-bit script string pointer, matching the native printer.
; Dispatch exactly ~hhhh[;]CR references; ASCII/numeric/echo paths use the
; original printer. Clobbers native string workspace E7/E8, but not D2/D3.
ko_print_script_string:
        sta $e7
        stx $e8
        ldy #0
        lda ($e7),y
        cmp #$fe                ; high-bit ~
        beq ko_parse_reference
        lda $e7
        ldx $e8
        jsr ko_native_print_script_string
        sec
        rts
ko_parse_reference:
        lda #0
        sta ko_reference_id
        sta ko_reference_id+1
ko_next_hex:
        iny
        lda ($e7),y
        cmp #$b0
        bcc ko_bad_reference
        cmp #$ba
        bcc ko_hex_digit
        cmp #$c1
        bcc ko_bad_reference
        cmp #$c7
        bcs ko_bad_reference
        sec
        sbc #7
ko_hex_digit:
        and #$0f
        sta ko_nibble
        ldx #4
ko_shift_hex:
        asl ko_reference_id
        rol ko_reference_id+1
        dex
        bne ko_shift_hex
        lda ko_reference_id
        ora ko_nibble
        sta ko_reference_id
        cpy #4
        bne ko_next_hex
        iny
        lda ($e7),y
        cmp #$bb
        beq ko_reference_semicolon
        cmp #$8d
        bne ko_bad_reference
        lda #1
        bne ko_reference_ready
ko_reference_semicolon:
        iny
        lda ($e7),y
        cmp #$8d
        bne ko_bad_reference
        lda #0
ko_reference_ready:
        sta ko_append_newline
        lda ko_reference_id
        ldx ko_reference_id+1
        jsr ko_print_message
        bcc ko_bad_reference
        lda ko_append_newline
        beq ko_reference_done
        lda #$8d
        jsr $fded
ko_reference_done:
        sec
        rts
ko_bad_reference:
        bit $c082
        clc
        rts

ko_print_message:
        sta ko_id
        txa
        and #$7f
        sta ko_id+1
        txa
        bmi ko_select_resident
        ldx #0
        lda #4                  ; room pool at most 1K
        sta ko_max_pages
        jmp ko_selected
ko_select_resident:
        ldx #2
        lda #16                 ; resident pool at most 4K
        sta ko_max_pages
ko_selected:
        lda ko_room_size,x
        sta ko_size
        lda ko_room_size+1,x
        sta ko_size+1
        cmp ko_max_pages
        bcc ko_size_upper_ok
        bne ko_bad_header
        lda ko_size
        bne ko_bad_header
ko_size_upper_ok:
        lda ko_size+1
        bne ko_size_lower_ok
        lda ko_size
        cmp #2
        bcc ko_bad_header
ko_size_lower_ok:
        txa
        asl a
        asl a
        sta ko_bank             ; X=0/2 -> LC bank switch index 0/8
        lda #0
        sta ko_cursor
        lda #$d0
        sta ko_cursor+1
        clc
        adc ko_size+1
        sta ko_end+1
        lda ko_size
        sta ko_end
        ; Font must fit the 8K common LC region; count may be 0 for ASCII only.
        lda ko_font_count+1
        cmp #4
        bcc ko_font_size_ok
        bne ko_bad_header
        lda ko_font_count
        bne ko_bad_header
ko_font_size_ok:
        jsr ko_read_byte
        sta ko_count
        jsr ko_read_byte
        sta ko_count+1
        cmp #8                  ; header alone would fill/exceed 4K
        bcs ko_bad_header
        lda ko_id+1
        cmp ko_count+1
        bcc ko_id_ok
        bne ko_bad_header
        lda ko_id
        cmp ko_count
        bcs ko_bad_header
ko_id_ok:
        lda ko_count
        asl a
        sta ko_header_size
        lda ko_count+1
        rol a
        sta ko_header_size+1
        clc
        lda ko_header_size
        adc #2
        sta ko_header_size
        bcc ko_header_size_ready
        inc ko_header_size+1
ko_header_size_ready:
        jmp ko_read_offset
ko_bad_header:
        bit $c082
        clc
        rts
ko_read_offset:
        ; Table begins at D002; range-checked reads also reject short headers.
        lda ko_id
        asl a
        sta ko_cursor
        lda ko_id+1
        rol a
        clc
        adc #$d0
        sta ko_cursor+1
        clc
        lda ko_cursor
        adc #2
        sta ko_cursor
        bcc ko_offset_cursor_ready
        inc ko_cursor+1
ko_offset_cursor_ready:
        jsr ko_read_byte
        bcc ko_bad_header
        sta ko_offset
        jsr ko_read_byte
        bcc ko_bad_header
        sta ko_offset+1
        ; Offset must be in the payload, never inside the count/index table.
        cmp ko_header_size+1
        bcc ko_bad_header
        bne ko_offset_after_header
        lda ko_offset
        cmp ko_header_size
        bcc ko_bad_header
ko_offset_after_header:
        lda ko_offset+1
        cmp ko_size+1
        bcc ko_offset_inside_pool
        bne ko_bad_header
        lda ko_offset
        cmp ko_size
        bcs ko_bad_header
ko_offset_inside_pool:
        lda ko_offset
        sta ko_cursor
        lda ko_offset+1
        clc
        adc #$d0
        sta ko_cursor+1
ko_next_character:
        jsr ko_read_byte
        bcc ko_bad_stream
        cmp #0
        beq ko_message_done
        cmp #10
        beq ko_message_newline
        cmp #$20
        bcc ko_bad_stream
        cmp #$7f
        bcc ko_ascii
        cmp #$80
        bcc ko_bad_stream
        cmp #$c0
        bcs ko_bad_stream
        and #$3f
        sta ko_glyph+1
        jsr ko_read_byte
        bcc ko_bad_stream
        sta ko_glyph
        lda ko_glyph+1
        cmp ko_font_count+1
        bcc ko_glyph_valid
        bne ko_bad_stream
        lda ko_glyph
        cmp ko_font_count
        bcs ko_bad_stream
ko_glyph_valid:
        lda ko_glyph
        sta $1e
        lda ko_glyph+1
        sta $1f
        asl $1e
        rol $1f
        asl $1e
        rol $1f
        asl $1e
        rol $1f
        lda $1f
        clc
        adc #$e0
        sta $1f
        ldx #0                  ; common E000-FFFF independent of D bank
        jsr lc_fetch_glyph
        lda #<lc_glyph_scratch
        sta $1e
        lda #>lc_glyph_scratch
        sta $1f
        jsr ko_native_locate_cursor_scanline
        jsr ko_native_draw_eight_scanlines
        jsr ko_native_advance_column
        jmp ko_next_character
ko_ascii:
        ora #$80
        jsr $fded
        jmp ko_next_character
ko_message_newline:
        lda #$8d
        jsr $fded
        jmp ko_next_character
ko_message_done:
        sec
        rts
ko_bad_stream:
        bit $c082
        clc
        rts

; Read one byte from current D bank and increment the private stream cursor.
; C=0 at end; IRQ mask restored before return. No ROM calls with LC selected.
ko_read_byte:
        lda ko_cursor+1
        cmp ko_end+1
        bcc ko_read_inside
        bne ko_read_eof
        lda ko_cursor
        cmp ko_end
        bcs ko_read_eof
ko_read_inside:
        lda ko_cursor
        sta $1e
        lda ko_cursor+1
        sta $1f
        php
        sei
        ldx ko_bank
        lda $c080,x
        ldy #0
        lda ($1e),y
        bit $c082
        plp
        inc ko_cursor
        bne ko_read_done
        inc ko_cursor+1
ko_read_done:
        sec
        rts
ko_read_eof:
        clc
        rts

ko_room_size:     .word 0
ko_resident_size: .word 0
ko_font_count:    .word 0
ko_id:           .word 0
ko_count:        .word 0
ko_header_size:  .word 0
ko_offset:       .word 0
ko_cursor:       .word 0
ko_end:          .word 0
ko_size:         .word 0
ko_glyph:        .word 0
ko_bank:         .byte 0
ko_max_pages:    .byte 0
ko_reference_id: .word 0
ko_nibble:       .byte 0
ko_append_newline: .byte 0
