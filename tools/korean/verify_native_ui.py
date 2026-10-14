#!/usr/bin/env python3
"""Audit synthetic native-UI packing and preserved bytes on all three disks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from build_full_media_probe import check_synthetic_pool
from build_messages import labels
from catalog import ROOT, DEFAULT, digest, write_json
from native_ui import INTRINSIC_IDS, RUNTIME_IDS, reference
from packages import split
from startup_disk import Disk, file_bytes


def read(path):return json.loads(path.read_text())


def audit(media, output):
    output.mkdir(parents=True, exist_ok=False)
    built=read(media/'startup-build.json')
    if not built['full_synthetic'] or not built.get('native_ui'):
        raise ValueError('requires full masked synthetic native UI build')
    for path, expected in (built['source_hashes']|built['runtime']['source_hashes']).items():
        if digest((ROOT/path).read_bytes()) != expected:raise ValueError('stale source: '+path)
    metadata=read(media/'native-ui.json')
    if metadata['tool_sha256'] != digest((ROOT/'tools/korean/native_ui.py').read_bytes()):
        raise ValueError('stale native UI packer')
    catalog=read(DEFAULT);messages={m['id']:m for m in catalog['messages']}
    aliases=read(media/'encoding/resident-aliases.json')
    encoding=read(media/'encoding/encoding.json')
    if encoding['catalog_sha256'] != digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode()):
        raise ValueError('stale catalog')
    records=metadata['records']
    expected_ids={f'parms:error-{i}' for i in range(4)}|{'intrinsic:'+s for s in INTRINSIC_IDS}|{'runtime:'+s for s in RUNTIME_IDS}
    if len(records)!=11 or {r['id'] for r in records}!=expected_ids:
        raise ValueError('missing/duplicate native UI patches')
    # Relink the objects from the exact fixture to obtain pre-packing bytes.
    # These contain the conditional engine/save guard but no UI string changes.
    for module, config, obj in [('intrinsics',ROOT/'src/intrinsics.cfg',media/'intrinsics.o'),
                               ('runtime',media/'runtime/messages.cfg',media/'runtime/messages.o')]:
        subprocess.run(['ld65','-C',str(config),str(obj),'-o',str(output/(module+'-unpacked.bin'))],check=True)
    original_runtime=bytearray((output/'runtime-unpacked.bin').read_bytes())
    rs=labels(media/'runtime/messages.lbl')
    at=rs['ko_media_id']-0x9400
    original_runtime[at:at+12]=bytes.fromhex(built['media_id'])
    modules={'runtime':(bytes(original_runtime),(media/'runtime/messages.bin').read_bytes()),
             'intrinsic':((output/'intrinsics-unpacked.bin').read_bytes(),(media/'intrinsics.bin').read_bytes()),
             'parms':((ROOT/'assets/raw/a/files/parms-obj.bin').read_bytes(),(media/'parms.bin').read_bytes())}
    preserved={}
    for module,(original,actual) in modules.items():
        if len(original)!=len(actual):raise ValueError('module length changed: '+module)
        expected=bytearray(original);owned=set()
        for r in records:
            if not r['id'].startswith(module+':'):continue
            at,n=r['offset'],r['slot_bytes']
            positions=set(range(at,at+n))
            if at<0 or at+n>len(expected) or owned&positions:raise ValueError('invalid native UI slot')
            owned|=positions
            if digest(original[at:at+n])!=r['original_sha256']:raise ValueError('source slot changed: '+r['id'])
            ref=reference(messages[r['id']],aliases)
            if ref.hex()!=r['reference_hex']:raise ValueError('stale reference ID: '+r['id'])
            expected[at:at+n]=ref.ljust(n,b'\0')
        if actual!=expected:raise ValueError('bytes outside declared patches changed: '+module)
        preserved[module]={'bytes':len(actual),'patched_slot_bytes':len(owned),
                           'preserved_bytes':len(actual)-len(owned),'sha256':digest(actual)}
    glyphs=read(media/'encoding/glyphs.json')
    check_synthetic_pool((media/'encoding/resident-pool.bin').read_bytes(),glyphs,encoding['synthetic_test_glyph'])
    for resource in encoding['files']:
        _,pool=split((media/'encoding'/resource['package']).read_bytes())
        check_synthetic_pool(pool,glyphs,encoding['synthetic_test_glyph'])
    retained=[];counts={}
    for side,key in [('startup','extra'),('a','game_a'),('b','game_b')]:
        image=(media/f'synthetic-{side}.dsk').read_bytes()
        if digest(image)!=built[key]['sha256']:raise ValueError('disk hash changed: '+side)
        files={f['name']:f for f in Disk(image).catalog()['files']}
        counts[side]=len(files)
        for spec in built[key]['files']:
            data=file_bytes(image,files[spec['name']])
            if digest(data[:spec['bytes']])!=spec['sha256'] or any(data[spec['bytes']:]):
                raise ValueError('disk content/padding mismatch: '+spec['name'])
        if side=='startup':
            if file_bytes(image,files['KO.RUNTIME'])[:16+built['runtime']['bytes']]!=(media/'runtime-asset.bin').read_bytes():
                raise ValueError('startup runtime differs')
        if 'PARMS.OBJ' in files:
            if file_bytes(image,files['PARMS.OBJ'])!=(media/'parms.bin').read_bytes():raise ValueError('unpatched PARMS disk copy')
        if side in ('a','b'):
            baseline=(ROOT/f'build/korean/english-baseline/mask-of-sun-{side}.dsk').read_bytes()
            originals={f['name']:f for f in Disk(baseline).catalog()['files']}
            if set(files)!=set(originals):raise ValueError('changed game file names')
            resources={f['name']:f for f in encoding['files'] if f['side']==side}
            for name,spec in resources.items():
                package=(media/'encoding'/spec['package']).read_bytes()
                if file_bytes(image,files[name])[:len(package)]!=package:raise ValueError('resource mismatch')
            for name,spec in originals.items():
                if name in resources or name in {'START','PARMS.OBJ','INTRIN.OBJ','ADVEN INTERP.OBJ'}:continue
                if file_bytes(image,files[name])!=file_bytes(baseline,spec):raise ValueError('native asset changed: '+name)
                retained.append({'side':side,'name':name})
    result=dict(kind='masked synthetic native-UI packing audit',pass_audit=True,
        catalog_sha256=encoding['catalog_sha256'],native_ui_records=records,preserved_modules=preserved,
        preserved_native_files=retained,disk_files=counts,
        free_sectors={key:built[key]['free_sectors'] for key in ['extra','game_a','game_b']},
        runtime_bytes=built['runtime']['bytes'],masked_pools_checked=1+len(encoding['files']),
        media_id=built['media_id'],save_id=built['save_id'],
        synthetic_disk_sha256={key:built[key]['sha256'] for key in ['extra','game_a','game_b']},
        source_sha256={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
                       [Path(__file__).resolve(),ROOT/'tools/korean/native_ui.py',ROOT/'tools/korean/startup_disk.py',
                        ROOT/'tools/korean/build_messages.py',ROOT/'src/korean/dispatch.s',ROOT/'src/korean/save.s']},
        limits=['Host packing proof, not execution of every native error branch.',
                'Only references to masked synthetic bodies; no approved translation applied.',
                'Excluded recovery/boot notices, ASCII side letters and OK prompts are preserved.'])
    write_json(output/'native-ui-audit.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--media',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rompath',type=Path,help='also run 26 packed-string/dirty-HGR cases on Apple II+ + LC')
    args=p.parse_args();out=args.output.resolve();r=audit(args.media.resolve(),out)
    if args.rompath:
        from build_native_ui_probe import build
        fixture=out/'screen-fixture';session=out/'screen-session'
        screen_build=build(args.media.resolve(),fixture)
        with (out/'screen.log').open('w') as log:
            subprocess.run([sys.executable,str(ROOT/'tools/mame_session.py'),
                '--rompath',str(args.rompath.resolve()),'--disk-a',str(ROOT/'build/korean/english-baseline/mask-of-sun-a.dsk'),
                '--output',str(session),'--headless','--fast','--debug','--language-card',
                '--script',str(ROOT/'tools/korean/native_ui_probe.lua')],
                env=dict(os.environ,MASK_KOREAN_NATIVE_UI=str(fixture)),stdout=log,stderr=subprocess.STDOUT,
                timeout=60,check=True)
        probe=read(session/'native-ui-probe.json')
        if not probe['pass'] or probe['case_count']!=len(screen_build['cases']):raise ValueError('native UI screen probe failed')
        r.update(screen_probe=probe,screen_fixture=screen_build,screen_session=read(session/'session.json'),
                 screen_scope='Instruction-boundary harness: 11 packed messages and native A/B prompt composition on both dirty HGR pages; page 1 inverse; room cache invalid. Compare all 16KB HGR and 13KB LC after each of 26 calls. This does not trigger every native error condition.')
        for name in ['build_native_ui_probe.py','native_ui_probe.lua']:
            r['source_sha256']['tools/korean/'+name]=digest((ROOT/'tools/korean'/name).read_bytes())
        write_json(out/'native-ui-audit.json',r)
    print(json.dumps(dict(pass_audit=r['pass_audit'],patched_messages=len(r['native_ui_records']),
                         preserved_native_files=len(r['preserved_native_files']),masked_pools=r['masked_pools_checked'])))
