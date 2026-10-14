# EXTRA+SAVE — three-disk Korean playtest build

The user requested EXTRA+SAVE, A and B. `r01-extra-save` implements that layout
with the existing 140K DOS images and save format. No ProDOS conversion.

## Disk layout

EXTRA remains the boot disk. The disk builder now reserves the native 144-sector
snapshot area (tracks 23–31) and the Korean commit/identity sector (track 22,
sector 15). These 145 sectors are excluded before allocating files and marked
unavailable in the DOS VTOC. They start at zero; the first successful save commits
the build identity. No DOS save file or additional disk is needed.

All three approved save/restore/retry instructions now say:

> EXTRA 디스크를 1번 드라이브에 넣고
> RETURN을 누르세요.

The obsolete instruction to insert an initialized blank disk is removed from the
Korean UI. Original English script sources and snapshot-transfer logic are
preserved. [The authorization ledger](approval-r01-extra-save.json) records these
three requested adaptations; the other 1,325 approved entries are unchanged.

There is one save slot per working EXTRA image. Saving again overwrites that
slot. EXTRA must be writable and must not be formatted. Keep the distribution ZIP
and make a working copy. Use matching EXTRA/A/B images; earlier build saves have
a different identity and are not supported.

## Verification

- MAME 0.285 Apple II+ with Language Card, natural keyboard and actual one-drive
  media swaps, no injected game state: 66-command A→B route, save to the same EXTRA
  image used to boot, change world state, restore B room 34.
- A separate emulator process cold-boots from that saved EXTRA, enters via A,
  restores the B-side world and mutated script, then accepts LOOK/INVENTORY.
- All 145 raw save sectors changed after saving. Every other sector, including
  boot tracks, catalog, VTOC, TS lists and startup files, remains byte-identical.
  The fresh-boot restore leaves the saved EXTRA unchanged.
- A/B request pixels match the expected glyphs. Captured save/restore screens
  explicitly request EXTRA.
- 45 host tests pass, including allocation across the reserved region, VTOC
  reservation, raw-save writes preserving files, and capacity overflow rejection.
- All 1,328 message bodies and disk files verified; ten repeat-build assets are
  byte-identical. The release EXTRA's reserved area is empty and unallocated to files.

Evidence: `docs/evidence/korean/approved-r01-extra-save-{build,game,output-audit}.json`.
The source-output inventory is complete; that audit does not claim every error
path was executed. AppleWin/GSSquared, error injection, the full ending route and
physical hardware were not rerun for this change. Human contextual playtesting
and timing-window comparison remain open.

## Capacity and delivery

EXTRA has 199 free sectors after reserving the save area; A has 3 and B has 8.
Runtime: 1,892/2,048 bytes; resident pool: 4,096/4,096; largest room pool:
1,013/1,024; font: 650 glyphs/5,200 bytes. Future changes must recheck both memory
and disk budgets; do not infer room from EXTRA's free sectors for resident RAM.

`output/korean-playtest-r01-extra-save.zip` contains exactly three `.dsk` files:
`mask-of-sun-ko-extra.dsk`, `mask-of-sun-ko-a.dsk`, `mask-of-sun-ko-b.dsk`.
See the [playtest guide](playtest-r01.md) for boot/save/restore steps.
