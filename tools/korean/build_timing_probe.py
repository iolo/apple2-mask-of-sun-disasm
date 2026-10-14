#!/usr/bin/env python3
"""Build cold-boot snake fixtures; native logic plus explicitly synthetic glyphs."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
from catalog import ROOT, digest, write_json
from build_messages import labels
from packages import split
sys.path.insert(0,str(ROOT/'tools'))
from dos_disk import Disk, offset


def high(text):return bytes(ord(c)|128 for c in text)


def markers(script):
    start=script.index(high('\r!TIME\r'))+len('\r!TIME\r')
    expire=script.index(high('.I B<250\r'),start)
    return {'window_start':0x6800+start,'expire_test':0x6800+expire,
            'script_sha256':digest(script),'script_bytes':len(script)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--profile',choices=['native','reference','draft','stress'],required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    baseline=ROOT/'build/korean/english-baseline'
    if args.profile=='native':
        image=bytearray((baseline/'mask-of-sun-a.dsk').read_bytes());files=Disk(bytes(image)).catalog()['files']
        native={f['name']:b''.join(image[offset(*pair):offset(*pair)+256] for pair in f['sectors']) for f in files}
        initial=native['INITIAL'];old=high('.G ROOM 1.0  ');assert initial.count(old)==1
        initial=initial[:initial.index(0)+1].replace(old,high('.S P=1\r.G ROOM 9.0  '))
        item=next(f for f in files if f['name']=='INITIAL');assert len(initial)<=item['allocated_bytes']
        initial=initial.ljust(item['allocated_bytes'],b'\0')
        for i,pair in enumerate(item['sectors']):image[offset(*pair):offset(*pair)+256]=initial[i*256:(i+1)*256]
        (out/'startup.dsk').write_bytes(image);(out/'game.dsk').write_bytes(image)
        script=native['ROOM 9.0'].split(b'\0',1)[0]+b'\0'
        success=native['ROOM 9.2'];death=native['DEATH'];built=None;renderer={};shape=None
    else:
        fixture=out/'startup'
        cmd=[sys.executable,str(ROOT/'tools/korean/startup_disk.py'),'--output',str(fixture),'--scene','snake']
        if args.profile!='reference':cmd+=['--synthetic-shape',args.profile]
        subprocess.run(cmd,check=True)
        (out/'startup.dsk').write_bytes((fixture/'synthetic-startup.dsk').read_bytes())
        (out/'game.dsk').write_bytes((fixture/'synthetic-a.dsk').read_bytes())
        report=json.loads((fixture/'encoding/encoding.json').read_text())
        def get(name):
            f=next(f for f in report['files'] if f['side']=='a' and f['name']==name)
            return split((fixture/'encoding'/f['package']).read_bytes())[0]
        script=get('ROOM 9.0');success=get('ROOM 9.2');death=get('DEATH')
        built=json.loads((fixture/'startup-build.json').read_text())
        symbols=labels(fixture/'runtime/messages.lbl')
        renderer={k:symbols[k] for k in ['ko_glyph_valid','ko_print_message','ko_reference_done','ko_bad_reference']}
        shape=json.loads((fixture/'timing-shape.json').read_text()) if (fixture/'timing-shape.json').exists() else None
    report={'profile':args.profile,'markers':markers(script),'success_prefix':list(success[:24]),
            'death_prefix':list(death[:24]),'startup_sha256':digest((out/'startup.dsk').read_bytes()),
            'game_sha256':digest((out/'game.dsk').read_bytes()),'build':built,'renderer_labels':renderer,'shape':shape,
            'scope':'Synthetic initializer sets P=1 then enters original ROOM 9.0 with the original inventory. No live PC/world injection. Not a full-route regression.'}
    write_json(out/'timing-build.json',report);print(out)


if __name__=='__main__':main()
