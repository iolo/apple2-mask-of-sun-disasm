# The Mask of the Sun — Apple II disassembly

Reverse engineering the supplied cracked two-sided Apple II game into readable
6502 assembly, documented assets and a standalone playable disk rebuild.

Implementation is in progress. The final disk build and gameplay equivalence
validation are not complete. See [PLAN.md](PLAN.md) and [PROGRESS.md](PROGRESS.md).

Start with [setup and emulator instructions](docs/setup.md), then run:

```sh
python3 tools/check_inputs.py
python3 tools/check_tools.py --rompath /path/to/locally-supplied/roms
python3 tools/mame_session.py --rompath /path/to/locally-supplied/roms \
  --output build/session-01 --debug --headless
```

[Input provenance](docs/inputs.json), [tool versions](docs/toolchain.json),
[reference notes](docs/reference-notes.md) and the
[candidate walkthrough route](docs/candidate-route.json) establish the baseline.
`src/` is for assembly, `assets/` for extracted game data, `tools/` for analysis
and build commands, `docs/` for evidence and explanations, and ignored `build/`
for generated output. Original inputs remain unchanged at the repository root.

A standalone source/asset rebuild is available:

```sh
python3 tools/build.py
```

It produces `build/disks/mask-of-sun-{a,b}.dsk`, assembles all loaded engine,
character generator, DOS/RWTS and bootstrap code, encodes editable
[font PNGs](docs/chargen.md) and [picture SVGs](docs/pictures.md), and packages
tracked data without reading original disk templates or native code/image
references. All disk regions and world scripts are classified/documented.
The separate manual baseline and final clean-checkout audit remain pending.
See the emitted `build.json` for dependencies and [baseline evidence](docs/baseline.md)
for the verified opening route. [Build instructions](docs/build.md) describe
source authority and the read audit. The [disk map](docs/disk-layout.md) documents
all extracted regions and the raw extraction round-trip checks.
The [boot trace](docs/boot-loading.md) explains load phases, and the
[behavior matrix](docs/behavior-matrix.md) links full-ending, sound and
save/restore results for the current partial build.
