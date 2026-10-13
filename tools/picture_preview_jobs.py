#!/usr/bin/env python3
"""Prepare native picture rendering fixtures from reference streams or edited SVGs."""
import argparse
import json
from pathlib import Path
from picture_assets import ROOT, decode_records, encode_all


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', action='store_true', help='use native provenance exports instead of SVGs')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory = ROOT / 'assets/decoded/pictures'
    manifest = json.loads((directory / 'manifest.json').read_text())
    converted = {} if args.reference else encode_all(directory)
    jobs = []
    for collection in manifest['collections']:
        data = (ROOT / collection['asset']).read_bytes() if args.reference else converted[collection['asset']]
        records = decode_records(data)
        if len(records) != len(collection['pictures']):
            raise ValueError('record count changed')
        for path, record in zip(collection['pictures'], records, strict=True):
            start = record['native_offset']
            size = record['native_size'] - len(record['padding'])
            if size > 0xc00:
                raise ValueError('fixture record exceeds $9000-$9BFF scratch space')
            jobs.append({'id': f'picture-{len(jobs):03d}', 'svg': path,
                         'name': record['name'], 'bytes': list(data[start:start+size])})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'reference': args.reference, 'jobs': jobs}) + '\n')
    print(f'Prepared {len(jobs)} native rendering fixtures')


if __name__ == '__main__':
    main()
