#!/usr/bin/env python3
"""Verify ordered replay inputs, ending prompt and semantic route requirements."""
import argparse
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session', type=Path)
    p.add_argument('route', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    route = json.loads(args.route.read_text())
    inputs = [json.loads(line) for line in (args.session / 'replay-inputs.jsonl').read_text().splitlines()]
    checkpoints = []
    for path in sorted(args.session.glob('*-*.json')):
        record = json.loads(path.read_text())
        if 'graphics_text' in record:
            checkpoints.append({'name': record['name'], 'time': record['time'], 'registers': record['registers'],
                                'lines': [line.rstrip() for line in record['graphics_text'] if line.strip() and '?' not in line]})
    expected = [command['command'] if isinstance(command, dict) else command for command in route['commands']]
    actual = [entry['reason'] for entry in inputs if entry['reason'] != 'pagination']
    checks = [{'id': 'ordered-command-sequence', 'pass': actual == expected},
              {'id': 'final-prompt', 'pass': bool(checkpoints) and checkpoints[-1]['name'].endswith(f'prompt-{len(expected)+1:02d}')},
              {'id': 'no-death', 'pass': not any('RESTORE GAME at this point' in line or 'You are dead.' in line
                                               for entry in checkpoints for line in entry['lines'])}]
    for requirement in route.get('requirements', []):
        matching = [entry['name'] for entry in checkpoints if any(requirement['text'] in line for line in entry['lines'])]
        checks.append({'id': requirement['id'], 'pass': bool(matching), 'expected': requirement['text'], 'checkpoints': matching})
    report = {'scope': route['scope'], 'session': json.loads((args.session / 'session.json').read_text()),
              'checks': checks, 'pass': all(check['pass'] for check in checks), 'inputs': inputs, 'checkpoints': checkpoints}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'pass': report['pass'], 'checks': checks}, indent=2))
    return not report['pass']


if __name__ == '__main__':
    sys.exit(main())
