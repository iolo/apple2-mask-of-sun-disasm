#!/usr/bin/env python3
"""Cold-boot a synthetic title; prove exact caption pixels and logo preservation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from build_messages import labels
from catalog import ROOT, DEFAULT, digest, write_json, validate
from encoding import decode, referenced_script
from font import load_font, subset
from packages import split
from startup_disk import Disk, file_bytes


def read(path):return json.loads(path.read_text())


def verify(media, reference, output, rompath):
    output.mkdir(parents=True,exist_ok=False)
    built=read(media/'startup-build.json');encoded=read(media/'encoding/encoding.json')
    approved=built.get('approved_translations',False)
    catalog=read(DEFAULT);caption=built['title_caption']
    assert (built['full_synthetic'] or approved) and caption
    assert encoded['catalog_sha256']==digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode())
    if approved:validate(catalog,approved=True)
    else:assert reference is not None,'synthetic verification requires reference media'
    prior=read(reference/'encoding/encoding.json') if reference else None
    if prior:assert encoded['catalog_sha256']==prior['catalog_sha256']
    for path,h in (built['source_hashes']|built['runtime']['source_hashes']).items():assert digest((ROOT/path).read_bytes())==h,path
    previous={(f['side'],f['name']):f for f in prior['files']} if prior else {}
    aliases=read(media/'encoding/resident-aliases.json')
    compared=0
    for f in encoded['files']:
        b,newpool=split((media/'encoding'/f['package']).read_bytes())
        if prior:
            old=previous[f['side'],f['name']]
            a,pool=split((reference/'encoding'/old['package']).read_bytes())
            assert pool==newpool
        else:
            lookup=aliases|{mid:i for i,mid in enumerate(f['message_ids'])}
            replacements=[(r,lookup[m['id']]) for m in catalog['messages'] if m['status']!='excluded'
                          for r in m['references'] if r['path']==f['source']]
            a=referenced_script((ROOT/f['source']).read_bytes(),replacements)
        if f['side']=='a' and f['name']=='INITIAL':
            at,n=caption['insertion_offset'],caption['inserted_bytes']
            assert b[at:at+n].hex()==caption['insertion_hex']
            assert b[:at]+b[at+n:]==a and digest(a)==caption['original_script_sha256']
        else:assert a==b,(f['side'],f['name'])
        compared+=1
    if prior:
        for name in ['resident-pool.bin','hangul-font.bin','resident-aliases.json','glyphs.json']:
            assert (media/'encoding'/name).read_bytes()==(reference/'encoding'/name).read_bytes(),name
    names=built.get('disk_names',{'extra':'synthetic-startup.dsk','a':'synthetic-a.dsk','b':'synthetic-b.dsk'})
    for side,key in [('extra','extra'),('a','game_a'),('b','game_b')]:
        image=(media/names[side]).read_bytes();assert digest(image)==built[key]['sha256']
        files={f['name']:f for f in Disk(image).catalog()['files']}
        if 'INITIAL' in files:
            wanted=(media/'encoding'/caption['package']).read_bytes()
            assert file_bytes(image,files['INITIAL'])[:len(wanted)]==wanted
    glyphs=read(media/'encoding/glyphs.json');font=(media/'encoding/hangul-font.bin').read_bytes()
    pool=(media/'encoding/resident-pool.bin').read_bytes();n=caption['message_id']&0x7fff
    at=int.from_bytes(pool[2+n*2:4+n*2],'little');end=at
    while pool[end]:end+=2 if pool[end]>=128 else 1
    text=decode(pool[at:end+1],glyphs)
    assert len(text)==caption['cells']
    if approved:assert text==next(m['ko'] for m in catalog['messages'] if m['id']=='picture:title')
    else:assert set(text)<=set('X '+encoded['synthetic_test_glyph'])
    symbols=labels(media/'runtime/messages.lbl')
    config=dict(pointer=0x6800+caption['reference_offset'],labels={k:symbols[k] for k in
                ['ko_print_script_string','ko_reference_done','ko_wait_game_media']})
    write_json(output/'config.json',config)
    session=output/'session'
    with (output/'mame.log').open('w') as log:
        subprocess.run([sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(rompath),
            '--disk-a',str(media/names['extra']),'--disk-b',str(media/names['a']),
            '--output',str(session),'--headless','--fast','--language-card','--script',str(ROOT/'tools/korean/title_probe.lua')],
            env=dict(os.environ,MASK_KOREAN_TITLE_CONFIG=str(output/'config.json')),stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
    run=read(session/'title-probe.json');assert run['pass'],run
    before=(session/'before-hgr.bin').read_bytes();after=(session/'after-hgr.bin').read_bytes()
    state=run['before'];assert (state['row'],state['column'])==(caption['row'],caption['column'])
    assert (run['after']['row'],run['after']['column'])==(2,0)
    assert state['page']==run['after']['page'] and state['background']==run['after']['background']
    expected=bytearray(before);changed=set();row,col=caption['row'],caption['column']
    ascii_chars,ascii_font=subset(''.join(chr(c) for c in range(32,127)),load_font())
    bitmaps={c:ascii_font[i*8:i*8+8] for i,c in enumerate(ascii_chars)}
    bitmaps.update({c:font[i*8:i*8+8] for i,c in enumerate(glyphs)})
    for char in text+' ':  # CR erases the cell after the caption before moving down.
        for y,value in enumerate(bitmaps[char]):
            scan=row*12+y
            at=(scan&7)*1024+((scan>>3)&7)*128+(scan>>6)*40+col+(8192 if state['page'] else 0)
            assert before[at]&127==0,'caption would cover existing artwork'
            expected[at]=value^state['background'];changed.add(at)
        col+=1
    assert after==expected,'caption pixels or preserved logo/page bytes mismatch'
    screenshot=session/'snapshot_directory/title-complete.png'
    shutil.copyfile(screenshot,output/'title.png')
    result=dict(pass_validation=True,kind='natural cold-boot title-caption integration with exact before/after HGR comparison',
        catalog_sha256=encoded['catalog_sha256'],caption=caption,caption_text=text,approved_translations=approved,
        compared_script_resources=compared,all_pools_and_font_unchanged=True if prior else None,
        checked_hgr_bytes=len(after),caption_cell_bytes=len(changed),preserved_hgr_bytes=len(after)-len(changed),
        before_hgr_sha256=digest(before),after_hgr_sha256=digest(after),
        screenshot_sha256=digest(screenshot.read_bytes()),run=run,session=read(session/'session.json'),
        runtime_bytes=built['runtime']['bytes'],free_sectors={key:built[key]['free_sectors'] for key in ['extra','game_a','game_b']},
        script_bytes=next(f['script_bytes'] for f in encoded['files'] if f['name']=='INITIAL'),
        media=str(media),reference_media=str(reference),
        disk_sha256={key:built[key]['sha256'] for key in ['extra','game_a','game_b']},
        source_sha256={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
          [Path(__file__).resolve(),ROOT/'tools/korean/title_probe.lua',ROOT/'tools/korean/title_caption.py',
           ROOT/'tools/korean/startup_disk.py',ROOT/'tools/korean/encoding.py']},
        limits=['Approved r01 caption; human contextual playtest acceptance pending.' if approved else 'Masked synthetic caption only; no human-approved translation applied.',
                'Natural boot stops at first A-media request. Full route/save/timing regression is separate.',
                'No native logo asset, control branch, input wait or world initialization statement changed.'])
    write_json(output/'title-validation.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--media',type=Path,required=True)
    p.add_argument('--reference-media',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rompath',type=Path,required=True);args=p.parse_args()
    r=verify(args.media.resolve(),args.reference_media.resolve() if args.reference_media else None,args.output.resolve(),args.rompath.resolve())
    print(json.dumps({k:r[k] for k in ['pass_validation','script_bytes','runtime_bytes','free_sectors','preserved_hgr_bytes']}))
