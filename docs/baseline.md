# Original gameplay baseline

The original supplied side A boots on the documented 48K Apple II+ profile.
The opening renders a plane interior with three pages of introductory text.
Space advances `[ waiting ]`; the live prompt is `OK>^` (the caret-like glyph
is part of the input cursor). The game uses full-screen high-resolution graphics,
including its text. Ordinary text page $0400 holds stale DOS/Applesoft prompts
and is not the game dialogue.

The character output vector at $0036/$0037 points to $B317. Static renderer
inspection and a CPU-visible RAM capture establish an 8-byte-per-character font
at `$B300 + 8*(ASCII & $7F)`, printable glyphs beginning at $B400. Characters
occupy one 7-bit HGR byte across eight scanlines, with a 12-scanline row pitch.
The grid is 40 columns by 16 rows. `$0346` selects the drawing page. The decoder
matches low-seven-bit glyph shapes; drawing regions become `?`, and cursor or
other unsupported glyphs are left explicit. PNG captures remain the visual
evidence; absence of a decoded word is not proof that it was absent on screen.

## Verified opening checks

[opening-original.json](evidence/opening-original.json) records the machine
command/media hashes, timed input log, CPU checkpoints, decoded dialogue and
pass/fail checks. It covers startup, `LOOK`, initial inventory (matches, knife,
pills, amulet, revolver), unknown word, missing object, absent object, missing
verb, leaving the plane, getting the map, jeep travel, food-for-flute exchange,
the statue inscription `XOTZIL`, picking up/replacing the head, and arrival in
the clearing. The last prompt is back in the jeep. The food exchange succeeds;
`TAKE ALL` logs only its last pickup line, so that line alone does not prove the
full acquired inventory.

Representative screenshots are in [evidence/opening](evidence/opening).
Replay captures every pagination page before advancing it and every command
prompt before submitting the next command. It waits at least three emulated
seconds after an action and half a second of stable decoded screen, with a
600-emulated-second deadline. It writes timestamps, so animation and disk loads
are distinguishable from tool latency. Natural keyboard is used; game RAM is
never patched. Unthrottled execution changes host speed, not emulated timers.

```sh
python3 tools/mame_session.py --rompath /path/to/roms --output build/opening-01 \
  --headless --fast --script tools/opening_replay.lua > build/opening-01.log 2>&1
python3 tools/verify_opening.py build/opening-01 --output build/opening-report.json
```

## First pyramid

[first-pyramid-original.json](evidence/first-pyramid-original.json) extends the
original route through the first pyramid and back to the jeep, passing ordered
input, no-death and seven puzzle checks at 626.6 emulated seconds. The supplied
short walkthrough's first quick `SHOOT` is a **snake** encounter, not a jaguar.
The later jaguar sequence is on side B. Static room scripts corroborate the
observed events but do not replace the runtime evidence.

The snake reacts to five successive keys `S H O O T`, without Return, while
cycling animation frames. `SHOOT` is queued immediately upon a ready prompt,
with the prior natural-keyboard queue empty. The skeleton encounter also needs
an immediate first-key response after pagination, followed by the full
`HIT SKELETON WITH AMULET` command. A three-second delay at that prompt failed
and led to the restart screen. The successful route keeps ordinary pagination
at three-second spacing; it never applies urgent command timing to Space.
The crypt waits for the observed apparition-fades message before taking the
gold bowl (about 41 emulated seconds after moving the stone). The condition is
latched across pagination so the next page cannot discard it.

```sh
python3 tools/mame_session.py --rompath /path/to/roms --output build/pyramid-01 \
  --headless --fast --script tools/opening_replay.lua \
  --route docs/first-pyramid-route.json > build/pyramid-01.log 2>&1
python3 tools/verify_route.py build/pyramid-01 docs/first-pyramid-route.json
python3 tools/script_views.py  # high-bit ASCII room/library views and line IDs
```

Earlier exploration caught failures in input gating and wait/pagination handling;
those runs are diagnostic, not accepted route evidence. The archived successful
run uses the corrected gates and never patches game RAM.

## Both sides and ending

[full-original.json](evidence/full-original.json) records the successful full
route, and [full-core-rebuilt.json](evidence/full-core-rebuilt.json) records its
repeat on disks built with the reconstructed interpreter and renderer. Both
pass seventeen checks and reach the ending at 1909.4 emulated seconds with
83 pills remaining. The 122 commands include the opening parser probes. The
replay captures 221 pagination/prompt checkpoints plus the final ending screen;
representative PNGs are in [full-original](evidence/full-original/).

[full-route.json](full-route.json) is the replay authority. The supplied guide
was interpreted incrementally, with targeted failed timing investigations kept
under ignored `build/`; the accepted route never patches game RAM. Blank lines
in the guide separate commands as well as commas. Earlier candidate extraction
incorrectly merged commands across paragraphs; that guide view is corrected.

The native COUT entry at $B317 is observed with a memory read tap, which logs
character A only when the CPU fetches that entry. It returns no replacement
data. This records short dialogue such as "You made it!" and Raoul's death
that transitions immediately into another room and can escape frame snapshots.
The bus observations supplement PNGs and decoded checkpoints. The decoder now
also recognizes rows drawn with inverted glyphs, used by the chasm and mask.

| Interaction | Accepted input/wait condition |
| --- | --- |
| First-pyramid snake | Urgent `SHOOT`, five keys without Return |
| Crypt ghost | Latch the observed apparition-fades message across pagination |
| Skeletons | Urgent initial key, then `HIT SKELETON WITH AMULET` |
| Gas chamber | Urgent `SW`; Raoul's death is part of this successful route |
| Chasm | Physical Return for 0.08 seconds when D=$6003 is 1 and script PC $D2/$D3 is in $6C8C–$6D26 |
| Roboff | Urgent `GIVE MASK` at the ready prompt |
| Final jaguar | Urgent `PLAY FLUTE` at the ready prompt |

The chasm clears old input with `.S R=0` before its timed loop. Posting Return
while its instructions were still printing was therefore ineffective. Natural
keyboard Return also arrived too late in an investigated run. The accepted
physical key is an enumerated Apple II keyboard field, cleared after the bounded
hold and on exit. RAM predicates read only RAM, never keyboard I/O. The original
run's optional keyboard bus tap corroborates that PLAY's initial P was polled
by the timed script, then consumed and acknowledged by the blocking input editor.
A delayed earlier attempt lost P and was rejected; it is not accepted evidence.

The replay mounts copied side B on the game's explicit disk-turn prompt, using
the same drive 1. It advances final pagination until the next-adventure text,
then exits rather than waiting for a command prompt that never appears.

```sh
python3 tools/mame_session.py --rompath /path/to/roms --output build/full-original \
  --headless --fast --script tools/opening_replay.lua --route docs/full-route.json
python3 tools/verify_route.py build/full-original docs/full-route.json
python3 tools/build.py --output build/rebuilt
python3 tools/mame_session.py --rompath /path/to/roms --output build/full-rebuilt \
  --disk-a build/rebuilt/mask-of-sun-a.dsk --disk-b build/rebuilt/mask-of-sun-b.dsk \
  --headless --fast --script tools/opening_replay.lua --route docs/full-route.json
python3 tools/verify_route.py build/full-rebuilt docs/full-route.json
```

## Sound and baseline controls

[audio-full.json](evidence/audio-full.json) compares two fresh complete route
recordings, original and rebuilt, at 22050 Hz, 16-bit PCM. Both have 42,101,830
frames; channel0 has nonzero output and the two additional recorded channels
are silent. Complete PCM hashes agree. Opening recordings also agree in
[audio-opening.json](evidence/audio-opening.json). Extracted mono examples of
the hut, statue, final flute and jaguar are under [audio](evidence/audio/).
These recordings are verification artifacts, not native game sound assets.
Exact PCM is useful evidence for this deterministic early build; future
intentional timing changes require assessing audible behavior rather than
assuming different samples mean different gameplay.

[control-route.json](control-route.json) tests sound toggles, pill effects,
command chaining, input overflow, empty GET ALL and rejected movement. Both
versions pass twelve route/state checks. [audio-controls.json](evidence/audio-controls.json)
also verifies zero mixer samples during a pill command with SOUND OFF and
nonzero output for the corresponding SOUND ON command. The input editor retains
thirty-six A characters from a forty-five-key overflow probe; the reference's
claimed thirty-seven-character window is not assumed to be the observed limit.

[save-route.json](save-route.json) saves in room3 inside the jeep, moves west
to room18, and restores room3 with all five object arrays equal to their earlier
values. Both versions pass eighteen checks. [restore-route.json](restore-route.json)
then restores that existing disk after another fresh boot, passing eight checks
for each version. Save changes exactly the 144 sectors in tracks23–31, leaving
other sectors and the catalog intact; original and rebuilt save disks agree.
The native transfer snapshots RAM $2000–$AFFF directly, despite requiring an
initialized scratch disk in the instructions. It does not create a catalog file.

```sh
a2kit mkdsk --os dos33 --type do --volume 254 --dimg build/save-blank.dsk
python3 tools/mame_session.py --rompath /path/to/roms --output build/save-test \
  --save-disk build/save-blank.dsk --headless --fast \
  --script tools/opening_replay.lua --route docs/save-route.json
python3 tools/verify_route.py build/save-test docs/save-route.json
```

The launcher copies the scratch disk; all explicit mount events follow observed
game instructions. An investigated mount-result assertion was incorrect because
MAME load returns nil on success; the fixed helper checks the mounted filename.
The failed run is excluded. [restart-route.json](restart-route.json) deliberately
kills the player with TAKE ALL PILLS, checks an invalid death-screen command,
then START. Both versions pass nine checks and return to room1 and initial
inventory. These deliberate-death tests explicitly expect death; successful
full-route checks still reject it.

[behavior-matrix.md](behavior-matrix.md) collects the accepted evidence and
remaining coverage limits. Step 2's separate all-manual full-route requirement
remains open; the accepted route was guided and automated incrementally.
Step 3's boot-to-game loading
and memory ownership still need full explanation. The current rebuilt full
route establishes only the early partial source build's behavior; it does not
make remaining opaque executable regions complete.
