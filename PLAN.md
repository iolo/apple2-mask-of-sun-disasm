# Implementation plan

## Goal and completion criteria

Reverse engineer the supplied cracked Apple II version of **The Mask of the
Sun** into readable, documented 6502 assembly and extracted assets, with a
repeatable build that produces playable disk images.

The project is complete when:

- Game code, including boot code and overlays, has buildable source with meaningful
  labels, comments, and documented interfaces. Code and data are distinguished;
  unresolved regions are explicitly recorded rather than presented as understood.
- Text, graphics, world data, and any sound data found in the game are extracted,
  documented, and incorporated into the build. Editable representations have
  encoders; assets retained in their native format have documented provenance.
- A clean checkout can generate both disk images from source and assets without
  reading the original disk images as build templates or extracting them at build time.
- Rebuilt disks boot and preserve the original game's commands, presentation,
  puzzles, transitions, disk changes, timing-sensitive events, and ending.
- Setup, build, validation, architecture, and remaining uncertainties are documented.

Byte-identical disk images are useful diagnostic targets, but are not required.
Preserve load addresses and disk layout initially to reduce variables. Change
layout only after all relevant disk accesses are understood and gameplay remains
equivalent. Preserve observed behavior of the cracked inputs; restoring copy
protection or redesigning gameplay is outside this project's scope.

## Starting point

The repository currently contains `PRD.md`, a minimal `README.md`, two 143,360-byte
disk images, manual and box scans, a booklet, and English/Korean walkthroughs.
No disassembly, extraction scripts, or build system exists yet.

`a2kit`, `ca65`, `cl65`, `da65`, Python 3, and MAME are available on the current
machine. Record versions and emulator/ROM prerequisites before relying on them.
Use `ca65`/`ld65` for address-controlled assembly, Python for extraction and
verification, and `a2kit` for disk inspection and packaging where supported.
Use MAME with Lua automation as the initial emulator; Apple2TS is an alternative
or a second implementation for investigating discrepancies.

Neither the `.dsk` extension nor image size establishes sector order, filesystem,
or loader behavior. Determine those from the images and runtime evidence.

## Working rules

- Keep all supplied inputs unchanged. Record hashes before analysis and write
  generated files into separate output directories.
- Give every extracted region its disk, track/sector or file offset, length,
  encoding, and load address where applicable. Distinguish evidence from inference.
- Maintain one authoritative representation for each code/data region; generate
  alternate views and previews from it to avoid conflicting copies.
- Reassemble small regions early. Compare bytes at each stage before adding
  semantic labels or restructuring modules.
- Combine static analysis with runtime traces, especially for computed jumps,
  overlays, self-modifying code, and timing-sensitive behavior.
- After each completed step, update `PROGRESS.md` with changes, evidence,
  validation commands/results, uncertainties, and the next step; commit that work.
  Break large steps into documented substeps with their own completion commits.
- Do not mark a step complete while its acceptance checks remain open. Revise
  this plan when evidence changes its assumptions or dependencies.

## Step-by-step work

### 0. Record the plan

- [x] Read the PRD and inventory the repository at a high level.
- [x] Save this plan and initialize `PROGRESS.md` with implementation still pending.
- Commit the planning documents before implementation begins.

**Acceptance:** The plan covers all PRD outputs and defines evidence needed to
complete each implementation step.

### 1. Establish input provenance and tooling

- [ ] Record hashes, sizes, roles, and provenance of every supplied input in an
  input manifest. Resolve any discrepancies between the PRD and actual filenames.
- [ ] Record tool versions and choose a reproducible emulator configuration:
  Apple II model, CPU, memory, ROM requirements, disk controller, and drive setup.
- [ ] Inspect the manuals and booklet for controls, disk changes, timing rules,
  and save/load features if present; turn walkthroughs into a candidate route.
- [ ] Review the earlier disassembly repositories linked in the PRD for reusable
  conventions, without assuming their engines or disk layouts apply here.
- [ ] Establish `src/`, `assets/`, `tools/`, `docs/`, and ignored `build/` outputs,
  plus an initial setup guide and tool checks.

**Acceptance:** Inputs are identifiable and unchanged, required tools are usable,
and another contributor can reproduce the chosen emulator setup.

### 2. Capture the original game's behavior

- [ ] Boot the original disks and record startup, controls, initial scene, and
  disk insertion/swap behavior in a reproducible emulator session.
- [ ] Capture representative screenshots, text, disk activity, and CPU/memory
  observations with the emulator configuration and input sequence attached.
- [ ] Exercise movement, descriptions, inventory, successful and rejected
  commands, and an early puzzle. Discover save/load or restart behavior from the
  actual game rather than assuming those features exist.
- [ ] Establish how timed events and player input interact. Record explicit
  waits, conditions, or emulated cycle counts where a plain command list is insufficient.
- [ ] Begin a behavior matrix and replay route based on the supplied walkthrough;
  expand it as later disk regions and game states become understood.

**Acceptance:** The unmodified game boots reliably, baseline artifacts exist,
and a repeatable opening route is available for later comparisons.

### 3. Map disk layout, boot sequence, and memory loading

- [ ] Identify container/sector order and catalog any recognized filesystem.
  If storage is custom, inspect and export sectors directly rather than forcing
  a filesystem interpretation.
- [ ] Trace boot sectors, loader entry points, disk reads, side selection, and
  any decoding, decompression, or relocation used when loading memory.
- [ ] Build a manifest mapping all disk regions to boot code, resident code,
  overlays, assets, metadata, padding, or explicitly unknown content.
- [ ] Record memory ranges, entry points, zero-page usage, stack assumptions,
  buffers, ROM calls, and Apple II soft-switch accesses.
- [ ] Export raw regions without altering their bytes and verify that a sector
  extraction/repacking round trip preserves each original image.

**Acceptance:** Boot-to-game loading is explained, exported data has complete
provenance, all disk bytes are accounted for, and round-trip comparisons pass.

### 4. Create an early assembly and disk rebuild

- [ ] Seed disassembly from traced entry points using `da65` or equivalent
  tooling. Separate known data from reachable code and flag ambiguous regions.
- [ ] Create `ca65` modules and explicit `ld65` segment layouts for boot,
  resident code, and overlays at their observed addresses.
- [ ] Preserve instruction encodings, tables, padding, self-modifying operands,
  and load/run-address differences. Use raw bytes temporarily where necessary,
  with each such region tracked for later interpretation.
- [ ] Assemble identified code and compare output region by region against the
  original exports. Report the location and context of any mismatch.
- [ ] Package an initial pair of rebuilt disks using the discovered layout and
  boot them through the opening replay. Original-image templates may be used
  temporarily here, with their removal tracked explicitly for Step 8.

**Acceptance:** A repeatable build produces disks that boot to the opening scene,
and identified assembled code matches the corresponding original regions.

### 5. Explain the loader and resident engine

- [ ] Replace generated address labels with meaningful names as evidence permits.
- [ ] Document boot/loader control flow, disk I/O, overlay ownership, and the
  entry/return conventions between resident code and loaded modules.
- [ ] Identify keyboard input, command parsing, vocabulary lookup, text output,
  graphics rendering, game-state updates, and timing/randomness routines as present.
- [ ] Annotate routine inputs, outputs, register clobbers, shared memory, firmware
  calls, and any self-modifying code.
- [ ] Maintain call graphs and memory maps; confirm uncertain indirect calls and
  code/data boundaries with targeted execution traces.

**Acceptance:** Core subsystems have readable source and documented interfaces,
reassembly still matches, and the opening behavior matrix passes.

### 6. Decode and extract assets

- [ ] Identify text encoding/compression, dictionary/token tables, graphics
  representation, palettes or artifact-color assumptions, and world-data formats.
- [ ] Export texts with stable identifiers and decoding notes; preserve control
  codes and references in an editable, reversible form.
- [ ] Export scene graphics in their native representation and generate indexed
  previews using the game's rendering rules. Document vector or compressed formats
  if discovered rather than assuming every picture is a stored bitmap.
- [ ] Extract room/object tables, vocabulary, puzzle data, and sound sequences
  where present. If sounds are generated by code, document the routines instead.
- [ ] Implement encoders for editable formats and meaningful round-trip checks,
  including malformed-input handling and length/address constraints.

**Acceptance:** Every identified asset region has provenance and format notes;
decode/encode checks preserve native data, and previews agree with original scenes.

### 7. Explain overlays, world logic, and puzzles

- [ ] Trace all discovered overlays and executable script formats. Distinguish
  interpreted game data from 6502 code and document the interpreter if present.
- [ ] Map rooms, exits, items, flags, event conditions, timers, failure states,
  and ending logic to symbols and extracted data.
- [ ] Cross-reference puzzle behavior with the manuals, walkthroughs, and runtime
  evidence. Treat reference material as a guide rather than proof of code behavior.
- [ ] Cover code paths beyond the main route: invalid actions, inventory changes,
  repeated interactions, alternate transitions, deaths, and restart/save handling
  where implemented.
- [ ] Review all remaining raw-code regions and unknown disk regions. Resolve
  game-critical uncertainties and document evidence for unused or opaque remnants.

**Acceptance:** All game-code regions have readable source, reachable gameplay
logic is documented, and a full original-game route reaches the ending.

### 8. Finish the standalone, reproducible build

- [ ] Remove original-disk template dependencies. Construct both disks entirely
  from assembled code, tracked assets, and documented required metadata/padding.
- [ ] Generate disk allocation tables and asset references from the manifest
  where possible; enforce fixed-address, size, overlap, and capacity constraints.
- [ ] Provide one documented build command, clean behavior, clear missing-tool
  errors, and machine-readable build manifests with output hashes.
- [ ] Retain the initial layout unless a change has a concrete benefit. Any
  changed layout must update all affected loader references and receive validation.
- [ ] Build twice from clean generated-output directories and compare outputs;
  verify that no original `.dsk` files are read by the final build.

**Acceptance:** Source and assets alone produce both playable images with
repeatable hashes, and the build documents any preserved non-game disk components.

### 9. Validate gameplay equivalence

- [ ] Automate original/rebuilt replays under the same emulator configuration,
  using fresh boots and controlled input timing.
- [ ] Compare semantic state, text, disk accesses, and representative rendered
  scenes at checkpoints; document acceptable differences in unused disk bytes.
- [ ] Complete a walkthrough on rebuilt disks, covering both sides, disk swaps,
  major puzzles, timed sequences, failures/restarts, and the ending.
- [ ] Exercise save/load if present, command errors, inventory limits or other
  discovered boundary conditions, and alternate reachable branches.
- [ ] Use a second emulator for significant unresolved behavior or timing
  discrepancies. Keep explanations and reproducible evidence with each finding.

**Acceptance:** The behavior matrix passes, the rebuilt game reaches its ending,
and there are no unexplained gameplay regressions. Validation limits are explicit.

### 10. Publish project documentation and final audit

- [ ] Expand `README.md` with purpose, prerequisites, build commands, output
  locations, emulator instructions, validation commands, and input provenance.
- [ ] Finish architecture, disk-layout, memory-map, engine, asset-format, and
  puzzle documentation with source cross-references.
- [ ] Separate confirmed findings from unresolved questions and explain any
  retained opaque bytes or incomplete path coverage.
- [ ] Perform a clean-checkout build and boot check using only documented steps.
- [ ] Update `PROGRESS.md` against the PRD's completion criteria and commit the
  final verified source, tools, assets, and documentation.

**Acceptance:** A new contributor can build, play, and navigate the disassembly
without relying on undocumented local files or knowledge.

## Dependencies and iteration

Steps 1–4 establish the evidence and a working rebuild. Steps 5–7 are iterative:
new engine findings inform asset decoders, and decoded world data exposes new
code paths. Keep rebuilding and replaying the established checkpoints during
that work. Step 8 requires complete loader and asset mapping; Step 9 validates
the final build; Step 10 closes documentation and reproducibility gaps.

The main uncertainties are custom sector loading, overlays, code mixed with
data, compression, self-modification, and event timing. Resolve each through
small byte comparisons and targeted runtime traces. Do not choose a filesystem,
relocate code, or declare a data format before the evidence supports it.
