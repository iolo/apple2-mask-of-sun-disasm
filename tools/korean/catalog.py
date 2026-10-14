#!/usr/bin/env python3
"""Extract lossless ULTRA text spans and manage the Korean review catalog.

Only source bytes explicitly identified as display literals are editable.
Line separators, conditional prefixes, semicolons and executable tokens stay
outside those spans. Catalog IDs use original file offsets, never translated
line numbers. Existing translations survive re-extraction only for matching
IDs/source hashes; deleted or changed entries are archived for reconciliation.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'assets/korean/messages.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def ascii_text(raw):
    return bytes(b & 127 for b in raw).decode('ascii')


def script_lines(raw):
    """Retain every byte, including EOF and allocated padding."""
    stop = raw.find(b'\0')
    if stop < 0:
        raise ValueError('script has no EOF')
    cursor = 0
    lines = []
    for part in raw[:stop].split(b'\x8d'):
        end = cursor + len(part)
        cr = end < stop
        lines.append({'offset': cursor, 'raw': part, 'cr': cr})
        cursor = end + int(cr)
    rebuilt = b''.join(x['raw'] + (b'\x8d' if x['cr'] else b'') for x in lines) + raw[stop:]
    if rebuilt != raw:
        raise ValueError('lossless script roundtrip failed')
    return lines


def directive(text):
    """Decode nested .T/.E modifiers without searching arbitrary text for .P."""
    if not text.startswith('.'):
        return None
    pos = 1
    conditions = []
    while pos + 1 < len(text) and text[pos] in 'TE' and text[pos + 1] == ' ':
        conditions.append(text[pos])
        pos += 2
    if pos >= len(text):
        return None
    opcode = text[pos]
    # The native dispatch consumes the opcode and one separator.
    return opcode, pos + 2, conditions


def entry(mid, source, reference, kind, context, newline=True, excluded=None):
    return {'id': mid, 'references': [reference], 'source': source,
            'source_hash': digest(source.encode()), 'context': context, 'kind': kind,
            'protected_tokens': [], 'layout': {'newline': newline, 'columns': 40},
            'ko': None, 'status': 'excluded' if excluded else 'draft',
            'reviewer': None, 'reviewed_at': None, 'reviewed_hash': None,
            'notes': excluded or ''}


def source_labels(module, base, build):
    labels = {}
    for line in (build / (module + '.lbl')).read_text().splitlines():
        match = re.fullmatch(r'al ([0-9A-Fa-f]+) \.(\S+)', line)
        if match:
            labels[match[2]] = int(match[1], 16)
    return labels, (build / (module + '.bin')).read_bytes(), base


def literal_bytes(source, label):
    """Read a labelled .byte block, rejecting expressions rather than guessing.

    New runtime notices are simple byte/string literals. This deliberately does
    not implement ca65 evaluation or read a previously built, possibly stale blob.
    """
    lines = source.splitlines()
    starts = [(n, match[1]) for n, line in enumerate(lines)
              if (match := re.fullmatch(r'\s*' + re.escape(label) + r':\s*(.*)', line))]
    if len(starts) != 1:
        raise ValueError('missing/duplicate literal label: ' + label)
    n, first = starts[0]
    data = bytearray()
    for line in [first] + lines[n + 1:]:
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        match = re.fullmatch(r'\.byte\s+(.+)', line)
        if not match:
            break
        rest = match[1]
        while rest:
            rest = rest.lstrip()
            if rest.startswith('"'):
                value, end = json.JSONDecoder().raw_decode(rest)
                data.extend(value.encode('ascii'))
            else:
                token = re.match(r'\$[0-9a-fA-F]+|[0-9]+', rest)
                if not token:
                    raise ValueError('unsupported .byte expression: ' + label)
                end = token.end()
                word = token[0]
                value = int(word[1:], 16) if word.startswith('$') else int(word)
                if not 0 <= value <= 255:
                    raise ValueError('out-of-range literal byte: ' + label)
                data.append(value)
            rest = rest[end:].lstrip()
            if not rest or rest.startswith(';'):
                break
            if not rest.startswith(',') or not rest[1:].strip():
                raise ValueError('unsupported .byte delimiter/expression: ' + label)
            rest = rest[1:]
    if not data:
        raise ValueError('empty literal block: ' + label)
    return bytes(data)


def runtime_notices():
    """Account for added technical UI, including deliberate pre-renderer English."""
    specs = [
        ('bootstrap.s', 'boot_error_text', 'boot_notice',
         'Before validated runtime/font/resident assets; ROM text output and retry startup.',
         'Korean rendering is not yet available after an initialization failure; retain essential English startup-media instructions.'),
        ('bootstrap.s', 'boot_no_lc_message', 'boot_notice',
         'Language Card detection failed; ROM text output followed by halt until reset.',
         'Required Language Card is absent, so the Korean font cannot be loaded; retain English hardware/reset instructions.'),
        ('dispatch.s', 'ko_media_text', 'media_prompt',
         'Game side A (GE(12) < 2): resource load retry and post-restore room-pool reload; resident assets are initialized, room cache may be invalid.', None),
        ('dispatch.s', 'ko_media_b_text', 'media_prompt',
         'Game side B (GE(12) >= 2): resource load retry and post-restore room-pool reload; resident assets are initialized, room cache may be invalid.', None),
        ('save.s', 'ko_save_prompt', 'media_prompt',
         'Before save-header invalidation and snapshot writes; resident assets are initialized.', None),
        ('restore-guard.inc', 'ko_restore_error_text', 'recovery_notice',
         'Snapshot read failure or incompatible save; fixed $0BF3 ASCII printer outside the snapshot.',
         'Partial restore may corrupt the snapshot-resident Korean extension; preserve the independent English retry instruction outside snapshot RAM.')]
    messages = []
    for filename, label, kind, context, excluded in specs:
        path = 'src/korean/' + filename
        raw = literal_bytes((ROOT / path).read_text(), label)
        if filename == 'bootstrap.s':
            if not raw.endswith(b'\r\0') or b'\0' in raw[:-1]:
                raise ValueError('unexpected boot notice terminator: ' + label)
            body = ascii_text(raw[:-1]).strip('\r').replace('\r', '\n')
        else:
            if not raw.endswith(b'\x8d') or any(b < 128 for b in raw):
                raise ValueError('unexpected high-bit runtime notice: ' + label)
            body = ascii_text(raw[:-1])
        messages.append(entry('runtime:' + label, body,
            {'path': path, 'label': label, 'original_hex': raw.hex(), 'literal_sha256': digest(raw)},
            kind, {'usage': context}, excluded=excluded))
    return messages


def python_text_constant(source, name):
    """Read one top-level literal without importing/executing a build tool."""
    values=[node.value for node in ast.parse(source).body if isinstance(node,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id==name for t in node.targets)]
    if len(values)!=1 or not isinstance(values[0],ast.Constant) or not isinstance(values[0].value,str):
        raise ValueError('missing/nonliteral/duplicate text constant: '+name)
    return values[0].value


def peripheral_notices(build):
    """Account explicitly for generated boot UI and retained non-game text."""
    path='tools/korean/startup_disk.py'
    body=python_text_constant((ROOT/path).read_text(),'A_BOOT_NOTICE')
    messages=[entry('generated:a_boot_notice',body,
        {'path':path,'name':'A_BOOT_NOTICE','literal_sha256':digest(body.encode())},
        'boot_notice',{'usage':'Full game A START prints this before LC/runtime initialization; boot the extra startup disk.'},
        excluded='Game A is not the Korean initialization disk; retain essential pre-renderer English boot guidance.')]
    labels,raw,base=source_labels('chargen',0xadfc,build)
    for name,label,delta in [('vtoc','legacy_editor_text_tail',1),('video','legacy_editor_video_action',9)]:
        offset=labels[label]-base+delta
        body=ascii_text(raw[offset:raw.index(0,offset)])
        messages.append(entry('legacy:'+name,body,
            {'path':'src/chargen.s','label':label,'address':base+offset,'original_hex':raw[offset:raw.index(0,offset)].hex()},
            'legacy_text',{'usage':'Retained older editor fragment below current CHAR GEN entry; no game caller established.'},
            excluded='Unused historical editor text, not part of the game UI; preserve original bytes.'))
    labels,raw,base=source_labels('dos-low',0x9b00,build)
    offset=labels['dos_dskvolum']-base
    data=raw[offset:offset+12]
    messages.append(entry('dos:catalog_volume',ascii_text(data[::-1]),
        {'path':'src/dos-low.s','label':'dos_dskvolum','address':labels['dos_dskvolum'],'original_hex':data.hex()},
        'boot_notice',{'usage':'DOS CATALOG header, emitted in reverse byte order; filenames/types/counts remain ASCII data.'},
        excluded='DOS command-shell catalog UI outside gameplay and before Korean initialization; retain English.'))
    labels,raw,base=source_labels('boot-a',0x0800,build)
    offset=labels['resident_diagnostic']-base
    data=raw[offset:offset+24]
    expected=bytes.fromhex('2058fca9c220edfda90120dafda9ad20edfda90020dafd60')
    if data!=expected:raise ValueError('boot diagnostic changed; re-audit generated output')
    messages.append(entry('boot:resident_diagnostic','B01-00',
        {'path':'src/boot-a.s','label':'resident_diagnostic','original_hex':data.hex()},
        'boot_notice',{'usage':'Retained uncalled diagnostic: literal B, ROM hex byte 01, hyphen, ROM hex byte 00.'},
        excluded='No game caller established; preserve historical English/hex diagnostic code.'))
    return messages


def extract(build):
    built = json.loads((build / 'build.json').read_text())
    for item in built['source_inputs']:
        if digest((ROOT / item['path']).read_bytes()) != item['sha256']:
            raise ValueError('stale baseline build; rebuild before extraction: ' + item['path'])
    for item in built['assembled']:
        path = build / (Path(item['source']).stem + '.bin')
        if digest(path.read_bytes()) != item['sha256']:
            raise ValueError('assembled binary hash mismatch: ' + str(path))
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())
    messages, files, outputs = [], [], []
    # Identical files duplicated across sides share entries, not unrelated text.
    duplicates = {}
    for disk in manifest['disks']:
        for file in disk['files']:
            if file['type'] != 0:
                continue
            raw = (ROOT / file['path']).read_bytes()
            lines = script_lines(raw)
            texts = [ascii_text(x['raw']) for x in lines]
            spans = []
            identity = (file['name'], digest(raw))
            canonical = duplicates.setdefault(identity, disk['side'])
            for n, line in enumerate(lines):
                text = texts[n]
                decoded = directive(text)
                if not decoded or file['name'] == 'START':
                    continue
                opcode, arg, conditions = decoded
                if opcode not in ('P', ']', '&', 'A', '=', '!', '1', '2'):
                    continue
                outputs.append({'side': disk['side'], 'file': file['name'],
                                'offset': line['offset'], 'line': n + 1,
                                'opcode': opcode, 'conditions': conditions, 'text': text})
                kind = 'script_text'
                if opcode == 'P' and text[arg:arg + 1] == '"':
                    start = arg + 1
                elif opcode == ']' and text[arg:]:
                    start, kind = arg, 'custom_prompt'
                else:
                    continue
                end = len(text)
                newline = kind == 'script_text' and not text.endswith(';')
                if kind == 'script_text' and text.endswith(';'):
                    end -= 1
                source = text[start:end]
                offset = line['offset'] + start
                ref = {'side': disk['side'], 'file': file['name'], 'path': file['path'],
                       'offset': offset, 'length': end - start, 'line': n + 1,
                       'conditions': conditions, 'file_hash': digest(raw),
                       'original_hex': raw[offset:offset + end - start].hex()}
                mid = f"{canonical}:{file['name']}:{offset:04x}"
                spans.append({'id': mid, 'offset': offset, 'length': end - start})
                if canonical != disk['side']:
                    next(m for m in messages if m['id'] == mid)['references'].append(ref)
                    continue
                excluded = 'Layout-only spacing/blank output; preserve original bytes.' if not source.strip() else None
                if source == 'OK>^' or (file['name'] == 'ROOM 9.0' and source in ('S^', 'H^', 'O^', 'T')):
                    kind = 'command_echo'
                    excluded = 'English input prompt/typed SHOOT feedback in timed input loop; preserve bytes and cursor positions.'
                messages.append(entry(mid, source, ref, kind,
                    {'before': texts[max(0, n - 3):n], 'after': texts[n + 1:n + 4]},
                    newline, excluded))
            # Replace each extracted source span with its decoded/re-encoded value.
            rebuilt = bytearray(raw)
            for span in spans:
                m = next(m for m in messages if m['id'] == span['id'])
                start, length = span['offset'], span['length']
                rebuilt[start:start + length] = bytes(
                    ord(c) | (b & 128) for c, b in zip(m['source'], raw[start:start + length]))
            if rebuilt != raw:
                raise ValueError(f"{file['path']}: text-span roundtrip failed")
            files.append({'side': disk['side'], 'name': file['name'], 'path': file['path'],
                          'sha256': digest(raw), 'allocated_bytes': len(raw),
                          'content_bytes': raw.index(0) + 1, 'spans': spans})
    # Structured PARMS data: prompt length + bytes, four CR-delimited errors.
    path = 'assets/raw/a/files/parms-obj.bin'
    raw = (ROOT / path).read_bytes()
    for name, offset, length, excluded in [('prompt', 5, raw[4], 'Keep the English command prompt OK>.')] + [
            (f'error-{i}', 4 + 0x50 + i * 16, 15, None) for i in range(4)]:
        messages.append(entry(f'parms:{name}', ascii_text(raw[offset:offset + length]),
            {'path': path, 'offset': offset, 'length': length, 'file_hash': digest(raw)},
            'engine_prompt' if name == 'prompt' else 'engine_error', {}, excluded=excluded))
    # Extract assembled source labels instead of reading reference executable blobs.
    labels, raw, base = source_labels('intrinsics', 0x0cfc, build)
    for name in ['disk_error_text', 'picture_load_overflow_text', 'disk_action_error_text',
                 'game_disk_prompt_text', 'disk_side_a_text', 'disk_side_b_text',
                 'drive_prompt_text', 'disk_prompt_ok_text']:
        offset = labels[name] - base
        stop = raw.index(0x8d, offset)
        body = ascii_text(raw[offset:stop])
        newline = not body.endswith(';')
        if not newline:
            body = body[:-1]
        excluded = 'Media identifier/command prompt; retain ASCII.' if name in (
            'disk_side_a_text', 'disk_side_b_text', 'disk_prompt_ok_text') else None
        messages.append(entry('intrinsic:' + name, body,
            {'path': 'src/intrinsics.s', 'label': name, 'address': labels[name]},
            'engine_error' if 'error' in name or 'overflow' in name else 'media_prompt',
            {}, newline, excluded))
    labels, raw, base = source_labels('boot-b', 0x0800, build)
    offset = labels['wrong_side_message'] - base
    messages.append(entry('boot:wrong_side', ascii_text(raw[offset:raw.index(0, offset)]),
        {'path': 'src/boot-b.s', 'label': 'wrong_side_message'}, 'boot_notice', {},
        excluded='Before HGR/LC initialization; retain essential English technical boot notice.'))
    labels, raw, base = source_labels('dos-low', 0x9b00, build)
    for name in sorted(n for n in labels if re.fullmatch(r'dos_err\d+', n)):
        if name == 'dos_err00':
            continue  # CR/bell control sequence, no words.
        offset = labels[name] - base
        stop = offset
        while raw[stop] < 128:
            stop += 1
        messages.append(entry('dos:' + name, ascii_text(raw[offset:stop + 1]),
            {'path': 'src/dos-low.s', 'label': name, 'address': labels[name]}, 'boot_error', {},
            excluded='Startup DOS error before Korean renderer; retain English technical diagnostic.'))
    picture_text = json.loads((ROOT / 'assets/korean/picture-text.json').read_text())
    for item in picture_text['messages']:
        refs = [{**ref, 'source_hash': digest((ROOT / ref['path']).read_bytes())} for ref in item['references']]
        m = entry(item['id'], item['source'], refs[0], 'picture_caption', item['context'])
        m['references'] = refs
        messages.append(m)
    messages.extend(runtime_notices())
    messages.extend(peripheral_notices(build))
    return {'schema_version': 1, 'messages': messages}, {
        'schema_version': 1, 'files': files, 'output_sites': outputs,
        'roundtrip_pass': True, 'script_count': len(files),
        'literal_reference_count': sum(len(f['spans']) for f in files),
        'coverage_complete': False,
        'picture_text_inventory': 'assets/korean/picture-text.json',
        'pending_audits': ['Live picture composition and Korean title-caption position',
                           'Computed output/macro call graph and dynamic layout',
                           'Firmware diagnostics reachable before engine initialization']}


def review_hash(message):
    payload = {k: message[k] for k in ('id', 'source_hash', 'ko', 'layout', 'protected_tokens',
                                     'context', 'references')}
    return digest(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode())


def validate(catalog, approved=False):
    if approved and catalog.get('orphaned'):
        raise ValueError('unreconciled removed/changed source entries')
    ids = set()
    for m in catalog['messages']:
        if m['id'] in ids:
            raise ValueError('duplicate ID: ' + m['id'])
        ids.add(m['id'])
        if digest(m['source'].encode()) != m['source_hash']:
            raise ValueError('source hash mismatch: ' + m['id'])
        if m['status'] not in ('draft', 'in_review', 'changes_requested', 'approved', 'excluded'):
            raise ValueError('invalid review state: ' + m['id'])
        if m['status'] == 'excluded':
            if not m['notes']:
                raise ValueError('missing exclusion reason: ' + m['id'])
            continue
        if m['ko'] is not None:
            if not isinstance(m['ko'], str) or unicodedata.normalize('NFC', m['ko']) != m['ko']:
                raise ValueError('translation must be NFC text: ' + m['id'])
            if any(ord(c) < 32 and c != '\n' for c in m['ko']):
                raise ValueError('control character in translation: ' + m['id'])
            for token in m['protected_tokens']:
                if not isinstance(token, str) or not token or not re.search(
                        r'(?<![A-Za-z0-9])' + re.escape(token) + r'(?![A-Za-z0-9])', m['ko']):
                    raise ValueError('missing protected input token: ' + m['id'] + ' ' + repr(token))
        if approved or m['status'] == 'approved':
            if (m['status'] != 'approved' or m['ko'] is None or
                    (m['ko'] == '' and not m['layout'].get('allow_empty_translation')) or not m['reviewer'] or
                    not m['reviewed_at'] or m['reviewed_hash'] != review_hash(m)):
                raise ValueError('missing or stale human approval: ' + m['id'])


def merge(old, new):
    prior = {m['id']: m for m in old.get('messages', [])}
    for m in new['messages']:
        previous = prior.pop(m['id'], None)
        if previous and previous['source_hash'] == m['source_hash'] and previous['kind'] == m['kind']:
            source_newline = m['layout']['newline']
            for key in ('ko', 'status', 'reviewer', 'reviewed_at', 'reviewed_hash', 'notes', 'protected_tokens', 'layout'):
                m[key] = previous[key]
            m['layout'] = dict(m['layout'], newline=source_newline)
            if m['status'] == 'approved' and m['reviewed_hash'] != review_hash(m):
                m.update(status='draft', reviewer=None, reviewed_at=None, reviewed_hash=None)
        elif previous:
            prior[previous['id']] = previous
    new['orphaned'] = old.get('orphaned', []) + list(prior.values())
    validate(new)
    return new


def check_sources(catalog, build):
    fresh, _ = extract(build)
    by_id = {m['id']: m for m in fresh['messages']}
    if set(by_id) != {m['id'] for m in catalog['messages']}:
        raise ValueError('source catalog IDs changed; re-extract and reconcile')
    for m in catalog['messages']:
        for field in ('source', 'source_hash', 'references', 'context', 'kind'):
            if m[field] != by_id[m['id']][field]:
                raise ValueError(f"source {field} changed: {m['id']}")


def cell(value):
    # JSON strings preserve significant spaces, quotes and explicit line breaks.
    return json.dumps(value, ensure_ascii=False).replace('|', '\\u007c')


def export_review(catalog, path):
    rows = ['# 한국어 번역 검수표', '',
            '각 셀은 JSON 값입니다. ko 셀만 수정한 뒤 import-review로 반영합니다.',
            '표 수정은 승인이 아닙니다. 승인은 카탈로그 해시와 함께 별도로 기록합니다.', '',
            '| id | source_hash | source | ko | context |', '| --- | --- | --- | --- | --- |']
    for m in catalog['messages']:
        if m['status'] != 'excluded':
            rows.append('| ' + ' | '.join(cell(v) for v in (
                m['id'], m['source_hash'], m['source'], m['ko'], m['context'])) + ' |')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(rows) + '\n')


def export_exclusions(catalog, path):
    rows = ['# 번역 제외 항목', '',
            '카탈로그에서 생성한 검토 자료입니다. 제외는 번역 승인과 별개이며 사유를 함께 검토합니다.', '',
            '| ID | 원문 | 제외 사유 | 출처 |', '| --- | --- | --- | --- |']
    for m in catalog['messages']:
        if m['status'] == 'excluded':
            rows.append('| ' + ' | '.join(cell(m[k]) for k in ('id', 'source', 'notes', 'references')) + ' |')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(rows) + '\n')


def import_review(catalog, path):
    expected = {m['id']: m for m in catalog['messages'] if m['status'] != 'excluded'}
    seen = set()
    for row in path.read_text().splitlines():
        if not row.startswith('| "'):
            continue
        mid, source_hash, source, ko, context = [json.loads(c.strip()) for c in row.split('|')[1:-1]]
        if mid not in expected or mid in seen:
            raise ValueError('unknown/duplicate review ID: ' + mid)
        m = expected[mid]
        if (source_hash, source, context) != (m['source_hash'], m['source'], m['context']):
            raise ValueError('review source/context conflict: ' + mid)
        seen.add(mid)
        if ko != m['ko']:
            m.update(ko=ko, status='draft', reviewer=None, reviewed_at=None, reviewed_hash=None)
    if seen != set(expected):
        raise ValueError('review table has missing IDs')
    validate(catalog)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['extract', 'check', 'export-review', 'import-review'])
    p.add_argument('--catalog', type=Path, default=DEFAULT)
    p.add_argument('--build', type=Path, default=ROOT / 'build/korean/english-baseline')
    p.add_argument('--coverage', type=Path, default=ROOT / 'docs/korean/extraction.json')
    p.add_argument('--review', type=Path, default=ROOT / 'docs/korean/review.md')
    p.add_argument('--exclusions', type=Path, default=ROOT / 'docs/korean/exclusions.md')
    p.add_argument('--require-approved', action='store_true')
    args = p.parse_args()
    old = json.loads(args.catalog.read_text()) if args.catalog.exists() else {}
    if args.command == 'extract':
        fresh, coverage = extract(args.build)
        catalog = merge(old, fresh)
        write_json(args.catalog, catalog)
        write_json(args.coverage, coverage)
    else:
        catalog = old
        validate(catalog, args.require_approved)
        check_sources(catalog, args.build)
        if args.command == 'export-review':
            export_review(catalog, args.review)
            export_exclusions(catalog, args.exclusions)
        elif args.command == 'import-review':
            import_review(catalog, args.review)
            write_json(args.catalog, catalog)
    print(json.dumps({'messages': len(catalog['messages']),
        'translated': sum(m['ko'] is not None for m in catalog['messages']),
        'excluded': sum(m['status'] == 'excluded' for m in catalog['messages']),
        'orphaned': len(catalog.get('orphaned', []))}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError) as error:
        sys.exit(str(error))
