#!/usr/bin/env python3
"""Construct DOS Korean playtest media or synthetic fixtures from source builds.

Default: original English messages plus an explicit synthetic Korean caption.
--full-synthetic uses draft byte shapes but masks all translated pool bodies
before disk construction. --approved requires current human approval for every
translation and includes native UI and the title caption automatically.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from build_messages import build, labels, bind_media_id
from catalog import ROOT, extract, write_json, digest, validate, check_sources
from encoding import measure
from font import load_font, hgr_glyph
from packages import HEADER_BYTES, package as frame_package, split, identify, seal
from synthetic import mask_encoding
from native_ui import pack_parms, pack_labels, INTRINSIC_IDS, RUNTIME_IDS
from title_caption import add_caption
sys.path.insert(0,str(ROOT/'tools'))
from dos_disk import Disk, offset

A_BOOT_NOTICE = 'BOOT THE STARTUP DISK.'


def approved_catalog(baseline):
    catalog=json.loads((ROOT/'assets/korean/messages.json').read_text())
    validate(catalog,approved=True)
    check_sources(catalog,baseline)
    return catalog


def file_bytes(image, file):
    return b''.join(image[offset(*pair):offset(*pair)+256] for pair in file['sectors'])


def reusable_file_sectors(image):
    disk=Disk(image)
    catalog=disk.catalog()
    vtoc=disk.sector(17,0)
    reusable={(t,s) for t in range(35) for s in range(16)
              if int.from_bytes(vtoc[0x38+4*t:0x3a+4*t],'big') & (1<<s)}
    for f in catalog['files']:
        reusable.update(tuple(pair) for pair in f['sectors']+f['ts_lists'])
    return reusable


def dos_disk(seed, files, reusable_sectors=None):
    """Fresh deterministic allocation, one TS per file, original boot tracks."""
    if len(files)>105 or len({name[:10] for name,_,_ in files})!=len(files):
        raise ValueError('catalog capacity or native ten-character name collision')
    data=bytearray(143360);data[:3*4096]=seed[:3*4096]
    reserved={(t,s) for t in range(3) for s in range(16)}|{(17,s) for s in range(16)}
    available=[(t,s) for t in range(3,35) if t!=17 for s in range(16)]
    if reusable_sectors is not None:
        # Full B is not a DOS boot volume: native files legitimately occupy
        # parts of tracks 1/2. Reclaim only caller-audited file/free sectors.
        available=sorted(set(reusable_sectors))
        if any(not (1<=t<35 and t!=17 and 0<=s<16) for t,s in available):
            raise ValueError('unsafe reusable sector (track zero/catalog/out of range)')
        reserved={(t,s) for t in range(35) for s in range(16)}-set(available)
    cats=[(17,s) for s in range(15,0,-1)]
    for i,pair in enumerate(cats):
        base=offset(*pair)
        if i+1<len(cats):data[base+1:base+3]=bytes(cats[i+1])
    entries=[];used=set(reserved)
    for i,(name,kind,content) in enumerate(files):
        count=(len(content)+255)//256
        if not 0<count<=122 or len(available)<count+1 or len(name)>30:
            raise ValueError('file/disk allocation overflow: '+name)
        ts=available.pop(0);parts=available[:count];del available[:count]
        used.add(ts);used.update(parts)
        start=offset(*ts)
        data[start:start+256]=bytes(256)
        for j,pair in enumerate(parts):
            data[start+12+2*j:start+14+2*j]=bytes(pair)
            block=content[j*256:j*256+256].ljust(256,b'\0')
            data[offset(*pair):offset(*pair)+256]=block
        cat=cats[i//7];pos=offset(*cat)+11+(i%7)*35
        entry=bytes(ts)+bytes([kind])+bytes(ord(c)|128 for c in name.ljust(30))+struct.pack('<H',count+1)
        data[pos:pos+35]=entry
        entries.append({'name':name,'type':kind,'bytes':len(content),'sha256':digest(content),
                        'ts':ts,'data_sectors':parts})
    vtoc=bytearray(seed[offset(17,0):offset(17,0)+256]);vtoc[1:3]=bytes(cats[0])
    vtoc[0x34:0x38]=bytes([35,16,0,1])
    for t in range(35):
        bitmap=sum(1<<s for s in range(16) if (t,s) not in used)
        vtoc[0x38+4*t:0x3c+4*t]=bitmap.to_bytes(2,'big')+b'\0\0'
    data[offset(17,0):offset(17,0)+256]=vtoc
    disk=Disk(bytes(data));audited=disk.catalog()
    assert len(audited['files'])==len(files)
    for spec,actual in zip(files,audited['files']):
        assert actual['name']==spec[0]
        assert file_bytes(data,actual)==spec[2].ljust(actual['allocated_bytes'],b'\0')
    assert not set(available).intersection(disk.owners)
    vtoc=disk.sector(17,0)
    free={(t,s) for t in range(35) for s in range(16)
          if int.from_bytes(vtoc[0x38+4*t:0x3a+4*t],'big') & (1<<s)}
    assert free==set(available)
    return bytes(data),{'files':entries,'free_sectors':len(available),'sha256':digest(data)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scene',choices=['opening','snake'],default='opening')
    p.add_argument('--synthetic-shape',choices=['none','draft','stress'],default='none',
                   help='snake-only synthetic glyphs; draft supplies lengths, never translation text')
    p.add_argument('--full-synthetic',action='store_true',
                   help='complete A/B with all draft pool bodies replaced by test characters')
    p.add_argument('--approved',action='store_true',help='complete media using human-approved translations')
    p.add_argument('--native-ui',action='store_true',
                   help='full-synthetic only: pack native UI references into masked resident text')
    p.add_argument('--title-caption',action='store_true',
                   help='full-synthetic only: insert a masked resident title below the publisher credit')
    args=p.parse_args()
    if args.approved and args.full_synthetic:
        p.error('--approved and --full-synthetic are mutually exclusive')
    complete=args.full_synthetic or args.approved
    if args.approved:
        args.native_ui=True;args.title_caption=True
    if args.native_ui and not complete:
        p.error('--native-ui requires --full-synthetic; no unapproved text application')
    if args.title_caption and not complete:
        p.error('--title-caption requires --full-synthetic; no unapproved text application')
    if complete and (args.scene!='opening' or args.synthetic_shape!='none'):
        p.error('complete media cannot be combined with snake shape/scene overrides')
    baseline=ROOT/'build/korean/english-baseline'
    # Fail before creating output or compiling if human approval is stale.
    approved=approved_catalog(baseline) if args.approved else None
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    disk_names=({s:f'mask-of-sun-ko-{s}.dsk' for s in ('extra','a','b')} if args.approved else
                {'extra':'synthetic-startup.dsk','a':'synthetic-a.dsk','b':'synthetic-b.dsk'})
    runtime=build(out/'runtime',native_ui=args.native_ui);runtime_data=(out/'runtime/messages.bin').read_bytes()
    rs=labels(out/'runtime/messages.lbl')
    catalog,_=extract(baseline)
    for m in catalog['messages']:
        if m['status']!='excluded':m['ko']=m['source']
        if m['source']=='     BR0DERBUND SOFTWARE presents:':m['ko']='한국어 합성 시험 ABC 123'
    if args.synthetic_shape!='none':
        assert args.scene=='snake'
        drafts={m['id']:m for m in json.loads((ROOT/'assets/korean/messages.json').read_text())['messages']}
        shapes=[]
        for m in catalog['messages']:
            if m['status']=='excluded' or not any(r.get('file')=='ROOM 9.0' for r in m['references']):continue
            if args.synthetic_shape=='draft':
                m['ko']=''.join(c if c in ' \n' else '가' for c in drafts[m['id']]['ko'])
            else:m['ko']='\n'.join(['가'*39]*3)
            shapes.append({'id':m['id'],'cells':len(m['ko'].replace('\n','')),
                           'hangul':m['ko'].count('가'),'newlines':m['ko'].count('\n')})
        write_json(out/'timing-shape.json',{'mode':args.synthetic_shape,'messages':shapes,
                    'draft_sha256':digest((ROOT/'assets/korean/messages.json').read_bytes())})
    if complete:
        catalog=approved if args.approved else json.loads((ROOT/'assets/korean/messages.json').read_text())
    else:
        write_json(out/'synthetic-messages.json',catalog)
    report=measure(catalog,baseline,out/'encoding')
    if args.approved:
        report['kind']='approved Korean translation encoding for playtest media'
    if args.full_synthetic:
        mask_encoding(report,out/'encoding',json.loads((out/'encoding/glyphs.json').read_text()))
    caption=add_caption(report,out/'encoding',catalog) if args.title_caption else None
    ui_records=[]
    if args.native_ui:
        aliases=json.loads((out/'encoding/resident-aliases.json').read_text())
        runtime_data,ui_records=pack_labels(runtime_data,catalog,aliases,rs,0x9400,'runtime',RUNTIME_IDS)
        (out/'runtime/messages.bin').write_bytes(runtime_data)
    if args.scene=='snake':
        initial=next(f for f in report['files'] if f['side']=='a' and f['name']=='INITIAL')
        path=out/'encoding'/initial['package'];package=path.read_bytes();n=initial['script_bytes']
        script,local_pool=split(package)
        old=bytes(ord(c)|128 for c in '.G ROOM 1.0  ')
        new=bytes(ord(c)|128 for c in '.S P=1\r.G ROOM 9.0  ')
        assert script.count(old)==1
        script=script.replace(old,new);assert len(script)<=2048
        package=frame_package(script,local_pool,identity=package[8:20],sides=package[20])
        path.write_bytes(package)
        initial.update(script_bytes=len(script),package_bytes=len(package),sha256=digest(package),
                       package_sectors=(len(package)+255)//256,scenario_script_patch=True)
        write_json(out/'encoding/encoding.json',report)
    font=(out/'encoding/hangul-font.bin').read_bytes()
    used=set(json.loads((out/'encoding/glyphs.json').read_text()));glyphs=load_font()
    if not args.approved:
        # Retain the original fixed-size synthetic stress fixture.
        if len(used)>650:raise ValueError('synthetic glyph budget exceeded')
        padding=[chr(n) for n in range(0xac00,0xd7a4) if chr(n) not in used][:650-len(used)]
        font+=b''.join(hgr_glyph(glyphs[ord(c)]) for c in padding)
    if not 0<len(font)<=8192 or len(font)%8:raise ValueError('font exceeds LC capacity')
    font_count=len(font)//8
    resident=(out/'encoding/resident-pool.bin').read_bytes().ljust(4096,b'\0')
    assert len(resident)==4096
    # Bind one identity to every resource and the runtime before making disks.
    # Runtime identity is still zero here; headers therefore have no hash cycle.
    components=[('runtime',runtime_data),('font',font),('resident',resident)]
    if args.native_ui:
        components.append(('native-ui-tool',(ROOT/'tools/korean/native_ui.py').read_bytes()))
    components += [(str(path.relative_to(ROOT)),path.read_bytes()) for path in
                   sorted((ROOT/'src').rglob('*')) if path.is_file()]
    components += [(f'baseline-{side}',(baseline/f'mask-of-sun-{side}.dsk').read_bytes()) for side in ('a','b')]
    media_id=identify(report,out/'encoding',components)
    seal(report,out/'encoding',media_id)
    write_json(out/'encoding/encoding.json',report)
    runtime=bind_media_id(out/'runtime',media_id)
    runtime_data=(out/'runtime/messages.bin').read_bytes()
    assets={}
    for name,magic,content,count in [('runtime',b'KOC1',runtime_data,0),('font',b'KOF1',font,font_count),('resident',b'KOT1',resident,0)]:
        header=magic+struct.pack('<HH',len(content),count)+hashlib.sha256(content).digest()[:8]
        assets[name]=(header,content)
        (out/(name+'-asset.bin')).write_bytes(header+content)
    binding=[f'ko_room_size = ${rs["ko_room_size"]:04x}',f'runtime_lc_detect = ${rs["lc_detect"]:04x}',
             f'runtime_resident_size = ${rs["ko_resident_size"]:04x}',f'runtime_font_count = ${rs["ko_font_count"]:04x}',
             f'runtime_bytes = {len(runtime_data)}',f'font_bytes = {len(font)}',f'font_glyphs = {font_count}','resident_bytes = 4096']
    (out/'boot-bindings.inc').write_text('\n'.join(binding)+'\n')
    (out/'boot-headers.inc').write_text('\n'.join(name+'_header: .byte '+','.join(str(b) for b in header)
                                        for name,(header,_) in assets.items())+'\n')
    (out/'bootstrap.cfg').write_text('MEMORY { MAIN: start=$5000, size=$800, file=%O; }\nSEGMENTS { CODE: load=MAIN, type=rw; }\n')
    subprocess.run(['ca65','-g','-I',str(out),'-I',str(ROOT/'src/korean'),str(ROOT/'src/korean/bootstrap.s'),'-o',str(out/'bootstrap.o')],check=True)
    subprocess.run(['ld65','-C',str(out/'bootstrap.cfg'),str(out/'bootstrap.o'),'-o',str(out/'bootstrap.bin'),'-Ln',str(out/'bootstrap.lbl')],check=True)
    boot=(out/'bootstrap.bin').read_bytes()
    # Compile conditional engine bindings; default English output remains untouched.
    (out/'korean-bindings.inc').write_text('\n'.join(f'{name} = ${rs[name]:04x}' for name in
                                            ['ko_print_script_string','ko_load_dispatch','ko_finish_startup',
                                             'ko_save_prepare','ko_save_finish','ko_restore_finish']
                                            +(['ko_clear_message_rows'] if args.native_ui else []))+'\n')
    identity=hashlib.sha256(runtime_data+font+resident+boot)
    # Include rebuilt native assets (PARMS, pictures, ASCII font, DOS), not just
    # source names. A save must not silently cross a different native build.
    for side in ('a','b'):
        identity.update((baseline/f'mask-of-sun-{side}.dsk').read_bytes())
    for path in sorted((ROOT/'src').rglob('*')):
        if path.is_file():identity.update(path.relative_to(ROOT).as_posix().encode()+b'\0'+path.read_bytes())
    for item in report['files']:
        identity.update((out/'encoding'/item['package']).read_bytes())
    save_id=b'KOS1'+identity.digest()[:12]
    (out/'save-id.inc').write_text('.byte '+','.join(str(b) for b in save_id)+'\n')
    ui_defines=['-D','KOREAN_NATIVE_UI=1'] if args.native_ui else []
    subprocess.run(['ca65','-g','-D','KOREAN=1',*ui_defines,'-I',str(out),'-I',str(ROOT/'src'),str(ROOT/'src/intrinsics.s'),'-o',str(out/'intrinsics.o')],check=True)
    subprocess.run(['ld65','-C',str(ROOT/'src/intrinsics.cfg'),str(out/'intrinsics.o'),'-o',str(out/'intrinsics.bin'),'-Ln',str(out/'intrinsics.lbl')],check=True)
    intrinsic_symbols=labels(out/'intrinsics.lbl')
    assert intrinsic_symbols['ko_save_id']==0x1ff0
    if args.native_ui:
        # DOS binary includes the four-byte BLOAD header before the $0D00 payload.
        packed,records=pack_labels((out/'intrinsics.bin').read_bytes(),catalog,aliases,
                                  intrinsic_symbols,0x0d00-4,'intrinsic',INTRINSIC_IDS)
        (out/'intrinsics.bin').write_bytes(packed);ui_records.extend(records)
    subprocess.run(['ca65','-g','-D','KOREAN=1','-I',str(out),str(ROOT/'src/interpreter.s'),'-o',str(out/'interpreter.o')],check=True)
    subprocess.run(['ld65','-C',str(ROOT/'src/interpreter.cfg'),str(out/'interpreter.o'),'-o',str(out/'interpreter.bin'),'-Ln',str(out/'interpreter.lbl')],check=True)
    image=(baseline/'mask-of-sun-a.dsk').read_bytes();original=Disk(image).catalog()
    originals={f['name']:(f['type'],file_bytes(image,f)) for f in original['files']}
    if args.native_ui:
        packed,records=pack_parms(originals['PARMS.OBJ'][1],catalog,aliases)
        originals['PARMS.OBJ']=(originals['PARMS.OBJ'][0],packed)
        (out/'parms.bin').write_bytes(packed);ui_records.extend(records)
        write_json(out/'native-ui.json',{'kind':('resident references to approved translations' if args.approved else 'resident references to masked synthetic bodies'),
            'records':ui_records,'tool_sha256':digest((ROOT/'tools/korean/native_ui.py').read_bytes()),
            'translated_bodies_applied':args.approved,'fixed_lengths_preserved':True})
    resources={f['name']:f for f in report['files'] if f['side']=='a'}
    def resource(name):
        f=resources[name]
        assert f['script_fits'] and f['pool_bytes']<=1024,name
        return (name,0,(out/'encoding'/f['package']).read_bytes())
    start='POKE1012,0:HGR:HGR2\rBLOAD ADVEN INTERP.OBJ,A$800\rBLOAD PARMS.OBJ,A$300\rBLOAD KOBOOT,A$5000\rCALL20480\r'
    extra=[('START',0,bytes(ord(c)|128 for c in start)+b'\0'),
           ('ADVEN INTERP.OBJ',4,(out/'interpreter.bin').read_bytes()),
           ('PARMS.OBJ',*originals['PARMS.OBJ']),('KOBOOT',4,struct.pack('<HH',0x5000,len(boot))+boot),
           ('KO.RUNTIME',0,b''.join(assets['runtime'])),('KO.FONT',0,b''.join(assets['font'])),('KO.TEXT',0,b''.join(assets['resident'])),
           resource('INITIAL'),resource('LIBRARY'),('INTRIN.OBJ',4,(out/'intrinsics.bin').read_bytes()),
           ('CHAR GEN',*originals['CHAR GEN']),('LOGO',*originals['LOGO'])]
    extra_bytes,extra_report=dos_disk(image,extra)
    (out/disk_names['extra']).write_bytes(extra_bytes)
    game=[];game_b_report=None
    for f in original['files']:
        name=f['name']
        if name in resources:
            if complete or name in {'INITIAL','LIBRARY','DEATH','TRAVEL','TUNNEL'} or name.startswith(tuple('ROOM '+str(n)+'.' for n in range(1,10 if args.scene=='snake' else 8))):
                game.append(resource(name))
        elif complete and name=='ADVEN INTERP.OBJ':game.append((name,4,(out/'interpreter.bin').read_bytes()))
        elif complete and name=='START':
            notice=bytes(ord(c)|128 for c in 'PRINT "'+A_BOOT_NOTICE+'"\r')+b'\0'
            game.append((name,f['type'],notice.ljust(f['allocated_bytes'],b'\0')))
        elif name=='INTRIN.OBJ':game.append((name,4,(out/'intrinsics.bin').read_bytes()))
        else:game.append((name,f['type'],originals[name][1]))
    game_bytes,game_report=dos_disk(image,game,reusable_file_sectors(image) if complete else None)
    (out/disk_names['a']).write_bytes(game_bytes)
    if complete:
        seed=(baseline/'mask-of-sun-b.dsk').read_bytes()
        originals_b=Disk(seed).catalog()
        resources={f['name']:f for f in report['files'] if f['side']=='b'}
        game_b=[]
        for f in originals_b['files']:
            name=f['name']
            if name in resources:game_b.append(resource(name))
            elif name in ('INTRIN.OBJ','ADVEN INTERP.OBJ'):
                module='intrinsics' if name=='INTRIN.OBJ' else 'interpreter'
                game_b.append((name,4,(out/(module+'.bin')).read_bytes()))
            else:game_b.append((name,f['type'],file_bytes(seed,f)))
        packed,game_b_report=dos_disk(seed,game_b,reusable_file_sectors(seed))
        (out/disk_names['b']).write_bytes(packed)
    if args.approved:
        write_json(out/'approved-messages.json',catalog)
    write_json(out/'startup-build.json',{'kind':('approved Korean playtest A/B/startup' if args.approved else 'complete synthetic draft-shaped A/B/startup; no translated message bodies' if args.full_synthetic else 'synthetic cold-boot prototype; original English + synthetic Korean caption, no translation drafts'),
        'approved_translations':args.approved,'disk_names':disk_names,
        'catalog_sha256':digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode()),
        'tool_versions':{tool:subprocess.run([tool,'--version'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True).stdout.strip()
                         for tool in ('ca65','ld65')},
        'scene':args.scene,'synthetic_shape':args.synthetic_shape,'full_synthetic':args.full_synthetic,
        'native_ui':args.native_ui,'native_ui_records':ui_records,
        'title_caption':caption,
        'runtime':runtime,'bootstrap_bytes':len(boot),'bootstrap_sha256':digest(boot),
        'bootstrap_labels':{k:v for k,v in labels(out/'bootstrap.lbl').items() if k in ['bootstrap_entry','boot_wait_media','boot_no_lc_wait']},
        'runtime_labels':{k:rs[k] for k in ['ko_wait_game_media','ko_resource_retry','ko_load_error','ko_room_size','ko_resident_size','ko_font_count']},
        'media_id':media_id.hex(),'package_header_bytes':HEADER_BYTES,
        'save_id':save_id.hex(),'save_labels':{k:v for k,v in intrinsic_symbols.items() if k.startswith('ko_')},
        'source_hashes':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
                         [ROOT/'src/interpreter.s',ROOT/'src/intrinsics.s',ROOT/'src/korean/restore-guard.inc',ROOT/'src/korean/bootstrap.s',Path(__file__).resolve(),
                          ROOT/'tools/korean/encoding.py',ROOT/'tools/korean/title_caption.py',
                          ROOT/'tools/korean/native_ui.py',ROOT/'tools/korean/build_messages.py']},
        'font_bytes':len(font),'resident_bytes':len(resident),'asset_hashes':{k:digest(v[1]) for k,v in assets.items()},
        'source_disk_sha256':digest(image),'extra':extra_report,'game_a':game_report,'game_b':game_b_report,
        'scope_limit':('Approved translation integration for playtesting. Context, full-game completion, timed scenes and human screen review remain separate acceptance checks.' if args.approved else ('Complete synthetic allocation; runtime/gameplay verification is separate. '
                        +('Eleven native messages reference masked resident bodies. ' if args.native_ui else 'Native UI remains English. ')
                        +'No approved translations.') if args.full_synthetic else 'Opening resources through room7 only. Not final A/B packing, save/restore, whole-game timing or approved translation integration.')})
    print(json.dumps({'extra_free_sectors':extra_report['free_sectors'],'a_free_sectors':game_report['free_sectors'],
                      'runtime_bytes':len(runtime_data),'bootstrap_bytes':len(boot)}))


if __name__=='__main__':main()
