# Startup DOS and file manager

`src/dos-low.s` reconstructs the 27 native pages at $9B00–$B5FF. Together with
`src/boot-a.s`, `src/boot-stage2.inc` and `src/rwts.inc`, it provides source for
all 37 pages actually loaded as side-A DOS. Source instructions are decoded from
the supplied native sectors; lookup tables, buffers and saved workspace are
explicit data. No executable span is included as a binary blob.

## Startup and lifetime

The first two pages, $9B00–$9CFF, are entirely zero in this supplied copy.
The standard relocator is absent. The bootstrap already places DOS at its
fixed destination and enters `dos_cold_start` at $9D84. This entry selects the
BASIC variant, installs intercept hooks, initializes DOS buffers and public
page-three vectors, then processes the pending startup command.

At $9E42 the native command index is $14, which selects EXEC. `START` is a
catalog text file, not tokenized BASIC. Its high-bit text issues:

```text
POKE1012,0:HGR:HGR2
BLOAD ADVEN INTERP.OBJ,A$800
BLOAD PARMS.OBJ,A$300
CALL2048
```

EXEC supplies these lines to Applesoft/DOS. BLOAD reads the binary headers and
uses the explicit destination options. `CALL2048` enters the resident game
interpreter at $0800. Its custom loader subsequently loads full allocated files
and calls retained $BD00 RWTS directly; see [engine.md](engine.md) and
[boot-loading.md](boot-loading.md). This differs from DOS BLOAD's header/payload
interface.

DOS's normal character-output intercept begins at $9EBD. The observed $A000
entry in boot traces is `dos_check_control_character`, within command parsing,
rather than the start of the intercept itself. Later vector graphics load at
$9C00 and CHAR GEN loads at $ADFC, overwriting portions of startup DOS. The game
uses its resident interpreter, intrinsic library and high-memory RWTS thereafter.
DOS startup code is required to reach the game; its full command set is retained
but not assumed callable after those overlapping loads.

## Interfaces and tables

| Address/span | Source symbols | Contract |
| --- | --- | --- |
| $9D00–$9D0F | `dos_address_table` | Eight public address constants, including hook, filename and parameter pointers. |
| $9D10–$9D1D | `dos_output_handler_table` | Seven output-state entry-minus-one vectors. |
| $9D1E–$9D55 | `dos_command_table` | 28 DOS command entry-minus-one vectors. |
| $9D56–$9D83 | BASIC vector tables | Mutable active vectors and Integer/ROM/RAM Applesoft templates. |
| $9D84 | `dos_cold_start` | Initialize native DOS/BASIC and execute startup text. |
| $9DBF | `dos_warm_start` | Reinstall hooks and reenter selected BASIC. |
| $9E51–$9E80 | `dos_imgdosvt` | 48-byte image copied to $03D0–$03FF; JMP vectors and pointer-return routines. |
| $9E81/$9EBD | Input/output intercepts | Preserve DOS's saved registers, select keyboard/EXEC/READ or output-state handler. |
| $A35D | `dos_command_bload` | Open binary, read address/length, copy payload to selected destination. |
| $A6A8 | `dos_file_manager_driver` | Call file manager, inspect carry/status and recover DOS command input. |
| $A884–$A908 | `dos_cmdtxtbl` | Low-bit command spelling, high-bit last character, zero terminator. |
| $A909–$A940 | `dos_cmdattrb` | Two attribute bytes for each command. |
| $A941–$AA4C | Options/error text | Option codes, masks/ranges, message pool and error offsets. |
| $AA4D–$AAC0 | DOS state | Current-file/register/pointer state, parsed options, filename buffers and defaults. |
| $AAC1–$AAC8 | `dos_file_manager_vectors` | IOB, VTOC, directory and DOS-limit pointers. |
| $AAC9–$AAFC | File/read/write dispatch tables | Entry-minus-one vectors, entered through a stack jump and RTS. |
| $AAFD | `dos_file_manager_external` | X=0 allows file creation; other X requires an existing file. |
| $AB06 | `dos_file_manager` | Save stack, restore current workspace, validate opcode and dispatch. |
| $B385/$B386 | Error/shared return | Store status, save workspace, recover stack and return with carry. |
| $B397–$B3BA | File-manager constants | Directory position, stack, masks, decimal digits and file-type text. |
| $B3BB–$B4BA | `dos_vtoc_buffer` | One 256-byte VTOC/allocation buffer. |
| $B4BB–$B5BA | `dos_catalog_buffer` | One 256-byte catalog buffer. |
| $B5BB–$B5D0 | `dos_file_parameters` | 22-byte public parameter block. |
| $B5D1–$B5FF | Workspace/padding | Structured fields through $B5FA, then five unused bytes. Workspace copying covers 45 bytes through $B5FD. |

The file-manager parameter block holds opcode/subfunction at +0/+1, a two-byte
count or record parameter at +2, byte offset/volume at +4, drive at +5, slot at
+6, file type at +7, filename/data pointer at +8/+9, status at +10, workspace
pointer at +12, track/sector-list pointer at +14 and sector-data pointer at +16.
Fields are reused by different functions; inspect the selected handler before
changing them.

File functions open, close, read, write, delete, catalog, lock, unlock, rename,
position, initialize and verify. Reads/writes offer byte and range operations,
including positioned variants. Track/sector-list traversal handles linked lists
of up to 122 sector pairs per list. Dirty data and list buffers are flushed
before movement/close. Allocation uses the VTOC bitmap and directory links.
`dos_rwtsdrvr` accepts X=track, Y=sector, A=command, builds the bootstrap IOB at
$B7E8 and calls `call_rwts_interrupt_masked`. RWTS carry/status becomes a DOS
error code. The file manager changes A/X/Y, $40–$49 and saved stack/workspace;
it is not a register-preserving subroutine.

Native append/error paths use the already assembled helpers at $B65E–$B6B1.
These are file-manager helpers in this copy, not the standard RAM-detection
routines sometimes found at similar addresses in other DOS versions.

## Symbols and provenance

Descriptive public names identify the major interfaces and commands. Internal
`dos_` symbols retain conventional abbreviated DOS vocabulary: `fn` denotes
file-manager function, `cmd` command, `prsd` parsed option, `fm` file manager,
`wa` workspace, `ts` track/sector, `vtoc` allocation table, and `rtn` return.
Offsets such as `dos_adinptcp+1` identify a high byte rather than inventing a
separate numeric label. Vector tables use source symbols; encoded text and
native saved variables retain explicit bytes.

The assembly is code/data authority; native sector streams are provenance
references. Routine identities and
table/workspace boundaries were checked against the independently maintained
[Apple II DOS transcription](https://github.com/cmosher01/Apple-II-Source/tree/master/src/dos/system/common).
That reference was assembled only as a local analysis aid to locate symbols;
its executable source is not a build dependency or imported implementation.
Native differences include cleared relocation pages, the EXEC startup selector,
BASIC vectors, captured workspace and patched helpers. Source represents those
differences directly.

## Build and validation

The build splits the assembled 6912 bytes into T0/S10–15 ($9B00–$A0FF),
T1/S0–15 ($A100–$B0FF) and T2/S0–4 ($B100–$B5FF). It checks source size,
entry addresses, complete source mapping, asset bounds and overlapping writes.
The unbooted side-B wrapper differs at startup index6/RUN and places only the
retained T0/S10–15 and T2/S3–4 fragments. The rest of its emitted source is unused;
it never replaces side-B live file data or runs during a normal media swap.
Symbols are emitted with debug information for source navigation.

Boot and opening replays exercise EXEC START, BLOAD, native DOS sector reads and
the transition to the game. Current native encoding equality is diagnostic.
Formatting, the entire DOS command set, RAM Applesoft and optional language-card
paths are not covered by these gameplay checks. Unloaded disk residue is
classified in [disk-layout.md](disk-layout.md). Intrinsics/CHAR GEN are complete
source, and fonts/pictures are editable inputs. This does not claim exhaustive
DOS command testing or close the remaining overall validation audit.
