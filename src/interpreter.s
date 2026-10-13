; ULTRA resident adventure interpreter, native ADVEN INTERP.OBJ payload.
; Source provenance: assets/raw/a/files/adven-interp-obj.bin, offset4 length$500.
; Load/run $0800. Remaining source labels reflect observed control/data roles;
; detailed intrinsic condition conventions are still being traced.
; See docs/engine.md for pointer ownership and current uncertainty limits.
        .setcpu "6502"
        .segment "INTERPRETER"
        .export engine_entry, dispatch_script_line, load_named_file, read_command, read_keyboard_wait
; Entry from START CALL2048. Resets hardware stack, initializes engine
; pointers/vectors from $0300 parameters, loads INITIAL/LIBRARY/INTRIN/CHAR GEN.
; Changes HGR soft switches; clobbers registers and engine zero page. Never returns.
engine_entry:

draw_character_vector           := $0348
dispatch_intrinsic           := $0D00
renderer_install           := $B300
dos_rwts           := $BD00
rom_bell           := $FBE2
rom_crout           := $FD8B
rom_cout           := $FDED
        ldx     #$FF
        txs
        ldy     #$00
        lda     #$00
        sta     $F0
        lda     #$03
        sta     $F1
        lda     #$F3
        sta     $0344
        lda     #$0B
        sta     $0345
        lda     #$A8
        sta     $034A
        lda     #$08
        sta     $034B
        lda     #$20
        sta     $034C
        lda     #$0B
        sta     $034D
        lda     #$00
        sta     $C0
        lda     $0342
        sta     $DC
        sta     $D0
        lda     $0343
        sta     $DD
        sta     $D1
        lda     #$8D
        sta     ($DC),y
        lda     $0310
        sta     $EE
        sta     $D4
        sta     $D2
        lda     $0311
        sta     $EF
        sta     $D5
        sta     $D3
        lda     $EE
        sta     $EC
        lda     $EF
        sta     $ED
        lda     #$12
        ldx     #$03
        jsr     load_named_file
        lda     $031C
        sta     $DA
        sta     $EC
        lda     $031D
        sta     $DB
        sta     $ED
        lda     #$1E
        ldx     #$03
        jsr     load_named_file
        lda     $0328
        sta     $EC
        lda     $0329
        sta     $ED
        lda     #$2A
        ldx     #$03
        jsr     load_named_file
        lda     $0334
        sta     $EC
        lda     $0335
        sta     $ED
        lda     #$36
        ldx     #$03
        jsr     load_named_file
        sta     $C057
        sta     $C054
        sta     $C052
        sta     $C050
        jsr     renderer_install
; Script PC $D2/$D3; active pattern/return frame $D0/$D1. A leading high-bit
; dot executes a directive through $0D00; other lines are matched command patterns.
; Script subroutines save two-byte pointers on the hardware stack.
dispatch_script_line:  ldy     #$00
        lda     ($D2),y
        cmp     #$AE
        bne     return_script_subroutine
advance_to_opcode:  inc     $D2
        bne     decode_dot_line
        inc     $D3
decode_dot_line:  iny
        lda     ($D2),y
        cmp     #$A0
        bne     call_script_subroutine
        iny
        lda     ($D2),y
        cmp     #$A0
        beq     call_script_subroutine
        jsr     dispatch_intrinsic
        ldy     #$00
        jsr     advance_script_line
        bne     dispatch_script_line
call_script_subroutine:  ldy     #$00
        tsx
        bmi     push_pattern_pointer
        jmp     script_stack_overflow

push_pattern_pointer:  lda     $D1
        pha
        lda     $D0
        pha
        lda     $D2
        sta     $D0
        lda     $D3
        sta     $D1
        bne     scan_room_handlers
return_script_subroutine:  lda     $D1
        cmp     $DD
        beq     scan_command_comma
        sta     $D3
        lda     $D0
        sta     $D2
        pla
        sta     $D0
        pla
        sta     $D1
        jsr     advance_script_line
        bne     dispatch_script_line
scan_command_comma:  lda     ($D0),y
        inc     $D0
        beq     acquire_next_command
        cmp     #$8D
        beq     acquire_next_command
        cmp     #$AC
        bne     scan_command_comma
scan_room_handlers:  lda     $D4
        sta     $D2
        lda     $D5
        sta     $D3
skip_action_lines:  lda     ($D2),y
        cmp     #$AE
        bne     test_handler
        jsr     advance_script_line
        bne     skip_action_lines
test_handler:  jsr     match_command_pattern
        ldy     #$00
        lda     $DE
        bne     find_handler_body
        jsr     advance_script_line
        bne     skip_action_lines
find_handler_body:  jsr     advance_script_line
        lda     ($D2),y
        cmp     #$AE
        bne     find_handler_body
        jmp     advance_to_opcode

acquire_next_command:  lda     $DC
        sta     $D0
        lda     $DD
        sta     $D1
        jsr     normalize_command
        ldy     #$00
        beq     scan_room_handlers
advance_script_line:  lda     ($D2),y
        inc     $D2
        bne     check_script_cr
        inc     $D3
check_script_cr:  cmp     #$8D
        bne     advance_script_line
        lda     ($D2),y
        cmp     #$C0
        bne     script_line_ready
        lda     $DA
        sta     $D2
        lda     $DB
        sta     $D3
script_line_ready:  rts

saved_input_first:  .byte $00 ; saved input prefix, mutable data
saved_input_second:  .byte $00
; Reads/normalizes a command into $DC/$DD scratch. Carries between chained
; commands through $C0-$C5; pads significant words to five high-bit characters.
; Uses the ignore/AND/THEN separator table at $0390. Clobbers registers and $E0-$E9.
normalize_command:  lda     $C0
        bne     normalize_input_buffer
retry_command_input:  jsr     prompt_and_read_command
normalize_input_buffer:  clc
        jsr     parse_input_words
        bcs     retry_command_input
        rts

prompt_and_read_command:  lda     #$0F
        sta     $25
        lda     #$00
        sta     $24
        ldy     #$01
print_prompt_character:  lda     ($F0),y
        sty     $DF
        sta     $33
        jsr     rom_cout
        ldy     $DF
        tya
        ldx     #$00
        iny
        cmp     ($F0,x)
        bne     print_prompt_character
        ldy     #$00
        lda     $0340
        sta     $C0
        sta     $C2
        sta     $C4
        lda     $0341
        sta     $C1
        sta     $C3
        sta     $C5
        lda     ($C0),y
        sta     saved_input_first
        iny
        lda     ($C0),y
        sta     saved_input_second
        jsr     read_command
        rts

parse_input_words:  lda     $C0
        sta     $C2
        ldy     #$00
        lda     $DC
        sta     $E7
        lda     $DD
        sta     $E8
begin_input_word:  ldx     #$00
        lda     #$90
        sta     $E0
        lda     #$03
        sta     $E1
        lda     ($C0),y
        cmp     #$AF
        bne     remember_input_character
        cpx     $C0
        bne     remember_input_character
        lda     saved_input_first
        sta     ($C0),y
        iny
        lda     saved_input_second
        sta     ($C0),y
        jmp     parse_input_words

next_input_character:  lda     ($C0),y
remember_input_character:  sta     $E9
        inc     $C0
        bne     input_page_in_bounds
        jmp     input_without_cr

input_page_in_bounds:  cpx     #$00
        beq     check_ignored_word
        cmp     #$A0
        bne     classify_input_separator
        jsr     pad_word_to_five
        lda     $C0
        sta     $C4
        dec     $C4
        jmp     begin_input_word

check_ignored_word:  dec     $C0
match_ignored_character:  cmp     ($E0),y
        bne     ignored_character_mismatch
        iny
        lda     ($C0),y
        jmp     match_ignored_character

ignored_character_mismatch:  lda     ($E0),y
        cmp     #$00
        beq     matched_ignored_word
        cmp     #$01
        beq     matched_ignored_word
seek_ignored_word_end:  iny
        lda     ($E0),y
        cmp     #$00
        beq     advance_ignored_word
        cmp     #$01
        bne     seek_ignored_word_end
        inc     $C0
        bne     classify_input_separator
advance_ignored_word:  iny
        tya
        clc
        adc     $E0
        sta     $E0
        ldy     #$00
        lda     $E9
        jmp     match_ignored_character

matched_ignored_word:  dey
        lda     ($E0),y
        cmp     #$8D
        bne     skip_matched_ignored_word
        ldy     #$00
        sty     $C0
        cpy     $E7
        bne     finish_normalized_command
        sec
        rts

skip_matched_ignored_word:  inc     $C0
        clc
        tya
        adc     $C0
        sta     $C0
        ldy     #$00
        cpy     $E7
        bne     finish_normalized_command
        lda     $C0
        sta     $C4
        sta     $C2
        jmp     begin_input_word

finish_normalized_command:  jsr     terminate_normalized_words
        clc
        rts

classify_input_separator:  lda     $E9
        cmp     #$AE
        beq     input_chain_separator
        cmp     #$AC
        bne     check_input_cr
input_chain_separator:  ldy     #$00
        cpx     #$00
        beq     separator_with_no_word
        jsr     pad_word_to_five
separator_with_no_word:  cpy     $E7
        bne     finish_chained_command
        lda     $C0
        sta     $C4
        sta     $C2
        jmp     begin_input_word

finish_chained_command:  jsr     terminate_normalized_words
        lda     $C0
        sta     $C4
        dec     $C4
        dec     $C4
        clc
        rts

check_input_cr:  ldy     #$00
        cmp     #$8D
        bne     check_significant_character
        cpx     #$00
        beq     finish_input_line
        jsr     pad_word_to_five
finish_input_line:  cpy     $E7
        bne     return_normalized_input
        sty     $C0
        sec
        rts

return_normalized_input:  jsr     terminate_normalized_words
        lda     $C0
        sta     $C4
        dec     $C4
        dec     $C4
        sty     $C0
        clc
        rts

check_significant_character:  cpx     #$05
        beq     discard_input_character
        cmp     #$A0
        beq     discard_input_character
        cmp     #$A1
        beq     discard_input_character
        cmp     #$C0
        bne     append_significant_character
discard_input_character:  jmp     next_input_character

append_significant_character:  sta     ($E7),y
        inc     $E7
        inx
        jmp     next_input_character

append_word_padding:  lda     #$A0
        sta     ($E7),y
        inc     $E7
        inx
pad_word_to_five:  cpx     #$05
        bne     append_word_padding
        rts

terminate_normalized_words:  lda     #$8D
        sta     ($E7),y
        rts

; Pattern at $D2/$D3, normalized words at $D0/$D1. Searches five-character
; words; returns $DE=$FF for match, 0 for no match. Clobbers A/X/Y,$E7/$E8.
match_command_pattern:  lda     $D0
        sta     $E7
        lda     $D1
        sta     $E8
match_pattern_word:  ldx     #$00
match_pattern_character:  lda     ($D2),y
        cmp     #$8D
        beq     pattern_matched
        cmp     ($E7),y
        bne     pattern_mismatch
        iny
        inx
        cpx     #$05
        bne     match_pattern_character
        beq     match_pattern_word
pattern_mismatch:  txa
        beq     seek_next_input_word
rewind_partial_match:  dey
        dex
        bne     rewind_partial_match
seek_next_input_word:  lda     ($E7),y
        cmp     #$8D
        beq     pattern_not_matched
        cmp     #$AC
        beq     pattern_not_matched
        clc
        lda     #$05
        adc     $E7
        bcs     pattern_not_matched
        sta     $E7
        bne     match_pattern_character
pattern_not_matched:  ldy     #$00
        sty     $DE
        rts

pattern_matched:  lda     #$FF
        sta     $DE
        rts

; A/X = low/high pointer to ten high-bit filename characters; $EC/$ED =
; destination. Scans DOS catalog, then loads entire allocated sectors (headers
; included). Returns $ED as the next destination page. Clobbers A/X/Y, $DF,
; $E0-$EB and mutable RWTS IOB. Does not use DOS BLOAD header addresses.
; Existing files have one TS list; additional-list behavior is not implemented.
load_named_file:  sta     $EA
        stx     $EB
        ldy     #$00
copy_ten_character_filename:  lda     ($EA),y
        sta     $E0,y
        iny
        cpy     #$0A
        bne     copy_ten_character_filename
        lda     #$00
        sta     rwts_buffer_low
        lda     #$B7
        sta     rwts_buffer_high
        lda     #$11
        ldx     #$00
        jsr     read_sector
next_catalog_sector:  lda     $B701
        bne     read_catalog_sector
        jmp     file_not_found

read_catalog_sector:  ldx     $B702
        jsr     read_sector
        ldy     #$0E
test_catalog_entry:  sty     $DF
        ldx     #$00
compare_filename_character:  lda     $B700,y
        cmp     $E0,x
        bne     advance_catalog_entry
        iny
        inx
        cpx     #$0A
        bne     compare_filename_character
        beq     read_file_ts_list
advance_catalog_entry:  lda     $DF
        cmp     #$E0
        beq     next_catalog_sector
        clc
        adc     #$23
        tay
        bne     test_catalog_entry
read_file_ts_list:  ldy     $DF
        lda     $B6FD,y
        cmp     #$FF
        beq     advance_catalog_entry
        ldx     $B6FE,y
        jsr     read_sector
        lda     $EC
        sta     rwts_buffer_low
        lda     $ED
        sta     rwts_buffer_high
        ldy     #$0C
read_allocated_file_sector:  lda     $B700,y
        beq     file_load_complete
        iny
        ldx     $B700,y
        iny
        sty     $DF
        jsr     read_sector
        ldy     $DF
        inc     rwts_buffer_high
        bne     read_allocated_file_sector
file_load_complete:  lda     rwts_buffer_high
        sta     $ED
        rts

; DOS 3.3 RWTS IOB and drive workspace, not executable instructions.
; $0BAB version, slot, drive, volume, track, sector, DCT pointer,
; buffer pointer, unused, command, status, actual volume; then drive bytes.
rwts_device_characteristics:
        .byte $00,$01,$EF,$D8
rwts_iob:
        .byte $01,$60,$01,$00
rwts_track:  .byte $00
rwts_sector:  .byte $00
        .word $0BA7
rwts_buffer_low:  .byte $00
rwts_buffer_high:  .byte $00
        .byte $00,$00
rwts_command:  .byte $01
        .byte $00,$00,$60,$01

; A=track, X=logical sector; mutable IOB buffer chooses destination.
; Calls DOS RWTS at $BD00 with A/Y=$0BAB. Carry set indicates an error.
; A/X/Y, flags and DOS workspace are not preserved. Original slot6/drive1 I/O.
read_sector:  sta     rwts_track
        stx     rwts_sector
        lda     #$01
        sta     rwts_command
        lda     #$0B
        ldy     #$AB
        jsr     dos_rwts
        bcs     disk_error
        rts

file_not_found:  lda     #$50
        ldx     #$03
        bne     print_engine_error
disk_error:  lda     #$60
        ldx     #$03
        bne     print_engine_error
input_without_cr:  lda     #$70
        ldx     #$03
        bne     print_engine_error
script_stack_overflow:  lda     #$80
        ldx     #$03
        bne     print_engine_error
print_engine_error:  jsr     print_script_string
        jsr     rom_crout
        jsr     rom_crout
        rts

; A/X = high-bit string pointer. Prints until CR. A semicolon immediately
; before CR suppresses the newline; embedded semicolons print literally.
; Clobbers A/Y,$E7/$E8; X may be changed by the firmware/output hooks.
print_script_string:  ldy     #$00
        sta     $E7
        stx     $E8
print_string_character:  lda     ($E7),y
        cmp     #$BB
        beq     check_trailing_semicolon
        cmp     #$8D
        beq     print_string_newline
emit_string_character:  jsr     rom_cout
        iny
        bne     print_string_character
check_trailing_semicolon:  iny
        lda     ($E7),y
        cmp     #$8D
        beq     string_done
        dey
        lda     #$BB
        bne     emit_string_character
print_string_newline:  jsr     rom_crout
string_done:  rts

input_prompt_length:  .byte $00 ; prompt length / first editable column
; Parameter input buffer $0340/$0341. Prompts occupy row15; edit through
; column38, leaving the final cell for cursor/bounds handling. CR terminates,
; backspace cannot cross the prompt. Clobbers A/X/Y,$1C/$1D,$2A/$2B,$24/$25.
read_command:  ldy     #$00
        lda     $0340,y
        sta     $2A
        iny
        lda     $0340,y
        sta     $2B
        lda     #$0F
        sta     $25
        ldy     #$00
        lda     ($F0),y
        sta     input_prompt_length
        sta     $24
        tay
        jsr     clear_input_field
read_editable_character:  jsr     draw_input_cursor
        jsr     read_keyboard_wait
        cpy     #$27
        bcc     input_field_has_space
        cmp     #$8D
        bne     input_field_full
        jmp     store_and_echo_character

input_field_full:  cmp     #$88
        beq     handle_input_backspace
        jsr     input_error_bell
        jsr     erase_input_cursor
        jmp     read_editable_character

input_field_has_space:  cmp     #$8D
        bne     check_input_backspace
        jmp     store_and_echo_character

check_input_backspace:  cmp     #$88
        bne     check_input_printable
handle_input_backspace:  cpy     input_prompt_length
        beq     backspace_at_prompt
        dey
        jsr     erase_input_cursor
        lda     #$88
        jsr     rom_cout
        jmp     read_editable_character

backspace_at_prompt:  jsr     input_error_bell
        jmp     read_editable_character

check_input_printable:  cmp     #$A0
        bcs     append_input_character
        jmp     read_editable_character

append_input_character:  jsr     store_and_echo_character
        iny
        jmp     read_editable_character

store_and_echo_character:  pha
        sty     $1D
        tya
        sec
        sbc     input_prompt_length
        tay
        pla
        sta     ($2A),y
        ldy     $1D
        jsr     rom_cout
        rts

draw_input_cursor:  lda     $0347
        eor     #$FF
        sta     $0347
        jsr     save_input_registers
        jsr     draw_cursor_space
        jsr     restore_input_registers
        lda     $0347
        eor     #$FF
        sta     $0347
        rts

erase_input_cursor:  jsr     save_input_registers
        jsr     draw_cursor_space
        jsr     restore_input_registers
        rts

; Waits for Apple keyboard strobe, returns high-bit key in A; clears
; strobe at $C010. This blocking editor has no gameplay timer: room scripts
; perform their timed first-key polls separately via intrinsic .W.
read_keyboard_wait:  bit     $C000
        bpl     read_keyboard_wait
        lda     $C000
        bit     $C010
        rts

save_input_registers:  tya
        sta     $1D
        txa
        sta     $1C
        rts

restore_input_registers:  lda     $1C
        tax
        lda     $1D
        tay
        rts

draw_cursor_space:  lda     #$A0
        jmp     (draw_character_vector)

        rts

input_error_bell:  jsr     save_input_registers
        jsr     rom_bell
        jsr     restore_input_registers
        rts

clear_input_field:  lda     #$27
        sec
        sbc     input_prompt_length
        tax
clear_input_cell:  lda     #$A0
        jsr     rom_cout
        dex
        bne     clear_input_cell
        sty     $24
        lda     #$0F
        sta     $25
        rts

        .byte $00,$00,$00,$00 ; allocation padding after clear_input_field
.assert * - engine_entry = $500, error, "interpreter must occupy $0800-$0CFF"
