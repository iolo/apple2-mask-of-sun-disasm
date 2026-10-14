#!/usr/bin/env python3
"""Inventory native English command/answer inputs and audit displayed spellings.

The resulting JSON contains puzzle answers and is a reviewer artifact, not
player-facing help. Matching below checks vocabulary, not handler reachability.
"""
import argparse
import json
from pathlib import Path
import re

from catalog import ROOT, DEFAULT, ascii_text, check_sources, digest, directive, extract, script_lines, validate, write_json


def normalized_words(text):
    return ''.join(word[:5].ljust(5) for word in text.split())


def vocabulary_matches(token, patterns):
    needle = normalized_words(token)
    return [p for p in patterns if any(p['pattern'][i:i+len(needle)].ljust(len(needle)) == needle
            for i in range(0, len(p['pattern']), 5))]


def audit(catalog, baseline):
    validate(catalog); check_sources(catalog, baseline)
    _, extraction = extract(baseline)
    patterns, questions, polls = [], [], []
    by_line = {(r.get('path'), r.get('line')): m for m in catalog['messages']
               for r in m['references'] if 'line' in r}
    for f in extraction['files']:
        if f['name'] == 'START':
            continue
        lines = script_lines((ROOT/f['path']).read_bytes())
        texts = [ascii_text(line['raw']) for line in lines]
        current = None
        for n, text in enumerate(texts):
            location = dict(side=f['side'], file=f['name'], path=f['path'], line=n+1)
            if re.match('[A-Z]', text):
                patterns.append(dict(location, pattern=text))
            op = directive(text)
            if not op:
                current = None
                continue
            code, arg, conditions = op
            if code == 'A':
                current = dict(location, conditions=conditions, comparisons=[],
                               preceding_messages=[by_line[f['path'], i+1]['id']
                                   for i in range(max(0, n-12), n) if (f['path'], i+1) in by_line])
                questions.append(current)
            elif code == '=':
                if current is None:
                    raise ValueError('answer comparison not associated with a local ask: '+str(location))
                current['comparisons'].append(dict(line=n+1, conditions=conditions, prefix=text[arg:]))
            elif code == 'W':
                polls.append(dict(location, conditions=conditions))
    spellings = []
    for m in catalog['messages']:
        if m['status'] == 'excluded' or m['ko'] is None:
            continue
        for token in re.findall(r'\(([A-Z][A-Z ]*)\)', m['ko']):
            matches = vocabulary_matches(token, patterns)
            if not matches:
                raise ValueError('displayed input spelling absent from native patterns: '+m['id']+' '+token)
            spellings.append(dict(id=m['id'], token=token, native_matches=matches))
    glossary = json.loads((ROOT/'assets/korean/glossary.json').read_text())
    glossary_matches = []
    for term in glossary['terms']:
        if not term['input']:
            continue
        matches = vocabulary_matches(term['input'], patterns)
        if not matches:
            raise ValueError('unsupported glossary input: '+term['input'])
        glossary_matches.append(dict(input=term['input'], native_matches=matches))
    action_matches = []
    for action in glossary.get('actions', []):
        matches = vocabulary_matches(action['input'], patterns)
        if not matches:
            raise ValueError('unsupported glossary action: '+action['input'])
        action_matches.append(dict(input=action['input'], native_matches=matches))
    # Only the explicit first-page examples; do not invent a HELP command.
    examples = ['LOOK', 'INVENTORY', 'N', 'S', 'E', 'W']
    guide_examples = examples + ['EXAMINE', 'GET', 'DROP', 'EXIT', 'ENTER', 'NE', 'NW', 'SE', 'SW',
                                'LEFT', 'RIGHT', 'FORWARD', 'BACK', 'UP', 'DOWN',
                                'SAVE GAME', 'RESTORE GAME', 'SOUND ON', 'SOUND OFF']
    for token in guide_examples:
        if not vocabulary_matches(token, patterns):
            raise ValueError('unsupported opening example: '+token)
    magic = next(m for m in catalog['messages'] if m['id']=='a:ROOM 6.0:0233')
    assert 'XOTZIL' in magic['source'] and 'XOTZIL' in magic['ko']
    assert vocabulary_matches('XOTZIL', patterns)
    return dict(kind='English input inventory for reviewers; contains puzzle solutions',
                catalog_sha256=digest(json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode()),
                tool_sha256=digest(Path(__file__).read_bytes()),
                parser_source_sha256=digest((ROOT/'src/interpreter.s').read_bytes()),
                intrinsic_source_sha256=digest((ROOT/'src/intrinsics.s').read_bytes()),
                script_files=sum(f['name']!='START' for f in extraction['files']), pattern_sites=len(patterns), patterns=patterns,
                asks=questions, raw_key_polls=polls, displayed_input_spellings=spellings,
                glossary_inputs=glossary_matches, opening_examples=examples, guide_examples=guide_examples,
                glossary_actions=action_matches,
                glossary_sha256=digest((ROOT/'assets/korean/glossary.json').read_bytes()),
                protected_token_messages=sum(bool(m['protected_tokens']) for m in catalog['messages']),
                all_displayed_spellings_known=True, all_input_guidance_complete=False,
                limits=['Vocabulary existence is not proof of reachable command handling in every room.',
                        'Question comparisons accept prefixes and keep the original fifteen-byte answer buffer.',
                        'Raw timed-key scenes require separate runtime tests; only their .W sites are inventoried here.',
                        'Scenery nouns without an English gloss and whole-game Korean-only playability remain to be reviewed.'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,default=DEFAULT)
    p.add_argument('--baseline',type=Path,default=ROOT/'build/korean/english-baseline')
    p.add_argument('--output',type=Path,default=ROOT/'docs/evidence/korean/input-audit.json')
    args=p.parse_args();r=audit(json.loads(args.catalog.read_text()),args.baseline)
    write_json(args.output,r)
    print(json.dumps(dict(pattern_sites=r['pattern_sites'],asks=len(r['asks']),
                         comparisons=sum(len(q['comparisons']) for q in r['asks']),
                         displayed_spellings=len(r['displayed_input_spellings']),
                         glossary_inputs=len(r['glossary_inputs']),raw_key_polls=len(r['raw_key_polls']))))
