# ProDOS port handoff

Prepared on 2026-10-13 for the next contributor to the Mask of the Sun disassembly.

The game uses direct DOS 3.3 track/sector I/O, but ordinary resource loading is
centralized behind a named-file interface. A ProDOS file-based port appears to
be a moderate implementation task that can preserve most gameplay, scripts,
graphics and sound. This is a feasibility assessment, not a tested port.

The user requested advice and this separate handoff file. Implementation of a
ProDOS port has not been requested or started. The completed native rebuild
still preserves the original disk layout and I/O. See [PLAN.md](../PLAN.md) for
the existing policy allowing an optional filesystem replacement while retaining
readable original I/O source and validating gameplay.

## Verified disk interfaces

| Path | Entry and source | Current behavior |
| --- | --- | --- |
| Startup | [boot-loading.md](boot-loading.md), [dos.md](dos.md) | Custom boot loads DOS; `START` initializes HGR pages, BLOADs interpreter at `$0800` and parameters at `$0300`, then enters `$0800`. |
| Resource loading | `load_named_file` at `$0B20`, [interpreter.s](../src/interpreter.s) | Reads DOS VTOC/catalog and a file's first track/sector list into `$B700`; transfers allocated sectors through RWTS. |
| Sector reading | `read_sector` at `$0BBC`, [interpreter.s](../src/interpreter.s) | Calls `$BD00` with IOB `$0BAB`, read command 1, slot 6, drive 1. |
| Save and restore | `save_game` at `$122C`, `restore_game` at `$129D`, [intrinsics.s](../src/intrinsics.s) | Writes/reads 144 RAM pages through RWTS commands 2/1, directly to fixed sectors. |
| Physical disk access | `rwts_entry` at `$BD00`, [rwts.inc](../src/rwts.inc) | Disk II phase, motor, drive and latch access; address/data decoding and sector writing. |

The original target is a 48K Apple II+ with no language card. Startup DOS is
mostly overwritten during gameplay: pictures start at `$9C00`, and `CHAR GEN`
occupies `$ADFC–$B6FB`. The game then uses its own loader and retained RWTS at
`$B800–$BFFF`, rather than the high-level DOS file manager. Read
[memory.md](memory.md), [engine.md](engine.md) and [rwts.md](rwts.md) before
changing these boundaries.

## Loader behavior to preserve

`load_named_file` receives A/X as the low/high pointer to ten high-bit filename
characters and `$EC/$ED` as the destination. It updates `$ED` to the next
destination page after loading. The loader copies whole allocated 256-byte
sectors, including any DOS binary header and allocation padding; it ignores
nominal binary header addresses and lengths.

This distinction matters for `INTRIN.OBJ` loaded at `$0CFC` and `CHAR GEN` loaded
at `$ADFC`: their four-byte headers position payloads at `$0D00` and `$AE00`.
The interpreter itself is initially loaded through DOS BLOAD, which strips the
header. Do not uniformly strip headers or trim every asset to nominal length.
Preserve allocated resource streams and returned destination-page behavior in
the first port, then simplify deliberately if desired. Binary file type does
not prove that a graphics resource has a meaningful DOS binary header.

The loader vector is `$034C/$034D`, but interpreter initialization explicitly
sets it to `$0B20` and initial loads call `load_named_file` directly. Replacing
only the vector would miss startup loads. A trampoline at the original entry
is one possible way to cover both routes.

Picture loading copies an executable error-handler template to `$0BD1`.
`picture_load_error_patch`, `install_picture_error_patch` and
`prompt_for_game_disk` in `intrinsics.s` depend on the original loader layout
and stack unwinding. Remove or redesign that mechanism alongside the loader;
do not let it overwrite the replacement code. Preserve legitimate missing-file
and I/O error behavior while replacing insertion prompts with resource lookup.

## Proposed implementation

1. Add a native `.SYSTEM` launcher that initializes the machine, loads the
   interpreter and parameters at their existing addresses, and enters `$0800`.
   Avoid keeping `BASIC.SYSTEM` resident: its high-memory allocation conflicts
   with the game. ProDOS loads system programs at `$2000`, so move any launcher
   code that must survive HGR initialization or later resource loads.
2. Replace resource loading with ProDOS MLI file access. Preserve the existing
   caller interface and error handling. Either map legacy names to valid ProDOS
   paths or pack resources into indexed archive files and use
   `OPEN`, `SET_MARK`, `READ`, `CLOSE`. Retain side identity when resolving names;
   audit duplicates before merging both catalogs. Do not assume all names are
   globally unique or require identical data across sides.
3. Replace raw snapshot transfers with a save file containing the existing
   `$2000–$AFFF` RAM image, length `$9000` bytes (36,864 bytes). Keep I/O code,
   parameters and the open-file buffer outside that range so restore cannot
   overwrite them. The original transfer runs downward in memory; define the
   new file byte order explicitly. Importing old scratch-disk saves would need
   a separate conversion, not ordinary file reading.
4. Update packaging, target-machine settings, error paths and validation tools.
   Keep the original source/build available as the behavioral baseline.

`$BA69` and `$BA72`, called around native saves, are register-return stubs in
the supplied cracked version. They do not preserve memory or initialize
workspace; see [rwts.md](rwts.md). Do not reproduce an invented preservation
contract in the replacement.

## Proposed memory arrangement

ProDOS requires at least 64K, reserves `$BF00–$BFFF`, and requires a 1K buffer
for each open file. Replacing RWTS and catalog scanning makes this candidate
layout plausible:

| Span | Proposed use |
| --- | --- |
| `$B700–$B7FF` | Adapter parameters, filename/index scratch; former catalog scratch. |
| `$B800–$BBFF` | One page-aligned 1K ProDOS open-file buffer. |
| `$BC00–$BEFF` | Resident adapter code. |
| `$BF00–$BFFF` | ProDOS global page and MLI entry. |

This layout has not been assembled or tested. Verify code size, memory bitmap
ownership, zero-page clobbers, stack use and all resource load bounds before
accepting it. Sequentially opening one resource or save file at a time avoids
needing multiple 1K buffers.

An Apple II+ target needs a 16K language card and a ProDOS version compatible
with its 6502. The separate [PRD-korean.md](../PRD-korean.md) proposes using that
language card for Korean support. If these projects are combined, design their
bank ownership together: ProDOS occupies language-card RAM, so the full 16K
cannot also be assumed available for Korean code/data.

The ProDOS requirements above are documented in the
[Memory Use reference](https://prodos8.com/docs/techref/memory-use/),
[MLI reference](https://prodos8.com/docs/techref/calls-to-the-mli/) and
[System Program reference](https://prodos8.com/docs/techref/writing-a-prodos-system-program/).

## First implementation and acceptance checks

Start by auditing the resource manifest in [assets/raw/manifest.json](../assets/raw/manifest.json)
and current build authority in [build.md](build.md). Establish a 64K emulator
profile, boot a minimal launcher, and verify all initial payload placements
before attempting the full game. The current [setup.md](setup.md) and
`tools/mame_session.py` use the original 48K profile and need adjustment for a port.

Use [validation.md](validation.md) and [behavior-matrix.md](behavior-matrix.md)
as the baseline. Acceptance should cover startup, room and picture loading from
both sides, the full ending route, timed scenes, commands, restart, sound,
same-session save/restore and fresh-boot restore. Add filesystem-specific checks
for missing/truncated resources, read/write errors, and a save destination with
insufficient space.

Native boot/RWTS trace identity and fixed save-sector footprint checks are
specific to the original implementation. Adapt those assertions to ProDOS
payload placement and save-file content; preserve gameplay/state comparisons.
Keep generated disks and emulator sessions under ignored `build/` directories,
and preserve original inputs. A passing native audit does not establish that
the proposed port works.
