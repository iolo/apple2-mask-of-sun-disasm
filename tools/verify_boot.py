#!/usr/bin/env python3
"""Verify native boot entry order, sector loading and initial payload placement."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def report(session):
    records = [json.loads(line) for line in (session / 'boot-entries.jsonl').read_text().splitlines()]
    first = {}
    for entry in records:
        first.setdefault(entry['address'], entry['time'])
    expected_entries = [0xc600, 0xc65c, 0x0801, 0xb700, 0xbd00, 0xa000, 0x0800, 0xb300, 0x0d00, 0xb317]
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())['disks'][0]
    def sector(track, number):
        entry = next(entry for entry in manifest['sectors'] if (entry['track'], entry['sector']) == (track, number))
        data = (ROOT / entry['path']).read_bytes()
        return data[entry['region_offset']:entry['region_offset']+256]
    loaded = (session / 'entry-b700-ram.bin').read_bytes()
    first_stage = all(loaded[0xb600+number*256:0xb700+number*256] == sector(0, number) for number in range(10))
    transfers = [entry['iob'] for entry in records if entry.get('iob', {}).get('address') == 0xb7e8][:27]
    expected_sectors = [(2, number) for number in range(4, -1, -1)]
    expected_sectors += [(1, number) for number in range(15, -1, -1)]
    expected_sectors += [(0, number) for number in range(15, 9, -1)]
    second_stage = len(transfers) == 27 and all((entry['track'], entry['sector']) == pair
                         and entry['buffer'] == 0xb500-index*256 and entry['command'] == 1
                         for index, (entry, pair) in enumerate(zip(transfers, expected_sectors)))
    engine = (session / 'entry-0800-ram.bin').read_bytes()
    parms = (ROOT / 'assets/raw/a/files/parms-obj.bin').read_bytes()
    interpreter = (ROOT / 'assets/raw/a/files/adven-interp-obj.bin').read_bytes()
    renderer = (session / 'entry-b300-ram.bin').read_bytes()
    chargen = (ROOT / 'assets/raw/a/files/char-gen.bin').read_bytes()
    intrinsics = (ROOT / 'assets/raw/a/files/intrin-obj.bin').read_bytes()
    checks = {'ordered-boot-entries': list(first) == expected_entries,
              'ten-first-stage-pages': first_stage,
              'twenty-seven-dos-pages': second_stage,
              'interpreter-placement': engine[0x0800:0x0d00] == interpreter[4:0x504],
              'parameter-placement': engine[0x300:0x3f0] == parms[4:244],
              'intrinsic-placement': renderer[0xcfc:0xcfc+len(intrinsics)] == intrinsics,
              'chargen-placement': renderer[0xadfc:0xadfc+len(chargen)] == chargen}
    return {'session': json.loads((session / 'session.json').read_text()), 'checks': checks,
            'pass': all(checks.values()), 'first_entries': first, 'entries': records}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original', type=Path)
    p.add_argument('rebuilt', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    original, rebuilt = report(args.original), report(args.rebuilt)
    signatures = [[{key: entry[key] for key in ('address', 'time', 'boot_buffer', 'boot_sector', 'registers', 'iob')
                    if key in entry} for entry in item['entries']] for item in (original, rebuilt)]
    result = {'original': original, 'rebuilt': rebuilt, 'trace_agreement': signatures[0] == signatures[1],
              'pass': original['pass'] and rebuilt['pass'] and signatures[0] == signatures[1]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'pass': result['pass'], 'original': original['checks'], 'rebuilt': rebuilt['checks'],
                      'trace_agreement': result['trace_agreement']}, indent=2))
    return not result['pass']


if __name__ == '__main__':
    sys.exit(main())
