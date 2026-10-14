#!/usr/bin/env python3
"""Allocate the complete three-disk candidate using sizes, never draft text.

Uses the real DOS allocator with zero-filled file bodies in memory. No disk
image is written: this proves sector capacity, not a runnable Korean build.
"""
import argparse
import json
from pathlib import Path

from catalog import ROOT, digest, write_json
from startup_disk import Disk, dos_disk
from dos_disk import offset


def verify_allocation(image, allocation):
    disk = Disk(image)
    catalog = disk.catalog()
    vtoc = disk.sector(17, 0)
    free = {(t, s) for t in range(35) for s in range(16)
            if int.from_bytes(vtoc[0x38+4*t:0x3a+4*t], 'big') & (1 << s)}
    assert not free.intersection(disk.owners), 'VTOC marks owned sectors free'
    assert len(free) == allocation['free_sectors'], 'VTOC free count mismatch'
    assert all(f['catalog_sector_count'] == f['actual_sector_count'] for f in catalog['files'])


def measure(encoding_dir, startup_dir, baseline):
    encoding = json.loads((encoding_dir / 'encoding.json').read_text())
    startup = json.loads((startup_dir / 'startup-build.json').read_text())
    catalog = json.loads((ROOT / 'assets/korean/messages.json').read_text())
    if encoding['catalog_sha256'] != digest(json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode()):
        raise ValueError('stale draft size report')
    for path, expected in startup['source_hashes'].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise ValueError('stale startup build: ' + path)
    packages = {(f['side'], f['name']): f for f in encoding['files']}
    result = []
    for side in ('a', 'b'):
        seed = (baseline / f'mask-of-sun-{side}.dsk').read_bytes()
        original = Disk(seed).catalog()
        vtoc = seed[offset(17, 0):offset(17, 0) + 256]
        reusable = {(t, s) for t in range(35) for s in range(16)
                    if int.from_bytes(vtoc[0x38+4*t:0x3a+4*t], 'big') & (1 << s)}
        for f in original['files']:
            reusable.update(tuple(pair) for pair in f['sectors'] + f['ts_lists'])
        files, authorities = [], []
        for f in original['files']:
            key = side, f['name']
            if key in packages:
                p = packages[key]
                data = (encoding_dir / p['package']).read_bytes()
                assert digest(data) == p['sha256'] and len(data) == p['package_bytes']
                assert p['script_fits'] and p['pool_bytes'] <= 1024
                size, authority = len(data), 'draft package size only'
            elif f['name'] in ('ADVEN INTERP.OBJ', 'INTRIN.OBJ'):
                module = 'interpreter' if f['name'] == 'ADVEN INTERP.OBJ' else 'intrinsics'
                size = len((startup_dir / (module + '.bin')).read_bytes())
                authority = 'assembled conditional Korean module size'
            else:
                size, authority = f['allocated_bytes'], 'preserved original allocation'
            # In-memory zero bodies exercise catalog/TS/VTOC allocation and
            # readback without constructing an image containing draft messages.
            files.append((f['name'], f['type'], bytes(size)))
            authorities.append({'name': f['name'], 'bytes': size, 'authority': authority})
        image, allocation = dos_disk(seed, files, reusable_sectors=reusable)
        verify_allocation(image, allocation)
        for record in allocation['files']:
            record.pop('sha256')  # hashes of zero bodies are not game assets
        allocation.pop('sha256')
        allocation.update(side=side, size_authorities=authorities,
                          source_disk_sha256=digest(seed),
                          reusable_sectors=len(reusable),
                          reused_early_track_sectors=sorted(pair for pair in reusable if pair[0]<3))
        result.append(allocation)
    # Startup has its own catalog, boot, code, font and resident assets. INITIAL
    # and LIBRARY are duplicated there; check their complete draft sizes too.
    seed = (baseline / 'mask-of-sun-a.dsk').read_bytes()
    extra = []
    for f in startup['extra']['files']:
        size = f['bytes']
        if ('a', f['name']) in packages:
            size = packages['a', f['name']]['package_bytes']
        elif f['name'] == 'KO.FONT':
            size = 16 + encoding['font_bytes']
        elif f['name'] == 'KO.TEXT':
            size = 16 + encoding['resident_budget']  # full 4KB padded transfer
        extra.append((f['name'], f['type'], bytes(size)))
    image, allocation = dos_disk(seed, extra)
    verify_allocation(image, allocation)
    for record in allocation['files']:
        record.pop('sha256')
    allocation.pop('sha256')
    allocation['side'] = 'extra'
    result.append(allocation)
    return {'kind': 'complete A/B/extra DOS allocation with zero-filled in-memory bodies',
            'catalog_sha256': encoding['catalog_sha256'],
            'encoding_report_sha256': digest((encoding_dir / 'encoding.json').read_bytes()),
            'startup_report_sha256': digest((startup_dir / 'startup-build.json').read_bytes()),
            'tool_sha256': digest(Path(__file__).read_bytes()),
            'allocator_sha256': digest((ROOT/'tools/korean/startup_disk.py').read_bytes()),
            'fits': True, 'disk_bytes_each': 143360, 'disks': result,
            'scope': 'All original A/B files, draft script/pool byte counts, conditional native module sizes, startup bootstrap/assets and their duplicated resources. Real allocator validates catalog, TS lists, VTOC and zero-body readback.',
            'limitations': ['No image written and no draft translation applied.',
                           'A/B reuse original file/TS/free sectors, including native B files in tracks 1/2; startup alone reserves complete DOS boot tracks.',
                           'Complete media contents, media identity, boot flow, B-side restore and gameplay remain to be integrated and tested.',
                           'Any later code/assets/translation growth requires a new capacity check.']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--encoding', type=Path, default=ROOT/'build/korean/draft-encoding')
    p.add_argument('--startup', type=Path, required=True, help='current startup fixture directory')
    p.add_argument('--baseline', type=Path, default=ROOT/'build/korean/english-baseline')
    p.add_argument('--output', type=Path, default=ROOT/'docs/evidence/korean/full-media-capacity.json')
    args = p.parse_args()
    report = measure(args.encoding, args.startup, args.baseline)
    write_json(args.output, report)
    print(json.dumps({'fits': report['fits'], 'free_sectors': {d['side']: d['free_sectors'] for d in report['disks']}}))
