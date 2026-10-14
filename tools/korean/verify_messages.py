#!/usr/bin/env python3
"""Run synthetic message reader on an owned Apple II+ + LC MAME session."""
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
    p.add_argument('--evidence',type=Path,default=ROOT/'docs/evidence/korean/message-probe.json')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    fixture=out/'fixture';session=out/'session'
    subprocess.run([sys.executable,str(ROOT/'tools/korean/build_message_probe.py'),'--output',str(fixture)],check=True)
    launch=[sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(args.rompath.resolve()),
            '--disk-a',str(ROOT/'build/korean/english-baseline/mask-of-sun-a.dsk'),
            '--disk-b',str(ROOT/'build/korean/english-baseline/mask-of-sun-b.dsk'),
            '--output',str(session),'--headless','--fast','--debug','--language-card',
            '--script',str(ROOT/'tools/korean/message_probe.lua')]
    with (out/'mame.log').open('w') as log:
        subprocess.run(launch,env=dict(os.environ,MASK_KOREAN_PROBE=str(fixture)),stdout=log,
                       stderr=subprocess.STDOUT,timeout=60,check=True)
    report=json.loads((session/'message-probe.json').read_text())
    if not report['pass']:
        raise ValueError('message probe failed: '+json.dumps(report))
    report['build']=json.loads((fixture/'build.json').read_text())
    report['session']=json.loads((session/'session.json').read_text())
    report['scope']='Synthetic runtime at $9400 and conditional Korean interpreter: message pool access, bounds checks, mixed text rendering, native error entry points with invalid room cache, ROM/I-flag restoration. Not disk loading, game timing, save/restore or approved translation integration.'
    args.evidence.parent.mkdir(parents=True,exist_ok=True)
    screenshot=args.evidence.with_suffix('.png')
    shutil.copyfile(session/'snapshot_directory/message-probe.png',screenshot)
    report['screenshot_sha256']=digest(screenshot.read_bytes())
    write_json(args.evidence,report)
    print('PASS: '+str(args.evidence))


if __name__=='__main__':main()
