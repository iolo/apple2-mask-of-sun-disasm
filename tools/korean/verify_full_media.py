#!/usr/bin/env python3
"""Cold startup plus actual Disk II reads of every complete synthetic A/B resource."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from catalog import ROOT, digest, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rompath',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT/'docs/evidence/korean/full-media-probe.json')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    fixture=out/'fixture';session=out/'session'
    subprocess.run([sys.executable,str(ROOT/'tools/korean/build_full_media_probe.py'),'--output',str(fixture)],check=True)
    built=json.loads((fixture/'build.json').read_text())
    cmd=[sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(args.rompath.resolve()),
         '--disk-a',str(fixture/'media/synthetic-startup.dsk'),'--disk-b',str(fixture/'media/synthetic-a.dsk'),
         '--output',str(session),'--headless','--fast','--debug','--language-card',
         '--script',str(ROOT/'tools/korean/full_media_probe.lua')]
    with (out/'mame.log').open('w') as log:
        subprocess.run(cmd,env=dict(os.environ,MASK_KOREAN_FULL_MEDIA=str(fixture)),stdout=log,
                       stderr=subprocess.STDOUT,timeout=300,check=True)
    report=json.loads((session/'full-media-probe.json').read_text())
    assert report['pass'] and len(report['cases'])==86,report
    assert [r['side'] for r in report['mounts']]==['a','b'],report['mounts']
    assert digest((fixture/'reader-b.dsk').read_bytes())==built['synthetic_b_sha256']
    assert digest((session/'side-b.dsk').read_bytes())==built['build']['game_a']['sha256']
    assert digest((session/'side-a.dsk').read_bytes())==built['build']['extra']['sha256']
    report.update(build=built,session=json.loads((session/'session.json').read_text()),
                  scope='Complete synthetic draft-shaped A/B media. All 86 resources read through real Disk II/RWTS, script/LC bytes and untouched regions compared, native retained files audited. Bootstrap is cold; reader harness and side flag are injected at a debugger instruction boundary. This is not game-route, B-side restore, translated UI or approval validation.',
                  source_sha256={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
                                 [Path(__file__).resolve()]+[ROOT/'tools/korean'/n for n in ['synthetic.py','startup_disk.py','build_full_media_probe.py','full_media_probe.lua']]})
    write_json(args.evidence,report)
    print('PASS: '+str(args.evidence))


if __name__=='__main__':main()
