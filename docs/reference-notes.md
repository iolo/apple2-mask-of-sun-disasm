# Supplied references and candidate route

The eleven supplied inputs are listed with size, SHA-256, role and provenance
limits in [inputs.json](inputs.json). The PRD calls the Korean walkthrough
`mask-of-the-sun-walkthrough-korean.pdf`; the actual supplied filename is
`mask-of-sun-walkthrough-korean.pdf`. The diskette scan is also present although
the PRD omitted its filename. None of these inputs has been renamed or edited.

## Controls described by the manuals

The manual JPEGs were visually inspected. Booklet PDF pages 5–8 were rendered
and visually inspected as well as checked against their OCR text. These are
**reference claims to verify in the cracked game**, not runtime findings:

- Boot side A in drive 1; use a 48K Apple II with DOS 3.3. Flip when prompted.
- `[waiting]` means press a key for the next three lines. The command prompt is
  `OK>`; only the first five letters of a word are significant.
- Use cardinal direction initials and `NW`, `NE`, `SW`, `SE` for diagonals.
  `FORWARD`, `BACK`, `RIGHT`/`R`, `LEFT`/`L`, `ENTER`, `EXIT`, `UP` and `DOWN`
  may be meaningful depending on the scene.
- `INVENTORY`, `SUPPLIES`, `EQUIPMENT`; `LOOK`, `EXAMINE`, `SEARCH`;
  `GET ALL`, `DROP ALL` and their `ALL BUT object` forms are documented.
  Carrying capacity has a limit, which the booklet does not quantify.
- `SOUND OFF` and `SOUND ON` control effects.
- `SAVE GAME` prompts for a separate formatted DOS 3.3 disk in drive 1, saves
  one game per disk, then asks for the indicated game side and Return.
  `RESTORE GAME` is available after a fresh side-A boot and follows similar
  prompts. Errors require checking the save disk and retrying.
- A 37-character input window supports chained commands separated by commas,
  periods, `AND`, or `THEN`. Errors or significant events terminate the chain.
- The story warns that pills must be taken regularly and excessive mask use
  has a curse. The reference does not establish timer units or deadlines.

## Route guide

[candidate-route.json](candidate-route.json) splits the supplied text walkthrough
into stable, ordered command candidates. Every entry is initially unverified.
Do not feed parenthetical instructions or wait descriptions literally to the
game. The reference's phases are plane/airstrip and map; food delivery at the
hut; statue head; lantern and jaguar; bowls, ghost and skeleton; travel to the
second pyramid; chasm timing, mask and altar; coffin maze; final mask exchange
and flute. The shorter guide may omit pills, pagination, exact disk-change
points and prerequisites; the English PDF guide is available for cross-checks.

The most explicit timing candidates are shooting promptly after entering the
first pyramid, waiting for a ghost to disappear, turning southwest quickly and
jumping at the correct chasm moment. Baseline runtime recordings must replace
these descriptions with observable conditions or emulated cycle counts.

Reference PDFs can be inspected without modifying them:

```sh
mkdir -p build/references
pdftotext -layout mask-of-sun-booklet.pdf build/references/booklet.txt
pdftotext -layout mask-of-sun-walkthrough.pdf build/references/walkthrough.txt
pdftoppm -f 5 -l 8 -scale-to 1600 -png mask-of-sun-booklet.pdf build/references/booklet
```

Consulted the local checkout corresponding to the PRD's earlier Stellar 7
project, `tools/mame_smoke.py`, for isolated media copies, ROM verification,
headless SDL setup and logging conventions. No engine or disk-layout assumption
was imported. No comprehensive survey of the earlier repositories is needed.
