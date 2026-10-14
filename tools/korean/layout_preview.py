#!/usr/bin/env python3
"""Host-only glyph previews and conservative straight-line output composition.

This never writes game images or grants approval. Individual messages start at
row 12 for a three-row dialogue capacity check. Runs are source-local consecutive
P/echo/OBJL statements; other control flow ends a run and remains an audit limit.
"""
import argparse
import itertools
import json
from pathlib import Path
from PIL import Image
from catalog import ROOT, DEFAULT, digest, directive, extract, script_lines, ascii_text, validate, write_json
from font import load_font, subset


class Screen:
    def __init__(self,row=12,col=0):
        self.row,self.col=row,col
        self.cells={};self.writes=[];self.overwrites=[];self.prompt=[];self.outside=[]

    def glyph(self,char,source,role="body"):
        key=(self.row,self.col)
        previous=self.cells.get(key)
        if not (0<=self.row<16 and 0<=self.col<40):self.outside.append({'row':self.row,'col':self.col,'source':source})
        if previous and previous['char']!=' ' and previous['char']!=char:
            self.overwrites.append({'row':self.row,'col':self.col,'old':previous,'new':{'char':char,'source':source}})
        self.cells[key]={'char':char,'source':source}
        self.writes.append({'row':self.row,'col':self.col,'char':char,'source':source,'role':role})
        if self.row==15 and char!=' ':self.prompt.append({'col':self.col,'source':source})

    def cr(self,source,role="body"):
        self.glyph(' ',source,role);self.col=0;self.row=min(15,self.row+1)

    def text(self,text,newline,source,role="body"):
        for char in text:
            if char=='\n':self.cr(source,role)
            else:
                self.glyph(char,source,role);self.col+=1
                if self.col>=40:self.col=0;self.row=min(15,self.row+1)
        if newline:self.cr(source,role)

    def result(self):
        return {'end_row':self.row,'end_column':self.col,'overwrites':self.overwrites,
                'prompt_row_used':bool(self.prompt),
                'body_on_prompt_row':any(w['row']==15 and w['char']!=' ' and w['role']=='body' for w in self.writes),'outside':self.outside,
                'rows':[''.join(self.cells.get((row,col),{'char':' '})['char'] for col in range(40)) for row in range(12,16)]}

    def image(self,mapping,path,top=12,rows=4):
        im=Image.new('RGB',(280,12*rows),'black')
        for (row,col),entry in self.cells.items():
            if not(top<=row<top+rows and 0<=col<40):continue
            for y,bits in enumerate(mapping[entry['char']]):
                for x in range(7):
                    if bits&(1<<x):im.putpixel((col*7+x,(row-top)*12+y),(255,255,255))
        im.resize((560,24*rows),Image.Resampling.NEAREST).save(path)


def displayed(message):
    return message['source'] if message['status']=='excluded' else message['ko']


def part(message):
    role="prompt" if message["source"].strip() in ("OK>^","OK>","[ waiting ]") else "body"
    return {"id":message["id"],"text":displayed(message),"newline":message["layout"]["newline"],"role":role}


def compositions(catalog,extraction):
    by_ref={(r.get('path'),r.get('line')):m for m in catalog['messages'] for r in m['references'] if 'line'in r}
    objects=[m for m in catalog['messages'] if any(r.get('file')=='LIBRARY' and 198<=r.get('line',0)<=244 for r in m['references'])]
    assert len(objects)==23
    runs=[]
    for spec in extraction['files']:
        if spec['name']=='START':continue
        rows=script_lines((ROOT/spec['path']).read_bytes());pending=[];start=None
        def flush():
            nonlocal pending,start
            if len(pending)>1:
                runs.append({'side':spec['side'],'file':spec['name'],'source':spec['path'],'line':start,'steps':pending})
            pending=[];start=None
        for n,row in enumerate(rows):
            text=ascii_text(row['raw']);op=directive(text);step=None
            if op:
                code,arg,conditions=op;argument=text[arg:]
                if code=='P' and argument.startswith('"'):
                    m=by_ref[(spec['path'],n+1)]
                    step={'conditions':conditions,'options':[part(m)]}
                elif code=='P':
                    maximum='65535' if ','in argument else '255'
                    step={'conditions':conditions,'options':[{'id':f'number:{argument}','text':maximum,'newline':not argument.endswith(';')}]}
                elif code=='&':
                    step={'conditions':conditions,'options':[{'id':'command-echo:36','text':'X'*36,'newline':False}]}
                elif code=='!' and argument=='OBJL':
                    step={'conditions':conditions,'options':[{'id':m['id'],'text':displayed(m),'newline':False}for m in objects]}
            if step:
                if start is None:start=n+1
                pending.append(step)
            else:flush()
        flush()
    return runs


def render(parts,mapping,path):
    screen=Screen()
    for item in parts:screen.text(item['text'],item['newline'],item['id'],item.get('role','body'))
    if path:screen.image(mapping,path)
    return screen.result()


def build(catalog,baseline,out):
    validate(catalog);_,extraction=extract(baseline);out.mkdir(parents=True,exist_ok=True)
    images=out/'images';images.mkdir(exist_ok=True)
    text=''.join(displayed(m) or '' for m in catalog['messages'])+'X25565535'
    # Early DOS notice CRs are technical source controls, represented as LF here.
    text=text.replace('\r','\n')
    chars,font=subset(text,load_font());mapping={c:font[i*8:i*8+8]for i,c in enumerate(chars)}
    records=[]
    for n,m in enumerate(catalog['messages']):
        if m['status']=='excluded':continue
        path=images/f'message-{n:04d}.png'
        item=part(m)
        result=render([item],mapping,path)
        records.append({'id':m['id'],'type':'message','source':m['source'],'ko':m['ko'],
                        'status':m['status'],'references':m['references'],'context':m['context'],
                        'newline':m['layout']['newline'],'protected_tokens':m['protected_tokens'],'notes':m['notes'],'layout_policy':m['layout'],'image':str(path.relative_to(out)),
                        'projection':'Individual message at row12/column0; actual caller position may differ.',
                        'layout':result})
    runs=compositions(catalog,extraction);cases=[]
    for n,run in enumerate(runs):
        seen=set()
        for condition in (True,False):
            steps=[s for s in run['steps'] if all((c=='T')==condition for c in s['conditions'])]
            if not steps:continue
            count=1
            for step in steps:count*=len(step['options'])
            if count>1024:raise ValueError('unbounded preview expansion: '+str(run))
            for variant in itertools.product(*(s['options']for s in steps)):
                signature=tuple((s['id'],s['text'],s['newline'])for s in variant)
                if signature in seen:continue
                seen.add(signature)
                result=render(variant,mapping,None)
                # Keep one normal representative and every capacity/overwrite concern.
                concern=bool(result['overwrites']or result['body_on_prompt_row']or result['outside'])
                case={'id':f"run:{run['side']}:{run['file']}:{run['line']}:{len(seen)}",
                      'type':'composition','source':run['source'],'file':run['file'],'side':run['side'],
                      'line':run['line'],'condition':condition,'parts':list(variant),'layout':result,
                      'projection':'Consecutive source output at row12/column0. Branch selection is local; no whole-game reachability claim.'}
                cases.append(case)
                if len(seen)==1 or concern:
                    path=images/f'run-{n:04d}-{len(seen):02d}.png';render(variant,mapping,path)
                    case['image']=str(path.relative_to(out))
    report={'catalog_sha256':digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode()),
            'font_sha256':digest(font),'font_source_sha256':digest((ROOT/'assets/korean/font/GalmuriMono7.kbitx').read_bytes()),
            'messages':records,'compositions':cases,'source_runs':len(runs),
            'counts':{'messages':len(records),'composition_variants':len(cases),
                      'message_concerns':sum(bool(r['layout']['overwrites']or r['layout']['body_on_prompt_row']or r['layout']['outside'])for r in records),
                      'composition_concerns':sum(bool(r['layout']['overwrites']or r['layout']['body_on_prompt_row']or r['layout']['outside'])for r in cases)},
            'complete_layout_validation':False,
            'limitations':['Host monochrome glyph preview, not NTSC artifact colors or an emulator screenshot.',
                           'A row12/column0 projection does not establish the actual cursor, page, picture overlap or reachable branches.',
                           'Computed calls, cross-block combinations, inventory pagination and conditional cursor changes require explicit cases or execution evidence.',
                           'No approval is granted and no game image is generated.']}
    write_json(out/'layout.json',report)
    data=json.dumps(records+[c for c in cases if 'image'in c],ensure_ascii=False).replace('</','<\\/')
    page=r'''<!doctype html><html lang="ko"><meta charset="utf-8"><link rel="icon" href="data:,"><title>한국어 초안 화면 검토</title>
<style>body{font:16px/1.5 sans-serif;max-width:1050px;margin:24px auto;padding:0 16px;background:#f5f3ec;color:#202522}header{position:sticky;top:0;background:#f5f3ec;padding:10px 0;border-bottom:1px solid #abb1a9}input,select{font:inherit;padding:7px;max-width:80%}article{border-top:1px solid #c5c9bf;padding:18px 0}h2{font:700 16px monospace;overflow-wrap:anywhere}pre{white-space:pre-wrap;font:14px/1.5 monospace}img{image-rendering:pixelated;max-width:100%;height:auto;background:black}.flag{color:#a13220;font-weight:bold}small{color:#515b51}.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}@media(max-width:650px){.columns{display:block}}</style>
<h1>한국어 초안 · 7×8 글리프 검토</h1><p>미승인 초안입니다. JSON/Markdown 원천에서 수정하고 다시 생성합니다. 검정 화면은 40열, 행 12–15의 <b>가정 배치</b>입니다. 실제 호출 위치·그림·분기를 검증한 화면이 아닙니다. 마지막 행은 입력 프롬프트와 충돌할 수 있습니다.</p>
<header><input id="query" aria-label="검색" placeholder="ID, 방 이름, 원문, 번역 검색"><select id="kind" aria-label="종류"><option value="all">전체</option><option value="message">개별 문구</option><option value="composition">문구 결합</option><option value="concern">배치 확인 필요</option></select><span id="count"></span><button id="more">100개 더 보기</button></header><main id="items"></main>
<script>const DATA=__DATA__;let limit=100;const $=id=>document.getElementById(id);function node(tag,text){let n=document.createElement(tag);n.textContent=text;return n}function concern(x){return x.layout.overwrites.length||x.layout.body_on_prompt_row||x.layout.outside.length}function show(){let q=$('query').value.toLowerCase(),k=$('kind').value;let rows=DATA.filter(x=>(k==='all'||(k==='concern'?concern(x):x.type===k))&&JSON.stringify(x).toLowerCase().includes(q));$('count').textContent=` ${rows.length}개 / 표시 ${Math.min(limit,rows.length)}개`;let root=$('items');root.replaceChildren();for(let x of rows.slice(0,limit)){let a=node('article','');a.id=x.id;a.append(node('h2',x.id));a.append(node('small',x.projection));if(concern(x)){let flag=node('p',`확인 필요: 덮어쓰기 ${x.layout.overwrites.length}회 · 입력 행 사용 ${x.layout.body_on_prompt_row?'있음':'없음'}`);flag.className='flag';a.append(flag)}let columns=node('div','');columns.className='columns';columns.append(node('pre',x.type==='message'?'원문\n'+x.source:'출처\n'+x.source+':'+x.line));columns.append(node('pre',x.type==='message'?'초안\n'+x.ko:'결합\n'+x.parts.map(p=>p.text+(p.newline?'↵':'')).join('')));a.append(columns);let img=node('img','');img.src=x.image;img.width=560;img.height=96;img.alt=x.id+'의 가정된 40열 출력';img.loading='lazy';a.append(img);let details=node('details','');details.append(node('summary','문맥·출처·제어 정보'));details.append(node('pre',JSON.stringify(x.type==='message'?{references:x.references,context:x.context,newline:x.newline,protected_tokens:x.protected_tokens,notes:x.notes,layout_policy:x.layout_policy}:x.parts,null,2)));a.append(details);root.append(a)}}for(let id of ['query','kind'])$(id).addEventListener('input',()=>{limit=100;show()});$('more').onclick=()=>{limit+=100;show()};show();</script></html>'''
    # Escaped newlines in JS strings must remain literal within the HTML script.
    page=page.replace('__DATA__',data)
    (out/'index.html').write_text(page)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,default=DEFAULT)
    p.add_argument('--baseline',type=Path,default=ROOT/'build/korean/english-baseline')
    p.add_argument('--output',type=Path,default=ROOT/'build/korean/layout-preview')
    args=p.parse_args();result=build(json.loads(args.catalog.read_text()),args.baseline,args.output)
    print(json.dumps(result['counts']))


if __name__=='__main__':main()
