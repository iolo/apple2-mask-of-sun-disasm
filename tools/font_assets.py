#!/usr/bin/env python3
"""Decode/encode native character bytes as individually editable 8x8 PNGs.

Columns 0..6 are pixels; column7 is the Apple II artifact phase bit. The final
four rows of glyph $7F have no bytes in the allocated native file and stay clear.
"""
import argparse
from pathlib import Path
import sys
try:
    from PIL import Image
except ImportError:
    sys.exit("Missing Pillow; install the Python Pillow package for editable font conversion")

ROOT = Path(__file__).resolve().parents[1]
BLACK, WHITE, PHASE, ABSENT = (0, 0, 0, 255), (255, 255, 255, 255), (0, 128, 255, 255), (0, 0, 0, 0)
FONT_BYTES = 764


def decode(data, directory):
    if len(data) != FONT_BYTES:
        raise ValueError('font must contain 764 native bytes')
    directory.mkdir(parents=True, exist_ok=False)
    for code in range(0x20, 0x80):
        glyph = Image.new('RGBA', (8, 8), ABSENT)
        for row in range(8):
            offset = (code - 0x20) * 8 + row
            if offset >= FONT_BYTES:
                continue
            value = data[offset]
            for bit in range(8):
                color = (PHASE if bit == 7 else WHITE) if value & (1 << bit) else BLACK
                glyph.putpixel((bit, row), color)
        glyph.save(directory / f'{code:02x}.png')


def encode(directory):
    expected = {f'{code:02x}.png' for code in range(0x20, 0x80)}
    found = {path.name for path in directory.glob('*.png')}
    if found != expected:
        raise ValueError(f'font glyph files missing={sorted(expected-found)}, extra={sorted(found-expected)}')
    output = bytearray()
    for code in range(0x20, 0x80):
        path = directory / f'{code:02x}.png'
        with Image.open(path) as source:
            if source.size != (8, 8):
                raise ValueError(f'{path}: glyph must be 8x8')
            glyph = source.convert('RGBA')
        for row in range(8):
            offset = (code - 0x20) * 8 + row
            if offset >= FONT_BYTES:
                if any(glyph.getpixel((bit, row)) != ABSENT for bit in range(8)):
                    raise ValueError(f'{path}: absent native rows must stay transparent')
                continue
            value = 0
            for bit in range(8):
                pixel = glyph.getpixel((bit, row))
                on = PHASE if bit == 7 else WHITE
                if pixel not in (BLACK, on):
                    raise ValueError(f'{path}: unsupported color at column {bit}, row {row}')
                if pixel == on:
                    value |= 1 << bit
            output.append(value)
    return bytes(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('decode')
    export.add_argument('--output', type=Path, required=True)
    build = sub.add_parser('encode')
    build.add_argument('directory', type=Path)
    build.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'decode':
        decode((ROOT/'assets/raw/a/files/char-gen.bin').read_bytes()[0x604:], args.output)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encode(args.directory))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(str(error))
