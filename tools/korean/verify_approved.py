#!/usr/bin/env python3
"""Verify approved text in every pool, disk-file readback and repeat-build bytes."""
import argparse
import json
from pathlib import Path

from catalog import ROOT, digest, review_hash, validate, write_json
from encoding import decode, encode
from packages import split
from startup_disk import Disk, file_bytes, SAVE_SECTORS


def read(path):return json.loads(path.read_text())


def verify(media, repeat, approval):
    built=read(media/'startup-build.json');catalog=read(media/'approved-messages.json')
    validate(catalog,approved=True)
    assert built['approved_translations'] and not built['full_synthetic']
    catalog_hash=digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode())
    assert catalog_hash==built['catalog_sha256']==approval['approved_catalog_sha256']
    active={m['id']:m for m in catalog['messages'] if m['status']!='excluded'}
    assert {mid:review_hash(m) for mid,m in active.items()}==approval['message_review_hashes']
    enc=read(media/'encoding/encoding.json');assert enc['catalog_sha256']==catalog_hash
    chars=read(media/'encoding/glyphs.json');ids={c:i for i,c in enumerate(chars)}
    resident=(media/'encoding/resident-pool.bin').read_bytes()
    aliases=read(media/'encoding/resident-aliases.json');checked=set()
    def check(pool,mid,index):
        at=int.from_bytes(pool[2+index*2:4+index*2],'little')
        wanted=encode(active[mid]['ko'],ids)
        assert decode(pool[at:at+len(wanted)],chars)==active[mid]['ko'],mid
        checked.add(mid)
    for mid,i in aliases.items():check(resident,mid,i&0x7fff)
    for f in enc['files']:
        data=(media/'encoding'/f['package']).read_bytes()
        assert digest(data)==f['sha256']
        script,pool=split(data)
        assert len(script)<=f['script_limit'] and len(pool)<=1024
        for i,mid in enumerate(f['message_ids']):check(pool,mid,i)
    assert checked==set(active)
    for side,key in [('extra','extra'),('a','game_a'),('b','game_b')]:
        image=(media/built['disk_names'][side]).read_bytes()
        assert digest(image)==built[key]['sha256']
        disk=Disk(image);files=disk.catalog()['files']
        assert len(files)==len(built[key]['files'])
        for record,f in zip(built[key]['files'],files):
            assert record['name']==f['name']
            assert digest(file_bytes(image,f)[:record['bytes']])==record['sha256']
        if side=='extra' and built.get('save_media',{}).get('disk')=='extra':
            assert {tuple(pair) for pair in built['extra']['save_sectors']}==SAVE_SECTORS
            assert not SAVE_SECTORS.intersection(disk.owners)
            vtoc=disk.sector(17,0)
            for t,s in SAVE_SECTORS:
                assert not int.from_bytes(vtoc[0x38+4*t:0x3a+4*t],'big')&(1<<s)
                assert disk.sector(t,s)==bytes(256)
    identical={}
    for name in [*built['disk_names'].values(),'runtime-asset.bin','font-asset.bin','resident-asset.bin',
                 'bootstrap.bin','interpreter.bin','intrinsics.bin','parms.bin']:
        assert (media/name).read_bytes()==(repeat/name).read_bytes(),name
        identical[name]=digest((media/name).read_bytes())
    return dict(pass_validation=True,approved_entries_verified=len(checked),approved_catalog_sha256=catalog_hash,
        human_contextual_playtest_acceptance=False,all_allocated_file_hashes_verified=True,
        save_media=built.get('save_media'),
        identical_artifacts=identical,free_sectors={k:built[k]['free_sectors'] for k in ['extra','game_a','game_b']},
        runtime_bytes=built['runtime']['bytes'],font_bytes=enc['font_bytes'],glyph_count=enc['glyph_count'],
        resident_pool_bytes=enc['resident_pool_bytes'],largest_room_pool=enc['largest_room_pool'],
        font_source=read(ROOT/'assets/korean/font/source.json'),
        verifier_sha256=digest(Path(__file__).read_bytes()))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--media',type=Path,required=True);p.add_argument('--repeat',type=Path,required=True)
    p.add_argument('--approval',type=Path,default=ROOT/'docs/korean/approval-r01.json')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=verify(args.media,args.repeat,read(args.approval));write_json(args.output,result)
    print('PASS: approved pool bodies, disk files and ten repeat-build artifacts')
