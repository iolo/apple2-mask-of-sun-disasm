#!/usr/bin/env python3
"""Compare all native picture fixtures and optionally publish generated previews."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('converted', type=Path)
    parser.add_argument('--publish', action='store_true', help='refresh generated companion PNGs')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = json.loads((args.reference / 'pictures.json').read_text())['jobs']
    after = json.loads((args.converted / 'pictures.json').read_text())['jobs']
    if [(j['id'],j['svg']) for j in before] != [(j['id'],j['svg']) for j in after]:
        raise ValueError('fixture order or mapping differs')
    pictures = []
    for job in after:
        picture = {'svg':job['svg'], 'id':job['id'], 'name':job['name'], 'checks':{}}
        for page in ('hgr1','hgr2'):
            a = (args.reference / f'{job["id"]}-{page}.bin').read_bytes()
            b = (args.converted / f'{job["id"]}-{page}.bin').read_bytes()
            picture['checks'][page] = a == b and len(a) == 8192
            picture[page+'_sha256'] = hashlib.sha256(b).hexdigest()
        picture['pass'] = all(picture['checks'].values())
        pictures.append(picture)
    report = {'scope':'257 standalone native record fixtures on white canvases; gameplay checked separately',
              'reference_session':str(args.reference), 'converted_session':str(args.converted),
              'pass':bool(pictures) and all(p['pass'] for p in pictures), 'pictures':pictures}
    if args.publish:
        if not report['pass']:
            raise ValueError('refusing to publish previews with mismatches')
        for job in after:
            source = args.converted / 'snapshot_directory' / f'{job["id"]}.png'
            destination = ROOT / 'assets/decoded/pictures' / Path(job['svg']).with_suffix('.png')
            shutil.copyfile(source,destination)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'pass':report['pass'],'pictures':len(pictures),'failed':[p['id'] for p in pictures if not p['pass']]}))
    return not report['pass']


if __name__ == '__main__':
    sys.exit(main())
