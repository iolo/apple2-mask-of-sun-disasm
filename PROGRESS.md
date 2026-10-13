# Progress

## Step 0 — Plan recorded

Completed on 2026-10-13.

- Read `PRD.md` and the current `README.md`.
- Confirmed both disk images and the supplied reference materials are present.
- Confirmed `a2kit`, `ca65`, `cl65`, `da65`, Python 3, and MAME are on PATH;
  versions and runtime prerequisites remain to be verified in Step 1.
- Created `PLAN.md` with staged deliverables, acceptance checks, and the required
  progress-update/commit workflow.

Validation: compared the plan with all requested PRD outputs and constraints.
No game analysis, extraction, source reconstruction, or build validation has
been performed. Original inputs are unchanged.

Next: Step 1 — record input hashes/provenance, verify tooling and emulator
prerequisites, and establish the project structure.

## Plan review revision

Completed on 2026-10-13 following review and user clarification.

- Made original-byte identity optional for disks, code, and encoded assets;
  distinguished behavioral validation, extraction integrity, and build repeatability.
- Moved the full original-game playthrough into the baseline step and reused the
  raw repacker for an early build without original-image templates.
- Clarified readable-code completion requirements and acceptable opaque data
  without requiring exhaustive instruction explanations or execution-path coverage.
- Required separate editable image files and project-specific decode/encode
  conversion, including verification that image edits appear in the rebuilt game.
- Made filesystem-based I/O replacement explicitly optional, with documented
  differences and behavior checks, and reduced optional tooling/documentation scope.

Validation: reviewed the revised plan against `PRD.md` and the user's clarified
requirements, and checked the documentation diff for formatting errors. No game
implementation or runtime validation was performed. Next remains Step 1.

## Step 1 — Input provenance and tooling

Completed on 2026-10-13.

- Recorded sizes, SHA-256, roles and provenance limits for all eleven supplied
  inputs in `docs/inputs.json`; documented the PRD's Korean-PDF filename mismatch
  and omitted diskette filename. Inputs remain unchanged.
- Recorded usable tool versions and successful Apple II+ ROM audit. Selected
  48K Apple II+, 6502, Applesoft ROM, slot 6 Disk II NG, no language card or
  Mockingboard. ROMs remain externally supplied. `START` invokes HGR/HGR2 and
  loads the interpreter at $0800, establishing the Applesoft requirement.
- Visually inspected manual scans and booklet controls/save/load pages; recorded
  reference claims separately from runtime findings and generated an unverified
  candidate route. Consulted the earlier local Stellar 7 MAME-check conventions.
- Established source/asset/tool/documentation directories, ignored generated
  output, input/tool checks, isolated media-copy MAME launcher and Lua capture
  helpers. Wrote setup and reference notes; expanded README entry points.

Validation: `python3 tools/check_inputs.py` verifies all eleven inputs;
`python3 tools/check_tools.py --rompath /home/iolo/workspace/retro/a2x/mame/roms
--output docs/toolchain.json` passes; `python3 -m py_compile tools/*.py` and
`git diff --check` pass. Launched the documented II+ profile with debug/headless
flags in `build/baseline-02`, loaded console helpers, ran from reset and captured
CPU, RAM, text and PNG. MAME successfully read the copied side A and entered
DOS during the initial capture. Opening gameplay is not yet verified.

Findings: default `apple2` Integer BASIC does not automatically boot this
Applesoft startup. MAME's autoboot script has a separate Lua environment from
the console, so helpers must be loaded explicitly there. Headless audio is
disabled and does not count as sound validation.

Next: Step 2 — wait for game loading, record startup/opening controls and
command checks, then establish the complete original route with timed events.

## Steps 2a/3a — Opening replay and complete raw sector export

Completed substeps on 2026-10-13; Steps 2 and 3 remain open.

- Captured the original game's plane introduction, pagination, live command
  prompt, inventory and parser errors. Incrementally replayed the opening route
  through the map, hut/flute exchange, statue inscription/head puzzle and
  clearing transition using a fresh boot and natural-keyboard input.
- Located the graphics text output vector ($B317) and font addressing in the
  captured renderer; implemented a glyph decoder for the native 40×16 grid.
  Runtime screenshots verify the decoded inventory and dialogue. Non-text
  drawing regions remain explicit unknown glyphs. Ordinary text RAM is stale.
- Added emulated-time bounded captures and a fresh-boot opening replay, with
  timestamps and an opening behavior verifier. Archived decoded checkpoint
  records, input/media configuration and six representative screenshots under
  `docs/evidence/`. Headless replay does not establish sound behavior.
- Identified DOS logical sector order, catalog/TS-list chains and full allocated
  file streams. Exported both disks into non-overlapping source regions and a
  complete 1,120-sector manifest. Repacking starts from empty arrays and reads
  only those regions; this remains a temporary raw build, not source completion.
- Compared every one of 139 live file streams independently against a2kit raw
  extraction. Two catalog counts have an unexplained added $2800, and graphical
  files with DOS binary type lack valid DOS binary headers. Both are preserved
  and documented rather than used as incorrect allocation limits.

Validation: `python3 tools/verify_opening.py build/opening-01 --output
docs/evidence/opening-original.json` passes all 13 opening checks. The replay
exits normally at 314.2 emulated seconds after 44 captured pagination/prompt
checkpoints. `python3 tools/dos_disk.py repack`, both disk `cmp` commands and
all 139 independent `a2kit get -t raw` comparisons pass. `tools/check_inputs.py`,
Python compilation and `git diff --check` pass. See `docs/baseline.md` and
`docs/disk-layout.md` for scope, commands, provenance and interpretation limits.

Remaining: original full route/ending, both-side and timed behavior, sound,
save/restore, restart/boundaries; boot-to-game loader tracing and memory map;
all readable assembly and editable graphics. Unowned sectors and mixed/font
regions are still under analysis. No opaque region is claimed as final retention.
Next: extend the original route into the first pyramid and investigate its
keyboard/timer conventions, then trace bootstrap/renderer and replace initial
raw-code regions with assembly.
