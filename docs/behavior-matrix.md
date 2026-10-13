# Current behavior evidence

All accepted runs use the documented 48K Apple II+ profile and copied media.
The rebuilt column refers to the current interpreter/renderer build, which
still contains temporary native code. Reports include exact commands, emulated
timestamps, media hashes, decoded output and CPU observations. Passing these
checks does not finish the remaining source reconstruction.

| Behavior | Original evidence | Rebuilt evidence | Result / limits |
| --- | --- | --- | --- |
| Fresh side-A boot, title and plane | [opening](evidence/opening-original.json) | [core opening](evidence/core-opening-rebuilt.json) | Pass |
| Inventory, invalid/missing verb and object | Same opening reports | Same opening reports | Pass, thirteen opening checks total |
| Food/flute and statue puzzle | Same opening reports | Same opening reports | Pass |
| Lantern, snake, bowls/ghost, skeleton, urn | [full original](evidence/full-original.json) | [full rebuilt](evidence/full-core-rebuilt.json) | Pass; first-key and wait predicates documented in baseline |
| Side B mount, gas escape, chasm | Same full reports | Same full reports | Pass; bounded physical Return at native safe phase |
| True mask, coffin maze, Roboff, jaguar, ending | Same full reports | Same full reports | Pass; 83 pills remaining, seventeen full-route checks |
| Full speaker effects and flute | [original with audio](evidence/audio-full-original-gameplay.json) | [rebuilt with audio](evidence/audio-full-core-gameplay.json) | Both reach ending; [full PCM comparison](evidence/audio-full.json) passes |
| Sound toggle state and actual effect suppression | [controls](evidence/controls-original.json) | [controls rebuilt](evidence/controls-core.json) | [PCM windows](evidence/audio-controls.json): pill silent with OFF, audible with ON |
| Command chaining, unknown-chain error | Same controls reports | Same controls reports | Pass; LOOK/INVENTORY chain and FERNAP rejection |
| Input overflow, empty pickup, blocked movement | Same controls reports | Same controls reports | Pass; forty-five A keys retain thirty-six, empty GET ALL and plane N reject |
| Save, move to room 18, restore room 3 | [save original](evidence/save-original.json) | [save rebuilt](evidence/save-core-rebuilt.json) | Eighteen checks each; five $FC-byte object arrays restored exactly |
| Raw save disk writes | [save disk comparison](evidence/save-disk.json) | Same comparison | Exactly 144 changed sectors, tracks 23–31; saved disks agree |
| Restore after another fresh boot | [fresh restore](evidence/restore-original.json) | [fresh restore rebuilt](evidence/restore-core.json) | Eight checks each; room, jeep and map restored |
| Deliberate death and START restart | [restart original](evidence/restart-original.json) | [restart rebuilt](evidence/restart-core.json) | Nine checks each; invalid death-screen command rejects, room 1 and initial inventory return |

Not yet covered: save/restore on side B, missing/unformatted save media errors,
backspace/repeat details, every invalid action, maximum carrying behavior,
alternative puzzle solutions and all room branches. Exhaustive path coverage is
not required, but later source/asset changes should add cases when they affect
currently untested behavior. A separate all-manual full-route recording has not
been established; the full route was guided and automated incrementally.
