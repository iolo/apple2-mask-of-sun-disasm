# Resident interpreter and interfaces

[interpreter.s](../src/interpreter.s) reconstructs the 1,280-byte payload of
`ADVEN INTERP.OBJ` at $0800–$0CFF. The native DOS binary header is four bytes;
the startup script BLOADs the payload at $0800 and calls it. The file's complete
allocated stream includes header and trailing bytes, which the repacker preserves
separately from the authoritative assembled payload.

At entry the interpreter resets the hardware stack, establishes pointers from
the $0300 parameter block, installs its intrinsic dispatch and helper vectors,
and loads `INITIAL`, `LIBRARY`, `INTRIN.OBJ` and `CHAR GEN`. It enables HGR1,
full-screen graphics and installs the character renderer. `INITIAL` initializes
game variables and then transfers to room 1. The initial game code is therefore
already scripting an interpreted room before the first prompt.

## Script control

The main dispatch at $08A8 distinguishes high-bit-dot action/directive lines
from command patterns. Directive execution calls $0D00 in `INTRIN.OBJ`. Nested
script action calls save a two-byte pattern pointer on the hardware stack;
return scanning restores it. A stack-depth guard prints an error before crossing
its allowed range. The general script line scanner recognizes $8D CR; the
`@@@@@` terminator transfers matching into the resident library pointer.

These roles are supported by source and runtime room/script content. Detailed
intrinsic opcode, condition/carry and timed-poll conventions remain under analysis.
The disassembly explicitly distinguishes saved prefix bytes, the input prompt
length and the RWTS parameter block from code.

| Memory | Current role |
| --- | --- |
| $0300 | Prompt length and high-bit prompt characters |
| $0310/$0311 | Initial script load base (observed $6800) |
| $031C/$031D | Resident library load base (observed $7000) |
| $0328/$0329 | Intrinsic allocated-stream base ($0CFC; payload $0D00) |
| $0334/$0335 | CHAR GEN allocated-stream base ($ADFC) |
| $0340/$0341 | Raw input buffer ($0250 in supplied parameters) |
| $0342/$0343 | Normalized command scratch base |
| $0344/$0345 | Script string printer ($0BF3) |
| $034A/$034B | Interpreter dispatch ($08A8) |
| $034C/$034D | Named file loader ($0B20) |
| $C0–$C5 | Raw input/chain start/end pointers |
| $D0/$D1 | Active normalized pattern/return frame |
| $D2/$D3 | Script instruction pointer |
| $D4/$D5, $EE/$EF | Current room script base |
| $DA/$DB | Library script base |
| $DC/$DD | Normalized-command scratch base |
| $DE | Pattern match result ($FF or 0) |
| $DF, $E0–$EB | Shared parser/file/string scratch |
| $EC/$ED | File destination pointer; updated next page |
| $F0/$F1 | Prompt/parameter base ($0300) |

This is a provisional resident map, not a complete zero-page ownership map.
Intrinsic/graphics routines share additional workspace and still need their
interfaces documented. Assembly comments state known register clobbers for
the reconstructed routines rather than asserting registers are preserved.

The intrinsic variable lookup table at $13CC uses four-byte entries: two
high-bit name characters followed by a little-endian address. Its native
contents and a runtime capture establish the following additional map:

| Script name | Address |
| --- | --- |
| A–P | $6000–$600F, one byte each |
| Q / R | $C000 keyboard latch / $C010 strobe clear |
| W / Z | $0205 command scratch / $C061 game button |
| S,T,X,Y,U,V | $169D,$169E,$169B,$169C,$16A0,$169F drawing state |
| CO / SV | $16A1 drawing color table / $12B8 sound control |
| GE | $6010 global flags |
| T0 / T1 / TC / TL / TV | $6020,$611C,$6218,$6314,$6410 object arrays |
| N0 / N1 / NV | $650C,$6608,$6704 room arrays |

Each object/room array reserves $FC bytes. Names and roles are corroborated by
room/library scripts; individual flag meanings still need puzzle cross-references.
Reads/writes of Q/R/Z access hardware and must not be treated as passive RAM.
For example `.S R=0` clears a previous key before a timed interaction.

## Command processing

The input editor at $0C1A displays on text row 15 and bounds input against column
39, protecting the prompt prefix from backspace. Its keyboard wait at $0CBC polls
$C000 and clears the keyboard strobe through $C010. Once a timed script accepts
the initial key and transfers into this blocking editor, the editor itself does
not poll a room timer. This explains why urgent first-key delivery and delivery
of the remaining sentence need different replay treatment.

The normalizer strips insignificant words and recognizes chain separators using
the table at $0390. Each significant word retains five high-bit characters and
space padding. The handler matcher compares those five-character words against
room and library patterns. Specific `%...` vocabulary expansion, command repeat
and intrinsic conditional flow remain to be documented after intrinsic analysis.
Observed invalid-command behavior is archived in the opening baseline.

## File loading

`load_named_file` at $0B20 takes a ten-character high-bit filename pointer in
A/X and an allocated-stream destination in $EC/$ED. It reads the VTOC/catalog
chain into $B700, scans catalog entries, follows the file's first TS list, and
loads each allocated sector into successive destination pages. This loader
deliberately includes any DOS binary header and ignores its address/length.
Destinations $0CFC and $ADFC position those headers immediately before their
actual high-memory payloads. All present files fit one TS list; support for
additional TS-list sectors is not implemented by this routine.

`read_sector` at $0BBC sets the mutable IOB at $0BAB, passing A/Y=$0BAB to DOS
RWTS at $BD00. The IOB requests read command 1, slot $60 (slot 6), drive 1.
The device-characteristics table at $0BA7 and the IOB are data. Carry indicates
an I/O error; the engine prints parameter-block strings for missing files, disk
errors, unterminated input and stack overflow. Original I/O is retained.
Boot-time relocation and the full DOS/RWTS source still require tracing and
reconstruction; the high entry address alone does not prove every memory owner.

Static intrinsic code at $122C/$129D implements save/restore with RWTS commands
2/1. Its shared transfer at $123B starts at track31/sector15 and buffer $AF00,
then reads/writes $90 pages in descending sector and memory order, ending with
track23/sector0 and $2000. It calls native entries $BA72/$BA69 around RWTS. This is a
raw RAM snapshot of $2000–$AFFF, not a DOS catalog file. Runtime isolated-media
comparisons observe exactly those 144 changed sectors, and restored object/room
state passes both same-session and fresh-boot checks. The complete intrinsic
source still needs reconstruction. Further native instruction inspection shows
$BA69/$BA72 are short register-return stubs, not workspace-preservation routines:
$BA69 returns X=$6E,Y=$36 and $BA72 returns X=$6F,Y=$00. Their purpose in the
supplied cracked version remains unconfirmed; no memory preservation is inferred.

The early build now assembles interpreter and renderer. Their original encodings
match as a diagnostic. It still needs intrinsics, boot/DOS, the remaining CHAR
GEN content and decoded editable graphics before satisfying PLAN.md.
