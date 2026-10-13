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
    for path in sorted(args.session.glob('*.json')):
        record = json.loads(path.read_text())
        if 'graphics_text' in record:
            checkpoints.append({'name': record['name'], 'time': record['time'], 'registers': record['registers'],
                                'lines': [line.rstrip() for line in record['graphics_text'] if line.strip() and '?' not in line]})
    expected = [command['command'] if isinstance(command, dict) else command for command in route['commands']]
    actual = [entry['reason'] for entry in inputs if 'reason' in entry and entry['reason'] != 'pagination']
    output_characters = []
    if (args.session / 'output-characters.jsonl').exists():
        output_characters = [json.loads(line) for line in (args.session / 'output-characters.jsonl').read_text().splitlines()]
    output_text = ''.join(chr(entry['value'] & 127) for entry in output_characters)
    final_ready = bool(checkpoints) and checkpoints[-1]['name'].endswith(f'prompt-{len(expected)+1:02d}')
    if route.get('ending_text'):
        final_ready = any(route['ending_text'] in line for checkpoint in checkpoints for line in checkpoint['lines'])
    checks = [{'id': 'ordered-command-sequence', 'pass': actual == expected},
              {'id': 'ending-observed' if route.get('ending_text') else 'final-prompt', 'pass': final_ready},
              {'id': 'no-death', 'pass': not any('RESTORE GAME at this point' in line or 'You are dead.' in line
                                               for entry in checkpoints for line in entry['lines'])
                and 'You are dead.' not in output_text}]
    if route.get('required_sides'):
        sides = {'a'} | {entry['side'] for entry in inputs if entry.get('kind') == 'mount'}
        checks.append({'id': 'required-disk-sides', 'pass': set(route['required_sides']) <= sides,
                       'observed': sorted(sides)})
    for requirement in route.get('requirements', []):
        matching = [entry['name'] for entry in checkpoints if any(requirement['text'] in line for line in entry['lines'])]
        streamed = requirement['text'] in output_text
        checks.append({'id': requirement['id'], 'pass': bool(matching) or streamed, 'expected': requirement['text'],
                       'checkpoints': matching, 'output_stream': streamed})
    report = {'scope': route['scope'], 'session': json.loads((args.session / 'session.json').read_text()),
              'checks': checks, 'pass': all(check['pass'] for check in checks), 'inputs': inputs, 'checkpoints': checkpoints,
              'output_character_count': len(output_characters), 'output_text': output_text}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'pass': report['pass'], 'checks': checks}, indent=2))
    return not report['pass']


if __name__ == '__main__':
    sys.exit(main())
