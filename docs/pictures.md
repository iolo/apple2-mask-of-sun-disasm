# Editable native vector pictures

`assets/decoded/pictures/manifest.json` maps 257 picture records to 48 allocated
files on sides A/B. Duplicate records on different sides have separate assets
because they are independently stored and may be edited independently. Each
record has an SVG containing editable geometry and a generated companion PNG
showing its native rendering. The build encodes the SVGs with
`tools/picture_assets.py`; the raw native streams remain provenance references.
PNG previews are never build inputs. Font bitmaps have a separate
[PNG workflow](chargen.md).

The SVGs expose every directional step and fill seed, rather than embedding a
packed native picture body. Their normal browser rendering is an approximation:
ordinary SVG fills, path endpoints and RGB colors differ from the native edge
fill, plotting order, textured patterns and Apple II artifact colors. Use the
companion PNG to review the native appearance. It renders the record alone on
a white canvas; gameplay can combine records, change drawing options and add
text. Previews preserve the emulator's horizontal display scaling.

## Format and source interfaces

These catalog type-B files do **not** begin with a DOS binary load header.
Each record has five high-bit ASCII name bytes, a little-endian total length,
five parameter bytes (X/Y origin, S/T scale, V options), a layer count U and U
color bytes. Its ordered layer bodies follow. A vector body stores an unsigned
X/Y origin, a little-endian packed-byte count minus one, then packed steps.
A high-bit color instead selects a two-byte fill seed. Bytes after the final
layer, within the total length, are unused allocation residue.

Each packed byte contains two three-bit commands and an optional nonzero
two-bit third command. Low two bits mean up/right/left/down; bit2 suppresses
plotting. The engine plots the current position **before** moving. Vector X has
140 units across 280 HGR pixels; Y has 192 scanlines. Seed X is a screen-byte
column (0–39 for ordinary seeds), rather than a vector X coordinate. Native
origins and steps use byte wrapping. Some original records deliberately use
offscreen coordinates and origins such as Y=200. The codec keeps these exact
unsigned parameters and unwrapped path coordinates; it does not assume a host
clipping algorithm reproduces native behavior.

`src/intrinsics.s` implements record selection at `select_picture`, parameter
copying at `read_picture_header`, and rendering at `draw_picture` ($1837).
`configure_vector_mode` selects pages, AND/OR plotting, scaled stepping and
horizontal reversal. `draw_vector_stream`, `flood_fill` and
`select_fill_pattern` implement the format. The CHAR GEN lookup pages provide
native byte/bit and scanline addresses. [Intrinsic contracts](intrinsics.md)
describe the scratch RAM and mutable instructions.

## Supported edits

Edit SVG XML with a text editor or an editor that preserves custom attributes.
The encoder accepts only this constrained format; generic SVG exports often
introduce curves, transforms or fractional coordinates and will be rejected.

- `data-name` is the five-character ASCII lookup name. Preserve names used by
  scripts unless their references are also updated.
- `data-origin-x/y`, `data-scale-x/y` and `data-options` are native unsigned
  bytes. The group translation must match the signed view of the origin bytes.
  Options use bits0/1 for displayed/target page, bit2 for OR, bit3 for scaling
  and bit5 for horizontal reversal. Other option bits are rejected.
- A vector layer is a `path` with `data-kind="vector"`, `data-color=0..127`
  and an absolute integer `d` consisting of M/L operations. The first M sets
  the unsigned origin. Later M moves without plotting and L plots before moving.
  Segments must be nonzero and orthogonal. Longer segments expand to unit steps;
  curves, diagonals, relative commands and fractional coordinates are unsupported.
  Later path coordinates must remain within -256..511. This bounds supported
  source geometry; it does not promise native clipping for arbitrary edits.
- A seed is a `circle` with `data-kind="seed"`, a high-bit color128..255 and
  integer `cx/cy` native seed coordinates. The circle is an editing marker; its
  SVG radius/style is not part of native rendering. Prefer native screen-byte
  columns0..39 and scanlines0..191 for new seeds.
- Layer order is significant. Add/remove/reorder layers within the single
  `data-role="layers"` group, retaining 1..64 layers. Color127 selects outlines;
  other low-bit colors select the native fill patterns, and seed colors use their
  low seven bits. Values0..5 select native solid patterns,16..95 alternating
  nibbles, and96+ textures. The native solid selector saturates values5..15.
  SVG `fill`, `stroke` and styling are review annotations. Change `data-color`
  to change the game color; changing CSS alone does not change native output.
- Keep dimensions280×192, viewBox`0 0 140 192` and aspect option`none`. Per-layer
  transforms, nested elements and additional graphic types are rejected.

`data-packing` lists the original two/three-step group widths. It contains no
directions or geometry. Keeping compatible widths preserves the native grouping
and drawing time. If an edit changes the step count or makes a third command
incompatible, the encoder groups the edited steps again. An odd final step
gets a final nonplotting move whose resulting coordinates are unused. Edited
pictures can take a different amount of time to draw; timed gameplay is verified
using the restored unmodified assets.

Each collection retains its original allocated sector capacity. Edited record
lengths and layer counts are regenerated; the last record absorbs the remaining
space as unused padding. If the payload exceeds that capacity, encoding fails
with the filename, capacity and excess bytes. Increasing file allocation is
outside the supported editing workflow. Metadata stores reference offsets,
sizes/hashes and unused padding only. It is not an alternative packed image.

## Conversion and preview verification

The normal build performs encoding automatically. To inspect generated streams:

```sh
python3 tools/picture_assets.py encode assets/decoded/pictures --output build/pictures
```

Decoding raw reference streams is a one-time extraction command, not a build
step. `decode --output NEW_DIRECTORY` refuses to overwrite an existing directory.

To regenerate native previews, first build, prepare fixtures, and run the
isolated renderer on the rebuilt disks using the documented MAME/ROM setup:

```sh
python3 tools/picture_preview_jobs.py --output build/picture-jobs.json
python3 tools/mame_session.py --rompath /path/to/roms --output build/picture-session \
  --disk-a build/early/mask-of-sun-a.dsk --disk-b build/early/mask-of-sun-b.dsk \
  --headless --fast --script tools/picture_preview.lua --route build/picture-jobs.json
```

The fixture deliberately injects record bytes into scratch RAM and invokes the
native renderer. It restores a booted RAM baseline before each call and uses a
mailbox loop between calls, avoiding mid-instruction PC changes. This verifies
assets independently of gameplay. Fresh game replays use normal keyboard and
disk input without RAM injection.

For reference comparison, prepare another job file with `--reference`, run it
on original disks in a new session, then:

```sh
python3 tools/verify_picture_previews.py build/reference-session build/picture-session \
  --publish --output build/picture-comparison.json
```

Publishing only proceeds when all fixture HGR pages agree. The committed
`docs/evidence/picture-roundtrip.json` records 257 successful comparisons on
both pages. The baseline full route also reaches the ending on both rebuilt
disks with the same recorded sound. A temporary outline rectangle added to
PIC1 is tested through the normal loader and opening replay; the baseline SVG
is restored before acceptance builds. This validates a geometry/layer edit,
in addition to the separate font pixel edit.

Limits: standalone white-canvas previews do not demonstrate every possible
composition, scale or color edit. Full-route checkpoints cover the observed
gameplay compositions; malformed/native overflow behavior is not generalized.
