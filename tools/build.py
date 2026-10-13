#!/usr/bin/env python3
"""Early template-free rebuild: assembled renderer plus tracked raw regions.

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
    subprocess.run(['ca65', str(ROOT / 'src/renderer.s'), '-o', str(out / 'renderer.o'),
                    '-l', str(out / 'renderer.lst')], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'src/renderer.cfg'), str(out / 'renderer.o'),
                    '-o', str(out / 'renderer.bin'), '-m', str(out / 'renderer.map'),
                    '-Ln', str(out / 'renderer.lbl')], check=True)
    renderer = (out / 'renderer.bin').read_bytes()
    if len(renderer) != 0x100:
        raise ValueError('renderer output must fit its original 256-byte page')
    asset = 'assets/raw/a/files/char-gen.bin'
    native = (ROOT / asset).read_bytes()
    converted = native[:0x504] + renderer + native[0x604:]
    repack(ROOT / 'assets/raw/manifest.json', out, {asset: converted})
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())
    dependencies = [{'side': disk['side'], 'path': region['path'], 'role': region['role']}
                    for disk in manifest['disks'] for region in disk['regions']
                    if region['role'].startswith('temporary')]
    (out / 'build.json').write_text(json.dumps({'status': 'early partial source build',
        'assembled': [{'source': 'src/renderer.s', 'load_address': 0xb300, 'size': len(renderer),
                       'sha256': hashlib.sha256(renderer).hexdigest(), 'asset': asset, 'offset': 0x504}],
        'temporary_raw_code_dependencies': dependencies,
        'renderer_original_encoding_equal': renderer == native[0x504:0x604]}, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
