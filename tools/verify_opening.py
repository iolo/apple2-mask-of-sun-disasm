#!/usr/bin/env python3
"""Verify original opening behavior from a fresh-boot replay's recorded screens."""
import argparse
import json
from pathlib import Path
import sys

CHECKS = {
    'intro': 'Your search for the Mask of the Sun has',
    'initial-inventory': 'a loaded revolver',
    'unknown-command': 'I don\'t understand "FERNAP".',
    'missing-object': 'I don\'t recognize an object',
    'absent-object': 'You don\'t see a lantern',
    'missing-verb': 'I don\'t recognize a verb',
    'map-pickup': 'You pick up a cryptic map.',
    'food-for-flute': 'please take this flute.',
    'statue-inscription': 'translates it as "XOTZIL".',
    'head-pickup': 'The head of the idol feels strangely',
    'head-replacement': 'As soon as the head is replaced on the',
    'statue-transition': 'You are in a large clearing.',
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    checkpoints = []
    for path in sorted(args.session.glob('*-*.json')):
        record = json.loads(path.read_text())
        if 'graphics_text' not in record:
            continue
        checkpoints.append({'name': record['name'], 'time': record['time'],
                            'registers': record['registers'],
                            'lines': [line.rstrip() for line in record['graphics_text']
                                      if line.strip() and '?' not in line]})
    checks = []
    for name, expected in CHECKS.items():
        matching = [r['name'] for r in checkpoints if any(expected in s for s in r['lines'])]
        checks.append({'id': name, 'expected': expected, 'pass': bool(matching), 'checkpoints': matching})
    inputs = [json.loads(line) for line in (args.session / 'replay-inputs.jsonl').read_text().splitlines()]
    checks.append({'id': 'route-complete', 'pass': any(r['reason'] == 'ENTER JEEP' and r['command_index'] == 25 for r in inputs)
                   and bool(checkpoints) and checkpoints[-1]['name'].endswith('prompt-26')})
    report = {'scope': 'original opening, parser checks and statue puzzle only; full route and sound pending',
              'session': json.loads((args.session / 'session.json').read_text()),
              'checks': checks, 'inputs': inputs, 'checkpoints': checkpoints}
    report['pass'] = all(item['pass'] for item in checks)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'pass': report['pass'], 'checks': checks}, indent=2))
    return not report['pass']


if __name__ == '__main__':
    sys.exit(main())
