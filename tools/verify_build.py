#!/usr/bin/env python3
"""Build twice in fresh directories and audit that native code/disks are not read."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='new audit directory inside this checkout')
    args=parser.parse_args();out=args.output.resolve()
    if not shutil.which('strace'):parser.error('strace is required for the read-dependency audit')
    out.mkdir(parents=True,exist_ok=False)
    outputs=[]
    for number in (1,2):
        destination=out/f'build-{number}';command=[sys.executable,str(ROOT/'tools/build.py'),'--output',str(destination)]
        if number==1:command=['strace','-f','-e','trace=openat','-o',str(out/'reads.log')]+command
        with (out/f'build-{number}.log').open('w') as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        outputs.append(json.loads((destination/'build.json').read_text()))
    classification=json.loads((ROOT/'assets/classification.json').read_text())
    forbidden={(ROOT/r['path']).resolve() for r in classification['regions'] if r.get('reference_only')}
    forbidden.update((ROOT/f'mask-of-sun-{side}.dsk').resolve() for side in ('a','b'))
    violations=[]
    for line in (out/'reads.log').read_text().splitlines():
        match=re.search(r'openat\([^,]+, "([^"\n]+)", (O_RDONLY[^)]*)\)\s*=\s*(\d+)',line)
        if not match:continue
        name=Path(match[1]);path=(name if name.is_absolute() else ROOT/name).resolve()
        if path in forbidden:violations.append(str(path.relative_to(ROOT)))
    disks=[]
    for side in ('a','b'):
        filename=f'mask-of-sun-{side}.dsk'
        a,b=[(out/f'build-{n}'/filename).read_bytes() for n in (1,2)]
        disks.append({'side':side,'sha256':hashlib.sha256(a).hexdigest(),'size':len(a),
                      'repeatable':a==b and len(a)==143360})
    checks={'repeatable_disks':all(d['repeatable'] for d in disks),
            'no_original_or_native_code_picture_reads':not violations,
            'all_regions_classified':not classification['unclassified_regions'],
            'no_raw_code_dependency':all(not b['temporary_raw_code_dependencies'] for b in outputs)}
    report={'pass':all(checks.values()),'checks':checks,'disks':disks,'violations':violations,
            'forbidden_reference_count':len(forbidden),'method':'strace openat successful O_RDONLY opens plus two clean generated-output builds',
            'scope':'source/data build audit; gameplay and clean-checkout validation are separate'}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return not report['pass']


if __name__=='__main__':sys.exit(main())
