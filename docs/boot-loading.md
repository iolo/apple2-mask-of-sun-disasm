# Boot and load phases

The unmodified side-A trace and six-module rebuilt trace agree on all 224
observed entries and sector-read requests. [boot-loading.json](evidence/boot-loading.json)
passes seven checks for each version and a trace agreement check. The native
slot-ROM bytes are external ROM prerequisites, not redistributed game source.
The four assembled disk bootstrap modules preserve original I/O and source
encodings. The remainder of DOS is still temporary native input.

## Native startup

1. The Apple II+ firmware enters slot6 ROM $C600 at 0.130 emulated seconds.
   Its read path $C65C reads physical sector0 into $0800, then enters $0801.
   At entry, ROM has incremented the destination page to $09. X/$2B are $60.
2. [boot-a.s](../src/boot-a.s) makes $3E/$3F point at $C65C. Its mutable page
   and index bytes at $08FE/$08FF start at $B6/9. The ROM transfers ten sectors,
   descending destination $BF00..$B600 using the physical interleave table.
   Runtime comparison identifies those bytes as DOS logical T0/S9..T0/S0;
   the resulting $B600..$BFFF matches logical T0/S0..T0/S9 exactly.
3. The boot sector advances its page pointer to $B7 and enters $B700 at 2.159
   seconds. [boot-stage2.inc](../src/boot-stage2.inc) configures the native IOB
   at $B7E8 and calls $BD00. It loads 27 pages downward: T2/S4..S0, T1/S15..S0,
   T0/S15..S10 into $B500..$9B00. The complete DOS boot extent is therefore
   $9B00..$BFFF, 37 pages. Firmware/DOS buffers later change some of those bytes.
4. Stage2 calls native DOS initialization entry $BA6D, then transfers to cold
   start $9D84. In this crack that entry is a short stub returning X=$8A,Y=$36;
   it does not initialize memory. The nibble decode table is already present.
   DOS locates the startup text file `START`, then executes its Applesoft/DOS
   commands. Its first observed output-processing entry at $A000 is at 4.809
   seconds. `START` initializes both HGR pages, BLOADs `ADVEN INTERP.OBJ` at
   $0800 and `PARMS.OBJ` at $0300, and CALLs 2048. At $0800 entry at 10.445
   seconds, both payloads match their recorded native file bytes.
5. The interpreter loads `INITIAL` and `LIBRARY`, then loads the **allocated
   streams including headers** of `INTRIN.OBJ` at $0CFC and `CHAR GEN` at $ADFC.
   The header offsets position intrinsic code at $0D00 and character lookup
   tables/renderer/font in high memory. Renderer install at $B300 is observed
   at 19.796 seconds; intrinsic dispatch follows. Both entire allocated streams
   match before renderer initialization. The first game COUT at $B317 is at
   22.645 seconds after the initial logo drawing.

The alternate reload/write routines and DOS helpers copied with the boot page
are retained as readable assembly. Their flags, IOB/DCT data and native padding
are explicit. The diagnostic routine in the side-A sector at offset $D0 has no
executed caller established; it is source, not an opaque code omission.

## Side selection and memory ownership

[boot-b.s](../src/boot-b.s) prints high-bit `BOOT OTHER SIDE.` through firmware
output and loops on BEQ at $0806. Separate original/rebuilt boot attempts observe
that exact PC and text; see [wrong-side.json](evidence/wrong-side.json). Side B's
second-stage page differs in its startup trampoline and one IOB status byte;
the source wrapper selects those native differences. Normal play boots A and
mounts B in the same drive only at the game's prompt, as the full route verifies.

Disk load headers do not necessarily describe runtime destinations. Parameters
have nominal address $0900 but START BLOADs them at $0300. CHAR GEN has nominal
$1700, yet its full allocated stream is loaded at $ADFC. The custom loader's
buffer addresses are authoritative for subsequent loads.

The game does not preserve the whole DOS boot extent as active OS code. Its
graphics files load at $9C00 and can overwrite front DOS code/buffers; CHAR GEN
overwrites $ADFC..$B6FB, including the copied bootstrap/DOS helper page. The
interpreter subsequently uses its own catalog loader and retained RWTS $BD00,
not the overwritten high-level DOS command/file interpreter. Save/restore calls
retained $BA72/$BA69 register-return stubs and RWTS. That phase change is important
when classifying a RAM capture: live font/graphics data can occupy addresses
that held DOS code during startup. Original DOS code still requires full source.

The trace observes selected execution entries rather than every instruction.
Captures are guarded against recursive observation of their own memory reads.
ROM read requests are recorded only when buffer/sector changes, avoiding header
scan-loop duplicates. It never writes game memory or reads keyboard/disk I/O
merely to inspect it. All bus observations return no replacement byte.

```sh
python3 tools/mame_session.py --rompath /path/to/roms --output build/boot-original \
  --headless --fast --script tools/boot_trace.lua
python3 tools/build.py --output build/boot-build
python3 tools/mame_session.py --rompath /path/to/roms --output build/boot-rebuilt \
  --headless --fast --script tools/boot_trace.lua \
  --disk-a build/boot-build/mask-of-sun-a.dsk --disk-b build/boot-build/mask-of-sun-b.dsk
python3 tools/verify_boot.py build/boot-original build/boot-rebuilt --output build/boot-report.json
```
