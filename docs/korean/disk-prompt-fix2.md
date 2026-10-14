# Explicit game-disk prompts — r01-fix2

The user confirmed that fix1 boots successfully in their emulator but still shows
“게임 디스크 A/B를 넣고 RETURN을 누르세요.” They requested A explicitly at startup.

The runtime now chooses the required disk using the same GE(12) convention as
its package loader: values below 2 select A, otherwise B. Both the resource retry
and post-restore pool reload use this selection. The displayed messages are:

- `게임 디스크 A를 넣고
RETURN을 누르세요.`
- `게임 디스크 B를 넣고
RETURN을 누르세요.`

The original combined notice was replaced by these two resident messages, so
neither depends on a valid room cache. All other 1,326 approved entries are
unchanged. [The correction ledger](approval-r01-fix2.json) records the user's
request and archives the replaced entry; the original r01 approval is preserved.

Verification: 44 host tests; all 1,328 pool bodies and disk-file hashes; ten
byte-identical repeat-build assets. MAME Apple II+ runs the 66-command A→B route,
same-session B save/restore and fresh-boot B restore. Each observed runtime prompt
is checked against its selected side and its rendered message cells against the
actual ASCII/Hangul font. Captures show A at startup and B after restore.
The ending route and AppleWin/GSSquared were not rerun for this wording revision.
The user confirmed fix1 works in their own testing; fix2 retains that startup fix.

Runtime: 1,891/2,048 bytes; resident pool: 4,093/4,096; largest room pool:
1,013/1,024; font: 650 glyphs/5,200 bytes. Free sectors: EXTRA 344, A 2, B 3.
No ProDOS conversion. Contextual translation playtesting remains open.

Use `output/korean-playtest-r01-fix2.zip`, replace EXTRA/A/B together, and use the
included blank save disk. Media/save identities are specific to this build.
Evidence: `docs/evidence/korean/approved-r01-fix2-{build,game,output-audit}.json`.
