; Candidate save header and post-restore cache reload. Main extension code may
; run only before or after the native snapshot transfer completes successfully.
.setcpu "6502"
.segment "CODE"
.export ko_save_prepare, ko_save_finish, ko_restore_finish
ko_save_prepare:
        lda #0                  ; invalidate old commit before first snapshot write
        beq ko_save_header
ko_save_finish:
        lda #1                  ; publish build identity only after all 144 pages
ko_save_header:
        sta ko_save_commit
ko_save_header_retry:
        lda #0
        tax
ko_clear_header:
        sta $0700,x
        inx
        bne ko_clear_header
        lda ko_save_commit
        beq ko_write_header
        ldx #15
ko_copy_save_id:
        lda ko_native_save_id,x
        sta $0700,x
        dex
        bpl ko_copy_save_id
ko_write_header:
        lda #0
        sta $0bb3
        lda #7
        sta $0bb4
        lda #22
        sta $0baf
        lda #15
        sta $0bb0
        lda #2
        sta $0bb7
        lda #$0b
        ldy #$ab
        jsr $bd00
        bcc ko_save_return
        lda #<ko_save_prompt
        ldx #>ko_save_prompt
        jsr ko_prompt_media
        jmp ko_save_header_retry
ko_save_return:
        rts
ko_restore_finish:
        lda #0
        sta ko_room_size
        sta ko_room_size+1
        ; Snapshot restored the current package name, but LC's room pool belongs
        ; to the pre-restore room. Reload only its pool, preserving script macros.
ko_restore_pool_retry:
        jsr ko_select_game_media
        jsr ko_prompt_media
        lda #0
        sta $ec
        lda #$68
        sta $ed
        lda #<ko_retry_name
        ldx #>ko_retry_name
        jsr ko_load_pool
        bcc ko_restore_pool_retry
        rts
ko_prompt_media:
        pha
        .ifdef KOREAN_NATIVE_UI
        jsr ko_clear_message_rows
        .else
        lda #0
        sta $24
        lda #12
        sta $25
        .endif
        pla
        .ifdef KOREAN_NATIVE_UI
        jsr ko_print_script_string
        .else
        jsr ko_native_print_script_string
        .endif
ko_save_wait:
        lda $c000
        bpl ko_save_wait
        bit $c010
        cmp #$8d
        bne ko_save_wait
        rts
ko_save_commit: .byte 0
ko_save_prompt: .byte $c9,$ce,$d3,$c5,$d2,$d4,$a0,$c5,$d8,$d4,$d2,$c1,$a0,$c4,$c9,$d3,$cb,$ac,$a0,$d0,$d2,$c5,$d3,$d3,$a0,$d2,$c5,$d4,$d5,$d2,$ce,$ae,$8d
