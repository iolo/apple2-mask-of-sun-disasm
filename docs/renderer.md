# High-resolution text renderer

[renderer.s](../src/renderer.s) is the first buildable, annotated module.
It occupies $B300–$B3FF and is delivered inside the file named `CHAR GEN`.
The native allocated stream starts with a nominal DOS binary header and is
loaded by the custom interpreter from $ADFC, so file offset $0504 maps to $B300.
The native header's address $1700 does not establish its actual custom-loader
destination. Runtime captures place the code and font at the high addresses.

Calling $B300 installs $B317 into the ROM output vector at $0036/$0037 and
$B33C into the drawing vector at $0348/$0349. COUT accepts a high-bit character
in A, saves/restores X and Y through $001C/$001D, handles backspace/CR/LF, and
draws printable glyphs. Other control bytes below $A0 are ignored. Direct draw
does not advance the cursor and clobbers registers/pointers as documented in
source. This workspace makes the renderer non-reentrant.

The cursor lives at $24 (column) and $25 (row). Columns wrap at 40; rows clamp
at 15 rather than scroll. Scripts manage clearing and pagination. Each text row
begins at `12*row` scanlines; an 8-row glyph occupies one HGR byte per scanline.
The address lookup tables are $B000 (low), $B100 (page 1 high) and $B200
(page 2 high). `$0346 == 0` selects HGR1, otherwise HGR2. The background byte
at $0347 is written then XORed with the glyph, preserving its high-bit color
phase behavior. Glyph addressing is `$B300 + 8*(A & $7F)`; printable characters
begin at $B400. Current scanline at $B303 is mutable data. In the original
inventory capture its value differs from the native zero, as expected.

The jump-over space at $B375–$B378 is four reserved zero bytes, not four BRKs.
The last nine bytes at $B3F7–$B3FF have no entry points or references in this
module; their origin remains unconfirmed and is explicitly recorded as data.
The surrounding CHAR GEN header, legacy fragment and generated lookup pages
are assembled in `src/chargen.s`. Font PNGs are authoritative build inputs;
see [chargen.md](chargen.md) for phase bits, truncated last glyph and editing rules.

```sh
python3 tools/build.py
python3 tools/decode_screen.py build/session-01/checkpoint-ram.bin
```

The early builder assembles the page with ca65/ld65 and replaces only its
allocated stream span. It validates length and fixed-address layout. The output
currently retains its original encoding (a diagnostic, not a final identity
requirement). [Opening replay evidence](evidence/opening-rebuilt.json) passes
the same 13 original opening checks on these disks.
[Early build verification](evidence/early-build-check.json) records a second
fresh-output build with identical hashes and an `openat` trace showing that the
builder reads no original disk images. The rest of the disks still include
temporary raw code; this does not establish the final standalone-build criteria.

MAME's natural keyboard exposes `empty` and `is_posting` separately; a timed
replay must check both before posting another command. The current documentation
is [MAME Lua input classes](https://docs.mamedev.org/luascript/ref-input.html);
the used properties were verified on installed MAME 0.285. The ready glyph
must be present (`OK>^`), since `OK>ENTER` while typing is not a fresh prompt.
