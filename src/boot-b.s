; Side B track0/sector0: fails boot with BOOT OTHER SIDE.
; Page-count byte is zero in the supplied crack. Executable entry is $0801.
        .setcpu "6502"
        .segment "BOOT"
boot_sector:
        .byte 0
wrong_side_entry:
        ldx #0
print_wrong_side_message:
        lda wrong_side_message,x
wrong_side_halt: ; BEQ -2 loops on itself at $0806 when the terminator is reached
        beq wrong_side_halt
        jsr $fdf0 ; firmware output
        inx
        bne print_wrong_side_message
        .byte 0,0 ; gap before the message, not executed
wrong_side_message:
        .byte $c2,$cf,$cf,$d4,$a0,$cf,$d4,$c8,$c5,$d2,$a0,$d3,$c9,$c4,$c5,$ae,0
        .res $100-(*-boot_sector),0
.assert wrong_side_message=$0810,error,"wrong-side message address"
.assert *-boot_sector=$100,error,"boot sector must be 256 bytes"
