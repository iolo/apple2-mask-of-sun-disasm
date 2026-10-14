#!/usr/bin/env python3
"""Build/run positive and absent-card MAME probes; fail on missing evidence."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from catalog import ROOT, digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rompath', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='new output directory')
    p.add_argument('--evidence', type=Path, default=ROOT/'docs/evidence/korean/lc-probe.json')
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    reports = []
    for has_lc in (True, False):
        name = 'lc' if has_lc else 'no-lc'
        fixture, session = out/name, out/(name+'-session')
        build = [sys.executable, str(ROOT/'tools/korean/build_lc_probe.py'), '--output', str(fixture)]
        if not has_lc:
            build.append('--without-lc')
        subprocess.run(build, check=True)
        launch = [sys.executable, str(ROOT/'tools/mame_session.py'), '--rompath', str(args.rompath.resolve()),
            '--disk-a', str(ROOT/'build/korean/english-baseline/mask-of-sun-a.dsk'),
            '--disk-b', str(ROOT/'build/korean/english-baseline/mask-of-sun-b.dsk'),
            '--output', str(session), '--headless', '--fast', '--debug',
            '--script', str(ROOT/'tools/korean/lc_probe.lua')]
        if has_lc:
            launch.append('--language-card')
        env = dict(os.environ, MASK_KOREAN_PROBE=str(fixture))
        with (out/(name+'.log')).open('w') as log:
            subprocess.run(launch, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
        report = json.loads((session/'lc-probe.json').read_text())
        if report['expect_lc'] != has_lc or not report['pass']:
            raise ValueError('failed LC probe: ' + name)
        report['build'] = json.loads((fixture/'build.json').read_text())
        report['session'] = json.loads((session/'session.json').read_text())
        if has_lc:
            image = args.evidence.parent/'lc-probe.png'
            image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(session/'snapshot_directory/lc-probe.png', image)
            report['screenshot_sha256'] = digest(image.read_bytes())
        reports.append(report)
    write_json(args.evidence, {'pass': True, 'scope': 'Synthetic fixture only: bank isolation, detect byte '
        'preservation, bank/common boundary, HGR1/HGR2 and inverse byte checks, ROM return, absent LC. '
        'Not final runtime placement, game loading, save/restore or timing validation.', 'cases': reports})
    print('PASS: both LC profiles; evidence ' + str(args.evidence))


if __name__ == '__main__':
    main()
