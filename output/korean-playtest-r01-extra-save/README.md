# Mask of the Sun — Korean r01-extra-save

**Three disks: EXTRA+SAVE, A, B.** EXTRA is now both the boot disk and save disk.
The startup-hang and explicit A/B prompt fixes are included.

Replace all three images together. Keep this ZIP and use writable working copies.
Saves from earlier builds are not compatible. Preserve any old saved EXTRA before
replacing it: overwriting the image also overwrites its save.

1. Boot **mask-of-sun-ko-extra.dsk**.
2. When asked for A, replace EXTRA with **mask-of-sun-ko-a.dsk in the same drive**
   and press RETURN. Use B when the game explicitly requests it.
3. To save, enter **SAVE GAME**, confirm, and insert **EXTRA** when prompted.
   Then reinsert the requested A or B disk.
4. To restore, enter **RESTORE GAME**, confirm, and insert the EXTRA containing
   your save. Reinsert A or B as requested.
5. You can boot from EXTRA after saving. Enter the game via A, then RESTORE GAME.

**Do not format EXTRA.** It is already prepared, and it must be writable to save.
One EXTRA image holds one save; saving again replaces it. No fourth disk is needed.
Commands remain English.

Verified on MAME Apple II+ with 48K main RAM + 16K Language Card: 66-command A→B
route, save to the booted EXTRA, B-side restore, and cold boot/restore from that
saved EXTRA. Only the 145 reserved sectors change; all startup files and every
other sector remain identical. Save/restore screenshots show the EXTRA prompt.
All 1,328 message bodies and disk files verified; ten repeat-build assets match;
45 host tests pass. EXTRA retains 199 free sectors.

AppleWin/GSSquared and the full ending route were not rerun for this revision.
Human contextual playtesting, timing-window comparison and physical hardware
verification remain open. Three 140K DOS images; no ProDOS conversion.

[Playtest guide](docs/korean/playtest-r01.md) · [Input guide](docs/korean/input-guide.md) · [Technical details](docs/korean/extra-save.md)

Font: Mask Korean 7x8, derived from GalmuriMono7 2.403.
[Provenance](assets/korean/font/source.json) · [SIL OFL 1.1](assets/korean/font/OFL.md)
