# Resident disk routines

`src/rwts.inc` assembles $B800–$BFFF, the eight resident pages loaded by
side A's first bootstrap. `src/rwts-a.s` and `src/rwts-b.s` preserve each
side's copy. Disk construction replaces T0/S2–9 from these sources; no
original disk image is a build input. The remaining DOS pages at $9B00–$B5FF
still require source reconstruction.

## Entries and ownership

| Address | Source symbol | Interface and purpose |
| --- | --- | --- |
| $B800 | `prenibble_sector` | Split the sector at ($3E/$3F) into 6-and-2 groups. |
| $B82A | `write_sector_data` | X=slot×16; write prenibbled buffers, carry reports protection. |
| $B8C2 | `postnibble_sector` | Recombine buffers into ($3E/$3F); $26=0 selects 256 bytes. |
| $B8DC | `read_sector_data` | X=slot×16; scan data prologue, decode and check GCR. |
| $B944 | `read_address_header` | Return sector/track/volume in $2D/$2E/$2F. |
| $B9A0 | `seek_halftrack` | A=target half-track, X=slot×16; drive phase stepping. |
| $BA00 | `motor_delay` | Short delay and $46/$47 elapsed counter; destroys X. |
| $BD00 | `rwts_entry` | A=IOB high, Y=IOB low; read/write/seek/format dispatcher. |
| $BEAF | `format_disk` | Format and verify 35 tracks; no game caller observed. |
| $BFC8–$BFFF | DOS tail helpers | Language-card reload, file selection and close/error paths. |

Public RWTS stores the IOB pointer in $48/$49 and copies its DCT/buffer pointers
into $3C–$3F. Command byte +12 selects seek/null (0), read (1), write (2), or
format (4). Carry clear indicates success; error byte +13 contains write
protection ($10), volume mismatch ($20), exhausted seeks ($40), or format
failure ($08). It uses $26–$2F, $35, $46/$47 and slot-indexed scratch in
text-page holes. A/X/Y are not preserved. Bootstrap, interpreter and save/restore
all call the same $BD00 entry using their own IOBs.

The read path locates D5 AA 96 address fields and D5 AA AD data fields. Address
bytes use 4-and-4 encoding; sector payloads use differential 6-and-2 GCR plus
checksum. The logical sector interleave is explicit at $BFB8. $C080–$C08F plus
the slot offset select phases, motor, drive and Q6/Q7 disk latches. PHA/PLA,
NOPs and small delay calls in writers are timing instructions, not padding.

At $BE47 a literal BIT-zero-page opcode consumes the SEC opcode at the alternate
$BE48 entry as its operand. Success skips SEC without changing carry; errors
enter SEC directly. This overlapping instruction is intentionally represented
by one annotated opcode byte, with both entry labels preserved.

## Native patch and data boundaries

Side A's $BA69, $BA6D and $BA72 entries return only register constants:
X=$6E/Y=$36, X=$8A/Y=$36 and X=$6F/Y=0 respectively. Their branches reach RTS
without writing memory. Earlier boot/save notes that described these as
workspace initialization/copying were incorrect and have been corrected.
The remaining $BA7C–$BA93 decoder-initializer fragment is readable assembly;
no live caller has been observed. It would modify the inverse GCR table and
its own EOR immediate.

Side B cannot boot DOS: its sector-zero entry prints BOOT OTHER SIDE. Its
$BA69–$BA93 copy contains 43 residual bytes instead of the side-A stub/fragment.
Those bytes are explicit data in the side-B source branch. They are not executed
during a normal disk swap: side-A RWTS remains in memory, and the custom loader
loads files from the newly inserted side. The other high-memory bytes agree.

| Span | Meaning and source representation |
| --- | --- |
| $B9FD–$B9FF | Three alignment/residual bytes following seek RTS. |
| $BA11–$BA28 | Twelve magnet-on and twelve magnet-off delays. |
| $BA29–$BA68 | The 64 legal GCR write codes. |
| $BA7B, $BA94–$BA95 | Isolated residual bytes outside native live entry paths. |
| $BA96–$BAFF | Inverse GCR table, indexed relative to $BA00. |
| $BB00–$BBFF | 256-byte primary nibble scratch buffer. |
| $BC00–$BC55 | 86-byte auxiliary nibble scratch buffer. |
| $BC56–$BCDE | Address-field writer: executable assembly, not part of the buffer. |
| $BCDF–$BCFF | 33 residual bytes with no static branch/call targets. |
| $BFA8–$BFB7 | Sixteen sector-verification flags. |
| $BFB8–$BFC7 | Sixteen logical-to-physical sector mappings. |
| $BFD9–$BFDB | Three padding bytes after the reload jump. |

Scratch seeds contain residue from prior encoding, rather than executable game
logic. Reads fill the nibble buffers before postconversion; writes prenibble
the requested sector first. Native seeds are retained as explicit data to keep
the component reproducible. No executable code is included through a binary
blob in this module.

The native bytes, traced IOB requests and callers establish the reconstruction.
The independently maintained [Apple II DOS source transcription](https://github.com/cmosher01/Apple-II-Source/tree/master/src/dos/system/common)
was consulted for routine roles and scratch/table boundaries. Its source was
not imported; the supplied game's patched entries are represented from the
native inputs rather than assumed to match a standard DOS distribution.

## Validation scope

Eight-page source size is asserted; current assembly equals the native bytes
on each side as an encoding diagnostic. Boot entry/request traces, opening
checkpoints and a save/restore replay exercise native read and write behavior.
Formatting, optional language-card reload and all DOS error branches remain
untested. This module does not finish the intrinsic engine, remaining DOS,
editable graphics or the full plan.
