#!/usr/bin/env python3
"""Host-only draft encoding/working-set experiment. Never patches a game disk.

ASCII is one byte, non-ASCII glyph IDs are two bytes (80..BF, low byte).
00 ends a message and 0A advances a line. Script references remain five
high-bit ASCII bytes, ~hhhh, so neither binary glyph IDs nor embedded line
breaks enter the interpreter's CR scanner. Bit 15 selects the resident pool.
This candidate format is not frozen until runtime/packing tests pass.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import struct
import unicodedata

from catalog import DEFAULT, ROOT, digest, extract, validate, write_json
from font import load_font, subset
from packages import package, identify, seal, SHARED_FILES


def encode(text, ids):
    if text != unicodedata.normalize('NFC', text):
        raise ValueError('text must be NFC')
    data = bytearray()
    for char in text:
        if char == '\n':
            data.append(10)
        elif 32 <= ord(char) <= 126:
            data.append(ord(char))
        else:
            if ord(char) < 128:
                raise ValueError('unsupported control character')
            index = ids[char]
            if not 0 <= index < 0x4000:
                raise ValueError('glyph ID exceeds 14 bits')
            data.extend((0x80 | (index >> 8), index & 255))
    data.append(0)
    return bytes(data)


def decode(data, chars):
    out, pos = [], 0
    while pos < len(data):
        value = data[pos]
        pos += 1
        if value == 0:
            if pos != len(data):
                raise ValueError('bytes after message terminator')
            return ''.join(out)
        if value == 10:
            out.append('\n')
        elif 32 <= value <= 126:
            out.append(chr(value))
        elif 0x80 <= value <= 0xbf:
            if pos >= len(data):
                raise ValueError('truncated glyph ID')
            index = ((value & 63) << 8) | data[pos]
            pos += 1
            if index >= len(chars):
                raise ValueError('invalid glyph ID')
            out.append(chars[index])
        else:
            raise ValueError('invalid stream opcode')
    raise ValueError('missing message terminator')


def pool(messages, ids):
    """u16 count, u16 absolute offsets, deduplicated terminated payloads."""
    header_size = 2 + 2 * len(messages)
    payload, offsets, known = bytearray(), [], {}
    for m in messages:
        data = encode(m['ko'], ids)
        if data not in known:
            known[data] = header_size + len(payload)
            payload.extend(data)
        offsets.append(known[data])
    if header_size + len(payload) > 65535:
        raise ValueError('pool exceeds 16-bit offsets')
    result = struct.pack('<H', len(messages))
    result += b''.join(struct.pack('<H', n) for n in offsets) + payload
    return result, len(known)


def reference(index):
    if not 0 <= index <= 65535:
        raise ValueError('reference exceeds four hex digits')
    return bytes(ord(c) | 128 for c in f'~{index:04X}')


def referenced_script(raw, replacements):
    """Replace literal spans only, retain CR/control bytes and one EOF."""
    end = raw.index(0) + 1
    cursor, parts = 0, []
    for ref, index in sorted(replacements, key=lambda item: item[0]['offset']):
        offset, length = ref['offset'], ref['length']
        if offset < cursor or offset + length >= end:
            raise ValueError('overlapping/out-of-range literal span')
        if raw[offset:offset + length].hex() != ref['original_hex']:
            raise ValueError('source literal changed')
        parts.extend((raw[cursor:offset], reference(index)))
        cursor = offset + length
    parts.append(raw[cursor:end])
    result = b''.join(parts)
    if result.count(b'\x8d') != raw[:end].count(b'\x8d'):
        raise ValueError('script CR topology changed')
    return result


def sectors(length):
    return (length + 255) // 256


def allocation_plan(disk, packages, vtoc):
    """Allocate actual T/S addresses without writing an image or its metadata."""
    sources = {f['path']: f for f in disk['files']}
    free = {(t,s) for t in range(35) for s in range(16)
            if int.from_bytes(vtoc[0x38+4*t:0x3a+4*t], 'big') & (1 << s)}
    reclaim = {tuple(pair) for f in packages for pair in sources[f['source']]['sectors']}
    if free & reclaim:
        raise ValueError('source file owns sectors marked free')
    available = sorted(free | reclaim)
    if any(t == 0 for t,s in available):
        raise ValueError('native TS reader uses track zero as EOF')
    needed = sum(f['package_sectors'] for f in packages)
    if needed > len(available):
        return {'fits': False, 'shortfall_sectors': needed-len(available)}
    allocations, cursor = [], 0
    for f in sorted(packages, key=lambda f: f['source']):
        original = sources[f['source']]
        if f['package_sectors'] > 122 or len(original['ts_lists']) != 1:
            raise ValueError('candidate exceeds supported single TS list')
        selected = available[cursor:cursor+f['package_sectors']]
        cursor += len(selected)
        allocations.append({'source': f['source'], 'ts_list': original['ts_lists'][0],
                            'data_sectors': selected, 'catalog_sector_count': len(selected)+1})
    assigned = {pair for f in allocations for pair in f['data_sectors']}
    fixed = {tuple(pair) for f in disk['files'] for pair in f['ts_lists']}
    fixed |= {tuple(pair) for f in disk['files'] if f['path'] not in {p['source'] for p in packages}
              for pair in f['sectors']}
    fixed |= {tuple(pair) for pair in disk['catalog_sectors']} | {(17,0)}
    if len(assigned) != needed or assigned & fixed:
        raise ValueError('candidate allocation overlaps itself or retained data/metadata')
    return {'fits': True, 'scope': 'Host T/S allocation only; no disk written or runtime loader verified',
            'allocations': allocations, 'remaining_free_sectors': available[cursor:]}


def resident_set(active, ids, budget):
    """Pin essential UI, then promote repeated text within one 4K LC bank.

    Review entries stay distinct. Only identical encoded display payloads share
    addresses; newline/conditional control remains in the original script.
    """
    common_names = {'LIBRARY', 'INITIAL', 'DEATH'}
    essential = sorted([m for m in active if m['kind'] != 'script_text' or
                        any(r.get('file') in common_names for r in m['references'])],
                       key=lambda m: m['id'])
    selected = {}
    for m in essential:
        selected.setdefault(m['ko'], m)
    used = 2 + sum(len(encode(ko, ids)) + 2 for ko in selected)
    if used > budget:
        raise ValueError(f'essential resident pool {used} exceeds budget {budget}')
    groups = defaultdict(list)
    for m in active:
        if m['ko'] not in selected:
            groups[m['ko']].append(m)
    candidates = []
    for ko, group in groups.items():
        paths = {r['path'] for m in group for r in m['references']}
        if len(paths) >= 2:
            cost = len(encode(ko, ids)) + 2
            candidates.append((-len(paths), -cost, ko, group))
    promoted = []
    for negative_count, negative_cost, ko, group in sorted(candidates):
        cost = -negative_cost
        if used + cost <= budget:
            selected[ko] = min(group, key=lambda m: m['id'])
            used += cost
            promoted.append({'representative': selected[ko]['id'], 'text': ko,
                             'source_files': -negative_count, 'resident_bytes': cost})
    resident = sorted(selected.values(), key=lambda m: m['id'])
    by_text = {m['ko']: 0x8000+i for i,m in enumerate(resident)}
    lookup = {m['id']: by_text[m['ko']] for m in active if m['ko'] in by_text}
    return resident, lookup, promoted


def measure(catalog, build, output, resident_budget=4096):
    validate(catalog)
    fresh, extraction = extract(build)
    # Validate current raw references, not an earlier extraction report.
    current = {m['id']: m for m in fresh['messages']}
    messages = catalog['messages']
    for m in messages:
        original = current.pop(m['id'])
        if any(m[key] != original[key] for key in ('source_hash', 'references', 'kind')):
            raise ValueError('stale catalog: ' + m['id'])
        if m['status'] != 'excluded' and m['ko'] is None:
            raise ValueError('missing draft: ' + m['id'])
    if current:
        raise ValueError('catalog is missing source messages')
    active = [m for m in messages if m['status'] != 'excluded']
    text = ''.join(m['ko'] for m in active)
    chars = sorted({c for c in text if ord(c) >= 128})
    ids = {c: i for i, c in enumerate(chars)}
    glyph_chars, font = subset(''.join(chars), load_font())
    assert glyph_chars == chars
    output.mkdir(parents=True, exist_ok=True)
    (output / 'hangul-font.bin').write_bytes(font)
    write_json(output / 'glyphs.json', chars)
    encoded_total = 0
    for m in active:
        data = encode(m['ko'], ids)
        if decode(data, chars) != m['ko']:
            raise ValueError('encoding roundtrip failed: ' + m['id'])
        encoded_total += len(data)
    resident, resident_ids, promoted = resident_set(active, ids, resident_budget)
    if len(resident) >= 0x8000:
        raise ValueError('resident namespace exhausted')
    resident_data, unique_resident = pool(resident, ids)
    (output / 'resident-pool.bin').write_bytes(resident_data)
    write_json(output / 'resident-index.json', [m['id'] for m in resident])
    write_json(output / 'resident-aliases.json', resident_ids)
    files = []
    for spec in extraction['files']:
        # START is a DOS EXEC input stream, not an interpreter room resource.
        # It retains its original allocation and must never receive KOR2 framing.
        if spec['name'] == 'START':
            continue
        path = spec['path']
        raw = (ROOT / path).read_bytes()
        file_messages = [m for m in active if any(r['path'] == path for r in m['references'])]
        local = sorted([m for m in file_messages if m['id'] not in resident_ids], key=lambda m: m['id'])
        local_ids = {m['id']: i for i, m in enumerate(local)}
        lookup = resident_ids | local_ids
        replacements = [(r, lookup[m['id']]) for m in file_messages for r in m['references'] if r['path'] == path]
        script = referenced_script(raw, replacements)
        data, unique = pool(local, ids)
        if not local:
            data = b''
        # One candidate file per room, rather than one file per individual message.
        # It requires a new streaming loader; do not feed to the native loader.
        sides = 3 if spec['name'] in SHARED_FILES else (1 if spec['side']=='a' else 2)
        framed = package(script, data, sides=sides)
        dest = output / spec['side'] / Path(path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(framed)
        # The candidate extension occupies 9400-9BFF; do not let LIBRARY use it.
        script_limit = 0x2400 if spec['name'] == 'LIBRARY' else 0x800
        files.append({'side': spec['side'], 'name': spec['name'], 'source': path,
                      'package': str(dest.relative_to(output)), 'source_sha256': digest(raw),
                      'sha256': digest(framed), 'original_sectors': sectors(len(raw)),
                      'script_bytes': len(script), 'script_limit': script_limit,
                      'script_fits': len(script) <= script_limit,
                      'pool_bytes': len(data), 'messages': len(local), 'unique_payloads': unique,
                      'package_bytes': len(framed), 'package_sectors': sectors(len(framed)),
                      'message_ids': [m['id'] for m in local]})
    largest = max(files, key=lambda f: f['pool_bytes'])
    report = {'schema_version': 1, 'kind': 'complete draft host encoding experiment; not approved game assets',
              'tool_sha256': digest(Path(__file__).read_bytes()),
              'font_sha256': digest(font),
              'format': 'ASCII + 14-bit non-ASCII IDs; zero terminator; LF; ~hhhh script references',
              'catalog_sha256': digest(json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode()),
              'translated': len(active), 'excluded': len(messages)-len(active),
              'glyph_count': len(chars), 'font_bytes': len(font), 'encoded_text_bytes': encoded_total,
              'resident_messages': len(resident), 'resident_unique_payloads': unique_resident,
              'resident_references': len(resident_ids), 'resident_budget': resident_budget,
              'promoted_repeated_text': promoted,
              'resident_pool_bytes': len(resident_data),
              'largest_room_pool': {'name': largest['name'], 'side': largest['side'], 'bytes': largest['pool_bytes']},
              'lc_data_bytes_without_code_or_buffers': len(font) + len(resident_data) + largest['pool_bytes'],
              'lc_remaining_before_code_or_buffers': 16384-len(font)-len(resident_data)-largest['pool_bytes'],
              'disk_scenarios': [], 'files': files,
              'runtime_proven': False, 'packing_proven': False,
              'limits': ['No disk image generated; no runtime addresses assigned.',
                         'Candidate packages require a streaming loader with distinct main/LC destinations.',
                         'RAM estimate excludes code, buffers, bank alignment and recovery workspace.',
                         'Sector deltas retain existing per-file TS lists; no resource relocation yet.',
                         'Dynamic screen composition, timers and input/puzzle guidance remain to be checked.']}
    components = [('font', font), ('resident', resident_data)]
    components += [(str(p.relative_to(ROOT)), p.read_bytes()) for p in
                   sorted((ROOT/'src').rglob('*')) if p.is_file()]
    components += [(f'baseline-{s}', (build/f'mask-of-sun-{s}.dsk').read_bytes()) for s in ('a','b')]
    seal(report, output, identify(report, output, components))
    refresh_allocation(report, output)
    write_json(output / 'encoding.json', report)
    return report


def refresh_allocation(report, output):
    """Recalculate file-sector accounting after a generated script insertion."""
    report['disk_scenarios'] = []
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())
    for disk in manifest['disks']:
        side = disk['side']
        vtoc = (ROOT / f'assets/raw/{side}/metadata/vtoc.bin').read_bytes()
        free = sum(int.from_bytes(vtoc[0x38+4*t:0x3c+4*t], 'big').bit_count() for t in range(35))
        selected = [f for f in report['files'] if f['side'] == side]
        delta = sum(f['package_sectors'] - f['original_sectors'] for f in selected)
        allocation = allocation_plan(disk, selected, vtoc)
        write_json(output / f'allocation-{side}.json', allocation)
        report['disk_scenarios'].append({'side': side, 'original_free_sectors': free,
             'package_sector_delta': delta, 'remaining_sectors_before_extra_code': free-delta,
             'host_sector_assignment_fits': allocation['fits'],
             'allocation_sha256': digest(json.dumps(allocation, sort_keys=True).encode())})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=DEFAULT)
    parser.add_argument('--build', type=Path, default=ROOT / 'build/korean/english-baseline')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/korean/draft-encoding')
    parser.add_argument('--resident-budget', type=int, default=4096)
    args = parser.parse_args()
    report = measure(json.loads(args.catalog.read_text()), args.build, args.output, args.resident_budget)
    print(json.dumps({k:v for k,v in report.items() if k not in ('files', 'promoted_repeated_text')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
