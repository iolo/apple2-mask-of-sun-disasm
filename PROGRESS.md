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

## Steps 2b/4a — First pyramid and assembled text renderer

Completed substeps on 2026-10-13; full Steps 2–4 remain open.

- Extended the fresh-boot original route through the first pyramid: lit lantern,
  snake response, secret platform door, jade-bowl descent, ghost wait/gold bowl,
  skeletal guardians/silver bowl, urn pedestal door, and return to the jeep.
  Archived the successful 626.6-emulated-second replay with ten route gates and
  five representative screenshots. Original full playthrough is not yet done.
- Corrected natural-keyboard gating after a failed investigation run: inspect
  both queue-empty and posting state, require the ready cursor rather than
  typed partial text, distinguish urgent command reactions from ordinary
  pagination, and latch event conditions across page changes. Snake SHOOT has
  five keys and no Return; the skeleton requires an immediate initial reaction.
- Added readable high-bit ASCII views/line provenance for all 87 text/script
  files, generated from native authority with `tools/script_views.py`.
- Reconstructed $B300–$B3FF in `src/renderer.s` with named routines, explicit
  code/data boundaries, workspace, clobbers and text/page interfaces. ca65/ld65
  build and package this page into the native CHAR GEN region. Nine tail bytes
  remain explicitly unconfirmed data; the surrounding asset remains temporary.
- Added `tools/build.py` as an early partial source rebuild; both output disks
  are constructed from assembled output plus tracked exports, never from
  original-image templates. Its manifest names remaining temporary raw code.

Validation: `tools/verify_route.py build/pyramid-06
docs/first-pyramid-route.json --output docs/evidence/first-pyramid-original.json`
passes ordered commands, final prompt, no death and all seven puzzle gates.
`tools/verify_opening.py build/opening-rebuilt-01 --output
docs/evidence/opening-rebuilt.json` passes all thirteen opening checks for the
early source rebuild. Two fresh-output builds have identical hashes; a
`strace -f -e trace=openat` inspection finds no original-disk reads. Renderer
encoding currently equals its native reference, including its preserved data,
as a diagnostic. Source address/size assertions pass. Python compilation,
`tools/check_inputs.py` and `git diff --check` pass.

Limits: only the renderer page is reconstructed so far. Interpreter/intrinsics,
boot/DOS and the remainder of mixed CHAR GEN need source/analysis. Graphics are
not yet editable build inputs. Save/load, sound and the entire second side and
ending remain unvalidated. `docs/renderer.md` documents this early build's scope.
Next: extend the original playthrough onto side B, including disk swapping,
jaguar/chasm timing and the ending; then complete resident/boot disassembly.

## Steps 2c/4b — Original ending and assembled resident interpreter

Completed substeps on 2026-10-13; complete Steps 2–4 remain open.

- Reconstructed the entire $0800–$0CFF resident interpreter payload in
  `src/interpreter.s`: initialization, script dispatch/stack, command input and
  normalization, handler matching, catalog/file loader, DOS IOB and string output.
  Code/data boundaries, mutable fields, interfaces and shared pointers are named
  and documented in `docs/engine.md`. Intrinsics and bootstrap remain unfinished.
- Extended the original fresh-boot route through gas escape, timed stepping
  stone, XOTZIL faces, true-mask cure, coffin maze, Roboff and the final jaguar.
  Corrected paragraph-separated walkthrough commands and late first-key input.
  The final route reaches the win and next-adventure screens with 83 pills.
- Added normal/inverse font decoding, a bounded physical Return at a corroborated
  chasm phase, keyboard field cleanup, passive COUT output logging and optional
  keyboard bus observation. No accepted run modifies game RAM or original media.
  Captured transient success dialogue is verified from the native character log.
- Repeated all 122 commands on the current two-module standalone rebuild. Both
  original and rebuilt runs pass seventeen route checks, observe side B mounting,
  avoid player death and reach the same ending at 1909.4 emulated seconds. Archived
  222 decoded/CPU checkpoints per run and six representative original PNGs.
- Added an optional emulated mixer recording mode. Original opening WAV contains
  nonzero speaker output; sound equivalence work is still in progress and is not
  inferred from the sound-disabled full-route replays.

Validation: `tools/verify_opening.py build/core-opening-01` passes thirteen gates;
`tools/verify_route.py build/full-original-02 docs/full-route.json` and the same
verifier on `build/full-core-rebuilt-01` pass seventeen each. Both owned MAME
processes exit normally. Fresh `tools/build.py --output build/core-check-02`
assembles both modules and produces complete disks using tracked regions. Native
payload encoding equality remains diagnostic, not the behavior gate. Input hash
verification and Python compilation pass; see `docs/evidence/` for reports.

Remaining: save/restore, sound comparison, restart/boundaries and behavior matrix;
boot/DOS mapping/source, intrinsic and vector-graphics analysis, editable graphics,
world documentation and final clean reproducibility. The original full ending is
now established but does not close all Step 2 checks. Next: finish the remaining
baseline controls while reconstructing the intrinsic dispatch and graphics formats.

## Step 2d — Sound, save/restore, controls and restart evidence

Completed substep on 2026-10-13; the separate all-manual full-route criterion
and full Steps 3–10 remain open.

- Recorded original and rebuilt opening and full routes with the emulated mixer
  enabled. Full recordings have 42,101,830 frames at 22050Hz, nonzero channel0
  and two silent extra channels. PCM agrees throughout the ending; four compact
  mono examples and reproducible streaming verification are archived.
- Tested SOUND OFF/ON, chained LOOK/INVENTORY, a rejected unknown-word chain,
  forty-five-key input overflow, empty GET ALL and invalid plane movement. Both
  versions pass twelve route/state gates; dedicated PCM windows confirm silent
  pill effects with OFF and audible effects with ON. Actual retained input is
  thirty-six characters, rather than assuming the booklet's stated window size.
- Tested SAVE GAME in the jeep at room3, westward movement to room18, RESTORE
  GAME, cancellation and sound flags. Both versions pass eighteen checks and
  restore five $FC-byte object arrays exactly. Separate fresh boots restore
  existing saved media and pass eight checks each.
- Identified the native $90-page raw save transfer: RAM $AF00 downward to $2000
  maps track31/sector15 downward to track23/sector0. Isolated save images have
  exactly those 144 changed sectors, unchanged surrounding/catalog sectors,
  and original/rebuilt agreement. Native save is not a catalog file.
- Tested deliberate pill-overdose death, invalid death-screen input, and START
  restart. Both versions pass nine gates and recover room1/initial inventory.
  Added explicit expected-death mode without weakening successful-route checks.
- Created `docs/behavior-matrix.md` and documented commands, scope, media
  operations and uncertainty limits. Scratch media are copied before writes.

Validation: all four original/rebuilt control/save/restore/restart route pairs
pass. Audio-enabled full-route pairs still pass seventeen gameplay checks each;
`tools/verify_audio.py` passes opening, full and toggle comparisons, and
`tools/verify_save_disk.py` passes both save footprints. Owned MAME processes
exit normally. Python compilation, supplied-input hashes and diff whitespace
checks pass. A failed investigation treated MAME's nil load-success result as
an error; the corrected mount helper verifies its resulting filename instead.

Limits: the full route was guided and automated incrementally; no separate
all-manual full-route recording is claimed. Maximum inventory, side-B save and
all error paths remain untested, as stated in the behavior matrix. Byte equality
of recordings/save files is diagnostic evidence for the current implementation,
not a universal future equivalence requirement. Next: trace the bootstrap and
reconstruct the intrinsic dispatch/vector renderer and editable graphics.

## Steps 3b/4c — Traced and assembled two-stage bootstrap

Completed substep on 2026-10-13. Early-build Step 4 acceptance now passes;
complete mapping/source and the remaining plan are still unfinished.

- Observed slot6 ROM $C600/$C65C, disk entry $0801, second stage $B700, native
  RWTS $BD00, DOS output $A000, engine $0800, renderer $B300 and intrinsic/COUT
  entries. Read taps record native IOB requests without replacing fetched bytes.
  Snapshot recursion is guarded, and repeated ROM header scans are deduplicated.
- Established ten first-stage sectors at $B600–$BFFF and the next 27 DOS pages
  at $9B00–$B5FF, mapping T2/S4 down through T0/S10. Verified START's payload
  placements and custom full-file loads of INTRIN/CHAR GEN including headers.
- Added readable assembly for side-A bootstrap plus its resident DOS helpers,
  side-B wrong-side halt/message, and both variants of the second stage. IOB,
  DCT, interleave, mutable counter/pointer, native padding and diagnostic code
  are explicit. Native diagnostic padding alignment was corrected during
  encoding investigation, without treating disk identity as the acceptance gate.
- The build now assembles six modules, correctly merging multiple source spans
  in one exported region. The repacker rejects unknown replacement paths. Source
  authority covers both first two boot sectors, engine payload and renderer page;
  remaining system/code regions remain tracked temporary dependencies.
- Documented phase ownership: graphics and CHAR GEN overwrite portions of
  startup DOS; gameplay retains custom file loading and high-memory RWTS.
  Documented physical-vs-DOS logical interleave and true load/run destinations.

Validation: `tools/verify_boot.py build/boot-trace-02
build/boot-rebuilt-trace-02` passes seven checks per version and full agreement
of 224 observed entries/requests. Both wrong-side attempts print BOOT OTHER SIDE.
and halt at $0806. `tools/verify_opening.py build/boot-opening-01` passes thirteen
checks on the six-module build. A fresh repeated build agrees in its source
manifest; strace confirms no original-disk reads. Sandbox ptrace restrictions
required explicit approved tracing. Input preservation, Python compilation and
diff whitespace checks pass. Reports are archived under `docs/evidence/`.

Limits: bootstrap assembly does not finish the remaining DOS file manager/RWTS
source. Intrinsic code, mixed CHAR GEN content, graphic encoding/edit authority,
world interpretation and final reproducibility remain open. Step 3's complete
semantic manifest/memory map also remains open. Next: map native DOS code/data
using its traced interfaces, then reconstruct the intrinsic/vector engine.

## Steps 3c/5a — Resident sector read/write source

Completed substep on 2026-10-13; full DOS and the remaining plan stay open.

- Reconstructed $B800–$BFFF as `src/rwts.inc`, with side-specific wrappers:
  6-and-2 conversion, timed GCR/address readers and writers, seek/motor control,
  public RWTS dispatch/retries, format code and DOS tail helpers. Interfaces,
  carry/status errors, shared scratch and cycle-sensitive instructions are named.
- Classified lookup tables, nibble scratch, verification flags and isolated
  residual/padding bytes explicitly. Preserved the overlapping BIT/SEC success
  and error entry with an annotated opcode byte rather than hiding a code span.
- Corrected the earlier interpretation of $BA69/$BA6D/$BA72: native side-A
  entries return register constants and perform no workspace writes. The old
  DOS initializer fragment is bypassed. Side B's corresponding 43 residual
  bytes are retained as data; normal swaps continue using side-A resident RWTS.
- Added source size/entry assertions and expanded the early build to eight
  modules. Both high-memory copies are now assembled without raw CODE includes.
  `docs/rwts.md` records data boundaries, caller contracts and validation limits.

Validation: new assembled disks pass seven boot checks and agreement of all
224 observed entry/request signatures, thirteen opening checks and eighteen
save/restore checks. Save-footprint verification confirms exactly the same 144
written sectors and untouched surrounding sectors. Repeated builds agree;
current native encoding agreement is diagnostic. Supplied-input hashes remain
unchanged. The first side-B investigation incorrectly attributed its difference
bytes to nibble scratch; direct comparison located them at $BA69–$BA93 and the
source was corrected before acceptance.

Limits: remaining $9B00–$B5FF DOS, INTRIN, mixed CHAR GEN code, graphics asset
edit authority and world analysis are unfinished. Formatting, optional language
card and all disk-error paths are not exercised. Next: reconstruct startup and
DOS file manager, then the intrinsic/vector engine.

## Steps 3d/5b — Source for all loaded startup DOS pages

Completed substep on 2026-10-13; intrinsic/graphics and later plan work remain open.

- Reconstructed the 27-page $9B00–$B5FF DOS command processor/file manager in
  `src/dos-low.s`. All 37 pages loaded by side A now have assembly authority.
  Cleared relocation sectors, vectors, command/option/error tables, buffers and
  captured state are explicit data; command/function dispatch vectors use symbols.
- Confirmed native boot uses EXEC START, with pending command index $14. START
  is high-bit text feeding Applesoft/DOS commands, not a tokenized BASIC program.
  Identified $9EBD as the output intercept and $A000 as its control-character
  processing path. Native boot-sector helpers serve file-manager recovery/append.
- Documented public DOS hooks, BLOAD, file-manager parameters, track/sector-list
  traversal, workspace lifetime and native differences in `docs/dos.md`.
  A standard transcription was consulted for identities/boundaries, not imported
  as the native implementation; incorrect standard-address assumptions were
  removed during analysis before final assembly.
- Extended build mappings to split one source module across three tracked disk
  regions. Source/asset bounds, source coverage and overlaps are checked. Debug
  symbols are emitted; unfinished dependencies now list precise unassembled spans
  instead of continuing to list fully reconstructed regions as raw code.

Validation: nine modules assemble; new boot replay passes all seven checks and
224 entry/request signatures agree with the original. New opening replay passes
thirteen checks. Two independent output directories have matching source manifests
and disk hashes. Current byte agreement remains diagnostic. Source assertions,
Python compilation, unchanged supplied-input hashes and whitespace checks pass.

Limits: unbooted side-B DOS remnants and unloaded reserved-sector residue still
need final classification; no claim is made that those copies are executed during
normal swaps. DOS formatting, every command/error path and alternate BASIC paths
are untested. INTRIN and mixed CHAR GEN remain temporary game-code dependencies.
Next: reconstruct intrinsic command dispatch, variable/expression evaluation,
vector graphics and sound, then make decoded graphics editable build inputs.

## Steps 5c/7a — Complete intrinsic payload source and ending replay

Completed substep on 2026-10-13; mixed CHAR GEN, assets, world and final audit
remain unfinished.

- Reconstructed every INTRIN.OBJ instruction: script directive dispatch,
  eight-bit expressions/variables, relative line jumps, prompt/answer handling,
  text/decimal output, script macros, room and picture loading, save/restore,
  tone/noise synthesis and vector/scan-fill drawing. Header and allocation tail
  are explicit source data, so this file is no longer a raw-code dependency.
- Named scratch/table/string/pattern boundaries and made the 37 variable entries
  symbolic. Instructions with mutable operands remain assembled instructions;
  drawing patches JSR operands, branches, row-table operands and plot operators,
  temporarily replacing an LDA with a fill callback JMP and restoring it later.
- Documented contracts and native edge behavior in `docs/intrinsics.md`: byte
  arithmetic, hardware-variable read effects, response-prefix comparison,
  relative jump limits, source-script macro mutation and speaker counter timing.
  Macro pairs are general action/direction text, not universally room digits.
- The build now assembles ten modules, including the full twenty-sector intrinsic
  file. Entry/table/size assertions pass. Graphics format structure is mapped,
  but decoded images have not yet become build-authoritative editable assets.

Validation: fresh sound-enabled rebuilt full route passes seventeen gates,
visits both sides and reaches the same ending. Full recording agrees with the
original nonzero PCM. Controls pass twelve gates plus silent/audible toggle
windows; save/restore passes eighteen gates and the 144-sector footprint check.
Owned sessions exit normally. Two output builds agree, input hashes are unchanged,
Python compilation and diff checks pass. During encoding review, two numeric
page tests were accidentally treated as high-bit characters; direct comparison
identified and corrected them before accepted replays.

Limits: no all-manual full-route recording is claimed. Malformed expressions,
every I/O error, optional quit and all response variants remain untested. Some
CHAR GEN bytes are legacy code and still need readable source; graphics need
codec/edit/render verification and remaining disk residue needs classification.
Next: finish CHAR GEN lookup/font and retained legacy content, then implement
editable vector assets and complete world/puzzle mapping.

## Steps 5d/6a — Complete CHAR GEN and editable glyph authority

Completed substep on 2026-10-13; vector assets and full plan remain open.

- Constructed all nine CHAR GEN sectors from source: nominal header, uncalled
  old editor instructions/key-address tables/mask residue, formula-generated
  horizontal/HGR scanline lookups, existing character renderer and encoded font.
  The old fragment is not a callable complete editor or live gameplay subsystem.
- Extracted 96 separately editable glyph PNGs, with exact 8x8 format. Seven
  columns contain glyph pixels and the eighth explicitly preserves the Apple II
  phase bit. Four absent final-glyph rows remain transparent rather than adding
  bytes outside the allocated file. Glyph PNGs are now authoritative build inputs.
- Added constrained font encoding, actionable errors for size/colors/phase/absent
  rows, input PNG hashes in the build manifest, and documentation/provenance.
  Identified graphics' 140 logical horizontal units across 280 physical pixels.
- Built a temporary Y glyph with one extra pixel, replayed the opening and
  verified the loaded font and displayed HGR byte both change by the expected
  bit. Exactly one HGR byte changes at the intro checkpoint. Restored the PNG
  immediately after producing the isolated edited disk; archived both screenshots.

Validation: baseline and edited builds pass thirteen opening checks each. All
764 unmodified font bytes round-trip, including the cursor phase bits. Six font
edit checks pass; unsupported dimensions, pixel colors, phase colors and absent
rows are rejected in isolated fixtures. Two baseline output manifests agree;
source/size assertions, Python compilation, input hashes and whitespace checks pass.
No raw file remains a live game-code dependency; three unused system-region
spans remain conservatively listed until their final provenance classification.

Limits: editable glyphs do not close vector-image extraction/conversion. Native
legacy editor command meanings are not all known, but their data/code boundaries
and absence from live game calls are recorded. World/puzzle analysis, remaining
baseline paths, separate manual route and final audit remain open. Next: decode
individual picture records and establish editable vector-image build inputs.

## Step 6b — Editable vector pictures and native rendering evidence

Completed substep on 2026-10-13; text/world documentation and full plan remain open.

- Decoded 257 records across 48 picture files into separately editable SVGs.
  Every directional step, native parameter, layer color and fill seed is exposed.
  Added 257 companion PNGs generated by the native renderer. Duplicate pictures
  on different sides retain separate mappings and provenance.
- Made SVGs authoritative build inputs, with hashes and generated collection
  sizes/hashes in the build manifest. No native packed vector body is embedded
  in metadata. Unused padding and reference offsets/hashes are explicitly marked.
  Compatible two/three-step grouping is retained to preserve unchanged draw timing.
- Added strict conversion constraints, manifest completeness/allocation checks,
  capacity errors, native rendering fixtures, comparison/publishing and edit
  verification. Documented SVG appearance limits, native artifact colors,
  seed coordinate units, drawing order and supported editing in docs/pictures.md.
- Injected standalone records into isolated native-render fixtures on original
  and rebuilt disks. All 257 records produce matching HGR pages. These fixtures
  are explicitly separate from normal keyboard/disk gameplay replay validation.
- Added a temporary color127 rectangle layer to PIC1, built an isolated edited
  disk, then restored the baseline SVG immediately. The normal loader reads the
  edited collection; the opening scene shows the rectangle. Its 52 changed HGR
  bytes exactly match the native fixture edit, confined to the intended area.

Validation: 257 two-page comparisons pass; seven geometry edit checks and
thirteen edited opening checks pass. Seven unsupported-format/capacity fixtures
fail with clear errors as intended. The baseline build completes all seventeen
full-route gates on both disks and retains matching nonzero recorded PCM through
the ending. Two baseline builds agree. Supplied inputs remain unchanged.

During fixture development, changing PC at successive MAME frame boundaries
retained in-flight 6502 work and corrupted the test harness control flow. Replaced
that mechanism with a stable mailbox loop; all accepted fixtures use it. Failed
fixture runs are not acceptance evidence. Preview comparison checks native HGR
buffers; no claim is made that ordinary SVG fill reproduces native scan-fill.

Limits: every arbitrary editing combination is not tested; compositions outside
the gameplay route, unusual scaled geometry and malformed native streams remain
outside accepted coverage. Text/vocabulary/world views, unused system residue,
remaining behavior branches, separate manual baseline and final audit remain open.
Next: map decoded scripts, text and vocabulary to world/puzzle state, then close
disk/memory classifications and final standalone build dependencies.

## Steps 5e/6c/7b — Script, vocabulary, world and memory indexes

Completed substep on 2026-10-13; disk-source closure and final audit continue.

- Generated readable high-bit ASCII views for all87 catalog text files with
  stable side/filename/line IDs and native offsets/lengths. Native scripts remain
  build authorities; views preserve controls and trailing-semicolon conventions.
- Indexed1352 text literals,94 vocabulary groups,23 object names/initial states,
  parameter pointers/errors/AND-THEN table and every script's literal room states,
  file/picture references, conditions, assignments and array uses. The world index
  explicitly distinguishes static references from proven reachable transitions.
- Documented multi-section library scanning, five-character pattern matching,
  macro substitutions, object containment/availability, puzzle flags, timers,
  major failure/ending logic and optional branches. Linked original/native script
  evidence rather than treating walkthrough prose as proof of engine behavior.
- Added startup/gameplay memory ownership, complete world array spans, shared
  zero-page roles, stack conventions, firmware/soft-switch interfaces, mutable
  instructions and a focused boot-to-engine call graph.
- Added a fresh parser/carrying route: corrected LOOX with backspace, tested
  backspace at the prompt boundary, AND/THEN chaining, slash, head load restriction
  and pickup restriction while holding the head. Both original/rebuilt versions
  pass eleven checks. Slash is actually rejected in this supplied configuration;
  the apparent repeat branch requires a different low buffer pointer and is not
  claimed as a working feature or changed in the rebuild.

Validation: all87 views' line bytes match native offsets; regenerating decoded
script/world views gives identical hashes. Python compilation, unchanged supplied
inputs and whitespace checks pass. An initial vocabulary index cleared pending
patterns at `.S L=...`, omitting numbered object synonyms; retaining the pattern
group through assignment fixes the index before acceptance.

Limits: world conditions are mapped but not every branch is executed. Arbitrary
script editing/encoding is not promised; retained native text is permitted by
the plan. Side-B saves, inactive DOS fragments/free-sector residue, standalone
read dependencies, separate manual baseline and final validation remain open.
Next: assemble the retained side-B DOS copies, generate unused reserved zeros,
finish per-region classification and audit source-only build reads.

## Steps 3c/7c/8 — Complete disk authority and standalone source build

Completed substep on2026-10-13; manual baseline and clean-checkout final audit remain.

- Assembled retained side-B lower/last DOS fragments with their native RUN
  startup selector. Side B's bootstrap still halts before them; normal swaps
  preserve side-A resident RWTS. Unplaced variant output never overwrites B files.
- Added source header/allocation tail for the complete interpreter file. Generated
 2816 unused reserved zero bytes on each side. All constructed code-region bytes
  now have explicit source/data/zero authority and overlap/coverage checks.
- Removed reads of native code/picture/TS-list exports from normal builds. The
  repacker directly consumes constructed replacements, retaining provenance hash
  checks only for authoritative native data. Every picture still comes from SVGs
  and glyphs from PNGs; no executable binary include is introduced.
- Generated139 TS-list streams, catalog live entries/links and the VTOC bitmap
  from manifest references. Four catalog/VTOC seeds retain inactive structured
  fields and native count anomalies. All289 regions are classified with sources,
  disk slices and retention reasons. Only three free sectors contain inactive
  historical DEATH/TS/BASIC data, outside current boot/files/save ranges.
- Added source/data/output hashes, generated/retained authority and metadata seeds
  to build.json; default output is now build/disks. Documented prerequisites,
  clean generated-output behavior, build command, editing and original I/O.

Validation: two fresh builds agree; strace finds no successful reads of the two
original disks or195 native code/image/TS reference exports. No raw-code dependency
or unknown region remains. Fresh standalone boot passes seven placement/loading
gates and224 entry/request agreement. Sixteen full-route checkpoints match emitted
text, displayed HGR pages and scalar/object/room state; full PCM had already passed.
Native encoding/hash agreement remains diagnostic, not a source/disk acceptance gate.

Added side-B save/restore coverage after both-disk travel: both versions pass
nineteen checks, restore room34/jeep/side and five full object arrays, and change
exactly144 expected save sectors. Parser/carrying, death/restart, sound and original
full-ending evidence remain accepted. Python compilation, unchanged input hashes
and whitespace checks pass. No significant unexplained timing discrepancy requires
a second emulator; unformatted media errors and exhaustive branches remain untested.

Next: complete the separate operator-stepped original playthrough, build/boot from
a clean tracked-file checkout without supplied/reference inputs, finish README/
validation navigation and perform the final PRD/plan audit before declaring complete.

## Step 2 completion — Operator-stepped original ending

Completed on 2026-10-13. Individually supplied and inspected all122 route
commands,102 page advances and side-B mount; the original reached victory and
the final sequel message with83 pills. Native snake/skeleton/gas/Roboff/jaguar
responses and an explicit ghost wait/jump-phase observation are recorded.

The session reset interrupted an earlier partial run. The accepted restart
records commands1–32 from reset, then a complete MAME checkpoint recovery before
the snake. A strict reader predicate had missed that timed prompt and caused
death; the failed attempt remains in raw logs/report. The successful continuation
records commands33–122 and two final timed-reader parser retries. No game RAM or
registers were patched. World bytes and both HGR pages agree across recovery.
This is an agent-operated manual checkpoint retry, not a claimed human or
uninterrupted single-life run. Fresh-boot automated equivalence remains separate.

Validation: tools/verify_manual.py passes26 checks, original media hashes match,
all122 commands/captures are present, and victory/final-message PNGs were visually
inspected. Logs/transcript/screenshots and recovery provenance are committed under
docs/evidence/manual-original; docs/manual-playthrough.md explains methods/limits.
The helper now saves whole native emulator state before pausing each capture.

Next: archive the clean reference-free checkout build/boot audit, finish README
and final navigation, audit every PRD/plan deliverable, and commit completion.

## Step 10 preparation — Contributor navigation and repeatable checkout audit

Published build/play instructions and a source/asset navigation table in README,
plus docs/validation.md with full-route, scene, sound, save and boot commands.
Added tools/verify_checkout.py to archive a committed tree, omit all11 supplied
inputs and195 reference regions, and execute documented builds plus strace audit.
Removed the stale pending-gameplay wording from the build manifest. No native
code, data, disk layout or gameplay behavior changed.

The earlier clean-checkout boot report survives, but its /tmp build directory
disappeared during the session reset. Rerun against this committed preparation
revision, archive the full report, and complete requirement-by-requirement
review before closing Step10. Python compilation and whitespace checks pass.

## Step 10 completion — Final PRD/PLAN audit

Completed on 2026-10-13. Every plan checklist and PRD output is fulfilled.

- Human-readable source: eleven fixed-address compiled modules cover bootstrap,
  both retained DOS/RWTS copies, resident interpreter/intrinsics and complete
  character generator. Code/data/zero authorities account for all289 disk regions;
  no unknown region, opaque executable include or temporary raw-code dependency
  remains. Interfaces, phase ownership, parser/world/timer/sound logic and
  self-modification have source cross-references.
- Extracted assets:87 native scripts with stable readable views; world/object/
  vocabulary/text/parameter indexes;257 separately editable SVGs and native
  PNG previews;96 editable font PNGs. Project codecs build images and enforce
  supported constraints. In-game vector/font edits and all257 native render
  comparisons pass. Speaker synthesis is source rather than an opaque asset.
- Standalone build: source/data plus generated metadata assemble both143360-byte
  disks. The final committed source/tool revision b557cd48979d4956d62f1c55d309ee5dc44335ca
  builds in an archived clean tree with11 supplied inputs and195 reference-only
  regions absent. Default build and two fresh audit builds agree;197 forbidden
  original/reference paths have zero successful reads. The reporting lookup
  initially used a nonexistent side field; corrected by emitted filename before
  the accepted rerun. No game/source content changed.
- Behavior: clean checkout disks boot through seven native placement/loading
  gates and224 matching entry/read observations. Emitted content is the pair
  already validated by the full122-command ending, both disks/timed sequences,
  sixteen scene/state comparisons and nonzero full PCM. Controls, input/carrying,
  deaths/restart, A/B saves and fresh restore reports pass. Separate manual
  ending evidence includes its native checkpoint recovery and failed attempts.
- Contributor documentation: README build/play/navigation, setup/tool versions,
  build authority, validation commands, disk/memory/engine/asset/world guides and
  final requirement review are complete. Current source/asset hashes, evidence
  checks, counts and output association are in docs/evidence/final-audit.json.

Final checks: all11 supplied input hashes unchanged; build-source/editable-asset
  hashes agree with the manifest and are tracked; Python compilation and
  whitespace checks pass; all local documentation links resolve. Fresh main-tree
  output is build/disks/mask-of-sun-{a,b}.dsk. Clean tree build/boot and final
  audit reports are committed under docs/evidence. The final commit changes
  documentation/evidence only after the tested source/tool revision.

Remaining limits: missing/unformatted media errors, all DOS/optional machine
paths, every invalid action/room branch/alternate solution and arbitrary image
editing combinations are not exhaustively tested. Historical catalog anomalies
and legacy editor semantics remain unconfirmed. These are explicit testing/
historical interpretation limits, not incomplete game-code reconstruction.
Original layout/I/O is retained and no significant unexplained behavior/timing
discrepancy requires a second emulator. No required implementation work remains.
