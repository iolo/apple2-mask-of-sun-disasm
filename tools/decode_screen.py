#!/usr/bin/env python3
"""Read ULTRA's 40 x 16 character grid from a CPU-visible 48K RAM capture."""
import argparse
from pathlib import Path


def decode(ram):
    if len(ram) != 0xc000:
        raise ValueError('expected a 48K CPU-visible RAM capture')
    font = {bytes(v & 127 for v in ram[0xb300 + c*8:0xb308 + c*8]): chr(c)
            for c in range(32, 127)}
    base = 0x2000 if ram[0x346] == 0 else 0x4000
    rows = []
    for row in range(16):
        cells = []
        for col in range(40):
            glyph = bytes(ram[base + ((y & 7) << 10) + ((y >> 3 & 7) << 7) +
                              (y >> 6)*40 + col] & 127 for y in range(row*12, row*12+8))
            cells.append(font.get(glyph, '?'))
        rows.append(''.join(cells))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ram', type=Path)
    args = p.parse_args()
    print('\n'.join(decode(args.ram.read_bytes())))
