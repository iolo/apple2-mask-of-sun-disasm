# Character generator and editable font

`src/chargen.s` now constructs the entire nine-sector CHAR GEN file, combining
its header, retained legacy fragment, generated lookup pages, existing character
renderer source and the font encoded from `assets/decoded/font/*.png`.
The native export is a provenance/reference artifact; its font bytes are not
copied into the constructed file.

| Runtime span | Authority and meaning |
| --- | --- |
| $ADFC–$ADFF | Source header: nominal $1700/$08FB, ignored by whole-sector custom load. |
| $AE00–$AEFF | Retained old editor fragment, command/address tables and mask copy. |
| $AF00–$AFFF | Generated 140-unit horizontal byte/bit lookup and native invalid entries. |
| $B000–$B0FF | Generated HGR scanline low bytes. |
| $B100–$B1FF / $B200–$B2FF | Generated page1/page2 high bytes. |
| $B300–$B3FF | `renderer.s`: install/output/glyph routines and cursor/patch data. |
| $B400–$B6FB | 764 font bytes, encoded only from editable PNGs. |

Horizontal drawing coordinates have 140 logical units across 280 physical HGR
pixels. A pixel mask affects a pair of screen bytes. For x<140 the lookup stores
`8*(x//7)+(x%7)`; higher values retain the native marker7. For y<192 the HGR offset
is `(y&7)*$400+((y>>3)&7)*$80+(y>>6)*$28`. Remaining row entries are native low0,
high$F0 markers. These invalid entries do not establish safe arbitrary clipping;
assets should stay within their supported native coordinate range.

## Glyph editing

There is one PNG per character code $20–$7F, named by lowercase hex code. Each
is exactly 8×8 RGBA. Columns0–6 correspond to seven glyph bits, left to right,
and use opaque black (off) or opaque white (on). Column7 represents the row's
artifact phase bit and uses opaque black or blue RGB(0,128,255). It is metadata,
not an eighth visible HGR pixel. This preserves the native all-$FF cursor glyph
at $5E instead of silently discarding its phase.

Glyph $7F has only four stored rows. Its last four rows must remain transparent
black because the allocated native file ends at $B6FB; their runtime addresses
are outside this file. The encoder does not invent or write those absent bytes.
Other rows must be opaque and use the prescribed colors. Scaling, antialiasing,
unsupported colors, extra/missing glyphs and filling absent rows fail with a
specific error.

`tools/font_assets.py encode assets/decoded/font --output build/font.bin`
encodes the PNGs. The normal build runs this operation automatically and includes
only the generated data at `character_bitmaps`. Changing glyph pixels changes
the constructed file and disk; phase changes are supported but also affect HGR
artifact color. Use a pixel editor and keep the exact dimensions/palette.
The decode command is a provenance extraction operation, not part of the build;
it refuses an existing output directory.

Python Pillow is required for this conversion. Font PNG hashes are included in
the build manifest. Do not edit the raw reference export to change a glyph.

## Unused editor residue

$AE00 begins with the tail of old inline text, followed by a few readable
6502 instructions calling an older editor's addresses. The strings include
`VTOC:` and `V-edit:`. Four tables contain key bytes and old handler addresses;
a final 28-byte block duplicates intrinsic pixel masks. These are explicit
source tables, rather than incorrectly disassembled arbitrary branches.
The fragment does not contain a complete editor: its external call targets
belong to the older program, not the current game's ABI.

The current game enters the renderer at $B300/$B317 and uses lookup pages
$AF00–$B2FF. No live game branch/call targets the editor fragment; room scripts
are interpreted data and graphics use their own renderer. The fragment is
retained for provenance and source reproducibility, not offered as a callable
subsystem. Its exact older editor command semantics remain unconfirmed and do
not hide unfinished gameplay code.

## Verification

Unmodified glyphs encode to all 764 native font bytes, including phase bits and
truncated last glyph. The constructed CHAR GEN stream matches the native encoding
as a diagnostic. The unmodified build passes the opening replay. A temporary
white pixel at column6,row7 in $59 (Y) is built into a separate test disk and
checked against the corresponding font byte and rendered opening text. The
baseline PNG is restored before the final baseline build. Detailed evidence is
recorded in `docs/evidence/font-edit.json`.

This font workflow covers character bitmaps. The separate vector picture files
still need editable assets and conversion/render verification to complete Step6.
