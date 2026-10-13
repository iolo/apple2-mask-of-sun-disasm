# Completion audit

The PRD and PLAN deliverables are implemented and validated. The final clean
source/tool revision tested is `b557cd48979d4956d62f1c55d309ee5dc44335ca`.
Subsequent completion changes are documentation/evidence only. The audit uses
source inspection, complete disk/asset manifests and runtime evidence; it does
not treat original-byte identity as a completion criterion.

## Completion criteria

| Requirement | Authoritative implementation and evidence | Finding |
| --- | --- | --- |
| Readable buildable game, boot and overlay code | Eleven compiled modules in [source index](../src/README.md); [boot](boot-loading.md), [DOS](dos.md), [RWTS](rwts.md), [engine](engine.md), [intrinsics](intrinsics.md) and [memory](memory.md) document labels, interfaces and mutable operands. All289 disk regions are [classified](../assets/classification.json); no unknown or temporary executable dependency remains. | Complete. Apparent overlays are interpreted scripts and phase-dependent reuse of DOS RAM; no separate unidentified 6502 overlay remains. |
| Extracted and incorporated text, graphics, world and sound | 87 native text streams with stable decoded line IDs; [world/vocabulary/object/text/parameter indexes](../assets/decoded/world/). 257 authoritative SVGs across48 collections, each with a native PNG;96 editable font PNGs. Speaker synthesis/tables are readable intrinsic source. | Complete. Native scripts/parameters remain documented build data; general text editing is not required. |
| Decoded editable images and converters | [Picture codec](pictures.md) and [font codec](chargen.md) enforce geometry, color, dimensions and allocation. [All257 native records](evidence/picture-roundtrip.json), [vector edit](evidence/picture-edit.json) and [font edit](evidence/font-edit.json) pass; unsupported inputs fail explicitly. | Complete. Native PNG companions, rather than ordinary SVG fills, show exact Apple II rendering. Baseline assets restored. |
| Independent repeatable clean build | [Clean-checkout report](evidence/clean-checkout.json): all11 supplied inputs and195 reference-only regions absent before building. Documented default build plus two fresh audit builds agree;197 forbidden paths have zero successful reads. [Clean boot](evidence/clean-checkout-boot.json) passes. | Complete. No original disk template, extraction at build time, raw executable include or external reference repository is needed. |
| Preserved behavior, both disks, timing and ending | [Full source/SVG route](evidence/pictures-full.json):17 gates,122 commands, both sides,83 pills and ending. [Sixteen scene/state checkpoints](evidence/full-scene-state-comparison.json) and [nonzero full PCM](evidence/pictures-audio-full.json) pass. [Behavior matrix](behavior-matrix.md) also covers errors, input/carrying limits, sound control, deaths/restart, native saves and fresh restores. | Complete within documented path coverage. Original I/O/layout retained; no optional replacement requiring different media behavior. |
| Setup, navigation, architecture and uncertainties | [README](../README.md), [setup](setup.md), [build](build.md), [validation](validation.md), [disk layout](disk-layout.md), [memory](memory.md) and [world puzzles](world.md) link source/data and evidence. | Complete. ROMs remain documented external prerequisites. Historical residue and untested paths are distinguished from source omissions. |

## Plan steps and invariants

| Step | Evidence reviewed |
| --- | --- |
| 0: Plan and PRD inventory | PLAN/PROGRESS planning commits and preserved PRD. |
| 1: Provenance/tooling | [Eleven input hashes](inputs.json), [tool versions](toolchain.json), [reference/control notes](reference-notes.md), external ROM audit and fixed48K Apple II+ profile. `check_inputs.py` passes again at final audit. |
| 2: Original baseline | Opening/control/full reports, speaker recordings and boot observations. [Separate operator-stepped playthrough](manual-playthrough.md) passes26 checks and reaches the ending, with native checkpoint recovery and failed attempts disclosed. |
| 3: Storage/load/memory | Complete1120-sector raw manifest, [extraction integrity](evidence/extraction-check.json), boot traces, phase/ZP/stack/buffer maps. Disk order established from catalog/allocation and runtime, not filename. |
| 4: Early assembly/rebuild | Historical [early-build report](evidence/early-build-check.json), progressive module commits and opening replays; temporary raw regions subsequently replaced. |
| 5: Engine explanation | Readable interpreter/intrinsic/renderer source and documented dispatch, parsing, text, graphics, state, native timers, firmware and self-modification. Targeted execution/keyboard/boot traces resolve indirect behavior. |
| 6: Assets | Stable line/text/world indexes, per-image SVG/PNG and font PNGs; converters/native fixtures/supported edit and rejection checks. No hidden packed body substitutes for editable geometry. |
| 7: World and code closure | All87 scripts mapped;23 objects,94 vocabulary groups,1352 text literals, puzzle/failure/ending/timer references. Invalid actions, carrying, repeated/chained input, deaths, alternate transitions and saves tested; historical data retention justified. |
| 8: Standalone build | Complete source/data/zero coverage, fixed-address bounds/overlap checks, generated139 TS streams/catalog entries/VTOC bitmap, deterministic clean builds and machine-readable source/asset/output hashes. |
| 9: Equivalence | Fresh-boot automated original/rebuilt ending, representative scene/state and nonzero PCM comparisons, saves/restores on A/B, controls/parser/restart routes. No significant unexplained timing discrepancy requires a second emulator. |
| 10: Final documentation/audit | Contributor build/play/validation/navigation instructions, reference-free checkout build/boot and this requirement review. Final source/tools/assets/docs/evidence committed with PROGRESS completion record. |

Supplied inputs remain unchanged. Each raw region has location/length/encoding
provenance; assembly, SVGs, font PNGs or explicitly retained native data provide
one build authority. Generated views and previews are not conflicting build
inputs. The sole binary include is generated font data, never executable code.
Metadata seeds retain inactive fields; three free historical sectors are outside
boot/file/save reach. Their possible earlier origins remain uncertain, with
retention reasons in the disk map. CHAR GEN's legacy fragment is readable source
with unconfirmed older-editor semantics, not hidden live gameplay code.

## Clean-checkout and final-content checks

The clean audit uses `git archive` of the tested revision, excludes206 input and
reference files before extraction/build, and invokes only documented commands.
All required source/assets and codecs are tracked. The tree needs no original
disk, downloaded analysis source, local font/picture generator cache or ROM to
build. Its own copied MAME launcher/helpers then boot its disk pair with explicitly
supplied external ROMs. The boot report verifies7 placement/load gates for each
version and agreement on224 native entry/read observations.

The clean-build disk hashes also identify the same emitted content used by the
accepted SVG/source full-ending and PCM runs. That connects prior runtime evidence
to the final constructed disks; matching the original disk hashes is incidental
and is not an acceptance gate. See [final-audit.json](evidence/final-audit.json)
for counts, current source/asset hashes, report checks and this content association.

The checkout report tool initially expected a nonexistent `side` field in the
build manifest. It was corrected to match output filenames and rerun from the
committed correction. The failed report is not accepted audit evidence.

## Remaining limits

Missing/unformatted save-media errors, every DOS command, optional language-card
paths, all invalid actions, alternative solutions and every room branch have not
been executed. Arbitrary SVG edit combinations, offscreen/scaled compositions and
malformed native streams are not exhaustively tested. Unsupported converter inputs
are rejected rather than promised as supported edits. These are test/editing limits,
not unfinished disassembly. The native slash command's observed rejection is
preserved; ambiguous historical metadata/editor purposes are explicitly unconfirmed.

The manual run uses complete emulator checkpoint recovery before the snake,
and retains initial timed-reader parser errors. It is not an uninterrupted
single-life run or a claim that the human user played. Fresh-boot automated routes
provide independent full-ending/timing equivalence evidence without checkpoint
recovery or game-RAM injection. Native renderer fixtures deliberately inject
scratch test data and are kept separate from gameplay runs.
