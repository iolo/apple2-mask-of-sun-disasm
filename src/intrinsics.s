; ULTRA intrinsic script engine, vector renderer and speaker synthesis.
; Native INTRIN.OBJ payload at $0D00-$1FFF; see docs/intrinsics.md.
.setcpu "6502"
.ifdef KOREAN
.include "korean-bindings.inc"
.endif
string_printer_vector := $0344
script_dispatch_vector := $034A
file_loader_vector := $034C
engine_continue_initial_load := $0879
engine_execute_opcode := $08B6
engine_scan_command_chain := $0919
engine_read_command := $0C1A
native_after_save_stub := $BA69
native_before_save_stub := $BA72
dos_rwts := $BD00
rom_autostart_slot_scan := $FAA6
rom_wait := $FCA8
rom_cout := $FDED
.segment "INTRINSICS_HEADER"
        .word $0D00,$1300 ; DOS nominal address/length; custom loader includes header
.segment "INTRINSICS"

; $0D00: $D2/$D3 points at high-bit directive letter. Consume letter and space.
; A/X/Y, shared zero page, stack and mutable source operands may change.
; Most actions return to the line scanner; transfers discard return frames.
dispatch_intrinsic:
        ldy     #$00
        lda     ($D2),y
        inc     $D2
        bne     dispatch_intrinsic_at_0d0a
        inc     $D3

dispatch_intrinsic_at_0d0a:
        inc     $D2
        bne     test_goto_room
        inc     $D3
        jmp     test_goto_room

; Twelve-byte native code template plus zero terminator, copied to $0BD1.
; On load failure it unwinds the loader/dispatch stack instead of changing RAM state.
room_load_error_patch:
        pla
        pla
        rts
        nop
        nop
        nop
        pla
        pla
        pla
        pla
        rts
        nop
        .byte $00

test_goto_room:
        cmp     #('G' | $80)
        beq     goto_room
        jmp     test_room_filename

; G: load named script at parameter $0310/$0311; blank argument uses filename scratch.
; Reset room/input pointers and hardware stack, then reenter dispatch.
goto_room:
        ldx     #$00

install_room_error_patch:
        lda     room_load_error_patch,x
        beq     set_room_load_destination
        sta     $0BD1,x
        inx
        bne     install_room_error_patch

set_room_load_destination:
        lda     $0310
        sta     $EC
        lda     $0311
        sta     $ED
        lda     ($D2),y
        cmp     #$8D
        bne     use_inline_room_filename
        lda     #$7B
        ldx     #$0D
        bne     load_room_script

use_inline_room_filename:
        lda     $D2
        ldx     $D3

load_room_script:
        jsr     call_file_loader

restart_room_dispatch:
        lda     $0310
        sta     $D2
        sta     $D4
        sta     $EE
        lda     $0311
        sta     $EF
        sta     $D5
        sta     $D3
        lda     $0342
        sta     $DC
        sta     $D0
        lda     $0343
        sta     $D1
        ldy     #$00
        lda     #$8D
        sta     ($DC),y
        ldx     #$FF
        txs
        jmp     (script_dispatch_vector)

; Ten mutable filename bytes set by .3; native initial bytes are stale workspace.
default_room_filename:
        .byte $08,$F0,$07,$20,$ED,$FD,$C8,$4C
        .byte $79,$08

test_room_filename:
        cmp     #('3' | $80)
        bne     test_wait

; 3: copy ten high-bit bytes into room filename scratch; no filename decoding.
set_room_filename:
        lda     ($D2),y
        sta     default_room_filename,y
        iny
        cpy     #$0A
        bne     set_room_filename
        rts

test_wait:
        cmp     #('W' | $80)
        beq     wait_short
        jmp     test_quit

; W: ROM WAIT with A=$C4; bounded busy delay used in polling loops.
wait_short:
        lda     #$C4
        jsr     rom_wait
        rts

test_quit:
        cmp     #('Q' | $80)
        beq     quit_boot_rom
        jmp     test_clear

; Q: jump to Applesoft autostart slot scan at $FAA6, not a host emulator exit.
quit_boot_rom:
        jmp     rom_autostart_slot_scan
        rts

; C argument ranges: fill 0..1, page 1..2, first scanline 0..191.
clear_argument_minimums:
        .byte $00,$01,$00

clear_argument_maximums:
        .byte $02,$03,$C0

; Blank .C uses fill=1, page=1, first scanline=0; invalid values use minima.
clear_argument_defaults:
        .byte $01,$01,$00

clear_arguments:
        .byte $00,$00,$00

test_clear:
        cmp     #('C' | $80)
        beq     clear_graphics
        jmp     test_text_inverse

; C: evaluate three comma-separated arguments, fill scanlines through 191.
; Normalize fill to $00/$FF; also clear HGR hole bytes and reset text cursor.
clear_graphics:
        ldx     #$00

parse_clear_argument:
        ldy     #$00
        lda     ($D2),y
        cpx     #$00
        beq     test_clear_no_arguments
        inc     $D2
        bne     parse_clear_argument_at_0dcf
        inc     $D3

parse_clear_argument_at_0dcf:
        lda     clear_argument_minimums,x
        jsr     evaluate_expression
        pha
        txa
        tay
        pla
        cmp     clear_argument_minimums,y
        bcs     check_clear_maximum

clear_argument_default:
        lda     clear_argument_minimums,x
        jmp     store_clear_argument

check_clear_maximum:
        iny
        iny
        iny
        cmp     clear_argument_minimums,y
        bcs     clear_argument_default

store_clear_argument:
        sta     clear_arguments,x
        inx
        cpx     #$03
        bcc     parse_clear_argument
        bcs     normalize_clear_fill

test_clear_no_arguments:
        cmp     #$8D
        bne     parse_clear_argument_at_0dcf
        ldx     #$02

copy_clear_defaults:
        lda     clear_argument_defaults,x
        sta     clear_arguments,x
        dex
        bpl     copy_clear_defaults

normalize_clear_fill:
        ldx     #$00
        lda     clear_arguments,x
        bne     clear_fill_ff
        beq     set_clear_fill_and_page

clear_fill_ff:
        lda     #$FF

set_clear_fill_and_page:
        sta     clear_arguments,x
        inx
        dec     clear_arguments,x

clear_scanline:
        ldx     #$02
        lda     clear_arguments,x
        tay
        lda     $B000,y
        sta     $26
        dex
        lda     clear_arguments,x
        bne     clear_page2_scanline
        lda     $B100,y
        bne     clear_scanline_address_ready

clear_page2_scanline:
        lda     $B200,y

clear_scanline_address_ready:
        sta     $27
        ldy     #$27
        ldx     #$00
        lda     clear_arguments,x

fill_scanline_bytes:
        sta     ($26),y
        dey
        bpl     fill_scanline_bytes
        ldx     #$02
        lda     clear_arguments,x
        clc
        adc     #$01
        sta     clear_arguments,x
        cmp     #$C0
        bcc     clear_scanline
        lda     #$00
        sta     $25
        sta     $24
        ldy     #$00
        lda     #$20
        sta     $27

clear_hgr_hole_bytes:
        lda     #$7F
        sta     $26
        tya
        sta     ($26),y
        lda     #$FF
        sta     $26
        tya
        sta     ($26),y
        inc     $27
        ldx     $27
        cpx     #$50
        bcc     clear_hgr_hole_bytes
        rts

test_text_inverse:
        cmp     #('M' | $80)
        beq     set_text_inverse
        jmp     test_display_page

; M: renderer background $0347; 1 stores zero, other values store $FF.
set_text_inverse:
        lda     #$00
        jsr     evaluate_expression
        cmp     #$00
        bne     inverse_value_one

inverse_default_on:
        lda     #$FF
        bne     store_text_inverse

inverse_value_one:
        cmp     #$01
        bne     inverse_default_on
        lda     #$00

store_text_inverse:
        sta     $0347
        rts

test_display_page:
        cmp     #('$' | $80)
        beq     set_display_page
        jmp     test_draw_page

; $: display HGR1/HGR2 with $C054/$C055; invalid values select page1.
set_display_page:
        lda     #$01
        jsr     evaluate_expression
        cmp     #$01
        bne     test_display_page_two

display_page_one:
        sta     $C054
        rts

test_display_page_two:
        cmp     #$02
        bne     display_page_one
        sta     $C055
        rts

test_draw_page:
        cmp     #('_' | $80)
        beq     set_draw_page
        jmp     test_vertical_cursor

; _: set renderer drawing page $0346 to 0/1 for arguments 1/2.
set_draw_page:
        lda     #$01
        jsr     evaluate_expression
        cmp     #$01
        bne     test_draw_page_two

draw_page_one:
        lda     #$00
        sta     $0346
        rts

test_draw_page_two:
        cmp     #$02
        bne     draw_page_one
        lda     #$01
        sta     $0346
        rts

test_vertical_cursor:
        cmp     #('V' | $80)
        beq     set_vertical_cursor
        jmp     test_horizontal_cursor

; V: text row 0..15, otherwise zero. Uses renderer cursor $25.
set_vertical_cursor:
        lda     #$00
        jsr     evaluate_expression
        cmp     #$00
        bcs     check_vertical_cursor

vertical_cursor_zero:
        lda     #$00
        beq     store_vertical_cursor

check_vertical_cursor:
        cmp     #$10
        bcs     vertical_cursor_zero

store_vertical_cursor:
        sta     $25
        rts

test_horizontal_cursor:
        cmp     #('H' | $80)
        beq     set_horizontal_cursor
        jmp     test_echo_command

; H: native column 0..57, otherwise zero. Uses cursor $24.
set_horizontal_cursor:
        lda     #$00
        jsr     evaluate_expression
        cmp     #$00
        bcs     check_horizontal_cursor

horizontal_cursor_zero:
        lda     #$00
        beq     store_horizontal_cursor

check_horizontal_cursor:
        cmp     #$3A
        bcs     horizontal_cursor_zero

store_horizontal_cursor:
        sta     $24
        rts

test_echo_command:
        cmp     #('&' | $80)
        beq     echo_command
        jmp     test_jump

; &: echo raw command span $C2..$C4, then clear command-chain marker $C0.
echo_command:
        sec
        lda     $C4
        sbc     $C2
        bcc     echo_done
        tax
        ldy     #$00

echo_command_byte:
        lda     ($C2),y
        jsr     rom_cout
        iny
        dex
        bpl     echo_command_byte
        ldy     #$00
        sty     $C0

echo_done:
        rts

jump_backwards:
        .byte $00

test_jump:
        cmp     #('J' | $80)
        beq     jump_script_lines
        jmp     test_custom_prompt

; J +/-count: scan CR-delimited lines forward/back from script PC.
; Stops at library/room base or @ terminator; discard scan frame on boundary.
jump_script_lines:
        ldy     #$00
        lda     ($D2),y
        inc     $D2
        bne     save_jump_scan_pointer
        inc     $D3

save_jump_scan_pointer:
        ldy     $D2
        sty     $E0
        ldy     $D3
        sty     $E1
        ldy     #$00
        cmp     #$AB
        bne     select_backward_jump
        sty     jump_backwards
        beq     parse_jump_count

select_backward_jump:
        iny
        sty     jump_backwards
        dey

parse_jump_count:
        tya
        jsr     evaluate_expression
        tax
        bne     adjust_backward_count
        rts

adjust_backward_count:
        ldy     jump_backwards
        beq     skip_jump_line
        inx

skip_jump_line:
        jsr     scan_jump_line
        dex
        bne     skip_jump_line
        jmp     commit_jump_pointer

scan_jump_line:
        ldy     #$00
        lda     ($E0),y
        cmp     #$8D
        bne     jump_direction
        jsr     step_after_jump_line
        rts

jump_direction:
        ldy     jump_backwards
        bne     check_backward_boundary
        cmp     #$C0
        beq     abort_jump_scan
        jsr     increment_jump_pointer
        jmp     scan_jump_line

check_backward_boundary:
        lda     $E1
        cmp     $DB
        bne     check_room_boundary
        lda     $E0
        cmp     $DA
        beq     abort_jump_scan

check_room_boundary:
        lda     $E1
        cmp     $D5
        bne     scan_previous_character
        lda     $E0
        cmp     $D4
        beq     abort_jump_scan

scan_previous_character:
        jsr     decrement_jump_pointer
        jmp     scan_jump_line

abort_jump_scan:
        pla
        pla
        rts

commit_jump_pointer:
        jsr     decrement_jump_pointer
        sta     $D2
        lda     $E1
        sta     $D3
        rts

step_after_jump_line:
        ldy     jump_backwards
        bne     decrement_jump_pointer

increment_jump_pointer:
        inc     $E0
        bne     increment_jump_pointer_at_0fb1
        inc     $E1

increment_jump_pointer_at_0fb1:
        rts

decrement_jump_pointer:
        dec     $E0
        lda     $E0
        cmp     #$FF
        bne     decrement_jump_pointer_at_0fbc
        dec     $E1

decrement_jump_pointer_at_0fbc:
        rts

; Mutable custom prompt flag/length/text and saved $F0/$F1 pointer.
; Native prompt/answer seeds are stale workspace, overwritten before use.
custom_prompt_active:
        .byte $00

custom_prompt_length:
        .byte $43

custom_prompt_text:
        .byte $00,$D6,$0A,$76,$02,$83,$34,$33
        .byte $2C,$37,$36,$2C,$35,$2C,$32

saved_prompt_pointer:
        .byte $00,$00

test_custom_prompt:
        cmp     #(']' | $80)
        beq     set_custom_prompt
        jmp     test_ask

; ]: use up to 15 characters as prompt; blank restores original pointer.
set_custom_prompt:
        ldy     #$00
        lda     ($D2),y
        cmp     #$8D
        beq     restore_default_prompt
        ldx     #$00

copy_custom_prompt:
        sta     custom_prompt_text,y
        inx
        iny
        lda     ($D2),y
        cmp     #$8D
        beq     store_custom_prompt_length
        cpx     #$0F
        bcc     copy_custom_prompt

store_custom_prompt_length:
        stx     custom_prompt_length
        lda     custom_prompt_active
        bne     install_custom_prompt_pointer
        lda     #$FF
        sta     custom_prompt_active
        lda     a:$00F0
        sta     saved_prompt_pointer
        lda     a:$00F1
        sta     saved_prompt_pointer+1

install_custom_prompt_pointer:
        lda     #$BE
        sta     a:$00F0
        lda     #$0F
        sta     a:$00F1
        rts

restore_default_prompt:
        lda     custom_prompt_active
        beq     restore_default_prompt_at_1025
        lda     saved_prompt_pointer
        sta     a:$00F0
        lda     saved_prompt_pointer+1
        sta     a:$00F1

restore_default_prompt_at_1025:
        rts

answer_length:
        .byte $31

answer_text:
        .byte $34,$2C,$32,$32,$2C,$53,$37,$20
        .byte $44,$32,$00,$49,$0B,$20,$03

saved_input_buffer:
        .byte $83,$31

test_ask:
        cmp     #('A' | $80)
        beq     ask_player
        jmp     test_answer_equals

; A: temporarily read into $0278, save up to 15 response bytes, restore input buffer.
; Cursor-column immediate and original input pointer are mutable workspace.
ask_player:
        lda     $0340
        sta     saved_input_buffer
        lda     $0341
        sta     saved_input_buffer+1
        lda     #$78
        sta     $0340
        lda     #$02
        sta     $0341
        lda     #$0F
        sta     $25

ask_cursor_column:
        lda     #$00
        sta     $24
        ldy     #$01

print_ask_prompt:
        lda     ($F0),y
        sty     $DF
        sta     $33
        jsr     rom_cout
        ldy     $DF
        tya
        ldx     #$00
        iny
        cmp     ($F0,x)
        bne     print_ask_prompt
        jsr     engine_read_command
        ldy     #$00

copy_answer_text:
        lda     $0278,y
        cmp     #$8D
        beq     restore_input_buffer
        sta     answer_text,y
        iny
        cpy     #$0F
        bcc     copy_answer_text

restore_input_buffer:
        sty     answer_length
        lda     saved_input_buffer
        sta     $0340
        lda     saved_input_buffer+1
        sta     $0341
        rts

condition_result:
        .byte $0B

test_answer_equals:
        cmp     #('=' | $80)
        beq     compare_answer
        jmp     test_print

; =: compare script argument to answer; script CR sets true immediately.
; This accepts a matching argument prefix of a longer answer; do not assume strict equality.
compare_answer:
        inc     answer_length
        ldy     #$00
        sty     condition_result

compare_answer_byte:
        lda     ($D2),y
        cmp     #$8D
        beq     answer_equal
        cmp     answer_text,y
        bne     answer_compare_done
        iny
        cpy     answer_length
        bcc     compare_answer_byte
        bcs     answer_compare_done

answer_equal:
        lda     #$FF
        sta     condition_result

answer_compare_done:
        dec     answer_length
        rts

decimal_leading_state:
        .byte $30

decimal_digit:
        .byte $30

decimal_value_low:
        .byte $3A

decimal_value_high:
        .byte $B0

; Seven-byte formatted-number/terminator scratch; output is high-bit ASCII.
decimal_output:
        .byte $33,$31,$30,$30,$3A,$B0,$8D

test_print:
        cmp     #('P' | $80)
        beq     print_script_value
        jmp     test_if

; P: quoted text uses parameter string printer; numeric argument is low byte,
; optional comma supplies high byte. Decimal conversion supports five digits.
print_script_value:
        ldy     #$00
        lda     ($D2),y
        cmp     #$A2
        bne     parse_print_number
        inc     $D2
        bne     print_quoted_string
        inc     $D3

print_quoted_string:
        lda     $D2
        ldx     $D3
        jmp     (string_printer_vector)

parse_print_number:
        jsr     evaluate_expression
        sta     decimal_value_low
        lda     ($D2),y
        cmp     #$AC
        beq     advance_print_comma
        lda     #$00
        beq     store_print_high_byte

advance_print_comma:
        inc     $D2
        bne     parse_print_high_byte
        inc     $D3

parse_print_high_byte:
        jsr     evaluate_expression

store_print_high_byte:
        sta     decimal_value_high

save_print_terminator:
        lda     ($D2),y
        pha
        jmp     format_decimal
        rts

format_decimal:
        ldx     #$04
        stx     decimal_leading_state

decimal_next_place:
        lda     #$B0
        sta     decimal_digit

decimal_subtract_place:
        sec
        lda     decimal_value_low
        sbc     decimal_place_low,x
        pha
        lda     decimal_value_high
        sbc     decimal_place_high,x
        bcc     decimal_finish_digit
        sta     decimal_value_high
        pla
        sta     decimal_value_low
        inc     decimal_digit
        jmp     decimal_subtract_place

decimal_finish_digit:
        pla
        lda     decimal_digit
        cpx     #$00
        beq     decimal_store_digit
        cmp     #$B0
        beq     decimal_test_leading
        sta     decimal_leading_state

decimal_test_leading:
        bit     decimal_leading_state
        bpl     decimal_next_digit

decimal_store_digit:
        sta     decimal_output,y
        iny

decimal_next_digit:
        dex
        bpl     decimal_next_place
        pla
        sta     decimal_output,y
        lda     #$C6
        sta     $E0
        lda     #$10
        sta     $E1
        lda     $E0
        ldx     $E1
        jmp     (string_printer_vector)

decimal_place_low:
        .byte $01,$0A,$64,$E8,$10

decimal_place_high:
        .byte $00,$00,$00,$03,$27

; 32 high-bit bytes spelling COPYRIGHT(C) 1981,1982 ULTRASOFT; not code.
legacy_text_residue:
        .byte $C3,$CF,$D0,$D9,$D2,$C9,$C7,$C8
        .byte $D4,$A8,$C3,$A9,$A0,$B1,$B9,$B8
        .byte $B1,$AC,$B1,$B9,$B8,$B2,$A0,$D5
        .byte $CC,$D4,$D2,$C1,$D3,$CF,$C6,$D4

; I: store eight-bit expression result; zero is false, any nonzero true.
test_if:
        cmp     #('I' | $80)
        bne     test_then
        lda     #$00
        jsr     evaluate_expression
        sta     condition_result
        rts

test_then:
        cmp     #('T' | $80)
        bne     test_else
        lda     condition_result
        bne     execute_conditional_opcode
        rts

; T/E: remove dispatch return frame and execute next opcode on same line.
; Condition is not recomputed by these branch directives.
execute_conditional_opcode:
        pla
        pla
        jmp     engine_execute_opcode

test_else:
        cmp     #('E' | $80)
        bne     test_skip_to_end
        lda     condition_result
        beq     execute_else_opcode
        rts

execute_else_opcode:
        pla
        pla
        jmp     engine_execute_opcode

test_skip_to_end:
        cmp     #('?' | $80)
        beq     skip_to_library_terminator
        jmp     test_macro_prefix

; ?: scan to @ or stop if crossing $9C00; jump back to engine chain handling.
skip_to_library_terminator:
        ldy     #$00

scan_library_terminator:
        lda     ($D2),y
        inc     $D2
        bne     test_library_terminator
        tax
        inc     $D3
        lda     $D3
        cmp     #$9C
        bne     restore_scanned_character
        rts

restore_scanned_character:
        txa

test_library_terminator:
        cmp     #('@' | $80)
        bne     scan_library_terminator
        pla
        pla

patchable_instruction_11d6:
        jmp     engine_scan_command_chain

; Four mutable macro characters; .1/.2 replace each pair. Native seed is 6015.
macro_prefix:
        .byte $36,$30

macro_suffix:
        .byte $31,$35

test_macro_prefix:
        cmp     #('1' | $80)
        bne     test_macro_suffix
        lda     ($D2),y
        sta     macro_prefix
        iny
        lda     ($D2),y
        sta     macro_prefix+1
        jmp     skip_to_library_terminator

test_macro_suffix:
        cmp     #('2' | $80)
        bne     test_macro_execute
        lda     ($D2),y
        sta     macro_suffix
        iny
        lda     ($D2),y
        sta     macro_suffix+1
        jmp     skip_to_library_terminator

; !: overwrite four following script bytes with macro scratch and execute them.
; This is self-modification of interpreted script text, not a 6502 overlay.
test_macro_execute:
        cmp     #('!' | $80)
        bne     test_save
        ldy     #$01

copy_macro_digits:
        lda     patchable_instruction_11d6+2,y
        sta     ($D2),y
        iny
        cpy     #$05
        bcc     copy_macro_digits
        pla
        pla
        jmp     engine_execute_opcode

disk_error_text:
        .byte $C4,$C9,$D3,$CB,$A0,$C5,$D2,$D2
        .byte $CF,$D2,$A1,$A1,$A1,$8D

save_pages_remaining:
        .byte $00

test_save:
        cmp     #('-' | $80)
        beq     save_game
        jmp     test_restore

; -: native before-save stub, RWTS command2, raw snapshot transfer, after-save stub.
save_game:
        .ifdef KOREAN
        jsr     ko_save_prepare
        .else
        jsr     native_before_save_stub
        .endif
        lda     #$02
        sta     $0BB7
        jsr     transfer_game_snapshot
        .ifdef KOREAN
        jsr     ko_save_finish
        .else
        jsr     native_after_save_stub
        .endif
        rts

; 144 pages: $AF00 downward to $2000, T31/S15 downward to T23/S0.
; Uses resident interpreter IOB; status/carry failures print and unwind frames.
transfer_game_snapshot:
        lda     #$00
        sta     $0BB3
        lda     #$AF
        sta     $0BB4
        lda     #$1F
        sta     $0BAF
        lda     #$0F
        sta     $0BB0
        lda     #$90
        sta     save_pages_remaining
        jsr     transfer_snapshot_sector
        rts

position_disk_message:
        .ifdef KOREAN_NATIVE_UI
        jmp     ko_clear_message_rows
        .res    6,$ea
        .else
        lda     #$0C
        sta     $25
        lda     #$00
        sta     $24
        rts
        .endif

snapshot_error:
        .ifdef KOREAN
        jsr     ko_snapshot_error_guard
        .else
        jsr     position_disk_message
        .endif
        lda     #$16
        ldx     #$12
        jsr     call_string_printer
        jsr     native_after_save_stub
        pla
        pla
        pla
        pla
        rts

transfer_snapshot_sector:
        lda     #$0B
        ldy     #$AB
        jsr     dos_rwts
        bcc     advance_snapshot_sector
        jmp     snapshot_error

advance_snapshot_sector:
        ldy     $0BB0
        dey
        bpl     commit_snapshot_sector
        ldy     #$0F
        dec     $0BAF

commit_snapshot_sector:
        sty     $0BB0
        dec     $0BB4
        dec     save_pages_remaining
        bne     transfer_snapshot_sector
        rts

test_restore:
        cmp     #('+' | $80)
        beq     restore_game
        jmp     test_restart

; +: same transfer with command1; restores RAM $2000..$AFFF from scratch media.
restore_game:
        .ifdef KOREAN
        jsr     ko_restore_guard
        .else
        jsr     native_before_save_stub
        .endif
        lda     #$01
        sta     $0BB7
        jsr     transfer_game_snapshot
        .ifdef KOREAN
        jsr     ko_restore_finish
        .else
        jsr     native_after_save_stub
        .endif
        rts

test_restart:
        cmp     #('*' | $80)
        beq     restart_script
        jmp     test_sound

restart_script:
        jmp     restart_room_dispatch

; Noise state and tone/noise parameters: SV base is tone_period at $12B8.
; Tone: period, duration low/high, sweep; noise fields follow at SV(4)..SV(7).
noise_shift_low:
        .byte $00

noise_shift_high:
        .byte $00

tone_period:
        .byte $00

tone_duration_low:
        .byte $00

tone_duration_high:
        .byte $00

tone_sweep:
        .byte $00

noise_period:
        .byte $00

noise_duration_low:
        .byte $00

noise_duration_high:
        .byte $00

noise_sweep:
        .byte $00

test_sound:
        cmp     #('N' | $80)
        beq     play_sound
        jmp     test_reverse_graphics

; N: second argument N selects noise, otherwise tone. Speaker toggles $C030.
; Preserve loop instruction timing; sweep sign chooses period increase/decrease.
play_sound:
        lda     ($D2),y
        cmp     #$CE
        bne     play_tone
        sec
        inc     noise_duration_high
        ldx     noise_period

; Rotate a two-byte shift register with feedback; toggle speaker after period ticks.
noise_loop:
        rol     noise_shift_low
        rol     noise_shift_high
        txa
        beq     noise_period_tick
        dex

noise_period_tick:
        bne     noise_feedback
        bcc     noise_feedback
        lda     $C030
        ldx     noise_period

noise_feedback:
        ror     a
        ror     a
        ror     a
        eor     noise_shift_high
        asl     a
        asl     a
        asl     a
        php
        lda     noise_sweep
        beq     noise_duration_tick
        dey
        bne     noise_duration_tick
        tay
        bmi     noise_sweep_up
        lda     noise_period
        beq     noise_duration_tick
        dec     noise_period
        tya
        bne     noise_duration_tick

noise_sweep_up:
        inc     noise_period
        and     #$7F
        tay

noise_duration_tick:
        plp
        dec     noise_duration_low
        bne     noise_loop
        dec     noise_duration_high
        bne     noise_loop
        rts

; Toggle speaker and count period/duration ticks; eight-bit counters wrap naturally.
play_tone:
        lda     tone_sweep
        and     #$7F
        tay
        ldx     tone_period
        lda     $C030

tone_loop:
        dex
        bne     tone_sweep_tick
        ldx     tone_period
        lda     $C030

tone_sweep_tick:
        lda     tone_sweep
        beq     tone_duration_tick
        dey
        bne     tone_duration_tick
        tay
        bmi     tone_sweep_up
        dec     tone_period
        tya
        bne     tone_duration_tick

tone_sweep_up:
        inc     tone_period
        and     #$7F
        tay

tone_duration_tick:
        dec     tone_duration_low
        bne     tone_loop
        dec     tone_duration_high
        bne     tone_loop
        rts

test_reverse_graphics:
        cmp     #('R' | $80)
        bne     test_set_variable
        lda     #$01
        jsr     evaluate_expression
        cmp     #$01
        bne     reverse_page_two
        lda     #$20
        ldx     #$40
        bne     reverse_page_selected

reverse_page_two:
        lda     #$40
        ldx     #$60

reverse_page_selected:
        sta     $C7
        lda     #$00
        sta     $C6

; R: complement all $2000..$3FFF or $4000..$5FFF bytes, including HGR holes.
reverse_graphics_byte:
        lda     #$FF
        eor     ($C6),y
        sta     ($C6),y
        inc     $C6
        bne     reverse_graphics_byte
        inc     $C7
        cpx     $C7
        bne     reverse_graphics_byte
        rts

; Saved assignment value/index/address; expression evaluation may replace $FE/$FF.
assignment_default:
        .byte $00

assignment_index:
        .byte $00

assignment_pointer:
        .byte $00,$00

test_set_variable:
        cmp     #('S' | $80)
        beq     set_variable
        jmp     test_select_picture

; S: resolve destination and optional index, preserve address, evaluate RHS and store byte.
; An unresolved variable leaves pointer zero and skips the assignment.
set_variable:
        ldy     #$00
        sty     $FE
        sty     $FF
        jsr     read_expression_atom
        sta     assignment_default
        lda     variable_index
        sta     assignment_index
        lda     $FE
        sta     assignment_pointer
        lda     $FF
        sta     assignment_pointer+1
        beq     set_variable_done
        jsr     advance_expression_pointer
        lda     assignment_default
        jsr     evaluate_expression
        tax
        lda     assignment_pointer
        sta     $FE
        lda     assignment_pointer+1
        sta     $FF
        ldy     assignment_index
        txa
        sta     ($FE),y

set_variable_done:
        rts

expression_value:
        .byte $00

expression_saved_y:
        .byte $00

expression_saved_x:
        .byte $00

expression_left:
        .byte $00

expression_right:
        .byte $00

expression_operator:
        .byte $00

variable_name_first:
        .byte $00

variable_name_second:
        .byte $00

variable_index:
        .byte $00

; 37 entries: two high-bit name bytes, little-endian address.
; Q/R/Z refer to hardware, so reading a variable can have an I/O side effect.
variable_table:
        .byte ('A' | $80),(' ' | $80) ; A
        .word $6000
        .byte ('B' | $80),(' ' | $80) ; B
        .word $6001
        .byte ('C' | $80),(' ' | $80) ; C
        .word $6002
        .byte ('D' | $80),(' ' | $80) ; D
        .word $6003
        .byte ('E' | $80),(' ' | $80) ; E
        .word $6004
        .byte ('F' | $80),(' ' | $80) ; F
        .word $6005
        .byte ('G' | $80),(' ' | $80) ; G
        .word $6006
        .byte ('H' | $80),(' ' | $80) ; H
        .word $6007
        .byte ('I' | $80),(' ' | $80) ; I
        .word $6008
        .byte ('J' | $80),(' ' | $80) ; J
        .word $6009
        .byte ('K' | $80),(' ' | $80) ; K
        .word $600A
        .byte ('L' | $80),(' ' | $80) ; L
        .word $600B
        .byte ('M' | $80),(' ' | $80) ; M
        .word $600C
        .byte ('N' | $80),(' ' | $80) ; N
        .word $600D
        .byte ('O' | $80),(' ' | $80) ; O
        .word $600E
        .byte ('P' | $80),(' ' | $80) ; P
        .word $600F
        .byte ('Q' | $80),(' ' | $80) ; Q
        .word $C000
        .byte ('R' | $80),(' ' | $80) ; R
        .word $C010
        .byte ('W' | $80),(' ' | $80) ; W
        .word $0205
        .byte ('Z' | $80),(' ' | $80) ; Z
        .word $C061
        .byte ('S' | $80),(' ' | $80) ; S
        .word draw_scale_x
        .byte ('T' | $80),(' ' | $80) ; T
        .word draw_scale_y
        .byte ('X' | $80),(' ' | $80) ; X
        .word draw_origin_x
        .byte ('Y' | $80),(' ' | $80) ; Y
        .word draw_origin_y
        .byte ('U' | $80),(' ' | $80) ; U
        .word draw_layer_count
        .byte ('V' | $80),(' ' | $80) ; V
        .word draw_options
        .byte ('C' | $80),('O' | $80) ; CO
        .word draw_layer_colors
        .byte ('S' | $80),('V' | $80) ; SV
        .word tone_period
        .byte ('G' | $80),('E' | $80) ; GE
        .word $6010
        .byte ('T' | $80),('0' | $80) ; T0
        .word $6020
        .byte ('T' | $80),('1' | $80) ; T1
        .word $611C
        .byte ('T' | $80),('C' | $80) ; TC
        .word $6218
        .byte ('T' | $80),('L' | $80) ; TL
        .word $6314
        .byte ('T' | $80),('V' | $80) ; TV
        .word $6410
        .byte ('N' | $80),('0' | $80) ; N0
        .word $650C
        .byte ('N' | $80),('1' | $80) ; N1
        .word $6608
        .byte ('N' | $80),('V' | $80) ; NV
        .word $6704

; A=default if CR/comma; preserve incoming X/Y; eight-bit one-operator evaluator.
; Operators & / % > < : # + -, postfix ! and ++/--; comparisons return $FF/0.
evaluate_expression:
        sta     expression_value
        sty     expression_saved_y
        stx     expression_saved_x
        ldy     #$00
        jsr     read_expression_character
        bne     read_expression_left
        jmp     return_expression_value

read_expression_left:
        jsr     read_expression_atom
        sta     expression_value
        sta     expression_left
        jsr     read_expression_character
        bne     read_expression_operator
        jmp     return_expression_value

read_expression_operator:
        sta     expression_operator
        jsr     advance_expression_pointer
        cmp     #$A1
        bne     test_increment_decrement
        lda     expression_value
        eor     #$FF
        jmp     restore_expression_registers

test_increment_decrement:
        lda     ($D2),y
        cmp     #$AB
        bne     test_decrement
        inc     expression_value
        jmp     consume_postfix_operator

test_decrement:
        cmp     #('-' | $80)
        bne     read_expression_right
        dec     expression_value
        jmp     consume_postfix_operator

read_expression_right:
        jsr     read_expression_atom
        sta     expression_right
        ldx     expression_left
        lda     expression_operator
        cmp     #$A6
        bne     expression_or
        txa
        and     expression_right
        jmp     restore_expression_registers

expression_or:
        cmp     #$AF
        bne     expression_xor
        txa
        ora     expression_right
        jmp     restore_expression_registers

expression_xor:
        cmp     #$A5
        bne     expression_greater
        txa
        eor     expression_right
        jmp     restore_expression_registers

expression_greater:
        cmp     #$BE
        bne     expression_less
        txa
        cmp     expression_right
        bcc     expression_false
        beq     expression_false
        lda     #$FF
        jmp     restore_expression_registers

expression_false:
        tya
        jmp     restore_expression_registers

expression_less:
        cmp     #$BC
        bne     expression_equal
        txa
        cmp     expression_right
        bcc     expression_less_true
        tya
        jmp     restore_expression_registers

expression_less_true:
        lda     #$FF
        jmp     restore_expression_registers

expression_equal:
        cmp     #$BA
        bne     expression_not_equal
        txa
        cmp     expression_right
        beq     expression_equal_true
        tya
        jmp     restore_expression_registers

expression_equal_true:
        lda     #$FF
        jmp     restore_expression_registers

expression_not_equal:
        cmp     #$A3
        bne     expression_add
        txa
        cmp     expression_right
        beq     expression_not_equal_false
        lda     #$FF
        jmp     restore_expression_registers

expression_not_equal_false:
        tya
        jmp     restore_expression_registers

expression_add:
        cmp     #$AB
        bne     expression_subtract
        txa
        clc
        adc     expression_right
        jmp     restore_expression_registers

expression_subtract:
        cmp     #$AD
        bne     return_expression_value
        txa
        sec
        sbc     expression_right
        jmp     restore_expression_registers

consume_postfix_operator:
        jsr     advance_expression_pointer

return_expression_value:
        lda     expression_value

restore_expression_registers:
        ldx     expression_saved_x
        ldy     expression_saved_y
        rts

; Read current byte and test CR/comma without advancing; Y remains zero.
read_expression_character:
        lda     ($D2),y
        cmp     #$8D
        beq     read_expression_character_at_1554
        cmp     #$AC

read_expression_character_at_1554:
        rts

advance_expression_pointer:
        inc     $D2
        bne     advance_expression_pointer_at_155b
        inc     $D3

advance_expression_pointer_at_155b:
        rts

saved_variable_name:
        .byte $00,$00

; Read variable or up to three decimal digits. Indexed two-character names recurse
; into atom parsing, not a general parenthesized expression. Result A; $FE/$FF
; is last resolved variable address, index at variable_index. No array bounds check.
read_expression_atom:
        lda     ($D2),y
        cmp     #$BA
        bcc     read_decimal_atom
        sta     variable_name_first
        jsr     advance_expression_pointer
        iny
        lda     ($D2),y
        cmp     #$A8
        bne     single_letter_variable
        ldy     #$00
        lda     ($D2),y
        sta     variable_name_second
        jsr     advance_expression_pointer
        jsr     advance_expression_pointer
        lda     variable_name_first
        sta     saved_variable_name
        lda     variable_name_second
        sta     saved_variable_name+1
        jsr     read_expression_atom
        sta     variable_index
        lda     saved_variable_name
        sta     variable_name_first
        lda     saved_variable_name+1
        sta     variable_name_second
        jsr     advance_expression_pointer
        jmp     find_variable

single_letter_variable:
        ldy     #$00
        sty     variable_index
        lda     #$A0
        sta     variable_name_second

find_variable:
        ldx     #$00

compare_variable_name:
        lda     variable_name_first
        cmp     variable_table,x
        bne     next_variable_entry
        lda     variable_name_second
        cmp     variable_table+1,x
        beq     load_variable_address

next_variable_entry:
        inx
        inx
        inx
        inx
        cpx     #$94
        bne     compare_variable_name
        tya
        jmp     atom_done

load_variable_address:
        lda     variable_table+2,x
        sta     $FE
        lda     variable_table+3,x
        sta     $FF
        ldy     variable_index
        lda     ($FE),y
        ldy     #$00

atom_done:
        rts

decimal_input_digits:
        .byte $00,$00,$00

; Scan one to three digits into hundreds/tens/units and advance script PC.
; Native tables support 0..255; larger literals are not a general integer parser.
read_decimal_atom:
        sty     decimal_input_digits
        sty     decimal_input_digits+1
        sty     decimal_input_digits+2
        ldy     #$02

find_decimal_digit_start:
        ldx     #$02

scan_decimal_digit:
        lda     ($D2),y
        sec
        sbc     #$B0
        cmp     #$0A
        bcs     seek_decimal_start
        sta     decimal_input_digits,x
        cpy     #$00
        beq     advance_decimal_atom
        dey
        dex
        jmp     scan_decimal_digit

seek_decimal_start:
        dey
        jmp     find_decimal_digit_start

advance_decimal_atom:
        jsr     advance_expression_pointer
        inx
        cpx     #$03
        bne     advance_decimal_atom
        clc
        ldy     decimal_input_digits
        lda     hundreds_table,y
        ldy     decimal_input_digits+1
        adc     tens_table,y
        adc     decimal_input_digits+2
        ldy     #$00
        rts

hundreds_table:
        .byte $00,$64,$C8

tens_table:
        .byte $00,$0A,$14,$1E,$28,$32,$3C,$46
        .byte $50,$5A

test_select_picture:
        cmp     #('B' | $80)
        beq     select_picture
        jmp     test_load_pictures

; B: find five-byte name in linked records at $9C00, stopping before $AF00 or @.
; Copy origin/scales/options/layer count/colors and retain vector-data pointer.
select_picture:
        lda     #$00
        sta     $FE
        lda     #$9C
        sta     $FF

next_picture_record:
        ldy     #$00

match_picture_name:
        lda     ($D2),y
        cmp     #$C0
        beq     select_picture_done
        cmp     ($FE),y
        beq     read_picture_header
        ldy     #$06
        lda     ($FE),y
        sta     draw_saved_plot_instruction
        dey
        clc
        lda     ($FE),y
        adc     $FE
        sta     $FE
        lda     draw_saved_plot_instruction
        adc     $FF
        sta     $FF
        cmp     #$AF
        bcc     next_picture_record
        jmp     select_picture_done

read_picture_header:
        iny
        cpy     #$05
        bne     match_picture_name
        ldy     #$0C
        lda     ($FE),y
        clc
        adc     #$0D
        sta     $FD
        ldy     #$07

copy_picture_parameters:
        lda     ($FE),y
        sta     draw_stream_pointer+1,y
        iny
        cpy     $FD
        bne     copy_picture_parameters
        clc
        lda     $FE
        adc     $FD
        sta     picture_vectors
        bcc     store_picture_vector_high
        inc     $FF

store_picture_vector_high:
        lda     $FF
        sta     picture_vectors+1

select_picture_done:
        rts

; Mutable graphics workspace: stream pointers, layer index/color, saved plot opcode,
; X/Y origin, S/T scales, V options, U layer count and CO colors. Filename
; scratch/pointer follow at $16E1; all are data, not sequences of BRK instructions.
picture_vectors:
        .byte $00,$00

draw_stream_pointer:
        .byte $00,$00

draw_layer_index:
        .byte $00

draw_layer_color:
        .byte $00

draw_previous_direction:
        .byte $00

draw_saved_plot_instruction:
        .byte $00,$00,$00

draw_origin_x:
        .byte $00

draw_origin_y:
        .byte $00

draw_scale_x:
        .byte $00

draw_scale_y:
        .byte $00

draw_options:
        .byte $00

draw_layer_count:
        .byte $00

draw_layer_colors:
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00

picture_load_separator:
        .byte $00

picture_load_filename:
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00

picture_load_pointer:
        .byte $00,$9C

; Code template copied to loader error path; prompts for game side then retries.
picture_load_error_patch:
        jmp     prompt_for_game_disk
        nop
        nop
        nop
        pla
        pla
        jmp     prompt_for_game_disk
        nop

picture_error_patch_end:
        .byte $00

test_load_pictures:
        cmp     #('L' | $80)
        beq     load_pictures
        jmp     test_draw_picture

; L L,filelist resets collection to $9C00; L N,filelist appends at $67FE/$67FF.
; Ten-character filenames, comma/CR delimiters. Custom loader includes whole sectors.
load_pictures:
        ldy     #$00

install_picture_error_patch:
        lda     picture_load_error_patch,y
        beq     parse_picture_load_mode
        sta     $0BD1,y
        iny
        bne     install_picture_error_patch

parse_picture_load_mode:
        ldy     #$00
        lda     ($D2),y
        tax
        jsr     advance_expression_pointer
        lda     ($D2),y
        cmp     #$AC
        beq     test_picture_load_mode
        jmp     load_pictures_done

test_picture_load_mode:
        txa
        cmp     #$CC
        beq     load_pictures_from_start
        cmp     #$CE
        beq     append_pictures
        jmp     load_pictures_done

load_pictures_from_start:
        lda     #$00
        sta     picture_load_pointer
        lda     #$9C
        sta     picture_load_pointer+1
        jsr     advance_expression_pointer
        jsr     parse_picture_filename
        lda     picture_load_pointer
        sta     $67FE
        lda     picture_load_pointer+1
        sta     $67FF
        jmp     terminate_picture_collection

append_pictures:
        lda     $67FE
        sta     picture_load_pointer
        lda     $67FF
        sta     picture_load_pointer+1
        jsr     advance_expression_pointer
        jsr     parse_picture_filename

terminate_picture_collection:
        lda     $ED
        cmp     #$AF
        beq     load_pictures_done
        bcs     picture_load_overflow
        lda     #$C0
        ldy     #$00
        sta     ($EC),y

load_pictures_done:
        rts

parse_picture_filename:
        lda     #$A0
        ldx     #$00

clear_picture_filename:
        sta     picture_load_filename,x
        inx
        cpx     #$0A
        bne     clear_picture_filename
        ldy     #$00
        ldx     #$00

read_picture_filename:
        jsr     read_expression_character
        beq     picture_filename_done
        jsr     advance_expression_pointer
        inx
        cpx     #$0A
        bcs     read_picture_filename
        sta     picture_load_separator,x
        bcc     read_picture_filename

picture_filename_done:
        sta     picture_load_separator
        lda     picture_load_pointer
        sta     $EC
        lda     picture_load_pointer+1
        sta     $ED

load_picture_file:
        lda     #$E2
        ldx     #$16
        jsr     call_file_loader
        lda     $EC
        sta     picture_load_pointer
        lda     $ED
        sta     picture_load_pointer+1
        lda     picture_load_separator
        cmp     #$8D
        beq     load_picture_file_at_17b9
        jsr     advance_expression_pointer
        jmp     parse_picture_filename

load_picture_file_at_17b9:
        rts

picture_load_overflow:
        lda     #$C2
        ldx     #$17
        jsr     call_string_printer

; Zero guard then high-bit disk-load error message; execution does not fall through.
picture_load_overflow_guard:
        .byte $00

picture_load_overflow_text:
        .byte $D3,$C8,$C1,$D0,$C5,$A0,$CC,$CF
        .byte $C1,$C4,$A0,$C5,$D2,$D2,$CF,$D2
        .byte $8D

call_file_loader:
        jmp     (file_loader_vector)

call_string_printer:
        jmp     (string_printer_vector)

saved_disk_prompt_page:
        .byte $00

; Native loader failure callback: discard two frames, print prompt on both text
; pages, read command then retry file. $601C selects side A/B text.
prompt_for_game_disk:
        pla
        pla
        lda     $0346
        sta     saved_disk_prompt_page
        ldx     #$00
        stx     $0346
        jsr     print_game_disk_prompt
        inx
        stx     $0346
        jsr     print_game_disk_prompt
        lda     saved_disk_prompt_page
        sta     $0346
        jsr     engine_read_command
        jmp     load_picture_file

print_game_disk_prompt:
        jsr     position_disk_message
        lda     #$EA
        ldx     #$1E
        jsr     call_string_printer
        lda     #$13
        ldx     #$1F
        jsr     call_string_printer
        lda     $601C
        cmp     #$02
        bcc     print_game_disk_prompt_at_181c
        lda     #$3D
        ldx     #$1F
        jmp     print_game_disk_prompt_at_181c_at_1820

print_game_disk_prompt_at_181c:
        lda     #$3A
        ldx     #$1F

print_game_disk_prompt_at_181c_at_1820:
        jsr     call_string_printer
        lda     #$41
        ldx     #$1F
        jsr     call_string_printer
        lda     #$69
        ldx     #$1F
        jsr     call_string_printer
        rts

test_draw_picture:
        cmp     #('D' | $80)
        beq     draw_picture
        rts

; D: configure native vector mode, then interpret U color-layer entries.
; High-bit color starts two-byte fill seed; otherwise a packed vector stream.
draw_picture:
        jsr     configure_vector_mode
        lda     picture_vectors
        sta     draw_stream_pointer
        lda     picture_vectors+1
        sta     draw_stream_pointer+1
        lda     draw_scale_x
        sta     $F6
        lda     draw_scale_y
        sta     $F8
        ldy     #$00
        sty     draw_layer_index

next_picture_layer:
        ldy     draw_layer_index
        cpy     draw_layer_count
        bne     read_picture_layer
        rts

read_picture_layer:
        iny
        sty     draw_layer_index
        lda     draw_layer_count,y
        tax
        and     #$7F
        sta     draw_layer_color
        txa
        and     #$80
        beq     draw_vector_layer
        ldy     #$00
        lda     draw_stream_pointer
        sta     $FE
        lda     draw_stream_pointer+1
        sta     $FF
        jsr     transform_vector_origin
        lda     $F3
        sta     $E0
        lda     $F5
        sta     $E1
        clc
        lda     $FE
        adc     #$02
        sta     $FE
        bcc     commit_fill_seed_pointer
        inc     $FF

commit_fill_seed_pointer:
        sta     draw_stream_pointer
        lda     $FF
        sta     draw_stream_pointer+1
        lda     draw_layer_color
        sta     $E8
        jsr     flood_fill
        jmp     next_picture_layer

draw_vector_layer:
        ldy     #$00
        lda     plot_pixel_instruction
        sta     draw_saved_plot_instruction
        lda     plot_pixel_instruction+1
        sta     draw_saved_plot_instruction+1
        lda     plot_pixel_instruction+2
        sta     draw_saved_plot_instruction+2
        lda     draw_stream_pointer
        sta     $FE
        lda     draw_stream_pointer+1
        sta     $FF
        jsr     draw_vector_stream
        lda     draw_layer_color
        cmp     #$7F
        beq     commit_vector_pointer
        sta     $E8
        lda     draw_stream_pointer
        sta     $FE
        lda     draw_stream_pointer+1
        sta     $FF
        jsr     configure_fill_pattern
        lda     #$4C
        sta     plot_pixel_instruction
        lda     #$F0
        sta     plot_pixel_instruction+1
        lda     #$1A
        sta     plot_pixel_instruction+2
        jsr     draw_vector_stream

commit_vector_pointer:
        lda     $FE
        sta     draw_stream_pointer
        lda     $FF
        sta     draw_stream_pointer+1
        lda     draw_saved_plot_instruction
        sta     plot_pixel_instruction
        lda     draw_saved_plot_instruction+1
        sta     plot_pixel_instruction+1
        lda     draw_saved_plot_instruction+2
        sta     plot_pixel_instruction+2
        jmp     next_picture_layer

; V option bits patch drawing instructions: bit0 display page, bit1 target page,
; bit2 OR-vs-AND plotting, bit3 scaled stepping, bit5 swaps horizontal directions.
; Instruction bytes/operands below are intentionally writable, not data boundaries.
configure_vector_mode:
        lda     draw_options
        sta     $B0
        and     #$01
        tax
        lda     $C054,x
        ldx     #$B2
        lda     $B0
        and     #$02
        bne     patch_scanline_page
        ldx     #$B1

patch_scanline_page:
        stx     plot_scanline_high+2
        stx     fill_seed_scanline_high+2
        stx     fill_scanline_high+2
        lda     $B0
        and     #$04
        beq     plot_replace_mode
        lda     #$5D
        ldy     #$64
        ldx     #$11
        bne     patch_plot_operator

plot_replace_mode:
        lda     #$4F
        ldy     #$56
        ldx     #$31

patch_plot_operator:
        sta     plot_pixel_instruction+1
        sty     plot_next_pixel_instruction+1
        stx     plot_pixel_operator
        stx     plot_next_pixel_operator
        lda     $B0
        and     #$08
        beq     unit_direction_mode
        ldy     #$1F
        ldx     #$EC
        lda     $B0
        and     #$20
        bne     patch_scaled_directions
        ldy     #$0E
        ldx     #$0E

patch_scaled_directions:
        sty     scaled_direction_zero_branch+1
        sty     scaled_direction_one_branch+1
        stx     scaled_direction_two_branch+1
        ldx     #$4C
        ldy     #$1A
        jmp     patch_vector_step_calls

unit_direction_mode:
        ldy     #$E6
        ldx     #$C6
        lda     $B0
        and     #$20
        bne     patch_unit_directions
        ldy     #$C6
        ldx     #$E6

patch_unit_directions:
        sty     unit_step_left
        stx     unit_step_right
        ldx     #$9D
        ldy     #$1A

patch_vector_step_calls:
        stx     vector_step_call_one+1
        stx     vector_step_call_two+1
        stx     vector_step_call_three+1
        sty     vector_step_call_one+2
        sty     vector_step_call_two+2
        sty     vector_step_call_three+2
        rts

; Clear fixed-point fractions/direction, transform origin, load byte-count-minus-one.
; Packed bytes contain two 3-bit steps and optional nonzero top 2-bit third step.
draw_vector_stream:
        ldy     #$00
        sty     $F2
        sty     $F4
        sty     $F7
        sty     $F9
        sty     draw_previous_direction
        jsr     transform_vector_origin
        iny
        lda     ($FE),y
        sta     $B1
        iny
        lda     ($FE),y
        sta     $B2
        lda     draw_scale_x
        sta     $F6
        lda     draw_scale_y
        sta     $F8
        jmp     skip_vector_header

transform_vector_origin:
        lda     ($FE),y
        sta     $F3
        iny
        lda     ($FE),y
        sta     $F5
        lda     $B0
        and     #$08
        beq     translate_vector_origin
        lda     $F6
        sta     $E2
        lda     #$00
        ldx     #$07

scale_origin_x:
        lsr     $F3
        asl     $E2
        bcc     scale_origin_x_tick
        clc
        adc     $F3

scale_origin_x_tick:
        dex
        bne     scale_origin_x
        sta     $F3
        lda     $F8
        sta     $E2
        lda     #$00
        ldx     #$07

scale_origin_y:
        lsr     $F5
        asl     $E2
        bcc     scale_origin_y_tick
        clc
        adc     $F5

scale_origin_y_tick:
        dex
        bne     scale_origin_y
        sta     $F5

translate_vector_origin:
        lda     $F3
        clc
        adc     draw_origin_x
        sta     $F3
        lda     $F5
        clc
        adc     draw_origin_y
        sta     $F5
        rts

skip_vector_header:
        ldy     #$00
        clc
        lda     #$04
        adc     $FE
        sta     $FE
        bcc     read_packed_vector
        inc     $FF

; Bits 0..2 first, 3..5 second, 6..7 third if nonzero; bit2 means move without plot.
; Direction low2: up, right, left, down. Plot occurs before movement.
read_packed_vector:
        lda     ($FE),y
        pha
        and     #$07

vector_step_call_one:
        jsr     scaled_vector_step
        pla
        lsr     a
        lsr     a
        lsr     a
        pha
        and     #$07

vector_step_call_two:
        jsr     scaled_vector_step
        pla
        lsr     a
        lsr     a
        lsr     a
        beq     advance_vector_byte

vector_step_call_three:
        jsr     scaled_vector_step

advance_vector_byte:
        inc     $FE
        bne     vector_count_tick
        inc     $FF

vector_count_tick:
        dec     $B1
        lda     $B1
        cmp     #$FF
        bne     read_packed_vector
        dec     $B2
        lda     $B2
        cmp     #$FF
        bne     read_packed_vector
        rts

; Use fixed-point x/y fractions ($F2/$F4) and integer positions ($F3/$F5).
; Patched branch displacements choose alternate scale direction behavior.
scaled_vector_step:
        sta     $E2
        and     #$04
        bne     scaled_vector_direction
        jsr     plot_vector_pixel

scaled_vector_direction:
        lda     $E2
        and     #$03
        sta     draw_previous_direction
        tax

scaled_direction_zero_branch:
        bne     scaled_direction_zero_branch_at_1a6d
        sec
        lda     $F4
        sbc     $F8
        sta     $F4
        lda     $F5
        sbc     $F9
        sta     $F5
        rts

scaled_direction_zero_branch_at_1a6d:
        dex

scaled_direction_one_branch:
        bne     scaled_direction_one_branch_at_1a7e
        clc
        lda     $F2
        adc     $F6
        sta     $F2
        lda     $F3
        adc     $F7
        sta     $F3
        rts

scaled_direction_one_branch_at_1a7e:
        dex

scaled_direction_two_branch:
        bne     scaled_direction_two_branch_at_1a8f
        sec
        lda     $F2
        sbc     $F6
        sta     $F2
        lda     $F3
        sbc     $F7
        sta     $F3
        rts

scaled_direction_two_branch_at_1a8f:
        clc
        lda     $F4
        adc     $F8
        sta     $F4
        lda     $F5
        adc     $F9
        sta     $F5
        rts

; Unit steps alter integer coordinates directly; move-only bit suppresses plotting.
unit_vector_step:
        sta     $E2
        and     #$04
        bne     unit_vector_direction
        jsr     plot_vector_pixel

unit_vector_direction:
        lda     $E2
        and     #$03
        sta     draw_previous_direction
        tax
        bne     unit_direction_one
        dec     $F5
        rts

unit_direction_one:
        dex
        bne     unit_direction_two

unit_step_right:
        inc     $F3
        rts

unit_direction_two:
        dex
        bne     unit_step_down

unit_step_left:
        dec     $F3
        rts

unit_step_down:
        inc     $F5
        rts

; Scanline lookup plus x-to-byte/bit tables at $AF00. Two-byte mask changes phase.
; This routine is patched into an edge-fill callback during vector filling.
plot_vector_pixel:
        ldx     $F5
        lda     $B000,x
        sta     $E4

plot_scanline_high:
        lda     $B100,x
        sta     $E5
        ldx     $F3
        lda     $AF00,x
        tay
        and     #$07
        tax
        tya
        lsr     a
        lsr     a
        lsr     a
        asl     a
        tay

; Native LDA mask,X is temporarily replaced by JMP fill_vector_edge ($1AF0).
plot_pixel_instruction:
        lda     pixel_clear_masks,x

plot_pixel_operator:
        and     ($E4),y
        sta     ($E4),y
        iny

plot_next_pixel_instruction:
        lda     pixel_clear_masks_next,x

plot_next_pixel_operator:
        and     ($E4),y
        sta     ($E4),y
        ldy     #$00
        rts

fill_saved_phase:
        .byte $00

; Color vector pass changes edge bits and fills boundary spans with selected pattern.
fill_vector_edge:
        lda     draw_previous_direction
        cmp     #$03
        beq     test_fill_edge_direction
        cmp     #$02
        bne     fill_edge_done
        lda     $E2
        cmp     #$03
        bne     fill_edge_done

test_fill_edge_direction:
        txa
        and     #$04
        beq     fill_edge_previous_byte
        iny
        jmp     fill_edge_pattern

fill_edge_previous_byte:
        txa
        bne     fill_edge_pattern
        dey
        ldx     #$07

fill_edge_pattern:
        sty     $E3
        lda     fill_bit_order,x
        tax
        lda     $F5
        ror     a
        bcc     fill_edge_even_pattern
        lda     ($EB),y
        bne     fill_edge_phase

fill_edge_even_pattern:
        lda     ($E9),y

fill_edge_phase:
        sta     $E7
        and     #$80
        sta     fill_saved_phase
        lda     ($E4),y
        and     #$7F
        ora     fill_saved_phase
        sta     ($E4),y

fill_edge_bits:
        lda     ($E4),y
        and     pixel_bit_masks,x
        beq     fill_edge_done
        and     $E7
        bne     fill_edge_next_bit
        lda     pixel_bit_masks,x
        eor     ($E4),y
        sta     ($E4),y

fill_edge_next_bit:
        dex
        bpl     fill_edge_bits
        asl     fill_direction_mask
        jsr     fill_scan_left_begin

fill_edge_done:
        ldy     #$00
        rts

pixel_clear_masks:
        .byte $FC,$F3,$CF,$BF,$FF,$FF,$FF

pixel_clear_masks_next:
        .byte $FF,$FF,$FF,$FE,$F9,$E7,$9F

pixel_clear_masks_padding:
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte $FF,$FF,$FF,$FF,$FF,$FF

fill_bit_order:
        .byte $00,$01,$03,$05,$00,$02,$04,$06

pixel_bit_masks:
        .byte $01,$02,$04,$08,$10,$20,$40,$80

; Seed-based scan fill: walk right/left then successive rows; $FF marks fillable bytes.
; Preserves native partial-byte/phase handling; not a general host flood-fill algorithm.
flood_fill:
        jsr     configure_fill_seed

flood_fill_at_1b7e:
        ldy     $E3
        lda     ($E4),y
        cmp     #$FF
        bne     fill_seed_partial
        lda     $F5
        ror     a
        bcc     fill_seed_even_pattern
        lda     ($EB),y
        bne     fill_seed_store_pattern

fill_seed_even_pattern:
        lda     ($E9),y

fill_seed_store_pattern:
        sta     ($E4),y
        bne     fill_scan_right_begin

fill_seed_partial:
        sta     $E6
        ror     a

fill_seed_phase_branch:
        bcc     fill_seed_phase_branch_at_1b9f
        asl     fill_direction_mask
        bmi     fill_seed_phase_branch_at_1b9f_at_1ba4

fill_seed_phase_branch_at_1b9f:
        rol     a
        rol     a
        rol     a
        bcc     fill_seed_done

fill_seed_phase_branch_at_1b9f_at_1ba4:
        lda     $E6
        jsr     fill_partial_byte

fill_seed_done:
        jmp     fill_done

fill_direction_mask:
        .byte $E0

fill_scan_right_begin:
        asl     fill_direction_mask

fill_scan_right:
        inc     $E3
        ldy     $E3
        cpy     #$28
        bcc     fill_right_byte
        bcs     fill_begin_left

fill_right_byte:
        lda     ($E4),y
        cmp     #$FF
        bne     fill_right_partial
        lda     $F5
        ror     a
        bcc     fill_right_even_pattern
        lda     ($EB),y
        bne     fill_right_store

fill_right_even_pattern:
        lda     ($E9),y

fill_right_store:
        sta     ($E4),y
        jmp     fill_scan_right

fill_right_partial:
        jsr     fill_partial_byte

fill_begin_left:
        lda     $E0
        sta     $E3
        jsr     fill_scan_left_begin
        jmp     fill_next_scanline

fill_scan_left_begin:
        lsr     fill_direction_mask

fill_scan_left:
        dec     $E3
        bpl     fill_left_byte
        bmi     fill_scan_done

fill_left_byte:
        ldy     $E3
        lda     ($E4),y
        cmp     #$FF
        bne     fill_left_partial
        lda     $F5
        ror     a
        bcc     fill_left_even_pattern
        lda     ($EB),y
        bne     fill_left_store

fill_left_even_pattern:
        lda     ($E9),y

fill_left_store:
        sta     ($E4),y
        jmp     fill_scan_left

fill_left_partial:
        jsr     fill_partial_byte

fill_scan_done:
        rts

fill_next_scanline:
        lda     $E0
        sta     $E3
        inc     $F5
        lda     $F5
        cmp     #$C0
        bcc     fill_next_scanline_address
        jmp     fill_done

fill_next_scanline_address:
        ldy     $F5
        lda     $B000,y
        sta     $E4

fill_scanline_high:
        lda     $B100,y
        sta     $E5
        jmp     flood_fill_at_1b7e

fill_done:
        rts

configure_fill_seed:
        lda     $E0
        sta     $E3
        lda     $E1
        sta     $F5
        jsr     set_fill_scanline_pointer

configure_fill_pattern:
        lda     #$40
        sta     fill_direction_mask
        jsr     select_fill_pattern
        rts

; CO values 0..5 select solid pattern/phase, 16..95 alternate two color nibbles,
; >=96 select native textured patterns. Higher values fall into final texture case.
select_fill_pattern:
        lda     $E8
        cmp     #$60
        bcc     select_solid_or_alternating
        jsr     select_texture_pattern
        rts

select_solid_or_alternating:
        cmp     #$10
        bcs     select_alternating_pattern
        jsr     select_solid_pattern
        sty     $E9
        sty     $EB
        sta     $EA
        sta     $EC
        rts

select_alternating_pattern:
        pha
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        jsr     select_solid_pattern
        sty     $E9
        sta     $EA
        pla
        and     #$0F
        jsr     select_solid_pattern
        sty     $EB
        sta     $EC
        rts

select_solid_pattern:
        cmp     #$05
        bcc     solid_pattern_four
        ldy     #$C1
        lda     #$1E
        bne     solid_pattern_done

solid_pattern_four:
        cmp     #$04
        bcc     solid_pattern_three
        ldy     #$98
        lda     #$1E
        bne     solid_pattern_done

solid_pattern_three:
        cmp     #$03
        bcc     solid_pattern_two
        ldy     #$6F
        lda     #$1E
        bne     solid_pattern_odd_offset

solid_pattern_two:
        cmp     #$02
        bcc     solid_pattern_one
        ldy     #$6F
        lda     #$1E
        bne     solid_pattern_done

solid_pattern_one:
        cmp     #$01
        bcc     solid_pattern_zero
        ldy     #$46
        lda     #$1E
        bne     solid_pattern_odd_offset

solid_pattern_zero:
        ldy     #$46
        lda     #$1E
        bne     solid_pattern_done

solid_pattern_odd_offset:
        iny

solid_pattern_done:
        rts

select_texture_pattern:
        cmp     #$62
        bcs     texture_pattern_two
        ldy     #$6F
        ldx     #$1D
        jsr     texture_normal_rows
        rts

texture_pattern_two:
        cmp     #$64
        bcs     texture_pattern_three
        ldy     #$9A
        ldx     #$1D
        jsr     texture_normal_rows
        rts

texture_pattern_three:
        cmp     #$66
        bcs     texture_pattern_four
        ldy     #$C5
        ldx     #$1D
        jsr     texture_swapped_rows
        rts

texture_pattern_four:
        cmp     #$68
        bcs     texture_pattern_five
        ldy     #$F0
        ldx     #$1D
        jsr     texture_swapped_rows
        rts

texture_pattern_five:
        ldy     #$1B
        ldx     #$1E
        jsr     texture_normal_rows
        rts

texture_normal_rows:
        ror     a
        bcc     texture_even_row_pointer
        iny
        sty     $E9
        bne     texture_odd_row_pointer
        inx
        bne     texture_odd_row_pointer

texture_even_row_pointer:
        sty     $E9

texture_odd_row_pointer:
        stx     $EA
        clc
        iny
        iny
        sty     $EB
        bcc     texture_store_odd_high
        inx

texture_store_odd_high:
        stx     $EC
        rts

texture_swapped_rows:
        ror     a
        bcc     texture_swapped_even_row
        iny
        sty     $EB
        bne     texture_store_odd_row
        inx

texture_store_odd_row:
        stx     $EC
        clc
        iny
        iny
        sty     $E9
        bcc     texture_store_even_high
        inx

texture_store_even_high:
        stx     $EA
        jmp     texture_done

texture_swapped_even_row:
        sty     $E9
        stx     $EA
        clc
        iny
        iny
        sty     $EB
        bcc     texture_swapped_odd_high
        inx

texture_swapped_odd_high:
        stx     $EC

texture_done:
        rts

set_fill_scanline_pointer:
        ldy     $F5
        lda     $B000,y
        sta     $E4

fill_seed_scanline_high:
        lda     $B100,y
        sta     $E5
        rts

fill_partial_byte:
        ora     #$80
        sta     $E6
        ldx     #$00
        bit     fill_direction_mask
        bmi     fill_count_left_bits
        clc
        rol     a

fill_count_right_bits:
        rol     a
        bcc     fill_right_mask
        inx
        bne     fill_count_right_bits

fill_right_mask:
        lda     fill_right_masks,x
        jmp     fill_merge_mask

fill_count_left_bits:
        clc

fill_left_bit_loop:
        ror     a
        bcc     fill_left_mask
        inx
        bne     fill_left_bit_loop

fill_left_mask:
        lda     fill_left_masks,x

fill_merge_mask:
        pha
        lda     $F5
        ror     a
        bcc     fill_partial_even_pattern
        lda     ($EB),y
        bne     fill_partial_merge

fill_partial_even_pattern:
        lda     ($E9),y

fill_partial_merge:
        sta     $E7
        pla
        ora     $E7
        and     $E6
        sta     ($E4),y
        rts

; Left/right partial-byte masks, then five 43-byte texture and four 41-byte solid patterns.
fill_left_masks:
        .byte $7F,$7E,$7C,$78,$70,$60,$40,$00

fill_right_masks:
        .byte $7F,$3F,$1F,$0F,$07,$03,$01,$00

texture_pattern_1:
        .byte $44,$08,$11,$22,$44,$08,$11,$22
        .byte $44,$08,$11,$22,$44,$08,$11,$22
        .byte $44,$08,$11,$22,$44,$08,$11,$22
        .byte $44,$08,$11,$22,$44,$08,$11,$22
        .byte $44,$08,$11,$22,$44,$08,$11,$22
        .byte $44,$08,$11

texture_pattern_2:
        .byte $C4,$88,$91,$A2,$C4,$88,$91,$A2
        .byte $C4,$88,$91,$A2,$C4,$88,$91,$A2
        .byte $C4,$88,$91,$A2,$C4,$88,$91,$A2
        .byte $C4,$88,$91,$A2,$C4,$88,$91,$A2
        .byte $C4,$88,$91,$A2,$C4,$88,$91,$A2
        .byte $C4,$88,$91

texture_pattern_3:
        .byte $77,$6E,$5D,$3B,$77,$6E,$5D,$3B
        .byte $77,$6E,$5D,$3B,$77,$6E,$5D,$3B
        .byte $77,$6E,$5D,$3B,$77,$6E,$5D,$3B
        .byte $77,$6E,$5D,$3B,$77,$6E,$5D,$3B
        .byte $77,$6E,$5D,$3B,$77,$6E,$5D,$3B
        .byte $77,$6E,$5D

texture_pattern_4:
        .byte $F7,$EE,$DD,$BB,$F7,$EE,$DD,$BB
        .byte $F7,$EE,$DD,$BB,$F7,$EE,$DD,$BB
        .byte $F7,$EE,$DD,$BB,$F7,$EE,$DD,$BB
        .byte $F7,$EE,$DD,$BB,$F7,$EE,$DD,$BB
        .byte $F7,$EE,$DD,$BB,$F7,$EE,$DD,$BB
        .byte $F7,$EE,$DD

texture_pattern_5:
        .byte $CC,$99,$B3,$E6,$CC,$99,$B3,$E6
        .byte $CC,$99,$B3,$E6,$CC,$99,$B3,$E6
        .byte $CC,$99,$B3,$E6,$CC,$99,$B3,$E6
        .byte $CC,$99,$B3,$E6,$CC,$99,$B3,$E6
        .byte $CC,$99,$B3,$E6,$CC,$99,$B3,$E6
        .byte $CC,$99,$B3

solid_pattern_0:
        .byte $55,$2A,$55,$2A,$55,$2A,$55,$2A
        .byte $55,$2A,$55,$2A,$55,$2A,$55,$2A
        .byte $55,$2A,$55,$2A,$55,$2A,$55,$2A
        .byte $55,$2A,$55,$2A,$55,$2A,$55,$2A
        .byte $55,$2A,$55,$2A,$55,$2A,$55,$2A
        .byte $55

solid_pattern_1:
        .byte $D5,$AA,$D5,$AA,$D5,$AA,$D5,$AA
        .byte $D5,$AA,$D5,$AA,$D5,$AA,$D5,$AA
        .byte $D5,$AA,$D5,$AA,$D5,$AA,$D5,$AA
        .byte $D5,$AA,$D5,$AA,$D5,$AA,$D5,$AA
        .byte $D5,$AA,$D5,$AA,$D5,$AA,$D5,$AA
        .byte $D5

solid_pattern_2:
        .byte $80,$80,$80,$80,$80,$80,$80,$80
        .byte $80,$80,$80,$80,$80,$80,$80,$80
        .byte $80,$80,$80,$80,$80,$80,$80,$80
        .byte $80,$80,$80,$80,$80,$80,$80,$80
        .byte $80,$80,$80,$80,$80,$80,$80,$80
        .byte $80

solid_pattern_3:
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
        .byte $FF

; High-bit native error, media-insertion, side-letter and RETURN prompt strings.
disk_action_error_text:
        .byte $C5,$F2,$F2,$EF,$F2,$A0,$E4,$F5
        .byte $F2,$E9,$EE,$E7,$A0,$E4,$E9,$F3
        .byte $EB,$A0,$E1,$E3,$F4,$E9,$EF,$EE
        .byte $A1,$A1,$A0,$A0,$A0,$A0,$A0,$A0
        .byte $A0,$A0,$A0,$A0,$A0,$A0,$A0,$8D
        .byte $EA

game_disk_prompt_text:
        .byte $D0,$EC,$E1,$E3,$E5,$A0,$D4,$C8
        .byte $C5,$A0,$CD,$C1,$D3,$CB,$A0,$CF
        .byte $C6,$A0,$D4,$C8,$C5,$A0,$D3,$D5
        .byte $CE,$A0,$E4,$E9,$F3,$EB,$AC,$A0
        .byte $F3,$E9,$E4,$E5,$A0,$BB,$8D

disk_side_a_text:
        .byte $C1,$A0,$8D

disk_side_b_text:
        .byte $C2,$A0,$8D,$EA

drive_prompt_text:
        .byte $E9,$EE,$F4,$EF,$A0,$C4,$F2,$E9
        .byte $F6,$E5,$A0,$A3,$B1,$A0,$E1,$EE
        .byte $E4,$A0,$F0,$F2,$E5,$F3,$F3,$A0
        .byte $D2,$C5,$D4,$D5,$D2,$CE,$AE,$A0
        .byte $A0,$A0,$A0,$A0,$A0,$A0,$A0,$8D

disk_prompt_ok_text:
        .byte $CF,$CB,$BE,$BB,$8D

; Residual signature/control bytes followed by zero padding; no code targets.
; Whole-sector loader also reads allocated file tail after this nominal payload.
legacy_signature_data:
        .ifdef KOREAN
        .include "korean/restore-guard.inc"
        .else
        .byte $55,$4D,$45,$53,$45,$00,$00,$90
        .byte $6F,$00,$02,$48,$9F,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        .byte $00,$00
        .endif
.assert dispatch_intrinsic = $0D00, error, "intrinsic entry moved"
.assert variable_table = $13CC, error, "variable table moved"
.assert save_game = $122C, error, "save entry moved"
.assert draw_picture = $1837, error, "picture renderer moved"
.assert * = $2000, error, "native intrinsic payload must occupy $1300 bytes"

.segment "INTRINSICS_TAIL"
; Allocated final-sector residue: $AD then 251 zero bytes. Never a code entry.
        .byte $AD
        .res $FB,0
.assert * = $20FC, error, "full allocated intrinsic stream must occupy 20 sectors"
