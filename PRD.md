# apple2-mask-of-sun-disasm

## GOAL

Reverse the Apple II game "The Mask of the Sun" for educational purposes.
The goal is to produce a human-readable disassembled source code, extract assets,
and provide a build script to generate disk images from the disassembled source code and extracted assets.

## Input

- mask-of-sun-a.dsk, mask-of-sun-b.dsk (cracked disk images)
- mask-of-sun-manual-1.jpg, mask-of-sun-manual-2.jpg, mask-of-sun-booklet.pdf, mask-of-sun-gamebox-cover.jpg, mask-of-sun-gamebox-back.jpg (official manual, booklet, gamebox, diskette scans)
- mask-of-sun-walkthrough.txt, mask-of-sun-walkthrough.pdf, mask-of-the-sun-walkthrough-korean.pdf (unofficial walkthroughs)

## Output

- human readable disassembled source code
- extracted assets(texts, images, sounds, etc.)
- build script to generate an (possibly) identical disk image from the disassembled source code and extracted assets

## Tools

- Cross assembler/disassembler for 6502
  - ca65/cl65 (part of cc65)
- Apple II emulator as you prefer
  - MAME with Apple II driver and lua scripting.
  - Apple2ts with Apple2ts-server mcp server
- Disk image tools(as you prefer)
  - a2kit
  - AppleCommander
- Python, Node or other scripting language as you prefer for automation and asset extraction.

## Notes

- Create a step-by-step plan in `PLAN.md`
- Update `PROGRESS.md` and commit changes after each step is completed
- Do NOT stick to identical disk image, as long as the game works the same way, it is fine to have a different disk image layout.

## References

- https://en.wikipedia.org/wiki/The_Mask_of_the_Sun
- https://www.mobygames.com/game/9544/the-mask-of-the-sun/
- https://www.adventuregamedb.com/game_info/the_mask_of_the_sun
- https://www.youtube.com/watch?v=cn6UNnSbgVs (longplay video of the game)
- My earlier disassembly projects for Apple II games
  - https://github.com/iolo/apple2-stella7-disasm
  - https://github.com/iolo/apple2-rescue-raiders-disasm
  - https://github.com/iolo/apple2-sundog-disasm
  - https://github.com/iolo/apple2-carmen-sandiego-world-disasm


