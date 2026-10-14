#!/usr/bin/env python3
"""Measure original allocation and a clearly labeled message-reference scenario."""
import argparse
import json
import math
from pathlib import Path

from catalog import ROOT, digest, write_json


def measure():
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())
    extraction = json.loads((ROOT / 'docs/korean/extraction.json').read_text())
    by_path = {f['path']: f for f in extraction['files']}
    report = {'schema_version': 1, 'scenario': 'Five ASCII bytes per message reference, e.g. ~0001; '
              'retain original control lines. Not a final encoding or proof that Korean fits.',
              'translation_capacity_proven': False, 'disks': [],
              'extra_disk': {'gross_bytes': 143360, 'usable_bytes': None,
                             'note': 'Boot/catalog/TS allocation pending concrete packing.'}}
    for disk in manifest['disks']:
        vtoc = (ROOT / f"assets/raw/{disk['side']}/metadata/vtoc.bin").read_bytes()
        free = sum(int.from_bytes(vtoc[0x38 + 4 * t:0x3c + 4 * t], 'big').bit_count() for t in range(35))
        files = []
        for file in disk['files']:
            if file['path'] not in by_path:
                continue
            f = by_path[file['path']]
            hypothetical = f['content_bytes'] + sum(5 - span['length'] for span in f['spans'])
            files.append({'name': f['name'], 'path': f['path'], 'sha256': f['sha256'],
                          'allocated_bytes': f['allocated_bytes'], 'used_bytes': f['content_bytes'],
                          'padding_bytes': f['allocated_bytes'] - f['content_bytes'],
                          'literal_bytes': sum(s['length'] for s in f['spans']),
                          'literal_count': len(f['spans']),
                          'reference_scenario_used_bytes': hypothetical,
                          'reference_scenario_allocated_bytes': math.ceil(hypothetical / 256) * 256})
        report['disks'].append({'side': disk['side'], 'original_vtoc_free_sectors': free,
            'file_data_sectors': sum(len(f['sectors']) for f in disk['files']),
            'ts_list_sectors': sum(len(f['ts_lists']) for f in disk['files']),
            'catalog_sectors': len(disk['catalog_sectors']), 'files': files,
            'reference_scenario_reclaimable_bytes': sum(f['allocated_bytes'] - f['reference_scenario_allocated_bytes'] for f in files)})
    inputs = [ROOT / 'assets/raw/manifest.json', ROOT / 'docs/korean/extraction.json']
    report['inputs'] = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in inputs}
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/korean/capacity.json')
    args = p.parse_args()
    report = measure()
    write_json(args.output, report)
    print(json.dumps([{k: v for k, v in d.items() if k != 'files'} for d in report['disks']], indent=2))


if __name__ == '__main__':
    main()
