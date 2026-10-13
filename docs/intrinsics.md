# Intrinsic script engine

`src/intrinsics.s` assembles the entire allocated `INTRIN.OBJ` stream: four-byte
DOS header at $0CFC, $1300-byte payload at $0D00–$1FFF, and final-sector data
through $20FB. Dispatch, expression/variable evaluation, drawing, speaker loops
and save/restore are readable instructions. Buffers, tables, patterns, strings
and residual allocation bytes have explicit data boundaries.

## Directive interface

The interpreter passes $D2/$D3 pointing at the high-bit directive letter.
`dispatch_intrinsic` consumes that letter and its separator, then tests it
against a sequence of handlers. Ordinary handlers return to the resident line
scanner. Transfers and conditional execution discard return frames and reenter
the interpreter directly. A/X/Y, flags, shared zero page, stack and self-modified
operands may change; this is an engine-internal interface.

| Directive | Source entry | Native behavior |
| --- | --- | --- |
| G | `goto_room` | Load room text at the initial-script base, reset command/room pointers and stack. Blank argument uses filename scratch. |
| 3 | `set_room_filename` | Copy ten filename characters for a later blank G. |
| W | `wait_short` | ROM WAIT with A=$C4; used by script polling/timer loops. |
| Q | `quit_boot_rom` | Enter ROM autostart slot scanning. |
| C | `clear_graphics` | Fill HGR from a scanline through row191; arguments fill,page,row. Defaults 1,1,0; valid ranges 0..1,1..2,0..191. |
| M | `set_text_inverse` | Set character background/inversion: 1 gives zero, other values $FF. |
| $ / _ | Display/draw page entries | Select visible page or renderer page separately; 1/2, otherwise page1. |
| V / H | Cursor entries | Vertical 0..15, horizontal 0..57; out-of-range values reset to zero. |
| & | `echo_command` | Print raw command span and clear its chain marker. |
| J | `jump_script_lines` | Relative CR-delimited line scan, bounded by room/library bases or terminator. |
| ] | `set_custom_prompt` | Save/install up to fifteen prompt characters; blank restores original. |
| A | `ask_player` | Temporarily read a response into $0278; retain up to fifteen characters. |
| = | `compare_answer` | Compare response with script argument; argument CR accepts a matching prefix. |
| P | `print_script_value` | Print quoted string or decimal low-byte[,high-byte] value. |
| I | `test_if` | Store expression result; zero false, nonzero true. |
| T / E | Conditional entries | Execute the following opcode on the same line when condition is true/false. |
| ? | `skip_to_library_terminator` | Scan to @ and resume command-chain processing. |
| 1 / 2 / ! | Macro entries | Set two scratch-character pairs; overwrite four script characters and execute them. |
| - / + | `save_game` / `restore_game` | Transfer 144 raw RAM pages through RWTS. |
| * | `restart_script` | Reset pointers/stack and restart current loaded script. |
| N | `play_sound` | Tone, or noise when argument begins N. |
| R | Reverse entry | Complement all bytes of selected HGR page, including holes. |
| S | `set_variable` | Resolve indexed destination, evaluate value and store one byte. |
| B | `select_picture` | Select a five-character record name in loaded graphics. |
| L | `load_pictures` | L mode starts at $9C00; N mode appends at saved end pointer. |
| D | `draw_picture` | Render selected vector/fill layers using current drawing variables. |

Macro scratch is text, not an executable overlay. The native first pair happens
to contain `60` and the second `15`; scripts replace them with direction/action
abbreviations too. Treating them as universally room numbers would be incorrect.
The blank-room filename and prompt/answer seeds likewise contain captured stale
workspace; normal scripts initialize them before use.

## Values, expressions and hardware

`evaluate_expression` accepts an eight-bit default in A and restores its incoming
X/Y. A CR/comma returns the default. An atom followed by at most one operator
supports AND `&`, OR `/`, XOR `%`, unsigned `>`/`<`, equality `:`, inequality `#`,
addition `+` and subtraction `-`. Comparisons return $FF/0. Postfix `!` complements,
and `++`/`--` increment/decrement. Arithmetic wraps to eight bits; this is not
BASIC precedence or a general expression parser.

`read_expression_atom` reads a variable or one to three decimal digits. The
hundreds table implements the intended 0..255 range; larger literals are not
supported as general integers. Two-character indexed names such as `TC(4)`
resolve an index through recursive atom parsing. There is no array capacity
check. The table at $13CC has 37 entries, each two high-bit name characters and
a little-endian address; it is now symbolic assembly. See [engine.md](engine.md)
for addresses of scalar and object/room arrays.

Variables Q/R/Z map to $C000/$C010/$C061. Reading R clears the keyboard strobe;
Q samples the latch. Assignment first resolves a variable by reading it, then
writes the requested value. Therefore `.S R=0` already clears stale input during
resolution, before its store. Runtime observations of timed input use passive bus
taps, not extra reads of these variables.

The A/=`ask_player` path does not perform strict whole-string equality: a script
CR sets success as soon as its matching argument prefix ends. Empty/prefix and
longer-response cases must follow that implementation when documenting puzzles.
The established gameplay route verifies the actual required answers, not every
possible answer variant.

## Sound and snapshot I/O

SV addresses $12B8: tone period, duration low/high, sweep, then noise period,
duration low/high and sweep. Tone toggles $C030 whenever its period counter
expires; noise rotates a two-byte shift register with feedback before toggling.
Sweep sign selects increasing/decreasing period. Counter wrap and exact loop
instructions determine sound/timing and are retained. Game SOUND OFF/ON is
implemented by library script state, which skips calling the effects; the speaker
routine itself is not an external audio asset.

Save/restore uses the interpreter IOB at $0BAB and resident $BD00 RWTS, commands
2/1 respectively. RAM pages $AF00 down to $2000 map T31/S15 down to T23/S0.
The before/after native stubs return register constants; no memory-copy semantics
are inferred for them. Errors print a message and unwind engine call frames.
See [rwts.md](rwts.md), the save routes and isolated-media footprint reports.

## Graphics and self-modification

B searches a collection at $9C00 by five-byte names and advances by each record's
little-endian byte length. A record header contains origin X/Y, scales S/T,
options V, layer count U and one color byte per layer. The vector pointer follows
that variable-length header. A high-bit layer color selects a two-byte fill seed;
other colors select a vector stream. Color $7F draws lines without a second
edge-fill pass.

Vector streams begin with two origin bytes and a two-byte packed-length-minus-one.
Each packed byte supplies low-three-bit and middle-three-bit commands, plus a
nonzero top-two-bit command when present. Command bit2 suppresses plotting;
direction low bits select up/right/left/down. Plotting occurs before movement.
Unit mode changes integer coordinates directly. Scaled mode also tracks fractional
coordinates; origin scaling uses the native shift/add calculation. The asset
codec must follow these operations before claiming decoded rendering equivalence.

V option bits patch executable source: bit0 selects visible page, bit1 selects
the destination scanline table, bit2 selects OR/AND plotting, bit3 selects scaled
versus unit stepping, and bit5 selects alternate horizontal directions. Three
JSR operands, conditional-branch displacements, scanline high-byte operands and
plot operator/opcode bytes are intentionally mutable. During edge filling, an
LDA instruction is replaced with JMP `fill_vector_edge`, then restored from
three saved bytes. These addresses remain instruction-relative expressions in
source, rather than being disassembled as separate data bytes.

The scan fill retains the original partial-byte, phase and row-pattern rules.
$FF marks fillable bytes. The pattern data comprises partial masks, five 43-byte
textures and four 41-byte solid/phase strips. CO values also select alternating
row colors. Remaining codec/render/edit-authority work is tracked separately;
source reconstruction alone does not make graphics editable.

## Retained data and validation limits

The source distinguishes $0D7B filename scratch, clearing arguments, jump state,
prompt/response buffers, decimal scratch/tables, macro text, sound state,
assignment/expression state, the variable table, graphics state and filename
buffers from instructions. The error-path templates at $0D13/$16EE are executable
code copied into the resident loader. Signature/control residue and zero padding
after $1F6E have no branch/call targets; the allocated tail contains $AD then 251
zero bytes and has no executable entry.

Assembly fixes the native entry at $0D00 and all payload/allocated-stream sizes.
Full-route sound-enabled replay, save/restore and control checks validate its
integration. Unsupported malformed expressions, every I/O error, optional quit,
all answer-prefix variants and graphics codec edits remain outside current
coverage. This closes the intrinsic source dependency, not the overall plan.
