; Native side-A DOS startup, command processor and file manager, $9B00-$B5FF.
; Disassembled from supplied native sectors, with explicit code/data boundaries.
; See docs/dos.md for interfaces, provenance and symbols.
        .setcpu "6502"

rom_output_vector:= $0036
rom_input_vector:= $0038
sector_buffer   := $003E
ram_applesoft_clear:= $0E65
ram_applesoft_run:= $0FD4
dos_load_and_clear_buffer:= $B65E
dos_resume_input:= $B66B
dos_advance_file_position:= $B671
dos_clear_pending_read:= $B67E
dos_process_saved_character:= $B686
dos_copy_file_position:= $B692
resume_dos_file_manager:= $B6A9
dos_mark_pending_read:= $B6AC
boot_reload_dos := $B744
reload_dos_pages:= $B74A
call_rwts_interrupt_masked:= $B7B5
prepare_dos_file_iob:= $B7C2
clear_dos_page  := $B7D6
native_initialize_stub:= $BA6D
rwts_entry      := $BD00
dos_reset_file_selection:= $BFDC
dos_close_from_exec:= $BFE6
dos_close_with_stack_recovery:= $BFED
dos_doslim      := $C000
rom_applesoft_clear:= $D665
rom_applesoft_run:= $D7D2
rom_reset       := $FA59
rom_text_mode   := $FB2F
rom_home        := $FC58
rom_read_key    := $FD0C
rom_print_hex_byte:= $FDDA
rom_cout        := $FDED
rom_keyboard_select:= $FE89
rom_input_select:= $FE8B
rom_set_video   := $FE93
rom_output_select:= $FE95
rom_iorts       := $FF58
rom_monitor     := $FF65

.segment        "DOSLOW": absolute

; $9B00..$9CFF: cleared relocation workspace, not executable BRK padding.
cleared_relocation_workspace:
        .res $100,0
cleared_relocation_workspace_page2:
        .res $100,0
; $9D00: eight public pointers; native DOS-start pointer is $9D00. Mutable.
dos_address_table:
        .word $9CD3
dos_adinptcp:
        .word dos_input_intercept
dos_adoputcp:
        .word dos_output_intercept
dos_adrpfnbf:
        .word dos_primary_filename
dos_adrsfnbf:
        .word dos_secondary_filename
dos_adlenadr:
        .word dos_lenadrbf
dos_adostart:
        .word dos_address_table
dos_adfmparm:
        .word dos_file_parameters
; Seven entry-minus-one vectors, dispatched by pushing high/low then RTS.
dos_output_handler_table:
        .word dos_oputhdl0-1
        .word dos_oputhdl1-1
        .word dos_oputhdl2-1
        .word dos_oputhdl3-1
        .word dos_oputhdl4-1
        .word dos_oputhdl5-1
        .word dos_oputhdl6-1
; 28 entry-minus-one command vectors; order matches dos_cmdtxtbl.
dos_command_table:
        .word dos_command_init-1
        .word dos_command_load-1
        .word dos_command_save-1
        .word dos_command_run-1
        .word dos_command_chain-1
        .word dos_command_delete-1
        .word dos_command_lock-1
        .word dos_command_unlock-1
        .word dos_command_close-1
        .word dos_command_read-1
        .word dos_command_exec-1
        .word dos_command_write-1
        .word dos_command_position-1
        .word dos_command_open-1
        .word dos_command_append-1
        .word dos_command_rename-1
        .word dos_command_catalog-1
        .word dos_command_mon-1
        .word dos_command_nommon-1
        .word dos_cmdpr-1
        .word dos_cmdin-1
        .word dos_command_maxfiles-1
        .word dos_command_fp-1
        .word dos_command_int-1
        .word dos_command_bsave-1
        .word dos_command_bload-1
        .word dos_command_brun-1
        .word dos_command_verify-1
; Active BASIC entry vectors, initialized for ROM Applesoft in this copy.
dos_active_basic_vectors:
        .word dos_runfprom
dos_runtry:
        .word dos_runfprom
dos_adbscerr:
        .word $D865
dos_tocldvec:
        .word $E000
dos_towrmvec:
        .word $D43C
dos_rlocntry:
        .word $D4F2
dos_integer_basic_vectors:
        .word $E836
        .word dos_runintgr
        .word $E3E3
        .word $E000
        .word $E003
dos_rom_applesoft_vectors:
        .word dos_runfprom
        .word dos_runfprom
        .word $D865
        .word $E000
        .word $D43C
        .word $D4F2
dos_ram_applesoft_vectors:
        .word dos_fpramrun
        .word dos_fpramrun
        .word $1067
        .word dos_cold_start
        .word $0C3C
        .word $0CF2
; $9D84: select BASIC from ROM, install hooks/vectors, initialize buffers and EXEC START.
; Uses ROM/DOS zero page and A/X/Y; does not preserve caller registers.
dos_cold_start:
        lda     $B7E9
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     dos_slotprsd
        lda     $B7EA
        sta     dos_drvprsd
        lda     $E000
        eor     #$20
        bne     dos_isfprom
dos_isint:
        sta     dos_actbsflg
        ldx     #$0A
dos_int2bsic:
        lda     dos_rlocntry+1,x
        sta     dos_command_table+55,x
        dex
        bne     dos_int2bsic
        jmp     dos_bypaswrm

dos_isfprom:
        lda     #$40
        sta     dos_actbsflg
        ldx     #$0C
dos_arom2bsc:
        lda     dos_integer_basic_vectors+9,x
        sta     dos_command_table+55,x
        dex
        bne     dos_arom2bsc
dos_bypaswrm:
        sec
        bcs     dos_cmwrmcld
; $9DBF: reinstall DOS hooks and reenter the selected BASIC warm path.
dos_warm_start:
        lda     dos_actbsflg
        bne     dos_ckbasic
        lda     #$20
        bne     dos_dtrmnbsc
dos_ckbasic:
        asl     a
        bpl     dos_forwarm
        lda     #$4C
dos_dtrmnbsc:
        jsr     dos_setrom
dos_forwarm:
        clc
dos_cmwrmcld:
        php
        jsr     dos_initiohk
        lda     #$00
        sta     dos_ciocumul
        sta     dos_oputcond
        plp
        ror     a
        sta     dos_condnflg
        bmi     dos_langcold
dos_langwarm:
        jmp     (dos_towrmvec)

dos_langcold:
        jmp     (dos_tocldvec)

dos_keycold:
        asl     a
        bpl     dos_skpdaram
        sta     dos_actbsflg
        ldx     #$0C
dos_aram2bsc:
        lda     dos_rom_applesoft_vectors+11,x
        sta     dos_command_table+55,x
        dex
        bne     dos_aram2bsc
        ldx     #$1D
dos_blnkprim:
        lda     dos_secondary_filename,x
        sta     dos_primary_filename,x
        dex
        bpl     dos_blnkprim
dos_skpdaram:
        lda     dos_default_maxfiles
        sta     dos_mxfilval
        jsr     dos_bildbufs
        lda     dos_execflag
        beq     dos_skpdexec
        pha
        jsr     dos_pt2exec
        pla
        ldy     #$00
        sta     ($40),y
dos_skpdexec:
        jsr     dos_close_file
        lda     dos_ndx2cmd
        bne     dos_oldboot
        ldx     #$2F
dos_stor3dos:
        lda     dos_imgdosvt,x
        sta     $03D0,x
        dex
        bpl     dos_stor3dos
        lda     dos_imgdosvt+2
        sta     $03F3
        eor     #$A5
        sta     $03F4
        lda     dos_imgdosvt+1
        sta     $03F2
        lda     #$14
        bne     dos_dopendng
dos_oldboot:
        lda     dos_nextcmd
        beq     dos_nopend
dos_dopendng:
        sta     dos_ndx2cmd
        jmp     dos_dodoscmd

dos_nopend:
        rts

; $9E51: 48-byte image copied to $03D0..$03FF; mixes executable vectors and data.
dos_imgdosvt:
        jmp     dos_warm_start
dos_imgcolvt:
        jmp     dos_cold_start

        jmp     dos_file_manager_external

        jmp     call_rwts_interrupt_masked

        lda     dos_adfmparm+1
        ldy     dos_adfmparm
        rts

        lda     dos_file_manager_vectors+1
        ldy     dos_file_manager_vectors
        rts

        jmp     dos_initiohk

        nop
        nop
        jmp     rom_reset

        jmp     rom_monitor

        jmp     rom_iorts

        jmp     rom_monitor

        jmp     rom_monitor

        .byte   $65,$FF
; $9E81: keyboard/EXEC/READ intercept; save registers before entering DOS.
dos_input_intercept:
        jsr     dos_prep4dos
        lda     dos_condnflg
        beq     dos_inputwrm
        pha
        lda     dos_asaved
        sta     ($28),y
        pla
        bmi     dos_inputcld
        jmp     dos_readtext

dos_inputcld:
        jsr     dos_keycold
        ldy     $24
        lda     #$60
        sta     ($28),y
dos_inputwrm:
        lda     dos_execflag
        beq     dos_inptnoxc
        jsr     dos_readexec
dos_inptnoxc:
        lda     #$03
        sta     dos_oputcond
        jsr     dos_restoreg
        jsr     dos_totruin
        sta     dos_asaved
        stx     dos_xsaved
        jmp     dos_dosexit

dos_totruin:
        jmp     (rom_input_vector)

; $9EBD: output intercept; dispatch through output state, monitor or consume DOS commands.
dos_output_intercept:
        jsr     dos_prep4dos
        lda     dos_oputcond
        asl     a
        tax
        lda     dos_output_handler_table+1,x
        pha
        lda     dos_output_handler_table,x
        pha
        lda     dos_asaved
        rts

dos_prep4dos:
        sta     dos_asaved
        stx     dos_xsaved
        sty     dos_ysaved
        tsx
        inx
        inx
        stx     dos_stksaved
dos_uncondos:
        ldx     #$03
dos_setruhks:
        lda     dos_cswtrue,x
        sta     rom_output_vector,x
        dex
        bpl     dos_setruhks
        rts

dos_oputhdl0:
        ldx     dos_run_intercepted
        beq     dos_nontrupt
        jmp     dos_finshrun

dos_nontrupt:
        ldx     dos_condnflg
        beq     dos_setignor
        cmp     #$BF
        beq     dos_oputhdl6
        cmp     $33
        beq     dos_set2eval
dos_setignor:
        ldx     #$02
        stx     dos_oputcond
        cmp     dos_control_character
        bne     dos_oputhdl2
        dex
        stx     dos_oputcond
        dex
        stx     dos_ndx2inbf
dos_oputhdl1:
        ldx     dos_ndx2inbf
dos_putinbuf:
        sta     $0200,x
        inx
        stx     dos_ndx2inbf
        cmp     #$8D
        bne     dos_dsplycmd
        jmp     dos_parsecmd

dos_oputhdl2:
        cmp     #$8D
        bne     dos_dsplyall
dos_set2eval:
        ldx     #$00
        stx     dos_oputcond
        jmp     dos_dsplyall

dos_oputhdl3:
        ldx     #$00
        stx     dos_oputcond
        cmp     #$8D
        beq     dos_asumimed
dos_testexec:
        lda     dos_execflag
        beq     dos_dsplyall
        bne     dos_dsplyinp
dos_asumimed:
        pha
        sec
        lda     dos_execflag
        bne     dos_testmode
        jsr     dos_ckbscrun
dos_testmode:
        pla
        bcc     dos_testexec
        ldx     dos_xsaved
        jmp     dos_putinbuf

dos_oputhdl4:
        cmp     #$8D
        bne     dos_cmwrtbyt
        lda     #$05
        sta     dos_oputcond
dos_cmwrtbyt:
        jsr     dos_writext
        jmp     dos_dsplyout

dos_oputhdl5:
        cmp     dos_control_character
        beq     dos_oputhdl0
        cmp     #$8A
        beq     dos_cmwrtbyt
        ldx     #$04
        stx     dos_oputcond
        bne     dos_oputhdl4
dos_oputhdl6:
        lda     #$00
        sta     dos_oputcond
        beq     dos_dsplyinp
dos_finshrun:
        lda     #$00
        sta     dos_run_intercepted
        jsr     dos_initiohk
        jmp     dos_runfpint

dos_finshcmd:
        lda     $0200
        cmp     dos_control_character
        beq     dos_dsplycmd
        lda     #$8D
        sta     $0200
        ldx     #$00
        stx     dos_xsaved
dos_dsplycmd:
        lda     #$40
        bne     dos_dsplychr
dos_dsplyout:
        lda     #$10
        bne     dos_dsplychr
dos_dsplyinp:
        lda     #$20
dos_dsplychr:
        and     dos_ciocumul
        beq     dos_dosexit
dos_dsplyall:
        jsr     dos_restoreg
        jsr     dos_godsply
        sta     dos_asaved
        sty     dos_ysaved
        stx     dos_xsaved
dos_dosexit:
        jsr     dos_initiohk
        ldx     dos_stksaved
        txs
dos_restoreg:
        lda     dos_asaved
        ldy     dos_ysaved
        ldx     dos_xsaved
        sec
        rts

dos_godsply:
        jmp     (rom_output_vector)

dos_crviados:
        lda     #$8D
        jmp     dos_godsply

; Parse the line buffer, recognize command text and comma-separated options.
dos_parsecmd:
        ldy     #$FF
        sty     dos_ndx2cmd
        iny
        sty     dos_nextcmd
dos_getchr1:
        inc     dos_ndx2cmd
        ldx     #$00
        php
        lda     $0200,x
        cmp     dos_control_character
        bne     dos_savlindx
        inx
dos_savlindx:
        stx     dos_ndx2inbf
dos_invscmd:
        jsr     dos_purgecmd
        and     #$7F
        eor     dos_cmdtxtbl,y
        iny
        asl     a
        beq     dos_ckifchrs
        pla
        php
dos_ckifchrs:
        bcc     dos_invscmd
        plp
        beq     dos_prpdocmd
        lda     dos_cmdtxtbl,y
        bne     dos_getchr1
dos_check_control_character:
        lda     $0200
        cmp     dos_control_character
        beq     dos_chkifcr
        jmp     dos_dsplyall

dos_chkifcr:
        lda     $0201
        cmp     #$8D
        bne     dos_prsynerr
        jsr     dos_close_file
        jmp     dos_dsplycmd

dos_prsynerr:
        jmp     dos_syntxerr

dos_prpdocmd:
        asl     dos_ndx2cmd
        ldy     dos_ndx2cmd
        jsr     dos_ckbscrun
        bcc     dos_chkifrun
dos_immed:
        lda     #$02
        and     dos_cmdattrb,y
        beq     dos_chkifrun
dos_nodircmd:
        lda     #$0F
        jmp     dos_errhndlr

dos_chkifrun:
        cpy     #$06
        bne     dos_tst4name
        sty     $33
dos_tst4name:
        lda     #$20
        and     dos_cmdattrb,y
        beq     dos_fnotappl
dos_fnxpctd:
        jsr     dos_blnkfnbf
        php
dos_fnamchr1:
        jsr     dos_purgecmd
        beq     dos_donefn
        asl     a
        bcc     dos_lglfnchr
        bmi     dos_lglfnchr
        jmp     dos_check_control_character

dos_lglfnchr:
        ror     a
        jmp     dos_svfnchar

dos_nchr2etc:
        jsr     dos_cmdchar
        beq     dos_donefn
dos_svfnchar:
        sta     dos_primary_filename,y
        iny
        cpy     #$3C
        bcc     dos_nchr2etc
dos_purgefn:
        jsr     dos_cmdchar
        bne     dos_purgefn
dos_donefn:
        plp
        bne     dos_ckfn2lgl
dos_finfirst:
        ldy     dos_ndx2cmd
        lda     #$10
        and     dos_cmdattrb,y
        beq     dos_ckfn1lgl
        ldy     #$1E
        php
        bne     dos_fnamchr1
dos_ckfn2lgl:
        lda     dos_secondary_filename
        cmp     #$A0
        beq     dos_goxitdos
dos_ckfn1lgl:
        lda     dos_primary_filename
        cmp     #$A0
        bne     dos_dfltprsd
        ldy     dos_ndx2cmd
        lda     #$C0
        and     dos_cmdattrb,y
        beq     dos_goxitdos
        bpl     dos_dfltprsd
dos_goxitdos:
        jmp     dos_check_control_character

dos_blnkfnbf:
        ldy     #$3C
dos_blnk1rst:
        lda     #$A0
dos_storblnk:
        sta     dos_monprsd,y
        dey
        bne     dos_storblnk
        rts

dos_fnotappl:
        sta     dos_primary_filename
        lda     #$0C
        and     dos_cmdattrb,y
        beq     dos_dfltprsd
dos_inprmax:
        jsr     dos_cnvrtasc
        bcs     dos_tosyntx
        tay
        bne     dos_argrnger
        cpx     #$11
        bcs     dos_argrnger
        ldy     dos_ndx2cmd
        lda     #$08
        and     dos_cmdattrb,y
        beq     dos_maxfmin
        cpx     #$08
        bcs     dos_goxitdos
        bcc     dos_dfltprsd
dos_maxfmin:
        txa
        bne     dos_dfltprsd
dos_argrnger:
        lda     #$02
        jmp     dos_errhndlr

dos_tosyntx:
        jmp     dos_syntxerr

dos_dfltprsd:
        lda     #$00
        sta     dos_cumloptn
        sta     dos_monprsd
        sta     dos_volprsd
        sta     dos_lenprsd
        sta     dos_lenprsd+1
        jsr     dos_reset_file_selection
        lda     dos_ndx2inbf
dos_nxcmdchr:
        jsr     dos_purgecmd
        bne     dos_chkoptns
        cmp     #$8D
        bne     dos_nxcmdchr
        ldx     dos_ndx2cmd
        lda     dos_cumloptn
        ora     dos_cmdattrb+1,x
        eor     dos_cmdattrb+1,x
        bne     dos_goxitdos
        ldx     dos_file_type
        beq     dos_todoscmd
        sta     dos_file_type
        stx     dos_ndx2inbf
        bne     dos_nxcmdchr
dos_chkoptns:
        ldx     #$0A
dos_cknxoptn:
        cmp     dos_cmdattrb+55,x
        beq     dos_optnok
        dex
        bne     dos_cknxoptn
dos_totosynt:
        beq     dos_tosyntx
dos_optnok:
        lda     dos_optntxt+9,x
        bmi     dos_cioptns
        ora     dos_cumloptn
        sta     dos_cumloptn
        dex
        stx     dos_ndx2optn
        jsr     dos_cnvrtasc
        bcs     dos_tosyntx
        lda     dos_ndx2optn
        asl     a
        asl     a
        tay
        lda     $45
        bne     dos_ckmaxval
        lda     $44
        cmp     dos_optnrng,y
        bcc     dos_argrnger
        lda     $45
dos_ckmaxval:
        cmp     dos_optnrng+3,y
        bcc     dos_svaloptn
dos_toargrng:
        bne     dos_argrnger
        lda     $44
        cmp     dos_optnrng+2,y
        bcc     dos_svaloptn
        bne     dos_toargrng
dos_svaloptn:
        lda     dos_file_type
        bne     dos_nxcmdchr
        tya
        lsr     a
        tay
        lda     $45
        sta     dos_volprsd+1,y
        lda     $44
        sta     dos_volprsd,y
dos_tonxoptn:
        jmp     dos_nxcmdchr

dos_cioptns:
        pha
        lda     #$80
        ora     dos_cumloptn
        sta     dos_cumloptn
        pla
        and     #$7F
        ora     dos_monprsd
        sta     dos_monprsd
        bne     dos_tonxoptn
        beq     dos_totosynt
dos_todoscmd:
        jsr     dos_dodoscmd
dos_aftrcmd:
        jmp     dos_finshcmd

; Dispatch command from index using the entry-minus-one command table.
dos_dodoscmd:
        jsr     dos_close_file
        jsr     dos_clrfmprm
        lda     dos_ndx2cmd
        tax
        lda     dos_command_table+1,x
        pha
        lda     dos_command_table,x
        pha
        rts

dos_cmdchar:
        ldx     dos_ndx2inbf
        lda     $0200,x
        cmp     #$8D
        beq     dos_cmdchrts
        inx
        stx     dos_ndx2inbf
        cmp     #$AC
dos_cmdchrts:
        rts

dos_purgecmd:
        jsr     dos_cmdchar
        beq     dos_cmdchrts
        cmp     #$A0
        beq     dos_purgecmd
        rts

dos_clrfmprm:
        lda     #$00
        ldy     #$16
dos_zfmparm:
        sta     dos_fil1size+211,y
        dey
        bne     dos_zfmparm
        rts

dos_cnvrtasc:
        lda     #$00
        sta     $44
        sta     $45
        jsr     dos_purgecmd
        php
        cmp     #$A4
        beq     dos_asc2hex
        plp
        jmp     dos_ckifdone

dos_asc2dec:
        jsr     dos_purgecmd
dos_ckifdone:
        bne     dos_subtrasc
        ldx     $44
        lda     $45
        clc
        rts

dos_subtrasc:
        sec
        sbc     #$B0
        bmi     dos_notascii
        cmp     #$0A
        bcs     dos_notascii
        jsr     dos_double
        adc     $44
        tax
        lda     #$00
        adc     $45
        tay
        jsr     dos_double
        jsr     dos_double
        txa
        adc     $44
        sta     $44
        tya
        adc     $45
        sta     $45
        bcc     dos_asc2dec
dos_notascii:
        sec
        rts

dos_double:
        asl     $44
        rol     $45
        rts

dos_asc2hex:
        plp
dos_getascii:
        jsr     dos_purgecmd
        beq     dos_ckifdone
        sec
        sbc     #$B0
        bmi     dos_notascii
        cmp     #$0A
        bcc     dos_prp2dubl
        sbc     #$07
        bmi     dos_notascii
        cmp     #$10
        bcs     dos_notascii
dos_prp2dubl:
        ldx     #$04
dos_times2:
        jsr     dos_double
        dex
        bne     dos_times2
        ora     $44
        sta     $44
        jmp     dos_getascii

dos_cmdpr:
        lda     $44
        jmp     rom_output_select

dos_cmdin:
        lda     $44
        jmp     rom_input_select

dos_command_mon:
        lda     dos_ciocumul
        ora     dos_monprsd
        sta     dos_ciocumul
        rts

dos_command_nommon:
        bit     dos_monprsd
        bvc     dos_clrmon
        jsr     dos_crviados
dos_clrmon:
        lda     #$70
        eor     dos_monprsd
        and     dos_ciocumul
        sta     dos_ciocumul
        rts

dos_command_maxfiles:
        lda     #$00
        sta     dos_execflag
        lda     $44
        pha
        jsr     dos_close_all
        pla
        sta     dos_mxfilval
        jmp     dos_bildbufs

dos_command_delete:
        lda     #$05
        jsr     dos_hndlcmd1
        jsr     dos_getbuff
        ldy     #$00
        tya
        sta     ($40),y
        rts

dos_command_lock:
        lda     #$07
        bne     dos_lokunlok
dos_command_unlock:
        lda     #$08
dos_lokunlok:
        jsr     dos_hndlcmd1
        jmp     dos_command_close

dos_command_verify:
        lda     #$0C
        bne     dos_lokunlok
dos_command_rename:
        lda     dos_adrsfnbf
        sta     dos_recnmbfm
        lda     dos_adrsfnbf+1
        sta     dos_recnmbfm+1
        lda     #$09
        sta     dos_file_type
        jsr     dos_closifop
        jmp     dos_command_close

dos_command_append:
        jsr     dos_command_open
dos_read2end:
        jsr     dos_rdtxtbyt
        bne     dos_read2end
        jmp     dos_advance_file_position

dos_command_open:
        lda     #$00
        jmp     dos_opncktyp

dos_hndlcmd:
        lda     #$01
dos_hndlcmd1:
        sta     dos_file_type
        lda     dos_lenprsd
        bne     dos_savlenfm
        lda     dos_lenprsd+1
        bne     dos_savlenfm
        lda     #$01
        sta     dos_lenprsd
dos_savlenfm:
        lda     dos_lenprsd
        sta     dos_recnmbfm
        lda     dos_lenprsd+1
        sta     dos_recnmbfm+1
dos_closifop:
        jsr     dos_command_close
        lda     $45
        bne     dos_savfnptr
        jmp     dos_nobuferr

dos_savfnptr:
        sta     $41
        lda     $44
        sta     $40
        jsr     dos_cpypfn
        jsr     dos_bufs2prm
        jsr     dos_cpy2parm
        lda     dos_file_type
        sta     dos_file_parameters
        jmp     dos_file_manager_driver

dos_command_close:
        lda     dos_primary_filename
        cmp     #$A0
        beq     dos_close_all
        jsr     dos_getbuff
dos_eventxit:
        bcs     dos_closerts
        jsr     dos_closeone
        jmp     dos_command_close

dos_closeone:
        jsr     dos_ckexcbuf
        bne     dos_freebuff
        lda     #$00
        sta     dos_execflag
dos_freebuff:
        ldy     #$00
        tya
        sta     ($40),y
        jsr     dos_bufs2prm
        lda     #$02
        sta     dos_file_parameters
        jmp     dos_file_manager_driver

dos_close_all:
        jsr     dos_getfnbf1
        bne     dos_ckifexec
dos_chknxbuf:
        jsr     dos_getnxbuf
        beq     dos_closerts
dos_ckifexec:
        jsr     dos_ckexcbuf
        beq     dos_chknxbuf
        jsr     dos_getfnby1
        beq     dos_chknxbuf
        jsr     dos_closeone
        jmp     dos_close_all

dos_closerts:
        rts

dos_command_bsave:
        lda     #$09
        and     dos_cumloptn
        cmp     #$09
        beq     dos_dobsav
        jmp     dos_check_control_character

dos_dobsav:
        lda     #$04
        jsr     dos_opncktyp
        lda     dos_adrprsd+1
        ldy     dos_adrprsd
        jsr     dos_wradrlen
        lda     dos_lenprsd+1
        ldy     dos_lenprsd
        jsr     dos_wradrlen
        lda     dos_adrprsd+1
        ldy     dos_adrprsd
        jmp     dos_rdwrange

; $A35D: open binary, read address/length header, then read range into requested address.
; START explicitly supplies interpreter $0800 and parameter $0300 destinations.
dos_command_bload:
        jsr     dos_hndlcmd
dos_lck4blod:
        lda     #$7F
        and     dos_filtypfm
        cmp     #$04
        beq     dos_adr4blod
        jmp     dos_typmism

dos_adr4blod:
        lda     #$04
        jsr     dos_opncktyp
        jsr     dos_rdadrlen
        tax
        lda     dos_cumloptn
        and     #$01
        bne     dos_len4blod
        stx     dos_adrprsd
        sty     dos_adrprsd+1
dos_len4blod:
        jsr     dos_rdadrlen
        ldx     dos_adrprsd
        ldy     dos_adrprsd+1
        jmp     dos_lodintfp

dos_command_brun:
        jsr     dos_command_bload
        jsr     dos_initiohk
        jmp     (dos_adrprsd)

dos_command_save:
        lda     dos_actbsflg
        beq     dos_savintgr
        lda     $D6
        bpl     dos_savapsft
        jmp     dos_toolarge

dos_savapsft:
        lda     #$02
        jsr     dos_opncktyp
        sec
        lda     $AF
        sbc     $67
        tay
        lda     $B0
        sbc     $68
        jsr     dos_wradrlen
        lda     $68
        ldy     $67
        jmp     dos_rdwrange

dos_savintgr:
        lda     #$01
        jsr     dos_opncktyp
        sec
        lda     $4C
        sbc     $CA
        tay
        lda     $4D
        sbc     $CB
        jsr     dos_wradrlen
        lda     $CB
        ldy     $CA
        jmp     dos_rdwrange

dos_opncktyp:
        sta     dos_filtypfm
        pha
        jsr     dos_hndlcmd
        pla
        jmp     dos_chkftype

dos_wradrlen:
        sty     dos_slotfm
        sty     dos_fnambufm
        sta     dos_filtypfm
        lda     #$04
        sta     dos_file_parameters
        lda     #$01
        sta     dos_subcodfm
        jsr     dos_file_manager_driver
        lda     dos_filtypfm
        sta     dos_fnambufm
        jmp     dos_file_manager_driver

dos_rdwrange:
        sty     dos_fnambufm
        sta     dos_fnambufm+1
        lda     #$02
        jmp     dos_process_saved_character

dos_closefm:
        jsr     dos_file_manager_driver
        jmp     dos_command_close

dos_totypmis:
        jmp     dos_typmism

dos_command_load:
        jsr     dos_close_all
dos_openload:
        jsr     dos_hndlcmd
        lda     #$23
        and     dos_filtypfm
        beq     dos_totypmis
        sta     dos_filtypfm
        lda     dos_actbsflg
        beq     dos_lodintgr
        lda     #$02
        jsr     dos_selctbsc
        jsr     dos_rdadrlen
        clc
        adc     $67
        tax
        tya
        adc     $68
        cmp     $74
        bcs     dos_totoolrg
        sta     $B0
        sta     $6A
        stx     $AF
        stx     $69
        ldx     $67
        ldy     $68
        jsr     dos_lodintfp
        jsr     dos_initiohk
        jmp     (dos_rlocntry)

dos_lodintgr:
        lda     #$01
        jsr     dos_selctbsc
        jsr     dos_rdadrlen
        sec
        lda     $4C
        sbc     dos_lenadrbf
        tax
        lda     $4D
        sbc     dos_lenadrbf+1
        bcc     dos_totoolrg
        tay
        cpy     $4B
        bcc     dos_totoolrg
        beq     dos_totoolrg
        sty     $CB
        stx     $CA
dos_lodintfp:
        stx     dos_fnambufm
        sty     dos_fnambufm+1
        jmp     dos_closefm

dos_rdadrlen:
        lda     dos_adlenadr
        sta     dos_fnambufm
        lda     dos_adlenadr+1
        sta     dos_fnambufm+1
        lda     #$00
        sta     dos_filtypfm
        lda     #$02
        sta     dos_slotfm
        lda     #$03
        sta     dos_file_parameters
        lda     #$02
        sta     dos_subcodfm
        jsr     dos_file_manager_driver
        lda     dos_lenadrbf+1
        sta     dos_filtypfm
        tay
        lda     dos_lenadrbf
        sta     dos_slotfm
        rts

dos_totoolrg:
        jsr     dos_command_close
        jmp     dos_toolarge

dos_selctbsc:
        cmp     dos_filtypfm
        beq     dos_selbsrtn
        ldx     dos_ndx2cmd
        stx     dos_nextcmd
        lsr     a
        beq     dos_swtch2fp
        jmp     dos_command_int

dos_swtch2fp:
        ldx     #$1D
dos_prim2snd:
        lda     dos_primary_filename,x
        sta     dos_secondary_filename,x
        dex
        bpl     dos_prim2snd
        jmp     dos_command_fp

dos_selbsrtn:
        rts

; $A4D1: LOAD followed by selected BASIC RUN entry; used to execute START.
dos_command_run:
        lda     dos_actbsflg
        beq     dos_load4run
        sta     dos_run_intercepted
dos_load4run:
        jsr     dos_command_load
dos_runfpint:
        jsr     dos_crviados
        jsr     dos_initiohk
        jmp     (dos_runtry)

dos_runintgr:
        lda     $4A
        sta     $CC
        lda     $4B
        sta     $CD
        jmp     (dos_active_basic_vectors)

dos_command_chain:
        jsr     dos_openload
        jsr     dos_crviados
        jsr     dos_initiohk
        jmp     (dos_active_basic_vectors)

dos_runfprom:
        jsr     rom_applesoft_clear
        sta     $33
        sta     $D8
        jmp     rom_applesoft_run

dos_fpramrun:
        jsr     ram_applesoft_clear
        sta     $33
        sta     $D8
        jmp     ram_applesoft_run

dos_command_write:
        jsr     dos_comrdwr
        lda     #$05
        sta     dos_oputcond
        jmp     dos_finshcmd

dos_command_read:
        jsr     dos_comrdwr
        lda     #$01
        sta     dos_condnflg
        jmp     dos_finshcmd

dos_comrdwr:
        jsr     dos_getbuff
        bcc     dos_bufs4rw
        jsr     dos_command_open
        jmp     dos_ckrboptn

dos_bufs4rw:
        jsr     dos_bufs2prm
dos_ckrboptn:
        lda     dos_cumloptn
        and     #$06
        beq     dos_rdwrrtn
        ldx     #$03
dos_cpybparm:
        lda     dos_recprsd,x
        sta     dos_recnmbfm,x
        dex
        bpl     dos_cpybparm
dos_bk2apnd:
        lda     #$0A
        sta     dos_file_parameters
        jsr     dos_file_manager_driver
dos_rdwrrtn:
        rts

dos_command_init:
        lda     #$40
        and     dos_cumloptn
        beq     dos_vol254
        lda     dos_volprsd
        bne     dos_othrvol
dos_vol254:
        lda     #$FE
        sta     dos_volprsd
dos_othrvol:
        lda     dos_adostart+1
        sta     dos_subcodfm
        lda     #$0B
        jsr     dos_hndlcmd1
        jmp     dos_command_save

dos_command_catalog:
        lda     #$06
        jsr     dos_hndlcmd1
        lda     dos_bytofffm
        sta     dos_volprsd
        rts

dos_command_fp:
        lda     #$4C
        jsr     dos_setrom
        beq     dos_todoscld
        lda     #$00
        sta     dos_actbsflg
        ldy     #$1E
        jsr     dos_blnk1rst
        ldx     #$09
dos_cpyapple:
        lda     dos_run_intercepted,x
        sta     dos_monprsd,x
        dex
        bne     dos_cpyapple
        lda     #$C0
        sta     dos_condnflg
        jmp     dos_command_run

dos_command_int:
        lda     #$20
        jsr     dos_setrom
        beq     dos_intprsnt
dos_nolngint:
        lda     #$01
        jmp     dos_errhndlr

dos_intprsnt:
        lda     #$00
        sta     dos_run_intercepted
dos_todoscld:
        jmp     dos_cold_start

dos_setrom:
        cmp     $E000
        beq     dos_dvicertn
        sta     $C081
        cmp     $E000
        beq     dos_dvicertn
        sta     $C080
        cmp     $E000
dos_dvicertn:
        rts

dos_command_exec:
        jsr     dos_command_open
        lda     dos_curfnadr
        sta     dos_execbuff
        lda     dos_curfnadr+1
        sta     dos_execbuff+1
        lda     dos_primary_filename
        sta     dos_execflag
        bne     dos_posnchkr
dos_command_position:
        jsr     dos_getbuff
        bcc     dos_bufs4psn
        jsr     dos_command_open
        jmp     dos_posnchkr

dos_bufs4psn:
        jsr     dos_bufs2prm
dos_posnchkr:
        lda     dos_cumloptn
        and     #$04
        beq     dos_doneposn
dos_ckpsndun:
        lda     dos_recprsd
        bne     dos_posnmore
        ldx     dos_recprsd+1
        beq     dos_doneposn
        dec     dos_recprsd+1
dos_posnmore:
        dec     dos_recprsd
dos_psnfield:
        jsr     dos_rdtxtbyt
        beq     dos_endaterr
        cmp     #$8D
        bne     dos_psnfield
        beq     dos_ckpsndun
dos_doneposn:
        rts

dos_writext:
        jsr     dos_ckbscrun
        bcs     dos_closzero
        lda     dos_asaved
        sta     dos_fnambufm
        lda     #$04
        sta     dos_file_parameters
        lda     #$01
        sta     dos_subcodfm
        jmp     dos_file_manager_driver

dos_readtext:
        jsr     dos_ckbscrun
        bcs     dos_closzero
        lda     #$06
dos_setcond:
        sta     dos_oputcond
        jsr     dos_rdtxtbyt
        bne     dos_notend
        jsr     dos_closeone
        lda     #$03
        cmp     dos_oputcond
        beq     dos_doneposn
dos_endaterr:
        lda     #$05
        jmp     dos_errhndlr

dos_notend:
        cmp     #$E0
        bcc     dos_savit
        and     #$7F
dos_savit:
        sta     dos_asaved
        ldx     dos_xsaved
        beq     dos_toexit
        dex
        lda     $0200,x
        ora     #$80
        sta     $0200,x
dos_toexit:
        jmp     dos_dosexit

dos_ckbscrun:
        pha
        lda     dos_actbsflg
        beq     dos_intbasic
        ldx     $76
        inx
        beq     dos_imedmode
        ldx     $33
        cpx     #$DD
        beq     dos_imedmode
dos_running:
        pla
        clc
        rts

dos_intbasic:
        lda     $D9
        bmi     dos_running
dos_imedmode:
        pla
        sec
        rts

dos_closzero:
        jsr     dos_closeone
        jsr     dos_close_file
        jmp     dos_dosexit

dos_readexec:
        jsr     dos_pt2exec
        jsr     dos_bufs2prm
        lda     #$03
        bne     dos_setcond
dos_rdtxtbyt:
        lda     #$03
        sta     dos_file_parameters
        lda     #$01
        sta     dos_subcodfm
        jsr     dos_file_manager_driver
        lda     dos_fnambufm
        rts

dos_pt2exec:
        lda     dos_execbuff+1
        sta     $41
        lda     dos_execbuff
        sta     $40
dos_pt2exec2:
        rts

; $A6A8: call file manager, handle carry/error and recover command input.
; Native error/append paths call helpers in the resident $B600 boot-sector copy.
dos_file_manager_driver:
        jsr     dos_file_manager
dos_aftrfunc:
        bcc     dos_fmdrvrtn
dos_aftrfunc2:
        lda     dos_rtncodfm
        cmp     #$05
        beq     dos_toapptch
        jmp     dos_load_and_clear_buffer

dos_toapptch:
        jmp     dos_copy_file_position

        nop
        nop
dos_bk2fmdrv:
        nop
        nop
        ldx     #$00
        stx     dos_fnambufm
dos_fmdrvrtn:
        rts

dos_syntxerr:
        lda     #$0B
        bne     dos_errhndlr
dos_nobuferr:
        lda     #$0C
        bne     dos_errhndlr
dos_toolarge:
        lda     #$0E
        bne     dos_errhndlr
dos_typmism:
        lda     #$0D
dos_errhndlr:
        sta     dos_asaved
        jsr     dos_close_from_exec
        lda     dos_actbsflg
        beq     dos_wasint
        lda     $D8
        bmi     dos_onerract
dos_wasint:
        ldx     #$00
        jsr     dos_prdoserr
        ldx     dos_asaved
        jsr     dos_prdoserr
        jsr     dos_crviados
dos_onerract:
        jsr     dos_initiohk
dos_onerract2:
        jsr     dos_ckbscrun
        ldx     dos_asaved
        lda     #$03
        bcs     dos_dowrm
dos_tobscerr:
        jmp     (dos_adbscerr)

dos_dowrm:
        jmp     (dos_towrmvec)

dos_prdoserr:
        lda     dos_off2err,x
        tax
dos_morermsg:
        stx     dos_file_type
        lda     dos_err00,x
        pha
        ora     #$80
        jsr     dos_godsply
        ldx     dos_file_type
        inx
        pla
        bpl     dos_morermsg
        rts

dos_cpy2parm:
        lda     dos_volprsd
        sta     dos_bytofffm
        lda     dos_drvprsd
        sta     dos_drvfm
        lda     dos_slotprsd
        sta     dos_slotfm
        lda     dos_adrpfnbf
        sta     dos_fnambufm
        lda     dos_adrpfnbf+1
        sta     dos_fnambufm+1
        lda     $40
        sta     dos_curfnadr
        lda     $41
        sta     dos_curfnadr+1
        rts

dos_cpypfn:
        ldy     #$1D
dos_cpyprim:
        lda     dos_primary_filename,y
        sta     ($40),y
        dey
        bpl     dos_cpyprim
        rts

dos_bufs2prm:
        ldy     #$1E
dos_adrinprm:
        lda     ($40),y
        sta     dos_fil1size+194,y
        iny
        cpy     #$26
        bne     dos_adrinprm
        rts

dos_close_file:
        ldy     #$00
        sty     dos_condnflg
        sty     dos_oputcond
        rts

dos_getbuff:
        lda     #$00
        sta     $45
        jsr     dos_getfnbf1
        jmp     dos_fnchar1

dos_getfnlnk:
        jsr     dos_getnxbuf
        beq     dos_nofnmtch
dos_fnchar1:
        jsr     dos_getfnby1
        bne     dos_nxfnbuf
        lda     $40
        sta     $44
        lda     $41
        sta     $45
        bne     dos_getfnlnk
dos_nxfnbuf:
        ldy     #$1D
dos_cmpfnchr:
        lda     ($40),y
        cmp     dos_primary_filename,y
        bne     dos_getfnlnk
        dey
        bpl     dos_cmpfnchr
        clc
        rts

dos_nofnmtch:
        sec
        rts

dos_getfnbf1:
        lda     dos_address_table
        ldx     dos_address_table+1
        bne     dos_setnxptr
dos_getnxbuf:
        ldy     #$25
        lda     ($40),y
        beq     dos_getnxrtn
        tax
        dey
        lda     ($40),y
dos_setnxptr:
        stx     $41
        sta     $40
        txa
dos_getnxrtn:
        rts

dos_getfnby1:
        ldy     #$00
        lda     ($40),y
        rts

dos_ckexcbuf:
        lda     dos_execflag
        beq     dos_notexcbf
        lda     dos_execbuff
        cmp     $40
        bne     dos_ckexcrtn
        lda     dos_execbuff+1
        cmp     $41
        beq     dos_ckexcrtn
dos_notexcbf:
        dex
dos_ckexcrtn:
        rts

dos_chkftype:
        eor     dos_filtypfm
        beq     dos_cktyprtn
        and     #$7F
        beq     dos_cktyprtn
        jsr     dos_command_close
        jmp     dos_typmism

dos_cktyprtn:
        rts

dos_bildbufs:
        sec
        lda     dos_address_table
        sta     $40
        lda     dos_address_table+1
        sta     $41
        lda     dos_mxfilval
        sta     dos_file_type
dos_zdosbufn:
        ldy     #$00
        tya
        sta     ($40),y
        ldy     #$1E
        sec
        lda     $40
        sbc     #$2D
        sta     ($40),y
        pha
        lda     $41
        sbc     #$00
        iny
        sta     ($40),y
        tax
        dex
        pla
        pha
        iny
        sta     ($40),y
        txa
        iny
        sta     ($40),y
        tax
        dex
        pla
        pha
        iny
        sta     ($40),y
        iny
        txa
        sta     ($40),y
        dec     dos_file_type
        beq     dos_zlnk2nxt
        tax
        pla
        sec
        sbc     #$26
        iny
        sta     ($40),y
        pha
        txa
        sbc     #$00
        iny
        sta     ($40),y
        sta     $41
        pla
        sta     $40
        jmp     dos_zdosbufn

dos_zlnk2nxt:
        pha
        lda     #$00
        iny
        sta     ($40),y
        iny
        sta     ($40),y
        lda     dos_actbsflg
        beq     dos_setintpt
        pla
        sta     $74
        sta     $70
        pla
        sta     $73
        sta     $6F
        rts

dos_setintpt:
        pla
        sta     $4D
        sta     $CB
        pla
        sta     $4C
        sta     $CA
        rts

; Install DOS intercepts in ROM $36/$37 and $38/$39 hooks, saving original devices.
dos_initiohk:
        lda     $39
        cmp     dos_adinptcp+1
        beq     dos_ckouthk
        sta     dos_kswtrue+1
        lda     rom_input_vector
        sta     dos_kswtrue
        lda     dos_adinptcp
        sta     rom_input_vector
        lda     dos_adinptcp+1
        sta     $39
dos_ckouthk:
        lda     $37
        cmp     dos_adoputcp+1
        beq     dos_sethkrtn
        sta     dos_cswtrue+1
        lda     rom_output_vector
        sta     dos_cswtrue
        lda     dos_adoputcp
        sta     rom_output_vector
        lda     dos_adoputcp+1
        sta     $37
dos_sethkrtn:
        rts

; $A884..$A908: command words; low-bit ASCII, final character high bit, zero end.
dos_cmdtxtbl:
        .byte   $49,$4E,$49,$D4,$4C,$4F,$41,$C4
        .byte   $53,$41,$56,$C5,$52,$55,$CE,$43
        .byte   $48,$41,$49,$CE,$44,$45,$4C,$45
        .byte   $54,$C5,$4C,$4F,$43,$CB,$55,$4E
        .byte   $4C,$4F,$43,$CB,$43,$4C,$4F,$53
        .byte   $C5,$52,$45,$41,$C4,$45,$58,$45
        .byte   $C3,$57,$52,$49,$54,$C5,$50,$4F
        .byte   $53,$49,$54,$49,$4F,$CE,$4F,$50
        .byte   $45,$CE,$41,$50,$50,$45,$4E,$C4
        .byte   $52,$45,$4E,$41,$4D,$C5,$43,$41
        .byte   $54,$41,$4C,$4F,$C7,$4D,$4F,$CE
        .byte   $4E,$4F,$4D,$4F,$CE,$50,$52,$A3
        .byte   $49,$4E,$A3,$4D,$41,$58,$46,$49
        .byte   $4C,$45,$D3,$46,$D0,$49,$4E,$D4
        .byte   $42,$53,$41,$56,$C5,$42,$4C,$4F
        .byte   $41,$C4,$42,$52,$55,$CE,$56,$45
        .byte   $52,$49,$46,$D9,$00
; Two attribute bytes per command; allowable type/options and command behavior.
dos_cmdattrb:
        .byte   $21
        .byte   $70,$A0,$70,$A1,$70,$A0,$70,$20
        .byte   $70,$20,$70,$20,$70,$20,$70,$60
        .byte   $00,$22,$06,$20,$74,$22,$06,$22
        .byte   $04,$23,$78,$22,$70,$30,$70,$40
        .byte   $70,$40,$80,$40,$80,$08,$00,$08
        .byte   $00,$04,$00,$40,$70,$40,$00,$21
        .byte   $79,$20,$71,$20,$71,$20
        .byte   $70
; Option characters V,D,S,L,R,B,A,C,I,O and corresponding masks/ranges.
dos_optntxt:
        .byte   $D6,$C4,$D3,$CC,$D2,$C2,$C1,$C3
        .byte   $C9
        .byte   $CF
dos_optnissd:
        .byte   $40,$20,$10,$08,$04,$02,$01,$C0
        .byte   $A0,$90
dos_optnrng:
        .byte   $00,$00
        .byte   $FE
        .byte   $00,$01,$00,$02,$00,$01,$00,$07
        .byte   $00,$01,$00,$FF,$7F,$00,$00,$FF
        .byte   $7F,$00,$00,$FF,$7F,$00,$00,$FF
        .byte   $FF
; Error-message pool: last character high bit; dos_off2err indexes messages.
dos_err00:
        .byte   $0D,$07,$8D
dos_err01:
        .byte   $4C,$41,$4E,$47,$55,$41,$47,$45
        .byte   $20,$4E,$4F,$54,$20,$41,$56,$41
        .byte   $49,$4C,$41,$42,$4C,$C5
dos_err03:
        .byte   $52,$41,$4E,$47,$45,$20,$45,$52
        .byte   $52,$4F,$D2
dos_err04:
        .byte   $57,$52,$49,$54,$45,$20,$50,$52
        .byte   $4F,$54,$45,$43,$54,$45,$C4
dos_err05:
        .byte   $45,$4E,$44,$20,$4F,$46,$20,$44
        .byte   $41,$54,$C1
dos_err06:
        .byte   $46,$49,$4C,$45,$20,$4E,$4F,$54
        .byte   $20,$46,$4F,$55,$4E,$C4
dos_err07:
        .byte   $56,$4F,$4C,$55,$4D,$45,$20,$4D
        .byte   $49,$53,$4D,$41,$54,$43,$C8
dos_err08:
        .byte   $49,$2F,$4F,$20,$45,$52,$52,$4F
        .byte   $D2
dos_err09:
        .byte   $44,$49,$53,$4B,$20,$46,$55,$4C
        .byte   $CC
dos_err10:
        .byte   $46,$49,$4C,$45,$20,$4C,$4F,$43
        .byte   $4B,$45,$C4
dos_err11:
        .byte   $53,$59,$4E,$54,$41,$58,$20,$45
        .byte   $52,$52,$4F,$D2
dos_err12:
        .byte   $4E,$4F,$20,$42,$55,$46,$46,$45
        .byte   $52,$53,$20,$41,$56,$41,$49,$4C
        .byte   $41,$42,$4C,$C5
dos_err13:
        .byte   $46,$49,$4C,$45,$20,$54,$59,$50
        .byte   $45,$20,$4D,$49,$53,$4D,$41,$54
        .byte   $43,$C8
dos_err14:
        .byte   $50,$52,$4F,$47,$52,$41,$4D,$20
        .byte   $54,$4F,$4F,$20,$4C,$41,$52,$47
        .byte   $C5
dos_err15:
        .byte   $4E,$4F,$54,$20,$44,$49,$52,$45
        .byte   $43,$54,$20,$43,$4F,$4D,$4D,$41
        .byte   $4E,$C4,$8D
dos_off2err:
        .byte   $00,$03,$19,$19,$24,$33,$3E,$4C
        .byte   $5B,$64,$6D,$78,$84,$98,$AA,$BB
; Pointer to current filename in the DOS buffer chain; captured native state.
dos_curfnadr:
        .byte   $2D
        .byte   $98
dos_condnflg:
        .byte   $00
dos_oputcond:
        .byte   $00
dos_cswtrue:
        .byte   $F0
        .byte   $FD
dos_kswtrue:
        .byte   $1B
        .byte   $FD
dos_mxfilval:
        .byte   $03,$03
dos_stksaved:
        .byte   $F4
dos_xsaved:
        .byte   $0C
dos_ysaved:
        .byte   $28
dos_asaved:
        .byte   $8D
dos_ndx2inbf:
        .byte   $0C
dos_ciocumul:
        .byte   $00
dos_ndx2cmd:
        .byte   $00
dos_lenadrbf:
        .byte   $4E
        .byte   $12
dos_nextcmd:
        .byte   $00
dos_file_type:
        .byte   $0B
dos_ndx2optn:
        .byte   $01
dos_cumloptn:
        .byte   $20
dos_volprsd:
        .byte   $FE
        .byte   $00
dos_drvprsd:
        .byte   $02,$00
dos_slotprsd:
        .byte   $06,$00
dos_lenprsd:
        .byte   $01
        .byte   $00
dos_recprsd:
        .byte   $00
        .byte   $00
dos_file_address:
        .byte   $00
dos_file_address_high:
        .byte   $00
dos_adrprsd:
        .byte   $03
        .byte   $08
dos_monprsd:
        .byte   $00
dos_primary_filename:
        .byte   $D3,$D4,$C1,$D2,$D4,$A0,$A0,$A0
        .byte   $A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0
        .byte   $A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0
        .byte   $A0,$A0,$A0,$A0,$A0,$A0
dos_secondary_filename:
        .byte   $A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0
        .byte   $A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0
        .byte   $A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0
        .byte   $A0,$A0,$A0,$A0,$A0,$A0
dos_default_maxfiles:
        .byte   $03
dos_control_character:
        .byte   $84
dos_execflag:
        .byte   $00
dos_execbuff:
        .byte   $00
        .byte   $00
dos_actbsflg:
        .byte   $40
dos_run_intercepted:
        .byte   $00
dos_applesoft_filename:
        .byte   $C1,$D0,$D0,$CC,$C5,$D3,$CF,$C6
        .byte   $D4
; $AAC1: public IOB/VTOC/catalog/end pointers, used by page-three entry vectors.
dos_file_manager_vectors:
        .word $B7E8
dos_adrvtoc:
        .word dos_vtoc_buffer
dos_adrdirbf:
        .word dos_catalog_buffer
dos_dosndpl1:
        .word dos_doslim
; Function 0..13 entry-minus-one table; 0 and 13 are null successful exits.
dos_file_function_table:
        .word dos_goodfmxt-1
        .word dos_fnopen-1
        .word dos_fnclose-1
        .word dos_fnread-1
        .word dos_fnwrite-1
        .word dos_fndelete-1
        .word dos_fncatlog-1
        .word dos_fnlock-1
        .word dos_fnunlock-1
        .word dos_fnrename-1
        .word dos_fnposn-1
        .word dos_fninit-1
        .word dos_fnverify-1
        .word dos_goodfmxt-1
; Read subfunctions: null, byte, range, positioned byte/range, null.
dos_file_read_table:
        .word dos_goodfmxt-1
        .word dos_readone-1
        .word dos_readrng-1
        .word dos_psnrdone-1
        .word dos_psnrdrng-1
        .word dos_goodfmxt-1
; Write subfunctions mirror reads. Native game uses DOS here only during startup.
dos_file_write_table:
        .word dos_goodfmxt-1
        .word dos_writeone-1
        .word dos_writerng-1
        .word dos_psnwrone-1
        .word dos_psnwrrng-1
        .word dos_goodfmxt-1
; $AAFD: X=0 allows creating files, other X requires an existing file.
; Parameters at $B5BB, per-file workspace through DOS buffer pointers.
dos_file_manager_external:
        cpx     #$00
        beq     dos_fmxtcmd
        ldx     #$02
dos_fmxtcmd:
        stx     dos_ndx2cmd
; $AB06: save stack, restore workspace, range-check opcode and RTS-dispatch.
; Carry and parameter return byte report status; clobbers registers and $40..$49.
dos_file_manager:
        tsx
        stx     dos_file_saved_stack
        jsr     dos_rstrfmwa
        lda     dos_file_parameters
        cmp     #$0D
        bcs     dos_toerrop
        asl     a
        tax
        lda     dos_file_function_table+1,x
        pha
        lda     dos_file_function_table,x
        pha
        rts

dos_toerrop:
        jmp     dos_rngerrop

; Open catalog file, create if allowed, and load its track/sector list.
dos_fnopen:
        jsr     dos_comnopen
        jmp     dos_goodfmxt

dos_comnopen:
        jsr     dos_zwrkarea
        lda     #$01
        sta     dos_secsizwa+1
        ldx     dos_recnmbfm+1
        lda     dos_recnmbfm
        bne     dos_streclen
        cpx     #$00
        bne     dos_streclen
        inx
dos_streclen:
        sta     dos_reclenwa
        stx     dos_reclenwa+1
        jsr     dos_getfntry
        bcc     dos_fillinwa
        stx     dos_curdirnx
        ldx     dos_ndx2cmd
        lda     dos_cmdattrb,x
        ldx     dos_curdirnx
        lsr     a
        bcs     dos_creatnew
dos_newillgl:
        lda     dos_condnflg
        cmp     #$C0
        bne     dos_tofilnot
        jmp     dos_lngnotav

dos_tofilnot:
        jmp     dos_filenot

dos_creatnew:
        lda     #$00
        sta     dos_fil1size+1,x
        lda     #$01
        sta     dos_fil1size,x
        stx     dos_curdirnx
        jsr     dos_asgntksc
        ldx     dos_curdirnx
        sta     dos_fil1tssc,x
        sta     dos_tsl1sec
        sta     dos_curtssec
        lda     dos_asigntrk
        sta     dos_fil1tstk,x
        sta     dos_file_workspace
        sta     dos_curtstrk
        lda     dos_filtypfm
        sta     dos_fil1type,x
        jsr     dos_wrdirect
        jsr     dos_seltsbuf
        jsr     clear_dos_page
        jsr     dos_writets
        ldx     dos_curdirnx
        lda     #$06
        sta     dos_rtncodfm
dos_fillinwa:
        lda     dos_fil1tstk,x
        sta     dos_file_workspace
        lda     dos_fil1tssc,x
        sta     dos_tsl1sec
        lda     dos_fil1type,x
        sta     dos_filtypfm
        sta     dos_filtypwa
        lda     dos_fil1size,x
        sta     dos_filensec
        lda     dos_fil1size+1,x
        sta     dos_filensec+1
        stx     dos_bytnxd1r
        lda     #$FF
        sta     dos_relprev
        sta     dos_relprev+1
        lda     dos_mxin1tsl
        sta     dos_mxscurts
        clc
        jmp     dos_readts

dos_zwrkarea:
        lda     #$00
        tax
dos_zerowrka:
        sta     dos_file_workspace,x
        inx
        cpx     #$2D
        bne     dos_zerowrka
        lda     dos_bytofffm
        eor     #$FF
        sta     dos_volwa
        lda     dos_drvfm
        sta     dos_drvwa
        lda     dos_slotfm
        asl     a
        asl     a
        asl     a
        asl     a
        tax
        stx     dos_slot16wa
        lda     #$11
        sta     dos_trkwa
        rts

; Flush dirty data/list and save workspace before releasing the buffer.
dos_fnclose:
        jsr     dos_ckdatup
        jsr     dos_cktsupdt
        jsr     dos_i
        lda     #$02
        and     dos_updatflg
        beq     dos_togdfmxt
        jsr     dos_readvtoc
        lda     #$00
        clc
dos_purgedir:
        jsr     dos_rddirect
        sec
        dec     dos_secnxd1r
        bne     dos_purgedir
        ldx     dos_bytnxd1r
        lda     dos_filensec
        sta     dos_fil1size,x
        lda     dos_filensec+1
        sta     dos_fil1size+1,x
        jsr     dos_wrdirect
dos_togdfmxt:
        jmp     dos_goodfmxt

dos_fnrename:
        jsr     dos_comnopen
        lda     dos_filtypwa
        bmi     dos_tofilock
        lda     dos_recnmbfm
        sta     $42
        lda     dos_recnmbfm+1
        sta     $43
        ldx     dos_curdirnx
        jsr     dos_nwdescrp
        jsr     dos_wrdirect
        jmp     dos_goodfmxt

; Dispatch selected byte/range/positioned read subfunction.
dos_fnread:
        lda     dos_subcodfm
        cmp     #$05
        bcs     dos_toerrsub
        asl     a
        tax
        lda     dos_file_read_table+1,x
        pha
        lda     dos_file_read_table,x
        pha
        rts

dos_toerrsub:
        jmp     dos_rngerrsb

dos_tofilock:
        jmp     dos_filelokd

; Dispatch selected byte/range/positioned write subfunction.
dos_fnwrite:
        lda     dos_filtypwa
        bmi     dos_tofilock
        lda     dos_subcodfm
        cmp     #$05
        bcs     dos_toerrsub
        asl     a
        tax
        lda     dos_file_write_table+1,x
        pha
        lda     dos_file_write_table,x
        pha
        rts

dos_psnrdone:
        jsr     dos_calcfptr
dos_readone:
        jsr     dos_rddata
        sta     dos_fnambufm
        jmp     dos_goodfmxt

dos_psnrdrng:
        jsr     dos_calcfptr
; Copy parameter-count bytes into caller buffer, traversing sectors as needed.
dos_readrng:
        jsr     dos_decrwlen
        jsr     dos_rddata
        pha
        jsr     dos_inciobuf
        ldy     #$00
        pla
        sta     ($42),y
        jmp     dos_readrng

dos_rddata:
        jsr     dos_nxtdatrd
        bcs     dos_ndaterr
        lda     ($42),y
        pha
        jsr     dos_increc
        jsr     dos_incfilpt
        pla
        rts

dos_ndaterr:
        jmp     dos_endofdat

dos_psnwrone:
        jsr     dos_calcfptr
dos_writeone:
        lda     dos_fnambufm
        jsr     dos_wrtdata
        jmp     dos_goodfmxt

dos_psnwrrng:
        jsr     dos_calcfptr
dos_writerng:
        jsr     dos_inciobuf
        ldy     #$00
        lda     ($42),y
        jsr     dos_wrtdata
        jsr     dos_decrwlen
        jmp     dos_writerng

dos_wrtdata:
        pha
        jsr     dos_nxtdatrd
        pla
        sta     ($42),y
        lda     #$40
        ora     dos_updatflg
        sta     dos_updatflg
        jsr     dos_increc
        jmp     dos_incfilpt

dos_fnlock:
        lda     #$80
        sta     dos_trk0yet
        bne     dos_comnlock
dos_fnunlock:
        lda     #$00
        sta     dos_trk0yet
dos_comnlock:
        jsr     dos_comnopen
        ldx     dos_curdirnx
        lda     dos_fil1type,x
        and     #$7F
        ora     dos_trk0yet
        sta     dos_fil1type,x
        jsr     dos_wrdirect
dos_tookfmxt:
        jmp     dos_goodfmxt

dos_fnposn:
        jsr     dos_calcfptr
        jmp     dos_goodfmxt

dos_fnverify:
        jsr     dos_comnopen
dos_vrfyread:
        jsr     dos_nxtdatrd
        bcs     dos_tookfmxt
        inc     dos_filptsec
        bne     dos_vrfyread
        inc     dos_filptsec+1
        jmp     dos_vrfyread

dos_fndelete:
        jsr     dos_comnopen
        ldx     dos_curdirnx
        lda     dos_fil1type,x
        bpl     dos_altrntry
        jmp     dos_filelokd

dos_altrntry:
        ldx     dos_curdirnx
        lda     dos_fil1tstk,x
        sta     dos_file_workspace
        sta     dos_fil1name+29,x
        lda     #$FF
        sta     dos_fil1tstk,x
        ldy     dos_fil1tssc,x
        sty     dos_tsl1sec
        jsr     dos_wrdirect
        clc
dos_rdts4del:
        jsr     dos_readts
        bcs     dos_donedel
        jsr     dos_seltsbuf
        ldy     #$0C
dos_delfree:
        sty     dos_curdirnx
        lda     ($42),y
        bmi     dos_bypasdel
        beq     dos_bypasdel
        pha
        iny
        lda     ($42),y
        tay
        pla
        jsr     dos_freesec
dos_bypasdel:
        ldy     dos_curdirnx
        iny
        iny
        bne     dos_delfree
        lda     dos_curtstrk
        ldy     dos_curtssec
        jsr     dos_freesec
        sec
        bcs     dos_rdts4del
dos_donedel:
        jsr     dos_writvtoc
        jmp     dos_goodfmxt

dos_freesec:
        sec
        jsr     dos_sub2free
        lda     #$00
        ldx     #$05
dos_releasec:
        sta     dos_asignsec,x
        dex
        bpl     dos_releasec
        rts

; Read linked directory sectors and print live filename/type/sector counts.
dos_fncatlog:
        jsr     dos_zwrkarea
        lda     #$FF
        sta     dos_volwa
        jsr     dos_readvtoc
        lda     #$16
        sta     dos_scrnsrch
        jsr     dos_crcatlog
        jsr     dos_crcatlog
        ldx     #$0B
dos_prdskvol:
        lda     dos_dskvolum,x
        jsr     rom_cout
        dex
        bpl     dos_prdskvol
        stx     $45
        lda     $B7F6
        sta     $44
        jsr     dos_prvolnmb
        jsr     dos_crcatlog
        jsr     dos_crcatlog
        clc
dos_rddirsec:
        jsr     dos_rddirect
        bcs     dos_tofmxtok
        ldx     #$00
dos_descrptk:
        stx     dos_curdirnx
        lda     dos_fil1tstk,x
        beq     dos_tofmxtok
        bmi     dos_nxdescrp
        ldy     #$A0
        lda     dos_fil1type,x
        bpl     dos_prlocode
        ldy     #$AA
dos_prlocode:
        tya
        jsr     rom_cout
        lda     dos_fil1type,x
        and     #$7F
        ldy     #$07
        asl     a
dos_chrtypix:
        asl     a
        bcs     dos_prtftype
        dey
        bne     dos_chrtypix
dos_prtftype:
        lda     dos_ftypetbl,y
        jsr     rom_cout
        lda     #$A0
        jsr     rom_cout
        lda     dos_fil1size,x
        sta     $44
        lda     dos_fil1size+1,x
        sta     $45
        jsr     dos_prvolnmb
        lda     #$A0
        jsr     rom_cout
        inx
        inx
        inx
        ldy     #$1D
dos_prtfname:
        lda     dos_fil1tstk,x
        jsr     rom_cout
        inx
        dey
        bpl     dos_prtfname
        jsr     dos_crcatlog
dos_nxdescrp:
        jsr     dos_nxplus35
        bcc     dos_descrptk
        bcs     dos_rddirsec
dos_tofmxtok:
        jmp     dos_goodfmxt

dos_crcatlog:
        lda     #$8D
        jsr     rom_cout
        dec     dos_scrnsrch
        bne     dos_crcatrtn
        jsr     rom_read_key
        lda     #$15
        sta     dos_scrnsrch
dos_crcatrtn:
        rts

dos_prvolnmb:
        ldy     #$02
dos_zonstk:
        lda     #$00
        pha
dos_getvnmb:
        lda     $44
        cmp     dos_baseten,y
        bcc     dos_tonegasc
        sbc     dos_baseten,y
        sta     $44
        lda     $45
        sbc     #$00
        sta     $45
        pla
        adc     #$00
        pha
        jmp     dos_getvnmb

dos_tonegasc:
        pla
        ora     #$B0
        jsr     rom_cout
        dey
        bpl     dos_zonstk
        rts

; Copy 45-byte workspace from the current DOS chain buffer into $B5D1.
dos_rstrfmwa:
        jsr     dos_selwkbuf
        ldy     #$00
        sty     dos_rtncodfm
dos_storfmwk:
        lda     ($42),y
        sta     dos_file_workspace,y
        iny
        cpy     #$2D
        bne     dos_storfmwk
        clc
        rts

; Copy the resident workspace back to its per-file chain buffer.
dos_cpyfmwa:
        jsr     dos_selwkbuf
        ldy     #$00
dos_storwrk:
        lda     dos_file_workspace,y
        sta     ($42),y
        iny
        cpy     #$2D
        bne     dos_storwrk
        rts

; Format via RWTS, initialize VTOC/directory and write DOS image; not a gameplay path.
dos_fninit:
        jsr     dos_zwrkarea
        lda     #$04
        jsr     dos_rwtsdrv1
        lda     dos_volwa
        eor     #$FF
        sta     dos_volused
        lda     #$11
        sta     dos_nxtrkuse
        lda     #$01
        sta     dos_drection
        ldx     #$38
        lda     #$00
dos_zvtoc:
        sta     dos_vtoc_buffer,x
        inx
        bne     dos_zvtoc
        ldx     #$0C
dos_freetrk:
        cpx     #$8C
        beq     dos_freedtks
        ldy     #$03
dos_freeit:
        lda     dos_fretkmsk,y
        sta     dos_fresecmap,x
        inx
        dey
        bpl     dos_freeit
        cpx     #$44
        bne     dos_freetrk
        ldx     #$48
        bne     dos_freetrk
dos_freedtks:
        jsr     dos_writvtoc
        ldx     #$00
        txa
dos_clrdirec:
        sta     dos_catalog_buffer,x
        inx
        bne     dos_clrdirec
        jsr     dos_pt2dirbf
        lda     #$11
        ldy     dos_secpertk
        dey
        dey
        sta     $B7EC
dos_setlnktk:
        sta     dos_dirlnktk
dos_setlnksc:
        sty     dos_dirlnksc
        iny
        sty     $B7ED
        lda     #$02
        jsr     dos_rwtsdrv1
        ldy     dos_dirlnksc
        dey
        bmi     dos_doimage
        bne     dos_setlnksc
        tya
        beq     dos_setlnktk
dos_doimage:
        jsr     prepare_dos_file_iob
        jsr     reload_dos_pages
        jmp     dos_goodfmxt

dos_selwkbuf:
        ldx     #$00
        beq     dos_pt2fmbuf
dos_seltsbuf:
        ldx     #$02
        bne     dos_pt2fmbuf
dos_seldabuf:
        ldx     #$04
dos_pt2fmbuf:
        lda     dos_wrkbuffm,x
        sta     $42
        lda     dos_wrkbuffm+1,x
        sta     $43
        rts

dos_ckdatup:
        bit     dos_updatflg
        bvs     dos_writdata
        rts

dos_writdata:
        jsr     dos_prpdaiob
        lda     #$02
        jsr     dos_rwtsdrvr
        lda     #$BF
        and     dos_updatflg
        sta     dos_updatflg
        rts

dos_cktsupdt:
        lda     dos_updatflg
        bmi     dos_writets
        rts

dos_writets:
        jsr     dos_settsiob
        lda     #$02
        jsr     dos_rwtsdrvr
        lda     #$7F
        and     dos_updatflg
        sta     dos_updatflg
        rts

dos_settsiob:
        lda     dos_tsbuffm
        sta     $B7F0
        lda     dos_tsbuffm+1
        sta     $B7F1
        ldx     dos_curtstrk
        ldy     dos_curtssec
        rts

dos_readts:
        php
        jsr     dos_cktsupdt
        jsr     dos_settsiob
        jsr     dos_seltsbuf
        plp
        bcs     dos_rdnxtts
dos_rdfirsts:
        ldx     dos_file_workspace
        ldy     dos_tsl1sec
        jmp     dos_rdtslst

dos_rdnxtts:
        ldy     #$01
        lda     ($42),y
        beq     dos_tslnkzro
        tax
        iny
        lda     ($42),y
        tay
        jmp     dos_rdtslst

dos_tslnkzro:
        lda     dos_file_parameters
        cmp     #$04
        beq     dos_updatets
        sec
        rts

dos_updatets:
        jsr     dos_asgntksc
dos_lnkoldnw:
        ldy     #$02
        sta     ($42),y
        pha
        dey
        lda     dos_asigntrk
        sta     ($42),y
        pha
        jsr     dos_writets
dos_zoutts:
        jsr     clear_dos_page
        ldy     #$05
        lda     dos_relastp1
        sta     ($42),y
        iny
        lda     dos_relastp1+1
        sta     ($42),y
        pla
        tax
        pla
        tay
        lda     #$02
        bne     dos_rdwrts
; Read and validate track/sector list; supports linked lists past 122 sector pairs.
dos_rdtslst:
        lda     #$01
dos_rdwrts:
        stx     dos_curtstrk
        sty     dos_curtssec
        jsr     dos_rwtsdrvr
        ldy     #$05
        lda     ($42),y
        sta     dos_relfirst
        clc
        adc     dos_mxscurts
        sta     dos_relastp1
        iny
        lda     ($42),y
        sta     dos_relfirst+1
        adc     dos_mxscurts+1
        sta     dos_relastp1+1
        clc
        rts

dos_readdata:
        jsr     dos_prpdaiob
        lda     #$01
        jmp     dos_rwtsdrvr

dos_prpdaiob:
        ldy     dos_datbuffm
        lda     dos_datbuffm+1
        sty     $B7F0
        sta     $B7F1
        ldx     dos_curdatrk
        ldy     dos_curdatsc
        rts

dos_readvtoc:
        lda     #$01
        bne     dos_rdwrvtoc
dos_writvtoc:
        lda     #$02
dos_rdwrvtoc:
        ldy     dos_adrvtoc
        sty     $B7F0
        ldy     dos_adrvtoc+1
        sty     $B7F1
        ldx     dos_trkwa
        ldy     #$00
        jmp     dos_rwtsdrvr

dos_rddirect:
        php
        jsr     dos_pt2dirbf
        plp
        bcs     dos_rdnxtdir
dos_rdfirdir:
        ldy     dos_firdirsc
        ldx     dos_firdirtk
        bne     dos_dodirrd
dos_rdnxtdir:
        ldx     dos_dirlnktk
        bne     dos_getdirlk
        sec
        rts

dos_getdirlk:
        ldy     dos_dirlnksc
dos_dodirrd:
        stx     dos_curdirtk
        sty     dos_curdirsc
        lda     #$01
        jsr     dos_rwtsdrvr
        clc
        rts

dos_wrdirect:
        jsr     dos_pt2dirbf
        ldx     dos_curdirtk
        ldy     dos_curdirsc
        lda     #$02
        jmp     dos_rwtsdrvr

dos_pt2dirbf:
        lda     dos_adrdirbf
        sta     $B7F0
        lda     dos_adrdirbf+1
        sta     $B7F1
        rts

; X=track,Y=sector,A=command; populate bootstrap IOB then call masked RWTS.
; Translate RWTS status into DOS file-manager errors. Buffer pointer is set separately.
dos_rwtsdrvr:
        stx     $B7EC
        sty     $B7ED
dos_rwtsdrv1:
        sta     $B7F4
        cmp     #$02
        bne     dos_skpwrset
        ora     dos_updatflg
        sta     dos_updatflg
dos_skpwrset:
        lda     dos_volwa
        eor     #$FF
        sta     $B7EB
        lda     dos_slot16wa
        sta     $B7E9
        lda     dos_drvwa
        sta     $B7EA
        lda     dos_secsizwa
        sta     $B7F2
        lda     dos_secsizwa+1
        sta     $B7F3
        lda     #$01
        sta     $B7E8
        ldy     dos_file_manager_vectors
        lda     dos_file_manager_vectors+1
        jsr     call_rwts_interrupt_masked
        lda     $B7F6
        sta     dos_bytofffm
        lda     #$FF
        sta     $B7EB
        bcs     dos_errwtsdr
        rts

dos_errwtsdr:
        lda     $B7F5
        ldy     #$07
        cmp     #$20
        beq     dos_setfmerr
        ldy     #$04
        cmp     #$10
        beq     dos_setfmerr
        ldy     #$08
dos_setfmerr:
        tya
        jmp     dos_file_error_exit

dos_nxtdatrd:
        lda     dos_filptsec
        cmp     dos_relprev
        bne     dos_ckwcurda
        lda     dos_filptsec+1
        cmp     dos_relprev+1
        beq     dos_xitnxdat
dos_ckwcurda:
        jsr     dos_ckdatup
dos_ckcurts:
        lda     dos_filptsec+1
        cmp     dos_relfirst+1
        bcc     dos_neednxts
        bne     dos_ckcurts1
        lda     dos_filptsec
        cmp     dos_relfirst
        bcc     dos_neednxts
dos_ckcurts1:
        lda     dos_filptsec+1
        cmp     dos_relastp1+1
        bcc     dos_getdatpr
        bne     dos_neednxts
        lda     dos_filptsec
        cmp     dos_relastp1
        bcc     dos_getdatpr
dos_neednxts:
        jsr     dos_readts
        bcc     dos_ckcurts
        rts

dos_getdatpr:
        sec
        lda     dos_filptsec
        sbc     dos_relfirst
        asl     a
        adc     #$0C
        tay
        jsr     dos_seltsbuf
        lda     ($42),y
        bne     dos_rddatsec
        lda     dos_file_parameters
        cmp     #$04
        beq     dos_newpair
        sec
        rts

dos_newpair:
        jsr     dos_nwdatksc
        jmp     dos_setprev

dos_rddatsec:
        sta     dos_curdatrk
        iny
        lda     ($42),y
        sta     dos_curdatsc
        jsr     dos_readdata
dos_setprev:
        lda     dos_filptsec
        sta     dos_relprev
        lda     dos_filptsec+1
        sta     dos_relprev+1
dos_xitnxdat:
        jsr     dos_seldabuf
        ldy     dos_filptbyt
        clc
        rts

dos_nwdatksc:
        sty     dos_scrnsrch
        jsr     dos_asgntksc
        ldy     dos_scrnsrch
        iny
        sta     ($42),y
        sta     dos_curdatsc
        dey
        lda     dos_asigntrk
        sta     ($42),y
        sta     dos_curdatrk
        jsr     dos_seldabuf
dos_zoutdat:
        jsr     clear_dos_page
        lda     #$C0
        ora     dos_updatflg
        sta     dos_updatflg
        rts

dos_increc:
        ldx     dos_recnmbwa
        stx     dos_recnmbfm
        ldx     dos_recnmbwa+1
        stx     dos_recnmbfm+1
        ldx     dos_bytoffwa
        ldy     dos_bytoffwa+1
        stx     dos_bytofffm
        sty     dos_drvfm
        inx
        bne     dos_bytvsrec
        iny
dos_bytvsrec:
        cpy     dos_reclenwa+1
dos_kikoff1:
        bne     dos_setbytof
        cpx     dos_reclenwa
dos_kikoff2:
        bne     dos_setbytof
        ldx     #$00
        ldy     #$00
        inc     dos_recnmbwa
dos_nokikoff:
        bne     dos_setbytof
        inc     dos_recnmbwa+1
dos_setbytof:
        stx     dos_bytoffwa
        sty     dos_bytoffwa+1
        rts

dos_incfilpt:
        inc     dos_filptbyt
        bne     dos_incptrtn
        inc     dos_filptsec
        bne     dos_incptrtn
        inc     dos_filptsec+1
dos_incptrtn:
        rts

dos_inciobuf:
        ldy     dos_fnambufm
        ldx     dos_fnambufm+1
        sty     $42
        stx     $43
        inc     dos_fnambufm
        bne     dos_inciortn
        inc     dos_fnambufm+1
dos_inciortn:
        rts

dos_decrwlen:
        ldy     dos_slotfm
        bne     dos_declenrw
        ldx     dos_filtypfm
        beq     dos_rwlen0
        dec     dos_filtypfm
dos_declenrw:
        dec     dos_slotfm
        rts

dos_rwlen0:
        jmp     dos_goodfmxt

dos_getfntry:
        jsr     dos_readvtoc
        lda     dos_fnambufm
        sta     $42
        lda     dos_fnambufm+1
        sta     $43
        lda     #$01
dos_setsrch:
        sta     dos_scrnsrch
        lda     #$00
        sta     dos_secnxd1r
        clc
dos_getdirsc:
        inc     dos_secnxd1r
        jsr     dos_rddirect
        bcs     dos_chngsrch
        ldx     #$00
dos_ckdirtrk:
        stx     dos_curdirnx
        lda     dos_fil1tstk,x
        beq     dos_chrsrcha
        bmi     dos_chrsrchb
        ldy     #$00
        inx
        inx
dos_cmpnames:
        inx
        lda     ($42),y
        cmp     dos_fil1tstk,x
        bne     dos_dontmtch
        iny
        cpy     #$1E
        bne     dos_cmpnames
        ldx     dos_curdirnx
        clc
        rts

dos_dontmtch:
        jsr     dos_nxplus35
        bcc     dos_ckdirtrk
        bcs     dos_getdirsc
dos_chrsrcha:
        ldy     dos_scrnsrch
        bne     dos_setsrch
dos_chrsrchb:
        ldy     dos_scrnsrch
        bne     dos_dontmtch
dos_nwdescrp:
        ldy     #$00
        inx
        inx
dos_setnwnam:
        inx
        lda     ($42),y
        sta     dos_fil1tstk,x
        iny
        cpy     #$1E
        bne     dos_setnwnam
        ldx     dos_curdirnx
        sec
        rts

dos_nxplus35:
        clc
        lda     dos_curdirnx
        adc     #$23
        tax
        cpx     #$F5
        rts

dos_chngsrch:
        lda     #$00
        ldy     dos_scrnsrch
        bne     dos_setsrch
        jmp     dos_diskfull

dos_asgntksc:
        lda     dos_asigntrk
        beq     dos_prpnwtrk
dos_anyavail:
        dec     dos_asignsec
        bmi     dos_asgnwtrk
        clc
        ldx     #$04
dos_adjstmap:
        rol     dos_asigntrk,x
        dex
        bne     dos_adjstmap
        bcc     dos_anyavail
        inc     dos_filensec
        bne     dos_xwithfre
        inc     dos_filensec+1
dos_xwithfre:
        lda     dos_asignsec
        rts

dos_asgnwtrk:
        lda     #$00
        sta     dos_asigntrk
dos_prpnwtrk:
        lda     #$00
        sta     dos_trk0yet
        jsr     dos_readvtoc
dos_getnwtrk:
        clc
        lda     dos_nxtrkuse
        adc     dos_drection
        beq     dos_ckiffull
        cmp     dos_tkperdsk
        bcc     dos_chk4free
        lda     #$FF
        bne     dos_srch4trk
dos_ckiffull:
        lda     dos_trk0yet
        bne     dos_todskful
        lda     #$01
        sta     dos_trk0yet
dos_srch4trk:
        sta     dos_drection
        clc
        adc     #$11
dos_chk4free:
        sta     dos_nxtrkuse
        sta     dos_asigntrk
        tay
        asl     a
        asl     a
        tay
        ldx     #$04
        clc
dos_cpytkmap:
        lda     dos_fresecmap+3,y
        sta     dos_asigntrk,x
        beq     dos_nxmapbyt
        sec
        lda     #$00
        sta     dos_fresecmap+3,y
dos_nxmapbyt:
        dey
        dex
        bne     dos_cpytkmap
        bcc     dos_getnwtrk
        jsr     dos_writvtoc
        lda     dos_secpertk
        sta     dos_asignsec
        bne     dos_anyavail
dos_todskful:
        jmp     dos_diskfull

dos_i:  lda     dos_asigntrk
        bne     dos_freextra
        rts

dos_freextra:
        pha
        jsr     dos_readvtoc
        ldy     dos_asignsec
        pla
        clc
        jsr     dos_sub2free
        lda     #$00
        sta     dos_asigntrk
        jmp     dos_writvtoc

dos_sub2free:
        ldx     #$FC
dos_stndard:
        ror     dos_fil1size+15,x
        inx
        bne     dos_stndard
        iny
        cpy     dos_secpertk
        bne     dos_sub2free
        asl     a
        asl     a
        tay
        beq     dos_sub2rtn
        ldx     #$04
dos_mergmaps:
        lda     dos_asigntrk,x
        ora     dos_fresecmap+3,y
        sta     dos_fresecmap+3,y
        dey
        dex
        bne     dos_mergmaps
dos_sub2rtn:
        rts

dos_calcfptr:
        lda     dos_recnmbfm
        sta     dos_filptbyt
        sta     dos_recnmbwa
        lda     dos_recnmbfm+1
        sta     dos_filptsec
        sta     dos_recnmbwa+1
        lda     #$00
        sta     dos_filptsec+1
        ldy     #$10
dos_nmbxlen:
        tax
        lda     dos_filptbyt
        lsr     a
        bcs     dos_nmbxlen1
        txa
        bcc     dos_nmbxlen2
dos_nmbxlen1:
        clc
        lda     dos_filptsec+1
        adc     dos_reclenwa
        sta     dos_filptsec+1
        txa
        adc     dos_reclenwa+1
dos_nmbxlen2:
        ror     a
        ror     dos_filptsec+1
        ror     dos_filptsec
        ror     dos_filptbyt
        dey
        bne     dos_nmbxlen
        lda     dos_bytofffm
        sta     dos_bytoffwa
        adc     dos_filptbyt
        sta     dos_filptbyt
        lda     dos_drvfm
        sta     dos_bytoffwa+1
        adc     dos_filptsec
        sta     dos_filptsec
        lda     #$00
        adc     dos_filptsec+1
        sta     dos_filptsec+1
dos_calcrts:
        rts

dos_lngnotav:
        lda     #$01
        bne     dos_file_error_exit
dos_rngerrop:
        lda     #$02
        bne     dos_file_error_exit
dos_rngerrsb:
        lda     #$03
        bne     dos_file_error_exit
dos_writprot:
        lda     #$04
        bne     dos_file_error_exit
dos_endofdat:
        lda     #$05
        bne     dos_file_error_exit
dos_filenot:
        lda     #$06
        bne     dos_file_error_exit
dos_diskfull:
        jmp     dos_close_with_stack_recovery

        nop
dos_filelokd:
        lda     #$0A
        bne     dos_file_error_exit
dos_goodfmxt:
        lda     dos_rtncodfm
        clc
        bcc     dos_file_return
; Carry set for file error; shared return stores status and restores saved stack.
dos_file_error_exit:
        sec
dos_file_return:
        php
        sta     dos_rtncodfm
        lda     #$00
        sta     $48
        jsr     dos_cpyfmwa
        plp
        ldx     dos_file_saved_stack
        txs
        rts

dos_curdirtk:
        .byte   $11
dos_curdirsc:
        .byte   $0F
dos_wabufadr:
        .byte   $00,$00
dos_file_saved_stack:
        .byte   $EE
dos_curdirnx:
        .byte   $46
dos_scrnsrch:
        .byte   $01
dos_trk0yet:
        .byte   $00,$00
dos_fretkmsk:
        .byte   $00,$00,$FF,$FF
dos_baseten:
        .byte   $01,$0A,$64
dos_ftypetbl:
        .byte   $D4,$C9,$C1,$C2,$D3,$D2,$C1,$C2
dos_dskvolum:
        .byte   $A0,$C5,$CD,$D5,$CC,$CF,$D6,$A0
        .byte   $CB,$D3,$C9,$C4
; $B3BB..$B4BA: one 256-byte VTOC buffer, including allocation bitmap.
dos_vtoc_buffer:
        .byte   $04
dos_firdirtk:
        .byte   $11
dos_firdirsc:
        .byte   $0F
dos_dosversion:
        .byte   $03,$00,$00
dos_volused:
        .byte   $FE,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00
dos_mxin1tsl:
        .byte   $7A,$00,$00,$00,$00,$00,$00,$00
        .byte   $00
dos_nxtrkuse:
        .byte   $11
dos_drection:
        .byte   $01,$00,$00
dos_tkperdsk:
        .byte   $23
dos_secpertk:
        .byte   $10
dos_bytpersc:
        .byte   $00,$01
dos_fresecmap:
        .byte   $00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$00,$00,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$FF,$FF,$00,$00,$FF,$FF,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00
; $B4BB..$B5BA: one 256-byte catalog-sector buffer.
dos_catalog_buffer:
        .byte   $00
dos_dirlnktk:
        .byte   $00
dos_dirlnksc:
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00
dos_fil1tstk:
        .byte   $00
dos_fil1tssc:
        .byte   $00
dos_fil1type:
        .byte   $00
dos_fil1name:
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00
        .byte   $00
dos_fil1size:
        .byte   $00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00,$00,$00,$00,$00,$00,$00,$00
        .byte   $00
        .byte   $00
; $B5BB..$B5D0: 22-byte public parameter block (opcode/subfunction, counts, buffers).
dos_file_parameters:
        .byte   $0B
dos_subcodfm:
        .byte   $9D
dos_recnmbfm:
        .byte   $01
        .byte   $00
dos_bytofffm:
        .byte   $FE
dos_drvfm:
        .byte   $02
dos_slotfm:
        .byte   $06
dos_filtypfm:
        .byte   $00
dos_fnambufm:
        .byte   $75
        .byte   $AA
dos_rtncodfm:
        .byte   $00,$00
dos_wrkbuffm:
        .byte   $00
        .byte   $98
dos_tsbuffm:
        .byte   $00
        .byte   $97
dos_datbuffm:
        .byte   $00
        .byte   $96
dos_nxtname:
        .byte   $00,$00,$00,$00
; $B5D1..$B5FA: structured workspace; five trailing padding bytes.
; Native workspace copy includes 45 bytes ($B5D1..$B5FD).
dos_file_workspace:
        .byte   $00
dos_tsl1sec:
        .byte   $00
dos_curtstrk:
        .byte   $00
dos_curtssec:
        .byte   $00
dos_updatflg:
        .byte   $02
dos_curdatrk:
        .byte   $00
dos_curdatsc:
        .byte   $00
dos_secnxd1r:
        .byte   $00
dos_bytnxd1r:
        .byte   $00
dos_mxscurts:
        .byte   $00
        .byte   $00
dos_relfirst:
        .byte   $00
        .byte   $00
dos_relastp1:
        .byte   $00
        .byte   $00
dos_relprev:
        .byte   $00
        .byte   $00
dos_secsizwa:
        .byte   $00
        .byte   $00
dos_filptsec:
        .byte   $00
        .byte   $00
dos_filptbyt:
        .byte   $00
dos_wastebyt:
        .byte   $00
dos_reclenwa:
        .byte   $00
        .byte   $00
dos_recnmbwa:
        .byte   $00
        .byte   $00
dos_bytoffwa:
        .byte   $00
        .byte   $00
dos_filensec:
        .byte   $00
        .byte   $00
dos_asignsec:
        .byte   $00
dos_asigntrk:
        .byte   $00
dos_asignmap:
        .byte   $00,$00,$00,$00
dos_filtypwa:
        .byte   $00
dos_slot16wa:
        .byte   $60
dos_drvwa:
        .byte   $02
dos_volwa:
        .byte   $01
dos_trkwa:
        .byte   $11,$00,$00,$00,$00
        .byte   $00

.assert dos_cold_start = $9D84, error, "DOS cold start moved"
.assert dos_output_intercept = $9EBD, error, "DOS output hook moved"
.assert dos_command_bload = $A35D, error, "DOS BLOAD moved"
.assert dos_file_manager = $AB06, error, "file manager moved"
.assert * = $B600, error, "DOS main/file manager must occupy 27 pages"

