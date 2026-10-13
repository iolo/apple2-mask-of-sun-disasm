#!/usr/bin/env python3
"""Early template-free rebuild: assembled modules plus tracked raw regions.

This is intentionally incomplete. All other code remains tracked temporary raw
dependencies in assets/raw/manifest.json; completing PLAN.md requires replacing
them and making decoded graphics authoritative inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from dos_disk import ROOT, repack
from font_assets import encode as encode_font


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'build/early')
    args = p.parse_args()
    for name in ('ca65', 'ld65'):
        if not shutil.which(name):
            p.error(f'missing {name}; install cc65 and run tools/check_tools.py')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    replacements, assembled = {}, []
    (out / "font.bin").write_bytes(encode_font(ROOT / "assets/decoded/font"))
    # name, native runtime address/size, then asset offset/source offset/length.
    modules = [
        ('chargen', 0xadfc, 0x900, [('assets/raw/a/files/char-gen.bin', 0, 0, 0x900)]),
        ('interpreter', 0x0800, 0x500, [('assets/raw/a/files/adven-interp-obj.bin', 4, 0, 0x500)]),
        ('boot-a', 0x0800, 0x100, [('assets/raw/a/system/track-00.bin', 0, 0, 0x100)]),
        ('boot-b', 0x0800, 0x100, [('assets/raw/b/system/track-00.bin', 0, 0, 0x100)]),
        ('boot-stage2-a', 0xb700, 0x100, [('assets/raw/a/system/track-00.bin', 0x100, 0, 0x100)]),
        ('boot-stage2-b', 0xb700, 0x100, [('assets/raw/b/system/track-00.bin', 0x100, 0, 0x100)]),
        ('rwts-a', 0xb800, 0x800, [('assets/raw/a/system/track-00.bin', 0x200, 0, 0x800)]),
        ('rwts-b', 0xb800, 0x800, [('assets/raw/b/system/track-00.bin', 0x200, 0, 0x800)]),
        ('intrinsics', 0x0cfc, 0x1400, [('assets/raw/a/files/intrin-obj.bin', 0, 0, 0x1400)]),
        ('dos-low', 0x9b00, 0x1b00, [
            ('assets/raw/a/system/track-00.bin', 0xa00, 0, 0x600),
            ('assets/raw/a/system/track-01.bin', 0, 0x600, 0x1000),
            ('assets/raw/a/system/track-02.bin', 0, 0x1600, 0x500)]),
    ]
    covered = {}
    for name, address, length, spans in modules:
        subprocess.run(['ca65', '-g', '--bin-include-dir', str(out), str(ROOT / f'src/{name}.s'), '-o', str(out / f'{name}.o'),
                        '-l', str(out / f'{name}.lst')], check=True)
        subprocess.run(['ld65', '-C', str(ROOT / f'src/{name}.cfg'), str(out / f'{name}.o'),
                        '-o', str(out / f'{name}.bin'), '-m', str(out / f'{name}.map'),
                        '-Ln', str(out / f'{name}.lbl')], check=True)
        code = (out / f'{name}.bin').read_bytes()
        if len(code) != length:
            raise ValueError(f'{name}: output must occupy its original {length}-byte region')
        mapped = bytearray(length)
        encoded_equal, mapped_spans = True, []
        for asset, offset, source_offset, size in spans:
            native = (ROOT / asset).read_bytes()
            if offset < 0 or offset + size > len(native) or source_offset < 0 or source_offset + size > length:
                raise ValueError(f'{name}: mapping outside source or asset boundary')
            coverage = covered.setdefault(asset, bytearray(len(native)))
            if any(coverage[offset:offset+size]) or any(mapped[source_offset:source_offset+size]):
                raise ValueError(f'{name}: overlapping assembly mapping')
            coverage[offset:offset+size] = b'\x01' * size
            mapped[source_offset:source_offset+size] = b'\x01' * size
            payload = code[source_offset:source_offset + size]
            current = replacements.get(asset, native)
            replacements[asset] = current[:offset] + payload + current[offset + size:]
            encoded_equal &= payload == native[offset:offset + size]
            mapped_spans.append({'asset': asset, 'offset': offset, 'source_offset': source_offset, 'size': size})
        if not all(mapped):
            raise ValueError(f'{name}: unmapped assembled bytes')
        assembled.append({'source': f'src/{name}.s', 'load_address': address, 'size': len(code),
                          'sha256': hashlib.sha256(code).hexdigest(), 'spans': mapped_spans,
                          'original_encoding_equal': encoded_equal})
    repack(ROOT / 'assets/raw/manifest.json', out, replacements)
    manifest = json.loads((ROOT / 'assets/raw/manifest.json').read_text())
    dependencies = []
    for disk in manifest['disks']:
        for region in disk['regions']:
            if not region['role'].startswith('temporary'):
                continue
            # Header/tail of the interpreter file is retained data, not code.
            if region['path'] == 'assets/raw/a/files/adven-interp-obj.bin':
                continue
            coverage = covered.get(region['path'], bytearray(region['length']))
            ranges, start = [], None
            for offset, value in enumerate(coverage + b'\x01'):
                if not value and start is None:
                    start = offset
                elif value and start is not None:
                    ranges.append({'offset': start, 'size': offset - start})
                    start = None
            if ranges:
                dependencies.append({'side': disk['side'], 'path': region['path'],
                                     'role': region['role'], 'unassembled_ranges': ranges})
    (out / 'build.json').write_text(json.dumps({'status': 'early partial source build',
        'assembled': assembled,
        'editable_font_assets': [{'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted((ROOT / 'assets/decoded/font').glob('*.png'))],
        'temporary_raw_code_dependencies': dependencies}, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
