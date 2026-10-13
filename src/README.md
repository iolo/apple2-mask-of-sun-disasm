# Assembly source

`chargen.s` constructs the whole character-generator file from lookup formulas,
legacy source/data and editable font PNGs. Its included `renderer.s` documents the high-resolution text output routines at $B300–$B3FF;
`interpreter.s` covers the resident $0800–$0CFF engine, command editor/parser and
named-file loader. `boot-a.s`, `boot-b.s` and the `boot-stage2` wrappers cover
both disk copies' bootstrap sectors. They have fixed-address ld65 configurations.
`dos-low.s` and the `rwts` wrappers cover all loaded DOS pages.
`intrinsics.s` covers script directives, expressions, vectors, speaker synthesis
and save/restore, including its allocated header/tail.
`tools/build.py` assembles these modules
and incorporates them into a pair of early disks. Other executable regions still
require disassembly; no executable blob is considered completed source.
