# Implementation plan

## Goal and completion criteria

Reverse engineer the supplied cracked Apple II version of **The Mask of the
Sun** into readable, documented 6502 assembly and extracted assets, with a
repeatable build that produces playable disk images.

The project is complete when:

- Game code, including boot code and overlays, has buildable source with meaningful
  labels, explanations of its role, and documented interfaces. Code and data are
  distinguished; remaining uncertainties are explicitly recorded. Raw executable
  blobs cannot substitute for disassembling game code. Exhaustive explanation of
  every instruction and exhaustive execution-path coverage are not required.
- Text, graphics, world data, and any sound data found in the game are extracted,
  documented, and incorporated into the build. Images have separate human-viewable,
  editable files, decoded from any game-specific compression or encoding, and
  project-specific converters that rebuild supported edits into the game.
  Other assets may retain their native format with provenance and decoded views
  where needed for understanding; general asset-editing tools are not required.
- A clean checkout can generate both disk images from source and assets without
  reading the original disk images as build templates or extracting them at build time.
- Rebuilt disks boot and preserve the original game's commands, text, graphics,
  sound where present, puzzles, progression, timing-sensitive interactions, and
  ending. Changes to disk insertion, swapping, or loading behavior caused by an
  optional I/O replacement are documented and validated on the target machine.
- Setup, build, validation, architecture, and remaining uncertainties are documented.

Byte-for-byte identity is not required for disk images, executable code, or encoded
assets. Byte comparisons are diagnostic tools, not completion criteria for the
rebuilt game. Intentional differences are acceptable when documented and validated
against the required behavior. Do not spend effort eliminating byte differences
solely to achieve identity. Exact checks of input preservation and raw extraction
still establish provenance; repeatable build hashes establish reproducibility,
not identity with the original disks.

Preserving load addresses and disk layout is a useful starting point, not a final
requirement. Replacing low-level track/sector I/O with filesystem-based I/O is
permitted but not required. Disk layout, allocation metadata, loader code, and
physical access patterns may change when affected dependencies are understood
and required behavior is preserved. Retain readable source for the original I/O
implementation and explain any replacement. Keep the original I/O approach when
replacement offers no concrete benefit. Preserve gameplay of the cracked inputs;
restoring copy protection or redesigning gameplay is outside this project's scope.

Retained opaque data must have provenance and a stated reason for retention,
including why it does not conceal unfinished game-code analysis. Distinguish
incomplete testing from incomplete disassembly when reporting limitations.

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
- Reassemble small regions early. Use byte comparisons to investigate unexpected
  differences where original encodings are retained; validate intentional changes
  through documented behavior checks without making byte identity a gate.
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

- [x] Record hashes, sizes, roles, and provenance of every supplied input in an
  input manifest. Resolve any discrepancies between the PRD and actual filenames.
- [x] Record tool versions and choose a reproducible emulator configuration:
  Apple II model, CPU, memory, ROM requirements, disk controller, and drive setup.
- [x] Inspect the manuals and booklet for controls, disk changes, timing rules,
  and save/load features if present; turn walkthroughs into a candidate route.
- [x] Consult the earlier disassembly repositories linked in the PRD when a
  specific convention would help; a comprehensive survey is optional. Do not
  assume their engines or disk layouts apply here.
- [x] Establish `src/`, `assets/`, `tools/`, `docs/`, and ignored `build/` outputs,
  plus an initial setup guide and tool checks.

**Acceptance:** Inputs are identifiable and unchanged, required tools are usable,
and another contributor can reproduce the chosen emulator setup.

### 2. Capture the original game's behavior

- [x] Boot the original disks and record startup, controls, initial scene, and
  disk insertion/swap behavior in a reproducible emulator session.
- [x] Capture representative screenshots, text, sound where present, disk activity,
  and CPU/memory observations with the emulator configuration and input sequence.
- [x] Exercise movement, descriptions, inventory, successful and rejected
  commands, and an early puzzle. Discover save/load or restart behavior from the
  actual game rather than assuming those features exist.
- [x] Establish how timed events and player input interact. Record explicit
  waits, conditions, or emulated cycle counts where a plain command list is insufficient.
- [ ] Complete a manual original-game playthrough to the ending using the supplied
  walkthrough as a guide, covering both disks and timed sequences. Record commands,
  observable wait conditions, and checkpoints; automate the route incrementally.
  If blocked, use targeted loader or logic investigation from later steps to
  resolve the obstacle before marking this baseline complete.
- [x] Begin a behavior matrix from that route and the command checks; expand it
  as later disk regions and game states become understood.

**Acceptance:** The unmodified game boots reliably, baseline artifacts exist,
and a recorded full route reaches the ending. The opening route is repeatable;
timed sections have explicit conditions suitable for later replay automation.

### 3. Map disk layout, boot sequence, and memory loading

- [x] Identify container/sector order and catalog any recognized filesystem.
  If storage is custom, inspect and export sectors directly rather than forcing
  a filesystem interpretation.
- [ ] Trace boot sectors, loader entry points, disk reads, side selection, and
  any decoding, decompression, or relocation used when loading memory.
- [ ] Build a manifest mapping all disk regions to boot code, resident code,
  overlays, assets, metadata, padding, or explicitly unknown content.
- [ ] Record memory ranges, entry points, zero-page usage, stack assumptions,
  buffers, ROM calls, and Apple II soft-switch accesses.
- [x] Export raw regions without altering their bytes and verify that a sector
  extraction/repacking round trip preserves each original image. Construct the
  repacked images from exports and the manifest, without reading an original
  image as a template; this exact check verifies extraction, not final-build identity.

**Acceptance:** Boot-to-game loading is explained, exported data has complete
provenance, all disk bytes are accounted for, and round-trip comparisons pass.

### 4. Create an early assembly and disk rebuild

- [x] Seed disassembly from traced entry points using `da65` or equivalent
  tooling. Separate known data from reachable code and flag ambiguous regions.
- [x] Create `ca65` modules and explicit `ld65` segment layouts for boot,
  resident code, and overlays at their observed addresses.
- [x] Account for tables, self-modifying operands, required padding, and
  load/run-address differences. Retain original encodings as a convenient starting
  point. Use raw bytes temporarily where necessary, with each such region tracked
  for later interpretation and executable blobs replaced by readable assembly.
- [x] Assemble identified code and compare output region by region against the
  original exports where useful. Investigate unexpected differences; record the
  reason and behavior checks for intentional changes rather than forcing a match.
- [x] Reuse Step 3's repacker to build an initial pair of disks from exported
  regions, progressively replacing code regions with assembled output. Boot them
  through the opening replay. Track all temporary raw-code dependencies.

**Acceptance:** A repeatable build produces disks that boot to the opening scene,
uses assembled output for identified code, and passes the opening behavior checks.
Unexpected differences are investigated; intentional differences have explanations
and validation evidence. Packaging does not read original-image templates.

Current scope: bootstrap, all loaded DOS/RWTS pages, resident interpreter,
intrinsics and complete CHAR GEN source/data with editable font PNGs. Reserved
unused disk residue still needs final classification; vector images are now
encoded from individual editable SVGs with native previews. No separate
6502 overlay has been established yet. Completing this early build step does not
close the complete-source or editable-graphics criteria in later steps.

### 5. Explain the loader and resident engine

- [x] Replace generated address labels with meaningful names as evidence permits.
- [x] Document boot/loader control flow, disk I/O, overlay ownership, and the
  entry/return conventions between resident code and loaded modules.
- [x] Identify keyboard input, command parsing, vocabulary lookup, text output,
  graphics rendering, game-state updates, and timing/randomness routines as present.
- [x] Annotate routine inputs, outputs, register clobbers, shared memory, firmware
  calls, and any self-modifying code.
- [x] Maintain memory maps and add focused call graphs where they aid understanding;
  comprehensive call graphs are optional. Confirm uncertain indirect calls and
  code/data boundaries with targeted execution traces.

**Acceptance:** Core subsystems have readable source and documented interfaces,
the build succeeds, and the established behavior checks pass. Intentional code
differences are documented without requiring original-byte identity.

### 6. Decode and extract assets

- [x] Identify text encoding/compression, dictionary/token tables, graphics
  representation, palettes or artifact-color assumptions, and world-data formats.
- [x] Export texts with stable identifiers and decoding notes; preserve control
  codes and references. Native build assets plus readable decoded views are
  sufficient; an editable text format and encoder are optional.
- [x] Extract each image into a separate documented, human-viewable and editable
  file. Decode any game-specific compression or encoding for review. Determine
  the actual representation, including vector formats if present, and preserve
  the game's rendering and artifact-color behavior for unmodified images.
- [x] Implement only the project-specific conversion needed to encode/compress
  those editable image files back into game assets. Make the editable files
  authoritative build inputs; native reference exports are provenance artifacts.
  Document supported edits, colors, dimensions, and storage constraints, and
  report unsupported input or edits that exceed those constraints.
- [x] Extract room/object tables, vocabulary, puzzle data, and sound sequences
  where present. If sounds are generated by code, document the routines instead.
- [x] Verify that unmodified image files rebuild to equivalent rendered scenes,
  even if encoded bytes differ. Make a representative supported image edit and
  verify its appearance in the rebuilt game, then restore the baseline asset.
  General-purpose editors and reusable asset-conversion frameworks are out of scope.

**Acceptance:** Every identified asset region has provenance and format notes;
images are separately reviewable and editable, unmodified images retain their
appearance after conversion, and a supported edit appears in the rebuilt game.
Other extracted assets are incorporated into the build with readable views where
needed. Encoded-byte identity is not required.

### 7. Explain overlays, world logic, and puzzles

- [x] Trace all discovered overlays and executable script formats. Distinguish
  interpreted game data from 6502 code and document the interpreter if present.
- [x] Map rooms, exits, items, flags, event conditions, timers, failure states,
  and ending logic to symbols and extracted data.
- [x] Cross-reference puzzle behavior with the manuals, walkthroughs, and runtime
  evidence. Treat reference material as a guide rather than proof of code behavior.
- [ ] Cover code paths beyond the main route: invalid actions, inventory changes,
  repeated interactions, alternate transitions, deaths, and restart/save handling
  where implemented.
- [ ] Review all remaining raw-code regions and unknown disk regions. Resolve
  game-critical uncertainties and replace temporary executable blobs with readable
  assembly. Document provenance and reasons for retaining opaque data, including
  evidence that it does not conceal unfinished game-code analysis.

**Acceptance:** All game-code regions have readable source with roles and interfaces
documented; major world, puzzle, and ending logic is explained. The rebuilt game
passes the established route checkpoints. Remaining uncertainties and untested
paths are recorded; exhaustive instruction commentary or path coverage is not required.

### 8. Finish the standalone, reproducible build

- [ ] Replace any remaining temporary raw-code dependencies. Construct both disks
  entirely from assembled code, tracked assets, and documented required metadata
  or retained opaque data, continuing to exclude original-image templates.
- [ ] Generate disk allocation tables and asset references from the manifest
  where possible; enforce fixed-address, size, overlap, and capacity constraints.
- [ ] Provide one documented build command, clean behavior, clear missing-tool
  errors, and machine-readable build manifests with output hashes.
- [ ] Keep the original layout and I/O approach unless a change has a concrete
  benefit. Optionally replace track/sector I/O with filesystem-based I/O; update
  affected references, document target memory and filesystem requirements, retain
  readable original I/O source, and validate required behavior. Document any changes
  to disk insertion, swapping, or loading. This replacement is not an acceptance gate.
- [ ] Build twice from clean generated-output directories and compare outputs;
  verify that no original `.dsk` files are read by the final build.

**Acceptance:** Source and assets alone produce both playable images with
repeatable hashes, and the build documents any preserved non-game disk components.
Repeatability compares clean builds with each other, not with original disk hashes.

### 9. Validate gameplay equivalence

- [ ] Automate original/rebuilt replays under the same emulator configuration,
  using fresh boots and controlled input timing or observable event conditions.
  Adapt replay loading steps for documented I/O changes without masking changes
  to gameplay timers or required player reactions.
- [ ] Compare semantic state, text, sound where present, and representative rendered
  scenes at checkpoints. Compare physical disk accesses only as diagnostics for
  unchanged layouts; changed layouts are checked for correct loaded content,
  logical transitions, disk prompts, and gameplay timing. Intentional differences
  in code, encoded assets, metadata, or layout do not require byte equality.
- [ ] Complete a walkthrough on rebuilt disks, covering content from both original
  sides, disk swaps as required by the rebuilt layout, major puzzles, timed
  sequences, failures/restarts, and the ending.
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
  retained opaque data or incomplete path coverage. Document intentional rebuild
  differences, image-editing constraints, and any optional I/O replacement.
- [ ] Perform a clean-checkout build and boot check using only documented steps.
- [ ] Update `PROGRESS.md` against the PRD's completion criteria and commit the
  final verified source, tools, assets, and documentation.

**Acceptance:** A new contributor can build, play, and navigate the disassembly
without relying on undocumented local files or knowledge.

## Dependencies and iteration

Steps 1–4 establish the evidence and a working rebuild. Step 2 establishes that
the original game can be completed before extensive reconstruction; targeted
investigation from later steps may be used to resolve baseline obstacles. Step 3's
raw repacker becomes Step 4's early template-free build. Steps 5–7 are iterative:
new engine findings inform asset decoders, and decoded world data exposes new
code paths. Keep rebuilding and replaying the established checkpoints during
that work. Step 8 requires complete loader and asset mapping; Step 9 validates
the final build; Step 10 closes documentation and reproducibility gaps.

The main uncertainties are custom sector loading, overlays, code mixed with
data, compression, self-modification, and event timing. Resolve each through
targeted runtime traces, behavior checks, and byte comparisons where useful.
Document original formats from evidence; base any relocation or replacement
filesystem choice on understood dependencies and validate the resulting behavior.
