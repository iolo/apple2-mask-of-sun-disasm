# Assembly source

`renderer.s` documents the high-resolution text output routines at $B300–$B3FF;
`interpreter.s` covers the resident $0800–$0CFF engine, command editor/parser and
named-file loader. `boot-a.s`, `boot-b.s` and the `boot-stage2` wrappers cover
both disk copies' bootstrap sectors. They have fixed-address ld65 configurations.
`tools/build.py` assembles these modules
and incorporates them into a pair of early disks. Other executable regions still
require disassembly; no executable blob is considered completed source.
