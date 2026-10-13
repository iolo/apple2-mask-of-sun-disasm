#!/usr/bin/env python3
"""Compare recorded original/rebuilt mixer output and export small mono clips.

Exact PCM agreement is useful for this deterministic baseline, not a blanket
requirement for future implementation changes. Silent recordings never pass.
"""
import argparse
import array
import hashlib
import json
from pathlib import Path
import sys
import wave


def recording(session):
    path = session / 'audio.wav'
    with wave.open(str(path), 'rb') as stream:
        channels, width, rate, frames = (stream.getnchannels(), stream.getsampwidth(),
                                          stream.getframerate(), stream.getnframes())
        if width != 2:
            raise ValueError('analysis requires signed 16-bit PCM')
        stats = [{'channel': channel, 'minimum': 0, 'maximum': 0, 'sum_square': 0} for channel in range(channels)]
        digest = hashlib.sha256()
        while pcm := stream.readframes(8192):
            digest.update(pcm)
            samples = array.array('h', pcm)
            if sys.byteorder != 'little':
                samples.byteswap()
            for channel in stats:
                values = samples[channel['channel']::channels]
                channel['minimum'] = min(channel['minimum'], min(values))
                channel['maximum'] = max(channel['maximum'], max(values))
                channel['sum_square'] += sum(value*value for value in values)
    for channel in stats:
        channel['mean_square'] = channel.pop('sum_square')/frames
    with path.open('rb') as source:
        file_hash = hashlib.file_digest(source, 'sha256').hexdigest()
    return {'sha256': file_hash, 'pcm_sha256': digest.hexdigest(), 'frames': frames,
            'rate': rate, 'channels': channels, 'sample_width': width, 'statistics': stats}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original', type=Path)
    p.add_argument('rebuilt', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--clips', type=Path)
    p.add_argument('--clip', action='append', help='NAME:START_SECONDS:DURATION; defaults to opening effects')
    p.add_argument('--route', type=Path, help='optional audio_checks in the recorded route')
    args = p.parse_args()
    original = recording(args.original)
    rebuilt = recording(args.rebuilt)
    checks = {'matching_format': all(original[key] == rebuilt[key]
                                     for key in ('rate', 'channels', 'sample_width', 'frames')),
              'nonzero_output': any(channel['mean_square'] > 0 for channel in original['statistics']),
              'matching_pcm': original['pcm_sha256'] == rebuilt['pcm_sha256']}
    windows = []
    if args.route:
        route = json.loads(args.route.read_text())
        for session in (args.original, args.rebuilt):
            events = [json.loads(line) for line in (session / 'replay-inputs.jsonl').read_text().splitlines()]
            commands = {event['command_index']: event['time'] for event in events
                        if 'reason' in event and event['reason'] != 'pagination'}
            for rule in route.get('audio_checks', []):
                start, end = commands[rule['command']], commands[rule['until_command']]
                with wave.open(str(session / 'audio.wav'), 'rb') as stream:
                    stream.setpos(int(start*stream.getframerate()))
                    values = array.array('h', stream.readframes(int((end-start)*stream.getframerate())))
                nonzero = any(values)
                passed = nonzero == rule['audible']
                windows.append({'session': str(session), 'id': rule['id'], 'start': start, 'end': end,
                                'nonzero': nonzero, 'pass': passed})
                checks[str(session)+'/'+rule['id']] = passed
    clips = []
    if args.clips:
        args.clips.mkdir(parents=True, exist_ok=True)
        channel = max(original['statistics'], key=lambda item: item['mean_square'])['channel']
        specifications = args.clip or ['hut-arrival:158:4', 'statue-opening:293:4']
        for specification in specifications:
            name, start_text, duration_text = specification.split(':')
            if not name.replace('-', '').isalnum():
                raise ValueError('clip name must contain only letters, digits or hyphens')
            start, duration = float(start_text), float(duration_text)
            if start < 0 or duration <= 0 or start+duration > original['frames']/original['rate']:
                raise ValueError('clip outside recording')
            first, last = int(start*original['rate']), int((start+duration)*original['rate'])
            with wave.open(str(args.original / 'audio.wav'), 'rb') as stream:
                stream.setpos(first)
                samples = array.array('h', stream.readframes(last-first))
            if sys.byteorder != 'little':
                samples.byteswap()
            clip = samples[channel::original['channels']]
            if sys.byteorder != 'little':
                clip.byteswap()
            path = args.clips / (name + '.wav')
            with wave.open(str(path), 'wb') as stream:
                stream.setparams((1, 2, original['rate'], len(clip), 'NONE', 'not compressed'))
                stream.writeframes(clip.tobytes())
            clips.append({'path': str(path), 'source_channel': channel, 'start_seconds': start,
                          'duration_seconds': duration, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    report = {'scope': 'mixer output for the recorded replay only', 'pass': all(checks.values()),
              'checks': checks, 'original': original, 'rebuilt': rebuilt, 'clips': clips,
              'windows': windows,
              'sessions': [json.loads((session / 'session.json').read_text())
                           for session in (args.original, args.rebuilt)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'pass': report['pass'], 'checks': checks}, indent=2))
    return not report['pass']


if __name__ == '__main__':
    sys.exit(main())
