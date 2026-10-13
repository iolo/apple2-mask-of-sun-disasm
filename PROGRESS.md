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
