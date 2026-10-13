# Operator-stepped original playthrough

The separate manual baseline reached the ending with 83 pills remaining on
2026-10-13. Codex supplied each command, page advance, physical key and disk
mount individually and inspected the returned native screen before proceeding.
This is an agent-operated manual run, not a claim that a human user played it.
The helper contains no route list, next-command choice, automatic pagination or
automatic disk swap. The supplied walkthrough guided the commands; native
responses established progress.

[manual-original.json](evidence/manual-original.json) passes 26 checks and archives
the 122 ordered route commands, two parser-error retries, 102 page advances,
conditions, timestamps, CPU observations, media hashes and complete emitted text.
[Raw segment logs and screenshots](evidence/manual-original/) retain the
underlying records. The [victory](evidence/manual-original/page101.png) and
[final message](evidence/manual-original/ending.png) were visually inspected.
The automatic [full route](full-route.json) remains a separate fresh-boot baseline.

## Recovery and failed attempts

The first operator session (`build/manual-original-02`) disappeared during a
session reset after command83; its partial captures are not a completed-run gate.
A checkpoint-helper probe (`manual-original-03`) resumed when scheduling a save;
it was stopped at startup. The fixed helper schedules the save before capturing
and pausing, preserving the paused state between actions.

The accepted recording starts at reset in `manual-original-04`. Commands1–32
reach the first pyramid entrance with the lantern lit. An overly strict
normal-reader predicate then missed the snake's timed prompt and captured death.
That failed command33 is retained in the first segment's complete raw logs and
the report's `excluded_attempt`, rather than being counted as a successful route.

`manual-original-05` loads MAME's complete native `command032.sta` checkpoint
from the first segment and continues with commands33–122. Recovery uses the
emulator's device/CPU save-state facility, without editing game RAM or registers.
The report records the checkpoint hash and verifies all world bytes
$6000–$67FD and both HGR pages against the pre-encounter capture. It is a
documented checkpoint retry, not an uninterrupted single-life run. Original
disk-copy hashes match the preserved inputs in both segments.

Timed readers consume the first natural-key character to leave their wait loop.
The final GIVE MASK and PLAY FLUTE therefore first produced `IVE MASK` and
`LAY FLUTE` parser errors; individually recorded retries succeeded. The native
snake command uses SHOOT without Return. Ghost progression waits explicitly for
`The apparition fades`, then its completed description. The stepping-stone
capture requires room39, D=1 and script PC $6C8C–$6D26 before a bounded physical
Return. The final screen has no input prompt: a bounded ready observation timed
out after the ending, followed by an explicit final-message observation.

## Record another manual run

Use a fresh output directory and the documented original Apple II+ profile:

```sh
python3 tools/mame_session.py --rompath /path/to/roms \
  --output build/manual-original --headless --fast --script tools/manual_mailbox.lua
```

From another terminal, supply one action at a time and read its result:

```sh
python3 tools/manual_control.py build/manual-original --keys ' ' --label page001
python3 tools/manual_control.py build/manual-original --command LOOK --label command001
python3 tools/manual_control.py build/manual-original --mount b
python3 tools/manual_control.py build/manual-original --observe \
  --condition 'The apparition fades' --maximum 90 --label ghost-fade
python3 tools/manual_control.py build/manual-original --observe \
  --condition safe-jump --minimum 0 --label jump-ready
python3 tools/manual_control.py build/manual-original --press Return --label command065
python3 tools/manual_control.py build/manual-original --finish
```

These examples illustrate independent operations, not a runnable startup route.
The process pauses after each capture. Checkpoints are saved under the session's
`state_directory/apple2p/`. `MASK_MANUAL_STATE=/absolute/path/checkpoint.sta`
selects explicit native checkpoint recovery on a new manual launch with the same
MAME version and machine profile. Save states are separate from the game's SAVE
GAME snapshots and are not portable across versions. See MAME's
[machine save/load API](https://docs.mamedev.org/luascript/ref-core.html).

Recheck the retained recording with:

```sh
python3 tools/verify_manual.py build/manual-original-04 build/manual-original-05 \
  --output build/manual-verification.json
```

Raw RAM/state files remain ignored runtime artifacts; the committed report,
transcript, logs and representative pictures provide reviewable evidence.
