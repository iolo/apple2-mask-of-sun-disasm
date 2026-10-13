# Setup and emulator profile

Use Python 3, cc65 (`ca65`, `ld65`, `da65`, `cl65`), a2kit, MAME with Lua
console/json plugins, and Poppler for reference inspection. Versions used in
the initial investigation are recorded in [toolchain.json](toolchain.json).
Python tools currently use only the standard library. Run:

```sh
python3 tools/check_inputs.py
python3 tools/check_tools.py --rompath /path/to/locally-supplied/roms
```

ROMs are external prerequisites and are not distributed in this repository.
[rom-requirements.txt](rom-requirements.txt) records MAME's required ROM names
and checksums. The recorded ROM audit passes. The default `apple2` character ROM
has a MAME `NEEDS REDUMP` warning; the selected `apple2p` ROM audit is good.
On this workstation the already supplied ROM directory is
`/home/iolo/workspace/retro/a2x/mame/roms`. Supply your own directory explicitly;
the launcher does not assume this local path or obtain ROMs.

The baseline profile is **Apple II+**, MOS 6502, 48K main RAM, Applesoft ROM,
no slot 0 language card, no slot 4 Mockingboard, slot 6 Disk II NG 16-sector
controller, two available 5.25-inch drives. Side A is mounted in drive 1 and
side B is copied but not mounted until the game requests it. Both supplied
manuals require 48K; the extracted `START` text invokes `HGR` and `HGR2` before
`BLOAD ADVEN INTERP.OBJ,A$800`, `BLOAD PARMS.OBJ,A$300`, and `CALL2048`.
This establishes the Applesoft requirement. The original `apple2` Integer BASIC
profile initially stopped at its firmware keyboard routine without booting the
game; it is not the chosen baseline. This is an explicit model choice, not a
claim that the game needs IIe features or additional RAM.

Start a new session (the output directory must not already exist):

```sh
python3 tools/mame_session.py --rompath /path/to/roms \
  --output build/session-01 --debug --headless
```

Omit `--headless` for a visible window and audible sound. Headless sessions have
no audio output and cannot establish sound equivalence. The launcher disables
configuration reads and isolates configuration, NVRAM, snapshots, states, and
disk copies inside the session directory. `session.json` records the exact
command and hashes of the media copies. Original disks are never mounted writable.

Enter the printed `dofile(...)` command into the owned Lua console. With
`--debug`, the CPU starts stopped at reset; `mask.go()` runs it. Without the
debugger it runs immediately. Helpers loaded by an autoboot script live in a
separate Lua environment and are not automatically globals in the console.

```lua
mask.capture('startup') -- pauses; writes PNG, text/CPU/media JSON and RAM views
mask.keys('LOOK\r')     -- queue input; verify consumption in a later capture
mask.resume()          -- resume an ordinary pause
mask.swap('b')         -- swap drive 1 to the copied side B when prompted
mask.exit()            -- stop only this owned session
```

`mask.capture` records CPU-visible low RAM, text page 1, and both high-resolution
pages without touching the soft-switch range. Its text decoder shows the native
40-column page and may include stale rows hidden by mixed graphics mode. It
does not yet decode the game's custom character rendering. Debugger run/stop
and ordinary pause are different: use `mask.go()` after a debugger stop, and
`mask.resume()` after a capture. Save states are not portable across emulator
versions or machine profiles.

The final source/asset disk build is still pending. Generated work belongs in
ignored `build/`; deleting a disposable session there cannot alter the inputs.
