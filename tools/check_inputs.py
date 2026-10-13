#!/usr/bin/env python3
"""Verify supplied inputs against the recorded manifest; never update hashes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'docs/inputs.json').read_text())
    failures = []
    for entry in manifest['inputs']:
        path = ROOT / entry['path']
        if not path.is_file():
            failures.append(f"missing: {entry['path']}")
            continue
        data = path.read_bytes()
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            failures.append(f"changed: {entry['path']}")
    if failures:
        sys.exit('\n'.join(failures))
    print(f"Verified {len(manifest['inputs'])} unchanged supplied inputs")


if __name__ == '__main__':
    main()
