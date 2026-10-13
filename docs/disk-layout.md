# Initial disk map and extraction

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
Alternate disassembly, text and image views belong in `build/` during analysis.

There are 63 live catalog entries on A and 76 on B. Their sectors are
non-overlapping. Files named `ROOM ...`, `INITIAL`, `LIBRARY`, `DEATH`, `TRAVEL`
and `TUNNEL` contain high-bit ASCII ULTRA scripts, not 6502 instructions. `START`
is an Applesoft/DOS command script. `ADVEN INTERP.OBJ` and `INTRIN.OBJ` are
resident interpreter and intrinsic code; `CHAR GEN` mixes lookup data, renderer
code and a font; `PARMS.OBJ` is a parameter block. Other binary-typed entries
mostly begin with high-bit ASCII named graphics definitions rather than valid
DOS binary headers. Their actual drawing representation still needs decoding.

Two side-A catalog sizes have an added $2800: `START` reports 10242 sectors but
owns one TS-list and one data sector; `ADVEN INTERP.OBJ` reports 10247 but owns
one list and six data sectors. Allocation follows the TS chains, not the
catalog count. The provenance exports preserve these values; their purpose
(possibly a crack artifact) is not established. Binary type alone does not
prove a DOS binary header. The manifest explicitly records whether each nominal
header length fits its allocation; the graphics-file values do not.

Sectors outside live file allocations are exported separately per track.
Tracks 0–2 contain boot/DOS code and are marked **temporary raw code**; all other
unowned sectors are pending allocation and content analysis. No region is
claimed as safely retained opaque data yet. Boot/DOS source and game-code
source are still required before the final build is complete.

[Boot loading](boot-loading.md) now documents the observed two-stage bootstrap,
37-page DOS extent and subsequent START/custom-loader destinations. Both disk
copies' first two sectors are assembled source authority; surrounding system
track exports remain temporary references and inputs for unfinished DOS analysis.

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
Final build output is permitted to differ in bytes after behavior is validated.
