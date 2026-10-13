#!/usr/bin/env python3
"""Verify the observed native raw-sector save footprint on isolated media."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('blank', type=Path)
    p.add_argument('original_session', type=Path)
    p.add_argument('rebuilt_session', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    blank = args.blank.read_bytes()
    images = [(session / 'save.dsk').read_bytes() for session in (args.original_session, args.rebuilt_session)]
    if len(blank) != 143360 or any(len(image) != len(blank) for image in images):
        raise ValueError('expected DOS-order 35-track, 16-sector images')
    expected = [(track, sector) for track in range(23, 32) for sector in range(16)]
    reports = []
    for session, image in zip((args.original_session, args.rebuilt_session), images):
        changed = [(offset//4096, (offset%4096)//256) for offset in range(0, len(blank), 256)
                   if image[offset:offset+256] != blank[offset:offset+256]]
        reports.append({'session': str(session), 'sha256': hashlib.sha256(image).hexdigest(),
                        'changed_sectors': changed, 'pass': changed == expected})
    report = {'scope': 'raw save footprint, supplements room/object restore checks',
              'blank_sha256': hashlib.sha256(blank).hexdigest(), 'images': reports,
              'original_rebuilt_equal': images[0] == images[1],
              'pass': all(item['pass'] for item in reports) and images[0] == images[1]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'pass': report['pass'], 'changed_sectors': [len(item['changed_sectors']) for item in reports]}))
    return not report['pass']


if __name__ == '__main__':
    sys.exit(main())
