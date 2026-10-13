# Current behavior evidence

All accepted runs use the documented 48K Apple II+ profile and copied media.
The rebuilt column records progressively reconstructed builds; later source
changes repeat the relevant routes. All live game code now has source and images
are editable build inputs. Reports include exact commands, emulated
timestamps, media hashes, decoded output and CPU observations. Passing these
checks does not establish exhaustive execution-path coverage. The separate
[operator-stepped baseline](manual-playthrough.md) now reaches the ending.

| Behavior | Original evidence | Rebuilt evidence | Result / limits |
| --- | --- | --- | --- |
| Fresh side-A boot, title and plane | [opening](evidence/opening-original.json) | [core opening](evidence/core-opening-rebuilt.json) | Pass |
| Inventory, invalid/missing verb and object | Same opening reports | Same opening reports | Pass, thirteen opening checks total |
| Food/flute and statue puzzle | Same opening reports | Same opening reports | Pass |
| Lantern, snake, bowls/ghost, skeleton, urn | [full original](evidence/full-original.json) | [full rebuilt](evidence/full-core-rebuilt.json) | Pass; first-key and wait predicates documented in baseline |
| Side B mount, gas escape, chasm | Same full reports | Same full reports | Pass; bounded physical Return at native safe phase |
| True mask, coffin maze, Roboff, jaguar, ending | Same full reports | Same full reports | Pass; 83 pills remaining, seventeen full-route checks |
| Full speaker effects and flute | [original with audio](evidence/audio-full-original-gameplay.json) | [SVG/source full route](evidence/pictures-full.json) | Both reach ending; [current full PCM comparison](evidence/pictures-audio-full.json) passes |
| Sound toggle state and actual effect suppression | [controls](evidence/controls-original.json) | [controls rebuilt](evidence/controls-core.json) | [PCM windows](evidence/audio-controls.json): pill silent with OFF, audible with ON |
| Command chaining, unknown-chain error | Same controls reports | Same controls reports | Pass; LOOK/INVENTORY chain and FERNAP rejection |
| Input overflow, empty pickup, blocked movement | Same controls reports | Same controls reports | Pass; forty-five A keys retain thirty-six, empty GET ALL and plane N reject |
| Save, move to room 18, restore room 3 | [save original](evidence/save-original.json) | [save rebuilt](evidence/save-core-rebuilt.json) | Eighteen checks each; five $FC-byte object arrays restored exactly |
| Raw save disk writes | [save disk comparison](evidence/save-disk.json) | Same comparison | Exactly 144 changed sectors, tracks 23–31; saved disks agree |
| Restore after another fresh boot | [fresh restore](evidence/restore-original.json) | [fresh restore rebuilt](evidence/restore-core.json) | Eight checks each; room, jeep and map restored |
| Deliberate death and START restart | [restart original](evidence/restart-original.json) | [restart rebuilt](evidence/restart-core.json) | Nine checks each; invalid death-screen command rejects, room 1 and initial inventory return |
| Backspace correction and prompt bound, AND/THEN, slash | [parser original](evidence/parser-original.json) | [parser rebuilt](evidence/parser-core.json) | Eleven checks pass; raw LOOK bytes agree after correction/boundary test; native slash repeat rejects. |
| Statue-head carrying restriction | Same parser reports | Same parser reports | Carried items block head pickup; dropping them permits pickup; carried head then blocks map pickup. |
| All257 native pictures and a supported vector edit | [reference comparison](evidence/picture-roundtrip.json) | Same comparison; [geometry edit](evidence/picture-edit.json) | Every standalone record matches both HGR pages; edited PIC1 loads and appears in game. |
| Side-B save/restore and media reinsertion | [side-B original](evidence/save-side-b-original.json) | [side-B source](evidence/save-side-b-rebuilt.json) | Nineteen checks pass; room34/jeep/side and all five object arrays restore; [144-sector footprint](evidence/save-side-b-disk.json) agrees. |
| Separate operator-stepped full playthrough | [manual original](evidence/manual-original.json) | Automatic full-route evidence above | 26 checks; documented complete native checkpoint retry, 122 commands, two parser retries, both sides and 83 pills. |
| Representative route scenes and complete world state | [scene/state comparison](evidence/full-scene-state-comparison.json) | Same comparison | Sixteen checkpoints match text, displayed HGR pages, scalar state and object/room arrays. |
| Clean checkout without original/reference build inputs | Original data used only as independent boot reference | [clean build](evidence/clean-checkout.json), [clean boot](evidence/clean-checkout-boot.json) | 206 supplied/reference files absent; three matching builds, zero forbidden reads, seven boot gates and native trace agreement. |

Not yet covered: missing/unformatted save media errors,
every invalid action, carrying restrictions beyond the observed head rule,
alternative puzzle solutions and all room branches. Exhaustive path coverage is
not required, but later source/asset changes should add cases when they affect
currently untested behavior. Manual checkpoint recovery and failed attempts are
documented separately from the fresh-boot automated equivalence tests.
