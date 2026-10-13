# Original opening baseline

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

This is **not the complete original-game baseline**. Side B, the jaguar/chasm
timers, the ghost, the ending, sound, inventory limits, save/restore and restart
remain to be exercised. Step 2 remains open. Step 3's raw sector mapping was
performed early to support loader and graphics-text investigation; boot-to-game
loading and memory ownership still need full explanation before that step closes.
