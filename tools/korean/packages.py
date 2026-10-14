"""KOR2 resource framing and deterministic identity; no disk writes."""
import hashlib
import struct

MAGIC = b'KOR2'
HEADER_BYTES = 24
IDENTITY_BYTES = 12
SHARED_FILES = {'INITIAL', 'LIBRARY', 'DEATH'}


def package(script, pool=b'', *, identity=bytes(IDENTITY_BYTES), sides=1):
    if len(identity) != IDENTITY_BYTES or sides not in (1, 2, 3):
        raise ValueError('invalid package identity or side mask')
    return (MAGIC + struct.pack('<HH', len(script), len(pool)) + identity +
            bytes([sides, 0, 0, 0]) + script + pool)


def split(data):
    if len(data) < HEADER_BYTES or data[:4] != MAGIC:
        raise ValueError('invalid package header')
    script_size, pool_size = struct.unpack_from('<HH', data, 4)
    if len(data) != HEADER_BYTES + script_size + pool_size:
        raise ValueError('package length mismatch')
    if data[20] not in (1, 2, 3) or data[21:24] != bytes(3):
        raise ValueError('invalid package side or reserved fields')
    return data[HEADER_BYTES:HEADER_BYTES+script_size], data[HEADER_BYTES+script_size:]


def identify(report, output, components):
    """Hash actual package bodies plus all caller-supplied build dependencies.

    Clear the identity field itself to avoid a circular hash. A caller changing
    synthetic bodies, startup code or padding must identify/seal again.
    """
    h = hashlib.sha256(b'MASK-KOR2-MEDIA\0')
    items = list(components)
    for f in report['files']:
        data = (output/f['package']).read_bytes()
        split(data)
        items.append((f['side']+'/'+f['name'], data[:8]+bytes(12)+data[20:]))
    for name, data in sorted(items):
        key = name.encode('utf-8')
        h.update(struct.pack('<I', len(key))+key+struct.pack('<I', len(data))+data)
    return h.digest()[:IDENTITY_BYTES]


def seal(report, output, identity):
    if len(identity) != IDENTITY_BYTES or not any(identity):
        raise ValueError('missing media identity')
    for f in report['files']:
        path = output/f['package']
        data = path.read_bytes()
        split(data)
        data = data[:8]+identity+data[20:]
        path.write_bytes(data)
        f.update(sha256=hashlib.sha256(data).hexdigest(), package_bytes=len(data),
                 package_sectors=(len(data)+255)//256)
    report.update(package_format='KOR2', package_header_bytes=HEADER_BYTES,
                  media_id=identity.hex())
