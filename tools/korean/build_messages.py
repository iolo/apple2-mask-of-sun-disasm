#!/usr/bin/env python3
"""Assemble main-RAM LC/message/loader code; no game patch or translation input."""
import argparse
from pathlib import Path
import json
import subprocess

from catalog import ROOT, digest, write_json


def labels(path):
    result = {}
    for line in path.read_text().splitlines():
        words = line.split()
        if len(words) == 3 and words[0] == 'al':
            result[words[2].lstrip('.')] = int(words[1], 16)
    return result


def bind_media_id(out, identity):
    if len(identity)!=12 or not any(identity):
        raise ValueError('missing runtime media identity')
    syms=labels(out/'messages.lbl')
    data=bytearray((out/'messages.bin').read_bytes())
    pos=syms['ko_media_id']-0x9400
    data[pos:pos+12]=identity
    (out/'messages.bin').write_bytes(data)
    report=json.loads((out/'build.json').read_text())
    report.update(sha256=digest(data),media_id=identity.hex())
    write_json(out/'build.json',report)
    return report


def build(out, baseline=ROOT/'build/korean/english-baseline', native_ui=False):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    native = labels(baseline/'chargen.lbl')
    aliases = ['locate_cursor_scanline', 'draw_eight_scanlines', 'advance_column']
    source = [f'ko_native_{name} = ${native[name]:04x}' for name in aliases]
    interpreter = labels(baseline/'interpreter.lbl')
    source.append(f'ko_native_print_script_string = ${interpreter["print_script_string"]:04x}')
    source.append(f'ko_native_file_loader = ${interpreter["load_named_file"]:04x}')
    source.append('ko_native_save_id = $1ff0')
    source += ['.include "lc.s"', '.include "messages.s"', '.include "loader.s"', '.include "dispatch.s"', '.include "save.s"']
    (out/'runtime_entry.s').write_text('\n'.join(source)+'\n')
    (out/'messages.cfg').write_text('MEMORY { MAIN: start=$9400, size=$800, file=%O; }\n'
                                     'SEGMENTS { CODE: load=MAIN, type=rw; }\n')
    defines = ['-D', 'KOREAN_NATIVE_UI=1'] if native_ui else []
    subprocess.run(['ca65', '-g', *defines, '-I', str(ROOT/'src/korean'), str(out/'runtime_entry.s'), '-o', str(out/'messages.o')],check=True)
    subprocess.run(['ld65', '-C', str(out/'messages.cfg'), str(out/'messages.o'), '-o', str(out/'messages.bin'),
                    '-Ln', str(out/'messages.lbl'), '-m', str(out/'messages.map')],check=True)
    data = (out/'messages.bin').read_bytes()
    report = {'kind':'candidate main-RAM Korean runtime; no game integration', 'load_address':0x9400,
              'bytes':len(data), 'remaining_in_2k':2048-len(data), 'sha256':digest(data), 'native_ui':native_ui,
              'source_hashes': {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
                               [ROOT/'src/korean/lc.s', ROOT/'src/korean/messages.s', ROOT/'src/korean/loader.s', ROOT/'src/korean/dispatch.s', ROOT/'src/korean/save.s']},
              'native_renderer_sha256':digest((baseline/'chargen.bin').read_bytes())}
    write_json(out/'build.json',report)
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'build/korean/messages')
    args=p.parse_args()
    print(build(args.output))
