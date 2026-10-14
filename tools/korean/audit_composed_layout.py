#!/usr/bin/env python3
"""Source-guarded host layout checks for inventory and multi-part media UI.

This models explicitly audited native call sequences. It does not execute the
6502 or establish reachability of an artificial inventory containing every item.
"""
import argparse
import json
from pathlib import Path

from catalog import ROOT, DEFAULT, check_sources, digest, script_lines, validate, write_json
from font import load_font, subset
from layout_preview import Screen, displayed, part


def emit(screen, message):
    p=part(message)
    screen.text(p['text'],p['newline'],p['id'],p['role'])


def check(screen):
    r=screen.result()
    return not (r['overwrites'] or r['body_on_prompt_row'] or r['outside'])


def inventory_pages(items, heading, wait, nearby):
    """Audited !ALTP/!INVN: I=3 nearby, I=12 on the full inventory page."""
    if not items:
        raise ValueError('empty inventory has caller-dependent cursor; outside this model')
    for item in items:
        if '\n' in displayed(item) or len(displayed(item))>=40 or item['layout']['newline']:
            raise ValueError('item no longer fits the one-row inventory invariant: '+item['id'])
    pages=[];screen=Screen(row=12 if nearby else 0)
    emit(screen,heading)
    if not nearby:screen.cr('blank heading separator')
    count=1 if nearby else 0
    limit=3 if nearby else 12
    def finish(prompt):
        screen.row=15
        if prompt=='wait':emit(screen,wait)
        else:screen.text('OK>',False,'native command prompt','prompt')
        pages.append(screen)
    for item in items:
        if count==limit:
            finish('wait')
            screen=Screen(row=12 if nearby else 0);count=0
        emit(screen,item);screen.cr('native blank .P after !OBJL');count+=1
    finish('command' if nearby else 'wait')
    return pages


def audit(catalog, baseline, output):
    validate(catalog);check_sources(catalog,baseline);output.mkdir(parents=True,exist_ok=True)
    by_id={m['id']:m for m in catalog['messages']}
    raw=(ROOT/'assets/raw/a/files/library.bin').read_bytes();lines=script_lines(raw)
    guards=[]
    for first,last,expected in [
        (68,96,'51e7348d2ff2beb1cb8fe413e5fe048e1540b5c8b007f8b29c022c625366586f'),
        (245,316,'96f12a05f889119c8226e6a93fd254ee88959220c80161ae76db378c8bb458bd')]:
        data=b''.join(l['raw']+(b'\x8d' if l['cr'] else b'') for l in lines[first-1:last])
        if digest(data)!=expected:raise ValueError('inventory control flow changed; re-audit host model')
        guards.append(dict(path='assets/raw/a/files/library.bin',first_line=first,last_line=last,sha256=expected))
    objects=[m for m in catalog['messages'] if any(r.get('file')=='LIBRARY' and 198<=r.get('line',0)<=244 for r in m['references'])]
    assert len(objects)==23
    chars,font=subset(''.join(displayed(m) or '' for m in catalog['messages']).replace('\r','\n'),load_font())
    mapping={c:font[i*8:i*8+8] for i,c in enumerate(chars)}
    results=[]
    for nearby in (False,True):
        kind='nearby' if nearby else 'inventory'
        heading=by_id['a:LIBRARY:0bdf' if nearby else 'a:LIBRARY:0c42']
        for count in range(1,24):
            pages=inventory_pages(objects[:count],heading,by_id['a:LIBRARY:02bf'],nearby)
            records=[]
            for n,screen in enumerate(pages):
                record=dict(number=n+1,pass_layout=check(screen),layout=screen.result(),
                    body_rows=sorted({w['row'] for w in screen.writes if w['role']=='body' and w['char']!=' '}),
                    message_ids=sorted({w['source'] for w in screen.writes if w['source'] in by_id}))
                if count==23:
                    path=output/f'{kind}-{n+1}.png';screen.image(mapping,path,top=0,rows=16)
                    record['image']=path.name
                records.append(record)
            results.append(dict(kind=kind,item_count=count,pages=records))
    sequences=[]
    for side in ('a','b'):
        sequences.append((f'native-media-{side}',12,[
            by_id['intrinsic:'+name] for name in ('disk_action_error_text','game_disk_prompt_text',
                'disk_side_'+side+'_text','drive_prompt_text','disk_prompt_ok_text')]))
        sequences.append((f'script-media-{side}',13,[by_id[mid] for mid in (
            'a:LIBRARY:1df9','a:LIBRARY:1e32' if side=='a' else 'a:LIBRARY:1e3a',
            'a:LIBRARY:1e40','a:LIBRARY:02bf')]))
    for name in ('ko_media_text','ko_save_prompt'):
        sequences.append((name,12,[by_id['runtime:'+name]]))
    media=[]
    for name,row,messages in sequences:
        screen=Screen(row=row)
        for message in messages:emit(screen,message)
        path=output/(name+'.png');screen.image(mapping,path)
        media.append(dict(name=name,start_row=row,message_ids=[m['id'] for m in messages],
                          pass_layout=check(screen),layout=screen.result(),image=path.name))
    result=dict(kind='Host inventory pagination and composed media UI audit',
        catalog_sha256=digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode()),
        tool_sha256=digest(Path(__file__).read_bytes()),renderer_model_sha256=digest((ROOT/'tools/korean/layout_preview.py').read_bytes()),
        source_guards=guards,inventory_cases=results,media_cases=media,
        native_source_hashes={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
            [ROOT/'src/intrinsics.s',ROOT/'src/korean/dispatch.s',ROOT/'src/korean/save.s']},
        one_row_item_invariant={'items':23,'max_cells':max(len(displayed(m)) for m in objects),
            'all_fit':True,'consequence':'Each selected item consumes exactly one row; selection identity cannot increase page height.'},
        pass_layout=all(p['pass_layout'] for r in results for p in r['pages']) and all(r['pass_layout'] for r in media),
        complete_game_layout_validation=False,
        limits=['No execution, HGR page-switch or picture-preservation proof; host monochrome previews only.',
                'The 23-item inventories are upper-bound fixtures, not a claim that all combinations are reachable.',
                'Empty inventory output and arbitrary callers/cursor state are not established by this audit.',
                'Other cross-block output, timed scenes and full-game layout remain to be validated.'])
    write_json(output/'composed-layout.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,default=DEFAULT)
    p.add_argument('--baseline',type=Path,default=ROOT/'build/korean/english-baseline')
    p.add_argument('--output',type=Path,default=ROOT/'build/korean/composed-layout')
    args=p.parse_args();r=audit(json.loads(args.catalog.read_text()),args.baseline,args.output)
    print(json.dumps(dict(pass_layout=r['pass_layout'],inventory_cases=len(r['inventory_cases']),
                         media_cases=len(r['media_cases']),max_item_cells=r['one_row_item_invariant']['max_cells'])))
    if not r['pass_layout']:raise SystemExit(1)
