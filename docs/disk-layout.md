# Disk map, source authority and retained data

Both inputs have 35 tracks × 16 sectors × 256 bytes. The DOS 3.3 VTOC at
track 17/sector 0 declares that geometry and volume 254. Its catalog chain
occupies track 17/sectors 15 down through 1 on side A. A2kit recognizes both
catalogs as Apple DOS. Direct logical-sector parsing of the `.dsk` file order
recovers the same allocated file streams as a2kit, and MAME boots the images in
this order. These observations establish DOS sector order independently of the
extension/size alone.

[Raw manifest](../assets/raw/manifest.json) maps **every disk byte** to exactly
one exported region slice. Each sector entry records original disk offset,
track/sector, owner, region path, and region offset. File entries additionally
record catalog location, linked TS lists, allocated size, SHA-256 and nominal
binary header where present. Regions remain native, unaltered allocated bytes.
The raw manifest records the initial extraction classifications. The completed
[classification manifest](../assets/classification.json) records current build
authority for all289 regions; no unknown or raw executable dependency remains.
Decoded script/world views and editable images are tracked separately.

There are 63 live catalog entries on A and 76 on B. Their sectors are
non-overlapping. Files named `ROOM ...`, `INITIAL`, `LIBRARY`, `DEATH`, `TRAVEL`
and `TUNNEL` contain high-bit ASCII ULTRA scripts, not 6502 instructions. `START`
is an Applesoft/DOS command script. `ADVEN INTERP.OBJ` and `INTRIN.OBJ` are
resident interpreter and intrinsic code; `CHAR GEN` mixes lookup data, renderer
code and a font; `PARMS.OBJ` is a parameter block. Other binary-typed entries
begin with high-bit ASCII named vector/fill records rather than DOS binary
headers. All48 files are generated from257 separately editable SVG records;
their format and native previews are documented in [pictures.md](pictures.md).

Two side-A catalog sizes have an added $2800: `START` reports 10242 sectors but
owns one TS-list and one data sector; `ADVEN INTERP.OBJ` reports 10247 but owns
one list and six data sectors. Allocation follows the TS chains, not the
catalog count. The provenance exports preserve these values; their purpose
(possibly a crack artifact) is not established. Binary type alone does not
prove a DOS binary header. The manifest explicitly records whether each nominal
header length fits its allocation; the graphics-file values do not.

Sectors outside live file allocations are exported per track. Their completed
authority is:

| Disk span | Build source / meaning |
| --- | --- |
| A/B T0 S0 | Separate first-stage/bootstrap helper source. B prints BOOT OTHER SIDE and halts. |
| A/B T0 S1 | Separate second-stage wrappers, including native startup/IOB differences. |
| A/B T0 S2–9 | Eight RWTS pages from readable source, with explicit tables/buffers and side-B unused residue. |
| A T0 S10–15, T1 S0–15, T2 S0–4 | Complete side-A DOS source at $9B00–$B5FF. |
| B T0 S10–15 and T2 S3–4 | Retained DOS fragments, assembled from the side-B variant. |
| A/B T2 S5–15 | Generated zeros; boot loads only through S4 and no file owns these sectors. |
| A T18 S11–12 | Inactive free-sector text/TS residue, retained native data. |
| A T22 S14 | Inactive tokenized BASIC residue, retained native data. |

B's other T1/T2 sectors belong to live catalog files. Its bootstrap cannot
reach the DOS fragment loads, and normal swaps retain A's resident RWTS and
only load requested files from B. The lower B DOS copy differs from A at just
$9E42: startup command index6 (RUN) instead of20 (EXEC). Its final copied buffer
pages agree with A. The variant is source even though unbooted; unplaced portions
of its assembled output are documented in build.json. No source bytes are
mapped over B's live file sectors.

The reserved zero spans total2816 bytes per side. Direct extraction checks show
all are zero; they are generated and never read as native build references.
Track18's free residue resembles an older DEATH script and its TS allocation;
track22 contains a tokenized Applesoft fragment issuing EXEC START. The VTOC
marks exactly these three sectors free, and no current TS chain refers to them.
They are outside the boot extent and the save range (tracks23–31). Current
machine-code entries, filenames and loaders cannot reach them. Retention is
historical disk data, not unfinished disassembly or a executable build input.
Their original program versions/complete provenance before the supplied disks
remain unknown and are not necessary to reproduce the current game.

## Metadata and allocation

The build generates all139 TS-list streams from manifest file sector lists and
next-list links, enforcing122 pairs per list. It regenerates catalog chain links,
live entries and the VTOC free bitmap from the manifest. Catalog/VTOC inactive
fields remain native structured data; native anomalous catalog counts are retained
instead of silently normalized. Those four small metadata seeds are required data
inputs. TS-list exports are reference-only and are not read by the source build.
Allocation, sector/source coverage, sizes and overlaps are checked before either
143360-byte disk is emitted. Original layout and physical I/O are preserved.

[Boot loading](boot-loading.md) documents the two-stage bootstrap,37-page DOS
extent and START/custom-loader destinations. [Memory ownership](memory.md)
explains why DOS addresses later contain library/pictures/CHAR GEN rather than
executable overlays. Headers/tails of all machine-code files are explicit source
data; the parameter file is fully decoded structured data. The retained scripts
are uncompressed high-bit text with line provenance, not hidden 6502 payloads.

```sh
# One-time analysis export; refuses an existing destination.
python3 tools/dos_disk.py export
# Reads only exported regions and the manifest, not either original disk.
python3 tools/dos_disk.py repack
cmp mask-of-sun-a.dsk build/raw-repack/mask-of-sun-a.dsk
cmp mask-of-sun-b.dsk build/raw-repack/mask-of-sun-b.dsk
```

The original inputs are needed only for the one-time export and independent
comparison. `repack` starts with an empty byte array, validates complete sector
and source-slice coverage, verifies export lengths/hashes, and constructs two
disks. This is an extraction-integrity check, **not the source/asset rebuild**.
Source build output is permitted to differ in bytes after behavior is validated.
Use [build.md](build.md) for the source/asset build and read-dependency audit.
