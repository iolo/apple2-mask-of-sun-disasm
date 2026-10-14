#!/usr/bin/env python3
"""Verify DOS-only synthetic startup, media retry, opening input and no-LC stop."""
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
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT/'docs/evidence/korean/startup-probe.json')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    fixture=out/'fixture'
    subprocess.run([sys.executable,str(ROOT/'tools/korean/startup_disk.py'),'--output',str(fixture)],check=True)
    shutil.copyfile(ROOT/'build/korean/english-baseline/mask-of-sun-a.dsk',fixture/'wrong-english-a.dsk')
    reports=[]
    for no_lc in (False,True):
        session=out/('no-lc' if no_lc else 'lc')
        cmd=[sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(args.rompath.resolve()),
             '--disk-a',str(fixture/'synthetic-startup.dsk'),'--disk-b',str(fixture/'synthetic-a.dsk'),
             '--output',str(session),'--headless','--fast','--script',str(ROOT/'tools/korean/startup_probe.lua')]
        if not no_lc:cmd.append('--language-card')
        with (out/(session.name+'.log')).open('w') as log:
            subprocess.run(cmd,env=dict(os.environ,MASK_KOREAN_PROBE=str(fixture),MASK_KOREAN_NO_LC=str(int(no_lc))),
                           stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
        report=json.loads((session/'startup-probe.json').read_text())
        report['session']=json.loads((session/'session.json').read_text())
        if not report['pass']:raise ValueError('startup probe failed: '+json.dumps(report))
        reports.append(report)
    result={'pass':True,'build':json.loads((fixture/'startup-build.json').read_text()),'runs':reports,
            'scope':'Cold DOS boot from an extra 140K disk, 5200-byte font and 4096-byte resident LC transfer, synthetic Korean title glyph pixels, wrong English disk rejection/retry, five English commands through entering jeep, no-LC notice. No code/PC/world injection. Opening subset only; not final translation, A/B packing, save/restore, timed scenes or physical hardware.'}
    for name in ('startup-assets-loaded','startup-success'):
        dest=args.evidence.with_name(name+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(out/'lc/snapshot_directory'/(name+'.png'),dest)
        result[name+'_sha256']=digest(dest.read_bytes())
    write_json(args.evidence,result);print('PASS: '+str(args.evidence))


if __name__=='__main__':main()
