# Assembly source

`renderer.s` documents the high-resolution text output routines at $B300–$B3FF,
with a fixed-address ld65 configuration. `tools/build.py` assembles this module
and incorporates it into a pair of early disks. Other executable regions still
require disassembly; no executable blob is considered completed source.
