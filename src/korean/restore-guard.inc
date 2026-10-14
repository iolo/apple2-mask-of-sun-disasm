; Linked into INTRIN's old 146-byte residue at $1F6E, outside raw save RAM.
; Never calls the snapshot-resident extension. Retry resets the stack to the
; restore intrinsic's caller and rechecks the save identifier before all pages.
ko_restore_guard:
        tsx
        inx
        inx
        stx ko_restore_stack
        lda #1
        sta $0bb7
        lda #0
        sta $0bb3
        lda #7
        sta $0bb4
        lda #22
        sta $0baf
        lda #15
        sta $0bb0
        lda #$0b
        ldy #$ab
        jsr $bd00
        bcs ko_restore_failed
        ldx #15
ko_check_save_id:
        lda $0700,x
        cmp ko_save_id,x
        bne ko_restore_failed
        dex
        bpl ko_check_save_id
        rts
ko_snapshot_error_guard:
        lda $0bb7
        cmp #1
        beq ko_restore_failed
        jmp position_disk_message
ko_restore_failed:
        ldx ko_restore_stack
        txs
        jsr position_disk_message
        lda #<ko_restore_error_text
        ldx #>ko_restore_error_text
        jsr $0bf3               ; original ASCII printer; extension may be corrupt
ko_restore_wait:
        lda $c000
        bpl ko_restore_wait
        bit $c010
        cmp #$8d
        bne ko_restore_wait
        jmp restore_game
ko_restore_stack: .byte 0
ko_restore_error_text:
        .byte $d2,$c5,$d3,$d4,$cf,$d2,$c5,$a0,$c5,$d2,$d2,$cf,$d2,$ae,$a0,$d2,$c5,$d4,$d2,$d9,$ba,$a0,$d2,$c5,$d4,$d5,$d2,$ce,$8d
.assert * <= $1ff0, error, "restore guard overlaps identifier"
        .res $82-(*-ko_restore_guard),0
ko_save_id:
        .include "save-id.inc"
.assert * <= $2000, error, "restore guard exceeds preserved intrinsic space"
        .res 16-(*-ko_save_id),0
