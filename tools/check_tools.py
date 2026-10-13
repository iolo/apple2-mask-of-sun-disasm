#!/usr/bin/env python3
"""Check build/analysis prerequisites, optionally audit locally supplied ROMs."""
import argparse
import json
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys

TOOLS = {'python3': '--version', 'a2kit': '--version', 'ca65': '--version',
         'ld65': '--version', 'cl65': '--version', 'da65': '--version',
         'mame': '-version', 'pdftotext': '-v', 'pdftoppm': '-v'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rompath', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--build-only', action='store_true', help='check only Python, Pillow and ca65/ld65')
    args = parser.parse_args()
    report = {'tools': {}, 'missing': []}
    for name, option in TOOLS.items():
        if args.build_only and name not in ('python3','ca65','ld65'):continue
        path = shutil.which(name)
        if not path:
            report['missing'].append(name)
            continue
        result = subprocess.run([path, option], capture_output=True, text=True, timeout=30)
        report['tools'][name] = {'path': path, 'version': (result.stdout + result.stderr).strip(),
                                 'exit_code': result.returncode}
        if result.returncode:
            report['missing'].append(name)
    try:
        report['pillow_version']=importlib.metadata.version('Pillow')
    except importlib.metadata.PackageNotFoundError:
        report['missing'].append('Pillow')
    if args.rompath:
        if not shutil.which('mame'):
            parser.error('MAME is required for ROM audit')
        result = subprocess.run(['mame', 'apple2p', '-noreadconfig', '-rompath',
                                 str(args.rompath.resolve()), '-verifyroms'],
                                capture_output=True, text=True, timeout=30)
        report['rom_audit'] = {'driver': 'apple2p', 'exit_code': result.returncode,
                               'output': result.stdout + result.stderr}
        if result.returncode:
            report['missing'].append('Apple II ROMs')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return bool(report['missing'])


if __name__ == '__main__':
    sys.exit(main())
