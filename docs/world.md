# World scripts, vocabulary and puzzle state

The world is interpreted data, rather than a set of machine-code overlays.
All 87 catalog text streams have [readable views](../assets/decoded/scripts/)
and stable side/filename/line IDs in `scripts.json`. The native high-bit ASCII
streams remain authoritative build assets. `tools/script_views.py` generates
views and file-offset provenance; `tools/world_views.py` generates the
[world index](../assets/decoded/world/world.json),
[1,352 text literal views](../assets/decoded/world/text.json),
[94 vocabulary groups](../assets/decoded/world/vocabulary.json),
[23 object entries](../assets/decoded/world/objects.json) and
[parameter decoding](../assets/decoded/world/parameters.json).
These generated indexes are review aids, not another editable script authority.

Each indexed line retains its native byte offset and length. Text is high-bit
ASCII, with $8D separators and the first $00 ending the text stream. The native
allocated file includes its final unused bytes. Quoted `.P` prints literal text;
a semicolon immediately before CR suppresses the newline. Embedded semicolons
print literally. Control characters remain in native streams and escaped JSON
views; they must not be stripped if native scripts are edited directly.

## Dispatch and vocabulary

Room scripts load at $6800, replacing the previous script. LIBRARY remains at
$7000. Entry actions initialize/draw a scene; subsequent nondot lines are command
patterns with dot-line bodies. `!` names internal subroutines; `%` names ordinary
script patterns populated through four-character macro dispatch. Neither is a
6502 opcode or compressed dictionary token. The room's @ terminator transfers
ordinary scanning to the resident library. An intrinsic `?`, `.1` or `.2` instead
scans to the next @ and resumes at $0919, advancing into the next library section.
Thus multiple @ sections implement the vocabulary pipeline, rather than separate
loaded libraries. Saved pattern pointers on the hardware stack provide returns.

Input significant words retain five characters and pad with spaces. The matcher
can try a pattern at successive normalized word boundaries; a pattern need not
consume all input. The `$0390` parameter table contains AND/THEN forms with
space/period/comma/CR boundaries. These split chained input. Articles such as
THE are not dictionary entries in that table; matching and the vocabulary
pipeline can tolerate intervening unrecognized words. Comma and period also
separate commands. This is not a modern natural-language parser.

The library first provides direct handlers and fallbacks, then resolves object
words to L and a two-character object number. It tests availability into O,
resolves category words such as door/key/bowl, resolves verbs to another pair,
and invokes `. ! %****` with those four characters rewritten in script RAM.
For example GET maps to GT, lantern to04 and the resulting `%GT04` can match
a room-specific handler or the library's general pickup handler. Category
patterns include `%GTBW` for a bowl and `%OPEN` for opening an entrance. C/G
control fallback/error reporting; they are parsing state rather than permanent
puzzle completion flags. Full encoded patterns and synonyms are in the generated
vocabulary index, including five-character truncation and multiword forms.

## Object and room state

Object names/numbers come from the library's OBJL table:

| Number | Object | Number | Object |
| --- | --- | --- | --- |
| 1 | Raoul | 13 | amulet |
| 2 | jeep | 14 | revolver |
| 3 | shovel | 15 | rope |
| 4 | lantern | 16 | jade bowl |
| 5 | matches | 17 | silver bowl |
| 6 | knife | 18 | gold bowl |
| 7 | food | 19 | golden key |
| 8 | pills | 20 | black key |
| 9 | jaguar | 21 | silver key |
| 10 | statue head | 22 | flute |
| 11 | snake | 23 | mask |
| 12 | map | | |

TC is object containment:0 means carried,2 can mean in the jeep,255 means not
contained. TL supplies room location when an object is not carried/contained.
The library also tests the containment object's TC/TL, so contents in a nearby
jeep remain reachable. O records availability:0 unrecognized,1 carried,
2 in a carried container,3 directly in this room,4 in a container in this room.
Special values254/253 are context-dependent: rope attachment and worn-mask
states use them. They are not universal room IDs. The jeep itself uses TC(2)=0
when the player is inside it; exiting sets TC(2)=255 and TL(2)=N.

T0/T1 are object-specific state, TV object values. Examples include T0(4) lit
lantern, T0(5) lit match, T0(8) disease cured, TV(8) remaining pills, T0(23)
true-mask identity, T1(23) altar/retrieval progress and TV(23) mask-use count.
The initializer sets TV(8)=100 and resets the first fifty array positions.
Generic pickup prevents taking additional objects while TC(10)=0; the head's
own handler also checks whether selected other items are carried. This is a
script-specific carrying restriction, not a general numeric weight system.

N is the current world-state ID; F often stores the previous room for directional
entry, and P is the displayed/drawing page. N0/N1/NV store room-specific states
and timers. Filename numbers are not always N: ROOM30.0/.1/.2 use90/91/92,
ROOM34.1/.2 use134/234, ROOM38.0 uses250, and ROOM44 variants use100–109.
The index records every literal N assignment and every static/deferred load
reference. Conditions, assignments, relative jumps and array references retain
line IDs so an apparent exit can be checked in its handler. A static reference
is not proof that an exit is reachable or unconditional.

GE includes shared state:0 jeep animation,1–4 travel-view choices,5 travel/swap
mode,6 tunnel topology,7 disease/pill interval,10 alternating rejected-direction
text,12 expected disk side,13 cached graphics region,14 travel animation and15
saved condition across nested library calls. Other GE entries are indexed where
used without assigning an unsupported global meaning. GE12=2 selects B; other
values select A in the generic reinsertion prompt (initial state is0).
normal play swaps media in the same drive. [Memory ownership](memory.md) separates
these tables from transient graphics/OS workspace.

## Main puzzles and failure paths

The supplied walkthrough informed the route; script conditions and the archived
original/rebuilt recordings establish the behavior. The following links point
to source views with their complete handlers and alternate actions.

| Puzzle / region | Script evidence and state | Observed route / limits |
| --- | --- | --- |
| Plane, map, jeep | [ROOM1.0](../assets/decoded/scripts/a/room-1-0.txt), ROOM2 variants; library containment | Opening covers map pickup, jeep entry/exit and inventory. |
| Food for flute | [ROOM19.0](../assets/decoded/scripts/a/room-19-0.txt): offering food advances N0(19), consumes food and makes flute available | Opening obtains flute; later playback is audible. |
| Statue transformation | [ROOM6.0](../assets/decoded/scripts/a/room-6-0.txt),6.1,6.2: inscription sets N0(6), replacement sets N1(6), special head carrying tests | Opening takes/replaces head and observes transformed clearing. |
| Lantern and snake | [ROOM9.0](../assets/decoded/scripts/a/room-9-0.txt),9.1,9.2: keyboard-polled attack and alternate dark-room path; library light/match state | Full route lights lantern and delivers urgent SHOOT. Dark-room strike/death remains a static alternate path. |
| Jade bowl drop | [ROOM11.0](../assets/decoded/scripts/a/room-11-0.txt): TC(16)=0, TL(16)=255, sets tunnel mode7 and room state16 before ROOM13 load | Full route observes drop and subsequent tunnel. |
| Ghost and gold bowl | [ROOM15.0](../assets/decoded/scripts/a/room-15-0.txt): N0/N1/NV(15), timed ghost appearance/fade and bowl pickup | Full replay waits for the observable apparition fade. Early pickup/failure remains in script. |
| Urn and skeletons | [ROOM16.0](../assets/decoded/scripts/a/room-16-0.txt), [ROOM17.0](../assets/decoded/scripts/a/room-17-0.txt): N0(16)0 left,1 held,2 ground,3 right,4 open; N0/N1(17) attack states/timer | Full route uses amulet, gets silver bowl, places urn right and opens middle door. Holding urn restricts exits/inventory. |
| Tunnel/travel overlays | [TRAVEL](../assets/decoded/scripts/a/travel.txt), [TUNNEL](../assets/decoded/scripts/a/tunnel.txt): GE6 turn/dead-end/pit topology; GE1–5/13–14 view layers | Full route exercises both disks and tunnel animation. GE6=9 unseen-pit death is an alternate path. |
| Keys, webs and locked doors | [ROOM25.0](../assets/decoded/scripts/b/room-25-0.txt),26.0,27.0,28.0: clearing webs, silver/gold/black key retrieval, N1(27) door state and golden-key test | Static branch mapping; main full route does not exercise every key solution. |
| Gas and stepping stone | [ROOM36.0](../assets/decoded/scripts/b/room-36-0.txt), [ROOM39.0](../assets/decoded/scripts/b/room-39-0.txt): polled reaction loops, Raoul fate and jump phase | Full route escapes southwest, observes Raoul's death and sends physical Return in the safe native phase. Keyboard bus predicates and phase bounds are recorded in full-route.json. |
| Rope/pyramid and priest word | [ROOM34.0](../assets/decoded/scripts/b/room-34-0.txt) and variants; [ROOM37.0](../assets/decoded/scripts/b/room-37-0.txt): rope TC15=254/TL15=34; XOTZI pattern opens face passage | Full route uses the learned word. Rope descent/alternate pyramid branches are statically mapped. |
| Bowl/altar and true mask | ROOM40/41 variants, [ROOM41.2](../assets/decoded/scripts/b/room-41-2.txt): T0(23) distinguishes mask, T1(23) controls altar/retrieval; search after first removal reveals blue-eyed mask and sets T0(8)=1 | Full route verifies true-mask text and disease removal state. |
| Riddles and maze | [ROOM43.0](../assets/decoded/scripts/b/room-43-0.txt), ROOM44.0–.9: N0(43) selects coffin/grave, fire, then man; third failure kills | Full route answers COFFIN and traverses maze. Alternate answers use native prefix matching, not strict equality. |
| Roboff, jaguar, ending | [ROOM49.0](../assets/decoded/scripts/b/room-49-0.txt),49.1,49.2, [ROOM50.0](../assets/decoded/scripts/b/room-50-0.txt): B timers, mask transfer, flute possession; final TV8 count | Full route hands over mask, plays flute and reaches victory with83 pills. Drawing/shooting or waiting too long are explicit death paths. |
| Death, restart, save | [DEATH](../assets/decoded/scripts/a/death.txt) and library SAVE/RESTORE handlers | Deliberate overdose, rejected death-screen command, START, same-session/fresh restore and144-sector saves have accepted recordings. |

Speaker sequences are script assignments to SV followed by native `.N` calls;
there is no separately stored sampled audio file. Effects and flute melodies are
covered by [intrinsic sound documentation](intrinsics.md) and recorded PCM.
Pill depletion is processed in the library between ordinary actions; timed
rooms add their own `.W`/Q polling loops. After a timer sees the first key and
hands control to the blocking input editor, typing the rest of the command does
not itself poll the room timer. The chasm loop instead requires Return in the
correct animation/keyboard-clear phase. Host delays are not substitutes for
these native observable conditions.

The full route and behavior matrix establish gameplay checks, while these indexes
map all scripts beyond that route. Every invalid action and alternate ending
path has not been executed; remaining testing limits are explicitly tracked in
[behavior-matrix.md](behavior-matrix.md). No executable overlay remains hidden
inside a native text or picture asset.
