#!/usr/bin/env python3
"""Verify the operator-stepped original route and its native checkpoint bridge.

This reads recordings only; it never chooses commands or controls an emulator.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('opening', type=Path)
    parser.add_argument('continuation', type=Path)
    parser.add_argument('--route', type=Path, default=Path('docs/full-route.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--publish', type=Path, help='archive logs and representative screenshots')
    args = parser.parse_args()
    route = json.loads(args.route.read_text())
    sessions = [args.opening, args.continuation]
    logs = [lines(path / 'manual-inputs.jsonl') for path in sessions]
    captures = {}
    for path in sessions:
        for file in path.glob('*.json'):
            record = json.loads(file.read_text())
            if 'graphics_text' in record:
                captures[(path, record['name'])] = record
    cutoff = captures[(args.opening, 'command032')]['time']
    # Next input is logged at the same paused timestamp as the prior capture.
    stop = next(i for i, entry in enumerate(logs[0])
                if entry['kind'] == 'capture' and entry['label'] == 'command032')
    selected = [logs[0][:stop + 1], logs[1]]
    events = [(path, entry) for path, entries in zip(sessions, selected) for entry in entries]
    actions = [(path, entry) for path, entry in events
               if entry['kind'] in ('input', 'physical-key') and entry['label'].startswith('command')]
    checks = []

    def check(name, passed, **detail):
        checks.append({'id': name, 'pass': bool(passed), **detail})

    expected = [item if isinstance(item, str) else item['command'] for item in route['commands']]
    labels = [entry['label'] for _, entry in actions]
    check('all-122-ordered-commands', labels == [f'command{i:03d}' for i in range(1, 123)])
    for index, (path, entry) in enumerate(actions, 1):
        if index > len(route['commands']):
            check('unexpected-command-input', False, label=entry['label'])
            continue
        command = route['commands'][index - 1]
        if isinstance(command, dict) and command.get('physical_key'):
            correct = entry['kind'] == 'physical-key' and entry['key'] == command['physical_key']
        else:
            raw = expected[index - 1]
            if not isinstance(command, dict) or not command.get('no_return'):
                raw += '\r'
            correct = entry['kind'] == 'input' and entry['text'] == raw
        if not correct:
            check(f'command-{index}-input', False)
    check('all-command-inputs-match', not any(not entry['pass'] for entry in checks))
    check('all-command-captures-present', all((path, entry['label']) in captures for path, entry in actions))
    retries = [entry for _, entry in events if entry.get('label', '').startswith('retry') and entry['kind'] == 'input']
    check('recorded-final-reader-retries', [(entry['label'], entry['text']) for entry in retries]
          == [('retry121', 'GIVE MASK\r'), ('retry122', 'PLAY FLUTE\r')], retries=retries)
    text = ''
    for index, path in enumerate(sessions):
        stream = lines(path / 'output-characters.jsonl')
        text += ''.join(chr(entry['value'] & 127) for entry in stream
                        if index or entry['time'] <= cutoff)
    check('no-death-in-completed-route', 'You are dead.' not in text)
    for requirement in route['requirements']:
        check(requirement['id'], requirement['text'] in text, expected=requirement['text'])
    end = captures[(args.continuation, 'ending')]
    check('final-message-observed', route['ending_text'] in '\n'.join(end['graphics_text']))
    check('83-pills-remaining', 'You completed the adventure with 83' in text)
    sides = {'a'} | {entry['side'] for _, entry in events if entry['kind'] == 'mount'}
    check('both-disk-sides', sides == {'a', 'b'}, observed=sorted(sides))
    inputs = json.loads(Path('docs/inputs.json').read_text())['inputs']
    hashes = {entry['path']: entry['sha256'] for entry in inputs}
    profiles = [json.loads((path / 'session.json').read_text()) for path in sessions]
    check('unmodified-original-media', all(profile['media'][side]['sha256'] == hashes[f'mask-of-sun-{side}.dsk']
                                           for profile in profiles for side in ('a', 'b')))
    before = (args.opening / 'command032-ram.bin').read_bytes()
    recovered = (args.continuation / 'recovery-ram.bin').read_bytes()
    check('native-checkpoint-world-preserved', before[0x6000:0x67fe] == recovered[0x6000:0x67fe])
    check('native-checkpoint-graphics-preserved', before[0x2000:0x6000] == recovered[0x2000:0x6000])
    jump = (args.continuation / 'jump-ready-ram.bin').read_bytes()
    pointer = int.from_bytes(jump[0xd2:0xd4], 'little')
    check('observed-native-jump-phase', jump[0x600d] == 39 and jump[0x6003] == 1 and 0x6c8c <= pointer <= 0x6d26,
          script_pc=pointer, D=jump[0x6003])
    check('explicit-ghost-wait', any(entry['kind'] == 'observe' and entry['condition'] == 'The apparition fades'
                                   for _, entry in events))
    checkpoint = args.opening / 'state_directory/apple2p/command032.sta'
    failed = ''.join(chr(entry['value'] & 127) for entry in lines(args.opening / 'output-characters.jsonl')
                     if entry['time'] > cutoff)
    report = {
        'scope': 'Operator-stepped original playthrough, with a documented native emulator checkpoint retry',
        'operator': 'Codex; each input/page/mount supplied individually and response inspected',
        'pass': all(entry['pass'] for entry in checks), 'checks': checks,
        'sessions': profiles, 'completed_route_inputs': [entry for _, entry in events],
        'checkpoint_recovery': {'source': str(checkpoint), 'sha256': digest(checkpoint),
            'from_capture': 'command032', 'to_capture': 'recovery',
            'times': [cutoff, captures[(args.continuation, 'recovery')]['time']],
            'method': 'MAME machine:load of complete native state; no game-RAM/register patch'},
        'excluded_attempt': {'session': str(args.opening), 'after': 'command032', 'output_text': failed,
            'reason': 'A strict normal-reader predicate missed the timed snake prompt; native checkpoint retry recorded.'},
        'output_text': text, 'checkpoints': [],
    }
    for path, entry in events:
        if entry['kind'] != 'capture':
            continue
        record = captures[(path, entry['label'])]
        ram = path / (entry['label'] + '-ram.bin')
        report['checkpoints'].append({'session': str(path), **record, 'ram_sha256': digest(ram),
                                      'observation_timeout': entry['timeout']})
    if args.publish:
        args.publish.mkdir(parents=True, exist_ok=True)
        for index, path in enumerate(sessions, 1):
            for name in ('manual-inputs.jsonl', 'output-characters.jsonl', 'session.json'):
                shutil.copyfile(path / name, args.publish / f'segment-{index}-{name}')
        for path, name in [(args.opening, 'command001'), (args.continuation, 'command034'),
                           (args.continuation, 'ghost-ready'), (args.continuation, 'jump-ready'),
                           (args.continuation, 'command073'), (args.continuation, 'page101'),
                           (args.continuation, 'ending')]:
            shutil.copyfile(path / 'snapshot_directory' / f'{name}.png', args.publish / f'{name}.png')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'pass': report['pass'], 'checks': checks}, indent=2))
    return not report['pass']


if __name__ == '__main__':
    sys.exit(main())
