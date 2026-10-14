"""Pack fixed-address native display strings as resident message references.

Only references are written here, never translated bodies. The synthetic caller
must mask the referenced pool first; a production caller must require approval.
"""
from catalog import ascii_text, digest

INTRINSIC_IDS = ('disk_error_text', 'picture_load_overflow_text',
                 'disk_action_error_text', 'game_disk_prompt_text', 'drive_prompt_text')
RUNTIME_IDS = ('ko_media_text', 'ko_save_prompt')


def reference(message, aliases):
    mid = aliases.get(message['id'])
    if message['status'] == 'excluded' or not isinstance(mid, int) or not 0x8000 <= mid <= 0xffff:
        raise ValueError('native UI requires an active resident message: '+message['id'])
    text = f'~{mid:04X}' + ('' if message['layout']['newline'] else ';') + '\r'
    return bytes(ord(c) | 128 for c in text)


def replace(data, offset, original, message, aliases):
    """Keep the original slot length and reject stale source or malformed slots."""
    data = bytearray(data)
    if (not original or original[-1] != 0x8d or any(b < 128 for b in original)
            or 0x8d in original[:-1] or offset < 0
            or data[offset:offset+len(original)] != original):
        raise ValueError('native UI source/terminator mismatch: '+message['id'])
    expected = message['source'] + ('' if message['layout']['newline'] else ';') + '\r'
    if ascii_text(original) != expected:
        raise ValueError('native UI catalog text/control mismatch: '+message['id'])
    encoded = reference(message, aliases)
    if len(encoded) > len(original):
        raise ValueError('native UI reference exceeds fixed slot: '+message['id'])
    data[offset:offset+len(original)] = encoded.ljust(len(original), b'\0')
    return bytes(data), dict(id=message['id'], offset=offset, slot_bytes=len(original),
                            message_id=aliases[message['id']], reference_hex=encoded.hex(),
                            original_sha256=digest(original))


def pack_parms(data, catalog, aliases):
    by_id = {m['id']:m for m in catalog['messages']}
    records = []
    for i in range(4):
        message = by_id[f'parms:error-{i}']
        ref = message['references'][0]
        offset, size = ref['offset'], ref['length']+1
        original = bytes(ord(c)|128 for c in message['source']+'\r')
        if size != len(original):raise ValueError('PARMS slot length mismatch')
        data, record = replace(data, offset, original, message, aliases)
        records.append(record)
    return data, records


def pack_labels(data, catalog, aliases, symbols, base, prefix, names):
    by_id = {m['id']:m for m in catalog['messages']}
    records = []
    for name in names:
        message = by_id[prefix+':'+name]
        ref = message['references'][0]
        address = symbols[name]
        if 'address' in ref and address != ref['address']:
            raise ValueError('native UI fixed label moved: '+name)
        original = (bytes.fromhex(ref['original_hex']) if 'original_hex' in ref else
                    bytes(ord(c)|128 for c in message['source']+
                          ('' if message['layout']['newline'] else ';')+'\r'))
        data, record = replace(data, address-base, original, message, aliases)
        record['address'] = address
        records.append(record)
    return data, records
