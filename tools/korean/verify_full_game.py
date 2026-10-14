#!/usr/bin/env python3
"""Reach B and save/restore from complete media, then fresh-boot restore."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from build_messages import labels
from catalog import ROOT, digest, write_json, validate
from packages import split, HEADER_BYTES
from encoding import decode
from startup_disk import offset


def high(text):return bytes(ord(c)|128 for c in text)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rompath',type=Path,required=True)
    p.add_argument('--media',type=Path,required=True,help='existing --full-synthetic output')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT/'docs/evidence/korean/full-game-probe.json')
    p.add_argument('--ending',action='store_true',help='run the 122-command ending route instead of save/restore')
    p.add_argument('--recheck-results',action='store_true',help='recheck existing captures; require the same generated replay configuration')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=args.recheck_results)
    media=args.media.resolve();built=json.loads((media/'startup-build.json').read_text())
    approved=built.get('approved_translations',False)
    assert built['full_synthetic'] or approved
    disk_names=built.get('disk_names',{'extra':'synthetic-startup.dsk','a':'synthetic-a.dsk','b':'synthetic-b.dsk'})
    for path,h in built['source_hashes'].items():assert digest((ROOT/path).read_bytes())==h,path
    for side,key in [('extra','extra'),('a','game_a'),('b','game_b')]:
        assert digest((media/disk_names[side]).read_bytes())==built[key]['sha256']
    encoding=json.loads((media/'encoding/encoding.json').read_text())
    catalog=json.loads((ROOT/'assets/korean/messages.json').read_text())
    if approved:validate(catalog,approved=True)
    assert encoding['catalog_sha256']==digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode())
    resident=json.loads((media/'encoding/resident-aliases.json').read_text())
    lookups={}
    for f in encoding['files']:
        local={m:i for i,m in enumerate(f['message_ids'])}
        lookups[f['side'],f['name']]=resident|local
    def references(prefix,contains=False):
        result=[]
        for m in catalog['messages']:
            match=prefix.lstrip() in m['source'].lstrip() if contains else m['source'].lstrip().startswith(prefix.lstrip())
            if m['kind']!='script_text' or not match:continue
            for r in m['references']:
                result.append((r['file'],lookups[r['side'],r['file']][m['id']]))
        assert result,prefix
        return result
    media_messages={}
    for prefix,event in [('Place an initialized disk','save'),('Place SAVE GAME disk','save'),
                         ('Place THE MASK OF THE SUN disk, side','game')]:
        for file,index in references(prefix):
            assert file=='LIBRARY' and index&0x8000
            media_messages[str(index)]=event
    route_path=ROOT/('docs/full-route.json' if args.ending else 'docs/save-side-b-route.json')
    route=json.loads(route_path.read_text())
    commands=route['commands']
    for command in commands:
        if isinstance(command,dict) and 'wait_for' in command:
            command['wait_messages']=[f'{name}:{index}' for name,index in references(command.pop('wait_for'))]
        if isinstance(command,dict) and 'ready_text' in command:
            refs=references(command.pop('ready_text'))
            command['ready_messages']=[f'{"*" if index&0x8000 else name}:{index}' for name,index in refs]
            files={name for name,index in refs};assert len(files)==1
            filename=files.pop()
            f=next(f for f in encoding['files'] if f['name']==filename)
            replacements=[r for m in catalog['messages'] if m['status']!='excluded'
                          for r in m['references'] if r['path']==f['source']]
            def remap(address):
                offset=address-0x6800
                assert all(not r['offset']<offset<r['offset']+r['length'] for r in replacements)
                return address+sum(5-r['length'] for r in replacements if r['offset']<offset)
            command['script_range']=[remap(address) for address in command['script_range']]
    library=next(f for f in encoding['files'] if f['name']=='LIBRARY')
    script=split((media/'encoding'/library['package']).read_bytes())[0]
    start=script.index(high('\r!MORE\r'))
    begin=script.index(high('.W \r'),start)
    end=script.index(high('.S R=0\r'),begin)
    symbols=labels(media/'runtime/messages.lbl')
    config={'labels':{k:symbols[k] for k in ['ko_retry_name','ko_room_size','ko_print_message','ko_glyph_valid','ko_bad_reference',
                                          'ko_wait_game_media','ko_save_wait']},
            'pagination':[0x7000+begin,0x7000+end],'media_messages':media_messages,
            'pools':{f['side']+'/'+f['name']:{'path':str(media/'encoding'/f['package']),
                                           'offset':HEADER_BYTES+f['script_bytes'],'bytes':f['pool_bytes']}
                     for f in encoding['files']},
            'resident':str(media/'resident-asset.bin'),'font':str(media/'font-asset.bin')}
    def message_keys(prefix,contains=False):
        return [f'{"*" if index&0x8000 else name}:{index}' for name,index in references(prefix,contains)]
    if args.ending:config['ending_messages']=message_keys(route['ending_text'])
    # Recognize the actual translated bottom-row waiting caption as pixels.
    # Animated rooms may poll keys without LIBRARY's .W loop.
    waiting=next(m['id'] for m in catalog['messages'] if m['source'].strip()=='[ waiting ]')
    glyphs=json.loads((media/'encoding/glyphs.json').read_text())
    font=(media/'encoding/hangul-font.bin').read_bytes()
    pool=(media/'encoding/resident-pool.bin').read_bytes();n=resident[waiting]&0x7fff
    at=int.from_bytes(pool[2+n*2:4+n*2],'little');end=at
    while pool[end]:end+=2 if pool[end]>=128 else 1
    text=decode(pool[at:end+1],glyphs)
    config['waiting_glyphs']=[ord(c) if ord(c)<128 else list(font[glyphs.index(c)*8:glyphs.index(c)*8+8]) for c in text]
    blank=out/'blank-save.dsk'
    if not args.recheck_results:
        subprocess.run(['a2kit','mkdsk','--os','dos33','--type','do','--volume','254','--dimg',str(blank)],check=True)
    reports=[]
    for profile in (('ending',) if args.ending else ('same-session','fresh-boot')):
        session=out/profile
        # The session launcher owns copies of startup and A. B/save are separate
        # owned copies; this probe never mounts the source media for writing.
        bcopy=out/(profile+'-b.dsk')
        save=out/(profile+'-save.dsk')
        if not args.recheck_results:
            shutil.copyfile(media/disk_names['b'],bcopy)
            shutil.copyfile(out/'same-session-save.dsk' if profile=='fresh-boot' else blank,save)
        active=dict(config,commands=['RESTORE GAME','Y','LOOK','INVENTORY'] if profile=='fresh-boot' else commands,
                    timeout=route['timeout'] if args.ending else 1800 if profile=='same-session' else 400,
                    media={'a':'side-b.dsk','b':str(bcopy),'save':str(save)})
        config_path=out/(profile+'-config.json')
        if args.recheck_results:assert json.loads(config_path.read_text())==active,'replay configuration changed'
        else:write_json(config_path,active)
        cmd=[sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(args.rompath.resolve()),
             '--disk-a',str(media/disk_names['extra']),'--disk-b',str(media/disk_names['a']),
             '--output',str(session),'--headless','--fast','--language-card',
             '--script',str(ROOT/'tools/korean/full_game_probe.lua')]
        if not args.recheck_results:
            with (out/(profile+'.log')).open('w') as log:
                subprocess.run(cmd,env=dict(os.environ,MASK_KOREAN_GAME_CONFIG=str(config_path)),stdout=log,
                               stderr=subprocess.STDOUT,timeout=300,check=True)
        result=json.loads((session/'full-game-probe.json').read_text())
        assert result['pass'] and result['bad_references']==0 and result['room_pool_checks']==len(active['commands'])+(0 if args.ending else 1),result
        def ram(index):return (session/f'prompt-{index:03d}-ram.bin').read_bytes()
        checks=[]
        if args.ending:
            for requirement in route['requirements']:
                if requirement['id']=='gold-bowl':
                    observed=all(any(result['seen_messages'].get(k) for k in message_keys(text))
                                 for text in ('You pick up ','a precious gold bowl'))
                    # The text is composed by !OBJL. Confirm the picked-up
                    # object as well: TC(18)=0 and TL(18)=255 after GET BOWL.
                    observed=observed and ram(42)[0x622a]==0 and ram(42)[0x6326]==255
                else:observed=any(result['seen_messages'].get(k) for k in message_keys(requirement['text'],contains=True))
                assert observed,requirement
                checks.append(dict(requirement,passed=True))
            assert {'a','b'}<={event['side'] for event in result['events'] if event['kind']=='mount'}
        elif profile=='same-session':
            for c in route['ram_checks']:
                actual=ram(c['before_command'])[c['address']]
                assert actual==c['equals'],(c,actual)
                checks.append(dict(c,actual=actual,passed=True))
            for c in route['ram_ranges_equal']:
                a=c['address'];n=c['length']
                assert ram(c['before_command'])[a:a+n]==ram(c['after_command'])[a:a+n],c
                checks.append(dict(c,passed=True))
            saved=save.read_bytes()
            assert saved[offset(22,15):offset(22,15)+16].hex()==built['save_id']
        else:
            restored=ram(3)
            original=(out/'same-session/prompt-060-ram.bin').read_bytes()
            assert restored[0x600d]==34 and restored[0x601c]==2 and restored[0x621a]==0
            assert restored[0x6020:0x650c]==original[0x6020:0x650c]
            saved=save.read_bytes()
            snapshot=b''.join(saved[offset(t,s):offset(t,s)+256] for t in range(23,32) for s in range(16))
            assert restored[0x6800:0x7000]==snapshot[0x4800:0x5000]
            checks.append({'id':'fresh-boot-B-world-and-mutated-script-preserved','passed':True})
        assert digest(bcopy.read_bytes())==built['game_b']['sha256']
        assert digest((session/'side-b.dsk').read_bytes())==built['game_a']['sha256']
        result.update(profile=profile,checks=checks,session=json.loads((session/'session.json').read_text()))
        reports.append(result);print('PASS: '+profile,flush=True)
    write_json(args.evidence,{'pass':True,'runs':reports,'build':built,
               'scope':('Full 122-command ending route with original English commands and source-linked message checks. Natural keyboard and real one-drive media, no CPU/world injection. Successful timed-scene progression is not a timing-window comparison or human contextual playtest acceptance.' if args.ending else 'Approved Korean r01 media. Original route through first pyramid and A-to-B transition, B room34 same-session save/restore and fresh-boot restore. Natural keyboard and real one-drive media, no CPU/world injection. Not ending, all timed scenes, full layout or human contextual playtest acceptance.' if approved else 'Full synthetic draft-shaped A/B media. Original route through first pyramid and A-to-B transition, B room34 same-session save/restore and fresh-boot restore. Natural keyboard and real one-drive media, no CPU/world injection. '
                        +('Eleven native messages reference masked synthetic text. ' if built.get('native_ui') else 'Native UI remains English. ')
                        +'Synthetic message bodies are not translations. Not ending, all timed scenes, full layout or human approval.'),
               'source_sha256':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
                                [Path(__file__).resolve(),ROOT/'tools/korean/full_game_probe.lua']}})
    print('PASS: '+str(args.evidence))


if __name__=='__main__':main()
