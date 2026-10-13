# Standalone source and asset build

The build needs Python3, Pillow and `ca65`/`ld65` on PATH. Tested versions are
recorded in [toolchain.json](toolchain.json); the current Pillow version is12.1.1.
MAME, ROMs, a2kit, original disks, PDF tools and NumPy are unnecessary for building.
Original code/image/TS-list exports are reference artifacts and are not read.
See [setup.md](setup.md) for the additional emulator/analysis requirements.

```sh
python3 tools/check_tools.py --build-only
python3 tools/build.py
```

Outputs are `build/disks/mask-of-sun-a.dsk` and `mask-of-sun-b.dsk`.
The build also emits objects, listings, labels, maps, generated font data and
`build.json`/`repack.json`. The manifests record source and editable-asset hashes,
generated/retained region authority, native metadata seeds, placement spans,
allocation constraints and final disk hashes. Reference-hash agreement is
diagnostic, not the criterion for correct gameplay. No raw-code dependency remains.

`--output build/OTHER_DIRECTORY` selects another generated directory. Every
invocation re-encodes images, assembles every module and rebuilds blank disk arrays;
there is no incremental extraction/cache dependency. For a clean build choose a
new output directory, or remove the old disposable generated directory first.
Repeated builds never depend on objects/maps from a previous build. The tools
report missing compiler/Pillow, unsupported image edits, invalid placement or
allocation overflow as errors. Run from the checkout root using documented paths.

## Authorities and constraints

| Component | Authoritative input |
| --- | --- |
| Bootstrap, DOS/RWTS, interpreter, INTRIN, CHAR GEN | Readable `src/*.s`/`*.inc` and fixed linker configurations. |
| Font |96 editable PNGs in `assets/decoded/font`; generated data-only include. |
| Native pictures |257 SVGs and collection manifest; constrained vector encoder. |
| World, library, startup text |87 native high-bit text streams, with decoded views. |
| Engine parameters | Native structured parameter file, completely decoded. |
| Allocation/asset references | Raw manifest file/sector map; TS lists, catalog live entries/links and bitmap generated. |
| Inactive catalog/VTOC fields | Four native metadata data seeds. |
| Free-sector history | Three inactive sectors in two reference-region files; documented retention reason. |
| Reserved unused sectors | Generated zero spans. |

The disk [classification manifest](../assets/classification.json) identifies all
289 regions and their source slices, provenance and retention reason. Code and
image reference bytes can be absent without preventing a build. Native scripts
remain build data by design; general script editing/conversion is not promised.
Font/vector editing uses [chargen.md](chargen.md) and [pictures.md](pictures.md).

All assembled fixed regions have size/address assertions. Source and asset spans
must be in bounds and cannot overlap; every byte of a constructed code region
has assembly/data/zero authority. The side-B DOS variant emits the complete source
but only its two retained disk spans are placed, leaving other emitted bytes unused.
Code-file headers and allocation tails are explicit source, including the
interpreter's six-sector stream whose DOS BLOAD payload is only five sectors.
Picture collections preserve their fixed allocation and regenerate record lengths.
The repacker validates complete1120-sector coverage across both disks and exact
region slicing. No original disk serves as a template.

## Read and reproducibility audit

```sh
python3 tools/verify_build.py --output build/source-audit
```

This requires strace and a new audit directory. It builds twice in clean output
directories, compares the two disk pairs and rejects successful reads of either
original disk or any of195 code/image/TS-list reference exports. It also checks
complete classification and absence of temporary raw-code dependencies. The
accepted report is [standalone-build.json](evidence/standalone-build.json).
This verifies build inputs and reproducibility; gameplay uses separate fresh
emulator replays with the original profile.

The final audit also builds a clean tracked-file checkout with supplied inputs
and reference-only regions deliberately absent, then boots its disks. That check
must be recorded separately before the overall plan is complete. The ordinary
`check_inputs.py` is a provenance check for a checkout containing supplied inputs;
it is not called by the build and is unnecessary in a reference-free checkout.

Original layout and low-level I/O are retained. There is no replacement filesystem,
new loader requirement or changed media insertion behavior. Boot A, swap A/B in
drive1 only at game prompts, and use an initialized scratch disk for native save
snapshots. Save writes144 sectors (tracks23–31), not a catalog file. Play and
validation commands are in [setup.md](setup.md) and [baseline.md](baseline.md).
