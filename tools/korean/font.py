#!/usr/bin/env python3
"""Convert pinned GalmuriMono7 bitmaps to 7x8 Apple II HGR glyphs.

Kbitx stores height/width as unsigned LEB128 followed by WIB-compressed
coverage bytes. Format checked against the upstream KbitxBitmapFontImporter
and WIBInputStream in https://github.com/kreativekorp/bitsnpicas.
This decoder neither evaluates XML entities nor rasterizes outline fonts.
"""
import argparse
import base64
import json
from pathlib import Path
import unicodedata
import xml.etree.ElementTree as ET

from catalog import ROOT, digest, write_json

FONT_DIR = ROOT / 'assets/korean/font'


def decode_bitmap(encoded):
    data = base64.b64decode(encoded + '=' * (-len(encoded) % 4), validate=True)
    pos = 0

    def number():
        nonlocal pos
        value = 0
        for shift in range(0, 35, 7):
            if pos >= len(data):
                raise ValueError('truncated bitmap dimensions')
            b = data[pos]
            pos += 1
            value |= (b & 127) << shift
            if not b & 128:
                return value
        raise ValueError('oversized bitmap dimensions')

    height, width = number(), number()
    if width * height > 65536:
        raise ValueError('bitmap too large')
    pixels = bytearray()
    while pos < len(data):
        command = data[pos]
        pos += 1
        count = (command & 31) * (32 if command & 32 else 1)
        kind = command >> 6
        if kind in (0, 1):
            pixels.extend(bytes([0 if kind == 0 else 255]) * count)
        elif kind == 2:
            if pos >= len(data):
                raise ValueError('truncated repeated pixel')
            pixels.extend(data[pos:pos + 1] * count)
            pos += 1
        else:
            if pos + count > len(data):
                raise ValueError('truncated literal pixels')
            pixels.extend(data[pos:pos + count])
            pos += count
        if len(pixels) > width * height:
            raise ValueError('bitmap run exceeds dimensions')
    if len(pixels) != width * height:
        raise ValueError('bitmap size mismatch')
    return width, height, pixels


def load_font():
    provenance = json.loads((FONT_DIR / 'source.json').read_text())
    for name, spec in provenance['files'].items():
        if digest((FONT_DIR / name).read_bytes()) != spec['sha256']:
            raise ValueError('pinned font hash mismatch: ' + name)
    xml = ET.parse(FONT_DIR / 'GalmuriMono7.kbitx').getroot()
    glyphs = {}
    for node in xml.findall('g'):
        if 'u' not in node.attrib:
            continue
        code = int(node.attrib['u'])
        w, h, pixels = decode_bitmap(node.attrib['d'])
        glyphs[code] = {'x': int(node.get('x', 0)), 'y': int(node.get('y', 0)),
                        'advance': int(node.get('w', 0)), 'width': w, 'height': h,
                        'pixels': pixels}
    return glyphs


def hgr_glyph(glyph):
    rows = bytearray(8)
    for py in range(glyph['height']):
        for px in range(glyph['width']):
            value = glyph['pixels'][py * glyph['width'] + px]
            if value not in (0, 255):
                raise ValueError('nonbinary coverage')
            if not value:
                continue
            x, y = glyph['x'] + px, 8 - glyph['y'] + py
            if not (0 <= x < 7 and 0 <= y < 8):
                raise ValueError('ink outside 7x8 cell')
            rows[y] |= 1 << x
    return bytes(rows)


def subset(text, glyphs):
    if text != unicodedata.normalize('NFC', text):
        raise ValueError('text must be NFC')
    chars = sorted(set(text) - {'\n'})
    missing = [f'U+{ord(c):04X} {c}' for c in chars if ord(c) not in glyphs]
    if missing:
        raise ValueError('missing font glyphs: ' + ', '.join(missing))
    bitmaps = []
    for char in chars:
        try:
            if 32 <= ord(char) <= 126:
                # Keep existing 8-row ASCII and its artifact phase/cursor bits.
                # Galmuri's Latin descenders can occupy a ninth baseline row.
                from PIL import Image
                im = Image.open(ROOT / f'assets/decoded/font/{ord(char):02x}.png').convert('RGBA')
                bitmap = bytearray(8)
                for y in range(8):
                    for x in range(7):
                        if im.getpixel((x, y))[:3] == (255, 255, 255):
                            bitmap[y] |= 1 << x
                    if im.getpixel((7, y))[:3] == (0, 128, 255):
                        bitmap[y] |= 128
                bitmaps.append(bytes(bitmap))
            else:
                bitmaps.append(hgr_glyph(glyphs[ord(char)]))
        except ValueError as error:
            raise ValueError(f'U+{ord(char):04X} {char}: {error}') from error
    return chars, b''.join(bitmaps)


def preview(text, chars, bitmaps, path, scale=4):
    from PIL import Image
    lines = text.split('\n')
    if any(len(line) > 40 for line in lines):
        raise ValueError('preview line exceeds 40 cells')
    mapping = {c: bitmaps[i * 8:i * 8 + 8] for i, c in enumerate(chars)}
    im = Image.new('RGB', (280, max(1, len(lines)) * 12), 'black')
    for row, line in enumerate(lines):
        for col, char in enumerate(line):
            for y, bits in enumerate(mapping[char]):
                for x in range(7):
                    if bits & (1 << x):
                        im.putpixel((col * 7 + x, row * 12 + y), (255, 255, 255))
    im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST).save(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text', default='한글 출력 시험 ABC 0123456789\n가나다라마바사아자차카타파하\n읽기 쓰기 저장 복원 디스크 교체')
    p.add_argument('--catalog', type=Path, help='subset all existing draft translations; no game patch')
    p.add_argument('--output', type=Path, default=ROOT / 'build/korean/font-probe')
    args = p.parse_args()
    glyphs = load_font()
    text = args.text
    if args.catalog:
        catalog = json.loads(args.catalog.read_text())
        text += ''.join(m['ko'] or '' for m in catalog['messages'])
    chars, data = subset(text, glyphs)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'font.bin').write_bytes(data)
    preview(args.text, chars, data, args.output / 'preview.png')
    report = {'derived_name': 'Mask Korean 7x8', 'bytes_per_glyph': 8,
              'glyphs': [{'id': i, 'character': c, 'codepoint': ord(c)} for i, c in enumerate(chars)],
              'glyph_count': len(chars), 'font_bytes': len(data), 'sha256': digest(data),
              'source_hash': digest((FONT_DIR / 'GalmuriMono7.kbitx').read_bytes()),
              'ascii_policy': 'Preserve native assets/decoded/font ASCII glyphs and phase bits',
              'supported_hangul_syllables': sum(c in glyphs for c in range(0xac00, 0xd7a4)),
              'kind': 'host synthetic font probe; not an emulator rendering test'}
    write_json(args.output / 'font.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'glyphs'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
