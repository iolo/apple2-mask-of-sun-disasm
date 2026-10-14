#!/usr/bin/env python3
"""Boot DOS and validate streaming loads from synthetic files on copied media."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from catalog import ROOT, digest, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rompath',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True,help='new directory')
    p.add_argument('--evidence',type=Path,default=ROOT/'docs/evidence/korean/loader-probe.json')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    fixture=out/'fixture';session=out/'session'
    subprocess.run([sys.executable,str(ROOT/'tools/korean/build_loader_probe.py'),'--output',str(fixture)],check=True)
    launch=[sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(args.rompath.resolve()),
            '--disk-a',str(fixture/'synthetic-a.dsk'),'--disk-b',str(ROOT/'build/korean/english-baseline/mask-of-sun-b.dsk'),
            '--output',str(session),'--headless','--fast','--debug','--language-card',
            '--script',str(ROOT/'tools/korean/loader_probe.lua')]
    with (out/'mame.log').open('w') as log:
        subprocess.run(launch,env=dict(os.environ,MASK_KOREAN_PROBE=str(fixture)),stdout=log,
                       stderr=subprocess.STDOUT,timeout=60,check=True)
    report=json.loads((session/'loader-probe.json').read_text())
    built=json.loads((fixture/'build.json').read_text())
    if not report['pass'] or len(report['cases'])!=len(built['cases']):
        raise ValueError('loader probe failed: '+json.dumps(report))
    report['build']=built;report['session']=json.loads((session/'session.json').read_text())
    report['scope']='Synthetic KOR2 reads after original DOS boot: real Disk II/RWTS, build/side rejection before payload writes, split main/LC loading, bounds, truncation, media error, cache validity and ASCII display. Not startup asset-disk integration, save/restore, gameplay timing or approved translations.'
    args.evidence.parent.mkdir(parents=True,exist_ok=True)
    screenshot=args.evidence.with_suffix('.png');shutil.copyfile(session/'snapshot_directory/loader-probe.png',screenshot)
    report['screenshot_sha256']=digest(screenshot.read_bytes());write_json(args.evidence,report)
    print('PASS: '+str(args.evidence))


if __name__=='__main__':main()
