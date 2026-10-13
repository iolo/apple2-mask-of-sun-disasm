#!/usr/bin/env python3
"""Early template-free rebuild: assembled modules plus tracked raw regions.

This is intentionally incomplete. All other code remains tracked temporary raw
dependencies in assets/raw/manifest.json; completing PLAN.md requires replacing
them and making decoded graphics authoritative inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from dos_disk import ROOT, repack


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'build/early')
    args = p.parse_args()
    for name in ('ca65', 'ld65'):
        if not shutil.which(name):
            p.error(f'missing {name}; install cc65 and run tools/check_tools.py')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    replacements, assembled = {}, []
    modules = [('renderer', 0xb300, 0x100, 'assets/raw/a/files/char-gen.bin', 0x504),
               ('interpreter', 0x0800, 0x500, 'assets/raw/a/files/adven-interp-obj.bin', 4),
               ('boot-a', 0x0800, 0x100, 'assets/raw/a/system/track-00.bin', 0),
               ('boot-b', 0x0800, 0x100, 'assets/raw/b/system/track-00.bin', 0),
               ('boot-stage2-a', 0xb700, 0x100, 'assets/raw/a/system/track-00.bin', 0x100),
               ('boot-stage2-b', 0xb700, 0x100, 'assets/raw/b/system/track-00.bin', 0x100),
               ('rwts-a', 0xb800, 0x800, 'assets/raw/a/system/track-00.bin', 0x200),
               ('rwts-b', 0xb800, 0x800, 'assets/raw/b/system/track-00.bin', 0x200)]
    for name, address, length, asset, offset in modules:
        subprocess.run(['ca65', str(ROOT / f'src/{name}.s'), '-o', str(out / f'{name}.o'),
                        '-l', str(out / f'{name}.lst')], check=True)
        subprocess.run(['ld65', '-C', str(ROOT / f'src/{name}.cfg'), str(out / f'{name}.o'),
                        '-o', str(out / f'{name}.bin'), '-m', str(out / f'{name}.map'),
                        '-Ln', str(out / f'{name}.lbl')], check=True)
        code = (out / f'{name}.bin').read_bytes()
        if len(code) != length:
            raise ValueError(f'{name}: output must occupy its original {length}-byte region')
        native = (ROOT / asset).read_bytes()
        current = replacements.get(asset, native)
        replacements[asset] = current[:offset] + code + current[offset + length:]
        assembled.append({'source': f'src/{name}.s', 'load_address': address, 'size': len(code),
                          'sha256': hashlib.sha256(code).hexdigest(), 'asset': asset, 'offset': offset,
                          'original_encoding_equal': code == native[offset:offset + length]})
    repack(ROOT / 'assets/raw/manifest.json', out, replacements)
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())
    dependencies = [{'side': disk['side'], 'path': region['path'], 'role': region['role']}
                    for disk in manifest['disks'] for region in disk['regions']
                    if region['role'].startswith('temporary') and region['path'] != 'assets/raw/a/files/adven-interp-obj.bin']
    (out / 'build.json').write_text(json.dumps({'status': 'early partial source build',
        'assembled': assembled,
        'temporary_raw_code_dependencies': dependencies}, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
