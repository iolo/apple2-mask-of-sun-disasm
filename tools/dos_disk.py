#!/usr/bin/env python3
"""Inspect DOS-order 35-track images; export non-overlapping disk regions.

Catalog sector counts are reported, never trusted for allocation. File ownership
comes from linked track/sector lists. Binary headers are decoded separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SECTOR_SIZE = 256
SECTORS = 16
TRACKS = 35
DISK_SIZE = SECTOR_SIZE * SECTORS * TRACKS


def sha(data):
    return hashlib.sha256(data).hexdigest()


def offset(track, sector):
    if not (0 <= track < TRACKS and 0 <= sector < SECTORS):
        raise ValueError(f'invalid track/sector {track}/{sector}')
    return (track * SECTORS + sector) * SECTOR_SIZE


class Disk:
    def __init__(self, data):
        if len(data) != DISK_SIZE:
            raise ValueError(f'expected {DISK_SIZE} bytes')
        self.data = data
        self.owners = {}

    def sector(self, track, sector):
        start = offset(track, sector)
        return self.data[start:start + SECTOR_SIZE]

    def claim(self, track, sector, owner):
        offset(track, sector)
        if (track, sector) in self.owners:
            raise ValueError(f'sector {track}/{sector} owned twice: {owner}, {self.owners[track, sector]}')
        self.owners[track, sector] = owner

    def catalog(self):
        vtoc = self.sector(17, 0)
        if vtoc[0x34:0x38] != bytes([35, 16, 0, 1]):
            raise ValueError('DOS VTOC geometry mismatch; sector order not established')
        self.claim(17, 0, 'vtoc')
        track, sector = vtoc[1:3]
        files, catalogs = [], []
        while track:
            self.claim(track, sector, 'catalog')
            catalogs.append((track, sector))
            content = self.sector(track, sector)
            for position in range(11, 256, 35):
                entry = content[position:position + 35]
                if entry[0] in (0, 255):
                    continue
                name = bytes(c & 127 for c in entry[3:33]).decode('ascii').rstrip()
                lists, sectors = [], []
                ts_track, ts_sector = entry[:2]
                expected_index = 0
                while ts_track:
                    self.claim(ts_track, ts_sector, 'ts-list:' + name)
                    lists.append((ts_track, ts_sector))
                    ts = self.sector(ts_track, ts_sector)
                    index = int.from_bytes(ts[5:7], 'little')
                    if index != expected_index:
                        raise ValueError(f'{name}: non-contiguous TS index {index}/{expected_index}')
                    for i in range(12, 256, 2):
                        pair = tuple(ts[i:i + 2])
                        if pair == (0, 0):
                            continue
                        self.claim(*pair, 'file:' + name)
                        sectors.append(pair)
                    expected_index += 122
                    ts_track, ts_sector = ts[1:3]
                raw = b''.join(self.sector(*pair) for pair in sectors)
                item = {'name': name, 'type': entry[2] & 127, 'locked': bool(entry[2] & 128),
                        'catalog': {'track': track, 'sector': sector, 'offset': position},
                        'catalog_sector_count': int.from_bytes(entry[33:35], 'little'),
                        'actual_sector_count': len(sectors) + len(lists),
                        'ts_lists': lists, 'sectors': sectors, 'allocated_bytes': len(raw),
                        'sha256': sha(raw)}
                if item['type'] == 4:
                    item['binary_header'] = {'load_address': int.from_bytes(raw[:2], 'little'),
                                             'length': int.from_bytes(raw[2:4], 'little'),
                                             'fits_allocation': int.from_bytes(raw[2:4], 'little') <= len(raw) - 4}
                files.append(item)
            track, sector = content[1:3]
        return {'volume': vtoc[6], 'dos_release': vtoc[3], 'catalog_sectors': catalogs, 'files': files}


def export(destination):
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'sector_order': 'DOS logical sectors in file order',
                'geometry': {'tracks': TRACKS, 'sectors': SECTORS, 'sector_size': SECTOR_SIZE}, 'disks': []}
    for side in ('a', 'b'):
        source = ROOT / f'mask-of-sun-{side}.dsk'
        disk = Disk(source.read_bytes())
        catalog = disk.catalog()
        sectors, regions = [], []

        def region(relative, pairs, role, note):
            path = destination / side / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            content = b''.join(disk.sector(*pair) for pair in pairs)
            path.write_bytes(content)
            asset_path = str(path.relative_to(ROOT))
            regions.append({'path': asset_path, 'length': len(content), 'sha256': sha(content),
                            'role': role, 'note': note})
            for i, (track, sector) in enumerate(pairs):
                sectors.append({'track': track, 'sector': sector, 'disk_offset': offset(track, sector),
                                'path': asset_path, 'region_offset': i * SECTOR_SIZE,
                                'length': SECTOR_SIZE, 'owner': disk.owners.get((track, sector), role)})
            return asset_path

        for file in catalog['files']:
            slug = re.sub(r'[^a-z0-9]+', '-', file['name'].lower()).strip('-')
            if file['type'] == 0:
                role = 'startup-text' if file['name'] == 'START' else 'interpreted-script'
            elif file['name'] in ('ADVEN INTERP.OBJ', 'INTRIN.OBJ'):
                role = 'temporary-raw-game-code'
            elif file['name'] == 'CHAR GEN':
                role = 'temporary-mixed-renderer-font-data'
            elif file['name'] == 'PARMS.OBJ':
                role = 'engine-parameters'
            else:
                role = 'binary-asset-pending-format-analysis'
            file['path'] = region(f'files/{slug}.bin', file['sectors'], role,
                                  'Full allocated file stream, including binary header and trailing sector bytes.')
            region(f'metadata/{slug}-ts.bin', file['ts_lists'], 'dos-ts-list',
                   f"Track/sector chain for {file['name']}; catalog count is not an allocation limit.")
        region('metadata/vtoc.bin', [(17, 0)], 'dos-vtoc', 'DOS volume/allocation metadata.')
        region('metadata/catalog.bin', catalog['catalog_sectors'], 'dos-catalog', 'Complete linked catalog sectors.')
        for track in range(TRACKS):
            pairs = [(track, sector) for sector in range(SECTORS) if (track, sector) not in disk.owners]
            if pairs:
                role = 'temporary-raw-boot-dos-code' if track < 3 else 'unowned-pending-analysis'
                region(f'system/track-{track:02d}.bin', pairs, role,
                       'Not referenced by live DOS files; classification requires boot traces and allocation review.')
        sectors.sort(key=lambda entry: entry['disk_offset'])
        if len(sectors) != TRACKS * SECTORS or [s['disk_offset'] for s in sectors] != list(range(0, DISK_SIZE, SECTOR_SIZE)):
            raise ValueError('incomplete or overlapping sector exports')
        manifest['disks'].append({'side': side, 'source': source.name, 'sha256': sha(disk.data),
                                 **catalog, 'regions': regions, 'sectors': sectors})
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def repack(manifest_path, output):
    manifest = json.loads(manifest_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    for disk in manifest['disks']:
        data, covered, cache = bytearray(DISK_SIZE), set(), {}
        for region in disk['regions']:
            content = (ROOT / region['path']).read_bytes()
            if len(content) != region['length'] or sha(content) != region['sha256']:
                raise ValueError(f"export changed: {region['path']}")
            cache[region['path']] = content
        used = {path: set() for path in cache}
        for entry in disk['sectors']:
            start = offset(entry['track'], entry['sector'])
            if start in covered or start != entry['disk_offset'] or entry['length'] != SECTOR_SIZE:
                raise ValueError('invalid or overlapping disk mapping')
            covered.add(start)
            chunk = cache[entry['path']][entry['region_offset']:entry['region_offset'] + SECTOR_SIZE]
            if len(chunk) != SECTOR_SIZE or entry['region_offset'] in used[entry['path']]:
                raise ValueError('invalid or reused region slice')
            used[entry['path']].add(entry['region_offset'])
            data[start:start + SECTOR_SIZE] = chunk
        if len(covered) != TRACKS * SECTORS or any(len(used[path])*SECTOR_SIZE != len(content) for path,content in cache.items()):
            raise ValueError('disk or region coverage is incomplete')
        digest = sha(data)
        if digest != disk['sha256']:
            raise ValueError('raw export/repack hash mismatch')
        path = output / f"mask-of-sun-{disk['side']}.dsk"
        path.write_bytes(data)
        reports.append({'path': str(path.relative_to(ROOT)), 'size': len(data), 'sha256': digest})
    (output / 'repack.json').write_text(json.dumps({'purpose': 'raw extraction integrity, not final rebuild',
                                                  'disks': reports}, indent=2) + '\n')
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='operation', required=True)
    e = sub.add_parser('export'); e.add_argument('--output', type=Path, default=ROOT / 'assets/raw')
    r = sub.add_parser('repack'); r.add_argument('--manifest', type=Path, default=ROOT / 'assets/raw/manifest.json')
    r.add_argument('--output', type=Path, default=ROOT / 'build/raw-repack')
    args = p.parse_args()
    try:
        if args.operation == 'export':
            result = export(args.output.resolve())
            print('Exported ' + ', '.join(f"side {d['side']}: {len(d['files'])} files, {len(d['sectors'])} sectors" for d in result['disks']))
        else:
            repack(args.manifest, args.output.resolve())
    except (OSError, ValueError) as error:
        sys.exit(str(error))
