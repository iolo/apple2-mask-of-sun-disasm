#!/usr/bin/env python3
"""Launch an isolated Apple II+ baseline console with copied writable media."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rompath', type=Path, default=os.environ.get('MAME_ROMPATH'))
    p.add_argument('--output', type=Path, required=True, help='new session directory')
    p.add_argument('--disk-a', type=Path, default=ROOT / 'mask-of-sun-a.dsk')
    p.add_argument('--disk-b', type=Path, default=ROOT / 'mask-of-sun-b.dsk')
    p.add_argument('--headless', action='store_true')
    p.add_argument('--debug', action='store_true')
    p.add_argument('--script', type=Path, help='optional owned replay startup Lua script')
    p.add_argument('--fast', action='store_true', help='unthrottled; compare emulated time, not wall time')
    p.add_argument('--route', type=Path, help='JSON exploration route for opening_replay.lua')
    p.add_argument('--record-audio', action='store_true', help='record emulated mixer output to session audio.wav')
    p.add_argument('--trace-keyboard', action='store_true', help='observe late-game keyboard bus reads without additional I/O reads')
    p.add_argument('--save-disk', type=Path, help='copy an initialized scratch disk for save/restore tests')
    args = p.parse_args()
    if not args.rompath or not args.rompath.is_dir():
        p.error('supply --rompath or MAME_ROMPATH with locally supplied ROMs')
    mame = shutil.which('mame')
    if not mame:
        p.error('missing MAME; install it and rerun tools/check_tools.py')
    plugins = Path('/usr/share/games/mame/plugins')
    if not (plugins / 'console/init.lua').is_file():
        p.error('MAME console/json plugins are required under /usr/share/games/mame/plugins')
    subprocess.run([mame, 'apple2p', '-noreadconfig', '-rompath', str(args.rompath.resolve()),
                    '-verifyroms'], check=True, timeout=30)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    media = {}
    for side, source in [('a', args.disk_a), ('b', args.disk_b)]:
        destination = out / f'side-{side}.dsk'
        shutil.copyfile(source, destination)
        media[side] = {'source': str(source.resolve()), 'copy': str(destination),
                       'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
    if args.save_disk:
        destination = out / 'save.dsk'
        shutil.copyfile(args.save_disk, destination)
        media['save'] = {'source': str(args.save_disk.resolve()), 'copy': str(destination),
                         'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
    cmd = [mame, 'apple2p', '-noreadconfig', '-rompath', str(args.rompath.resolve()),
           '-ramsize', '48K', '-sl0', '', '-sl4', '', '-sl6', 'diskiing',
           '-flop1', media['a']['copy'], '-console', '-pluginspath', str(plugins),
           '-skip_gameinfo', '-natural', '-window', '-nomouse', '-homepath', str(out)]
    for option in ['cfg_directory', 'nvram_directory', 'snapshot_directory',
                   'state_directory', 'diff_directory']:
        directory = out / option
        directory.mkdir()
        cmd.extend(['-' + option, str(directory)])
    env = os.environ.copy()
    env['MASK_PROJECT_ROOT'] = str(ROOT)
    if args.trace_keyboard:
        env['MASK_KEYBOARD_TRACE'] = '1'
    if args.route:
        env['MASK_ROUTE'] = str(args.route.resolve())
    if args.headless:
        env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', QT_QPA_PLATFORM='offscreen')
        cmd.extend(['-video', 'none'])
        if not args.record_audio:
            cmd.extend(['-sound', 'none'])
    if args.record_audio:
        cmd.extend(['-wavwrite', str(out / 'audio.wav'), '-samplerate', '22050'])
    if args.debug:
        cmd.extend(['-debug', '-debugger', 'qt'])
    if args.script:
        cmd.extend(['-autoboot_script', str(args.script.resolve()), '-autoboot_delay', '0'])
    if args.fast:
        cmd.append('-nothrottle')
    (out / 'session.json').write_text(json.dumps({'command': cmd, 'media': media,
        'headless': args.headless, 'debug': args.debug}, indent=2) + '\n')
    print('Session: ' + str(out), flush=True)
    print('Load helpers: dofile(' + repr(str(ROOT / 'tools/mame_control.lua')) + ')', flush=True)
    print('Lua: mask.capture("checkpoint"); mask.keys("LOOK\\r"); mask.swap("b")', flush=True)
    os.chdir(out)
    os.execve(mame, cmd, env)


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
