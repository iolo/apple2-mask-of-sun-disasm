# The Mask of the Sun — Apple II disassembly

Readable 6502 assembly, extracted game assets and a repeatable disk rebuild of
the supplied cracked two-sided Apple II adventure. All boot, DOS/RWTS and game
code has source; graphics are built from editable SVGs and font PNGs. The original
disk layout, loading, speaker synthesis and gameplay are preserved.

Build with Python3, Pillow and cc65's `ca65`/`ld65` on PATH:

```sh
python3 tools/check_tools.py --build-only
python3 tools/build.py
```

Outputs are `build/disks/mask-of-sun-a.dsk` and `mask-of-sun-b.dsk`, plus assembly
listings/maps and a dependency/hash manifest, `build.json`. Building reads tracked
source and assets; original disks and native code/image reference exports are
unnecessary. [Build instructions](docs/build.md) explain authority, fixed-address
constraints and clean builds. Tested versions are in [toolchain.json](docs/toolchain.json).

Play in MAME with locally supplied Apple II+ ROMs:

```sh
python3 tools/mame_session.py --rompath /path/to/roms --output build/play-01 \
  --disk-a build/disks/mask-of-sun-a.dsk --disk-b build/disks/mask-of-sun-b.dsk
```

The launcher creates isolated writable disk copies and uses a 48K Apple II+ with
the slot6 Disk II controller. Boot side A. When the game asks for side B, enter
the printed helper-loading command in MAME's Lua console, then `mask.swap('b')`,
and continue at the game's prompt. Use the corresponding A swap when requested.

To play through the ending automatically using the supplied walkthrough route:

```sh
python3 tools/mame_session.py --rompath /path/to/roms --output build/walkthrough-01 \
  --headless --fast --script tools/walkthrough_replay.lua
python3 tools/verify_route.py build/walkthrough-01 docs/full-route.json
```

The Lua script advances pages, issues commands at prompts, handles timed actions
and swaps its copied disk sides. It writes `replay-result.json` and an ending
capture in the session directory; the verifier checks the route and victory.
For the original game, native SAVE GAME/RESTORE GAME use an initialized scratch
disk; they write tracks 23–31 rather than a catalog file.

The Korean `r01-extra-save` release uses the same English commands, boots its
EXTRA disk, and needs a 16K Language Card. Run its dedicated Lua replay with all
three release images:

```sh
python3 tools/mame_session.py --rompath /path/to/roms \
  --output build/korean/walkthrough-01 \
  --disk-extra output/korean-playtest-r01-extra-save/mask-of-sun-ko-extra.dsk \
  --disk-a output/korean-playtest-r01-extra-save/mask-of-sun-ko-a.dsk \
  --disk-b output/korean-playtest-r01-extra-save/mask-of-sun-ko-b.dsk \
  --boot-extra --language-card --headless --fast \
  --script tools/korean/walkthrough_replay.lua
```

Use a fresh output directory for each run. The script recognizes Korean page
pauses, disk requests, the ghost and jump cues, and the final message. It writes
`korean-replay-result.json` and an ending capture under the session directory.
The Korean EXTRA disk also serves as its save disk. [Setup](docs/setup.md)
covers ROM checks, visible/headless operation, audio and debugger controls.

Fresh-boot original/rebuilt routes reach the ending across both disks, including
timed sequences. Checks cover commands/parser limits, puzzles, inventory, deaths,
restart, both-side saves/restores, representative scene/state comparisons and
nonzero speaker recordings. Every one of the 257 picture records passes native
render comparisons, and supported font/vector edits were verified in game.
The separate [manual baseline](docs/manual-playthrough.md) records an
operator-stepped ending with a documented native checkpoint retry.

```sh
python3 tools/verify_build.py --output build/source-audit
python3 tools/verify_checkout.py --output build/checkout-audit
```

These strace audits verify repeatability and excluded reference reads. The second
builds a committed clean tree with all supplied inputs and reference-only regions
removed. [Validation instructions](docs/validation.md) give fresh gameplay,
sound, save, boot and clean-checkout commands; the [behavior matrix](docs/behavior-matrix.md)
links accepted reports and coverage limits.

| Read or edit | Guide |
| --- | --- |
| Assembly modules and interfaces | [Source index](src/README.md), [boot/loading](docs/boot-loading.md), [DOS](docs/dos.md), [RWTS](docs/rwts.md) |
| Interpreter, input and script operations | [Engine](docs/engine.md), [intrinsics](docs/intrinsics.md) |
| Memory, shared state and call flow | [Memory map](docs/memory.md) |
| Rooms, vocabulary, objects and puzzles | [World logic](docs/world.md), [decoded indexes](assets/decoded/world/) |
| Pictures and supported SVG edits | [Picture format](docs/pictures.md), [editable assets](assets/decoded/pictures/) |
| Font PNGs and text rendering | [Character generator](docs/chargen.md), [renderer](docs/renderer.md) |
| Disk provenance and retained data | [Disk map](docs/disk-layout.md), [classification](assets/classification.json) |

All eleven supplied inputs remain unchanged; [inputs.json](docs/inputs.json)
records their hashes and actual filenames, including the Korean walkthrough
filename discrepancy in the PRD. Original media and scans stay at the repository
root; generated work belongs in ignored `build/`. The native scripts/parameters,
inactive metadata fields and three free historical sectors are retained data with
documented reasons, and contain no unfinished executable-source dependency.

Untested coverage includes missing/unformatted save-media errors, every optional
room branch and alternate puzzle solution. Historical crack metadata purposes
remain uncertain. Those limits are distinct from incomplete disassembly.
[PLAN.md](PLAN.md) and [PROGRESS.md](PROGRESS.md) record implementation and evidence.
