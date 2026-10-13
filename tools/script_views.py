#!/usr/bin/env python3
"""Generate readable ULTRA script views and line provenance from native assets."""
import argparse
import json
from pathlib import Path
import re
from dos_disk import ROOT


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'build/views')
    args = p.parse_args()
    output = args.output.resolve()
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())
    records = []
    for disk in manifest['disks']:
        for file in disk['files']:
            if file['type'] != 0:
                continue
            native = (ROOT / file['path']).read_bytes()
            # DOS text stops at the first zero. Preserve high-bit controls in
            # the native authority, and record byte ranges for every view line.
            end = native.find(b'\0')
            if end < 0:
                end = len(native)
            content = native[:end]
            lines, cursor = [], 0
            for number, raw in enumerate(content.split(b'\x8d'), 1):
                text = bytes(c & 127 for c in raw).decode('ascii')
                lines.append({'id': f"{disk['side']}:{file['name']}:{number:04d}",
                              'file_offset': cursor, 'length': len(raw), 'text': text})
                cursor += len(raw) + 1
            target = output / disk['side'] / (Path(file['path']).stem + '.txt')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('\n'.join(line['text'] for line in lines))
            text = '\n'.join(line['text'] for line in lines)
            records.append({'side': disk['side'], 'name': file['name'], 'native': file['path'],
                            'encoding': 'high-bit ASCII; $8D line separator, first $00 EOF',
                            'view': str(target.relative_to(ROOT)), 'content_bytes': len(content),
                            'room_assignments': re.findall(r'^\.S N=(\d+)$', text, re.M),
                            'named_room_references': sorted(set(re.findall(r'ROOM [0-9]+\.[0-9]+', text))),
                            'lines': lines})
    output.mkdir(parents=True, exist_ok=True)
    (output / 'scripts.json').write_text(json.dumps({'status': 'decoded views; native scripts remain authoritative',
                                                    'scripts': records}, indent=2) + '\n')
    print(f'Generated {len(records)} readable script views and line provenance')


if __name__ == '__main__':
    main()
