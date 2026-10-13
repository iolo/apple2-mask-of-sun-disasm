#!/usr/bin/env python3
"""Check a supported Y-glyph edit in loaded font and rendered opening HGR bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from font_assets import encode

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('edited', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    captures = [(directory/'001-waiting-01-ram.bin').read_bytes() for directory in (args.baseline, args.edited)]
    original, edited = captures
    y, column, row = 0x59, 6, 7
    font_address = 0xb400 + (y - 0x20) * 8 + row
    scanline = 12*12+row
    offset = (scanline&7)*0x400 + ((scanline>>3)&7)*0x80 + (scanline>>6)*0x28
    page = 0x4000 if original[0x346] else 0x2000
    address = page + offset
    graphics_changes = [i for i in range(page, page+0x2000) if original[i] != edited[i]]
    baseline_font = encode(ROOT/'assets/decoded/font')
    native_font = (ROOT/'assets/raw/a/files/char-gen.bin').read_bytes()[0x604:]
    checks = {'baseline-font-roundtrip': baseline_font == native_font,
              'baseline-glyph-restored': baseline_font[(y-0x20)*8+row] == original[font_address],
              'font-one-pixel-change': original[font_address] ^ edited[font_address] == 1<<column,
              'same-drawing-page': original[0x346] == edited[0x346],
              'rendered-pixel-change': original[address] ^ edited[address] == 1<<column,
              'only-expected-hgr-byte-changed': graphics_changes == [address]}
    result = {'pass': all(checks.values()), 'checks': checks,
              'edit': {'glyph': y, 'column': column, 'row': row},
              'font_address': font_address, 'screen_address': address,
              'font_bytes': [original[font_address], edited[font_address]],
              'screen_bytes': [original[address], edited[address]],
              'graphics_changes': graphics_changes,
              'baseline_font_sha256': hashlib.sha256(baseline_font).hexdigest(),
              'sessions': [json.loads((directory/'session.json').read_text()) for directory in (args.baseline,args.edited)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pass':result['pass'],'checks':checks},indent=2))
    return not result['pass']


if __name__ == '__main__':
    sys.exit(main())
