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

An **early partial rebuild** is now available:

```sh
python3 tools/build.py
```

It produces `build/early/mask-of-sun-{a,b}.dsk`, assembles the documented text
renderer and packages tracked exports without reading original disk templates.
Other code and graphics still use temporary native exports. See the emitted
`build.json` for those dependencies and [baseline evidence](docs/baseline.md)
for the verified opening route. The [disk map](docs/disk-layout.md) documents
all extracted regions and the raw extraction round-trip checks.
