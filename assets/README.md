# Assets

`raw/manifest.json` records the complete native sector exports, including disk,
track/sector, file offsets, allocated lengths, roles and nominal load headers.
See `docs/disk-layout.md`. Exports are the current representation for unconverted
regions and provenance references for converted regions. Decoded views are
generated under `build/`.

In the early build, `src/renderer.s` is authoritative for CHAR GEN allocated
file offsets $0504–$0603. The builder overwrites that provenance span with the
assembled page. The surrounding bytes remain native temporary inputs. Editable
graphics will become authoritative build inputs after their format and rendering
are understood. Supplied disks at the repository root are never build templates.

`src/interpreter.s` is authoritative for ADVEN INTERP.OBJ file offsets
$0004–$0503; its four-byte header and allocation tail remain native metadata.

The boot modules are authoritative for track0/sector0 and sector1 on both sides,
each system track-00 region offsets $0000–$01FF. Remaining DOS sectors are still
temporary raw code inputs; see `docs/boot-loading.md` for verified load phases.
