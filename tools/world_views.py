#!/usr/bin/env python3
"""Generate evidence-linked script, vocabulary, object and parameter indexes.

These are decoded views of native authoritative data, not a second script source.
Static file references and conditions are indexes, not proofs of reachable exits.
"""
import argparse
import json
from pathlib import Path
import re
from dos_disk import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scripts',type=Path,default=ROOT/'assets/decoded/scripts/scripts.json')
    parser.add_argument('--output',type=Path,default=ROOT/'assets/decoded/world')
    args=parser.parse_args()
    scripts=json.loads(args.scripts.read_text())['scripts']
    result=[];vocabulary=[];literals=[]
    for script in scripts:
        annotated=[];sections=[];section=[];patterns=[];states=[];targets=[];pictures=[]
        for line in script['lines']:
            text=line['text'];entry=dict(line)
            if text.startswith('.'):
                entry['kind']='directive'
                entry['array_references']=re.findall(r'\b(GE|T0|T1|TC|TL|TV|N0|N1|NV)\(([^)]+)\)',text)
                action=re.sub(r'^\.(?:[TE] )*','',text)
                if action.startswith('P "'):
                    literals.append({'id':line['id'],'file_offset':line['file_offset'],
                                     'native':script['native'],'text':action[3:]})
                assignment=re.fullmatch(r'S ([A-Z][A-Z0-9]?(?:\([^)]+\))?)=(.+)',action)
                if assignment:entry['assignment']={'variable':assignment[1],'expression':assignment[2]}
                condition=re.fullmatch(r'I (.+)',action)
                if condition:entry['condition']=condition[1]
                destination=re.fullmatch(r'[3G] (.+)',action)
                if destination:targets.append({'id':line['id'],'target':destination[1].rstrip(),
                                               'mode':'deferred filename' if action[0]=='3' else 'direct load'})
                picture=re.fullmatch(r'B (.+)',action)
                if picture:pictures.append({'id':line['id'],'name':picture[1]})
                state=re.fullmatch(r'S N=(\d+)',action)
                if state:states.append({'id':line['id'],'value':int(state[1])})
                macro=re.fullmatch(r'([12]) (..)',action)
                if macro and patterns:
                    vocabulary.append({'side':script['side'],'file':script['name'],
                        'id':line['id'],'pair':'verb' if macro[1]=='1' else 'object/category',
                        'value':macro[2],'patterns':list(patterns)})
                    patterns=[]
            elif text.startswith('@'):
                entry['kind']='section terminator';sections.append(section);section=[];patterns=[]
            else:
                entry['kind']='internal handler' if text.startswith('!') else 'macro handler' if text.startswith('%') else 'command pattern'
                if not text.startswith('!') and text:
                    if annotated and annotated[-1]['kind'] not in ('command pattern','macro handler'):
                        patterns=[]
                    patterns.append({'id':line['id'],'text':text})
                else:patterns=[]
            section.append(line['id']);annotated.append(entry)
        if section:sections.append(section)
        result.append({'side':script['side'],'name':script['name'],'native':script['native'],
                       'view':script['view'],'states':states,'file_references':targets,
                       'picture_references':pictures,'sections':sections,'lines':annotated})
    library=next(s for s in scripts if s['side']=='a' and s['name']=='LIBRARY')
    initial=next(s for s in scripts if s['name']=='INITIAL')
    defaults={}
    for line in initial['lines']:
        match=re.fullmatch(r'\.S (TC|TL|TV)\((\d+)\)=(\d+)',line['text'])
        if match:defaults.setdefault(int(match[2]),{})[match[1]]=int(match[3])
    start=next(i for i,l in enumerate(library['lines']) if l['text']=='!OBJL')
    names=[l for l in library['lines'][start+1:] if l['text'].startswith('.P "')][:23]
    objects=[{'number':i,'name':line['text'][4:].rstrip(';'),'name_line':line['id'],
              'initial':defaults.get(i,{})} for i,line in enumerate(names,1)]
    parms=(ROOT/'assets/raw/a/files/parms-obj.bin').read_bytes()
    payload=parms[4:244];ignored=[];cursor=0x90
    while cursor<len(payload):
        end=cursor
        while end<len(payload) and payload[end] not in (0,1):end+=1
        if end==len(payload):raise ValueError('unterminated insignificant-word table')
        ignored.append({'address':0x300+cursor,'file_offset':4+cursor,
                        'text':bytes(c&127 for c in payload[cursor:end]).decode('ascii'),
                        'terminator':payload[end]})
        cursor=end+1
        if payload[end]==1:break
    parameters={'native':'assets/raw/a/files/parms-obj.bin','nominal_address':int.from_bytes(parms[:2],'little'),
        'nominal_length':int.from_bytes(parms[2:4],'little'),'actual_load_address':0x300,
        'prompt':bytes(c&127 for c in payload[1:1+payload[0]]).decode('ascii'),
        'initial_loads':[{'parameter_address':0x300+i,'destination':int.from_bytes(payload[i:i+2],'little'),
                         'filename':bytes(c&127 for c in payload[i+2:i+12]).decode('ascii')}
                         for i in (0x10,0x1c,0x28,0x34)],
        'raw_input':int.from_bytes(payload[0x40:0x42],'little'),
        'normalized_input':int.from_bytes(payload[0x42:0x44],'little'),
        'errors':[{'address':0x300+i,'text':bytes(c&127 for c in payload[i:i+15]).decode('ascii')}
                  for i in range(0x50,0x90,0x10)],'insignificant_words':ignored,
        'allocation_tail':{'file_offset':244,'length':12,'meaning':'zero allocation padding'}}
    output=args.output;output.mkdir(parents=True,exist_ok=True)
    for name,value in [('world',{'scope':'static index; conditional references may be unreachable', 'scripts':result}),
                       ('vocabulary',{'entries':vocabulary}),('objects',{'objects':objects}),
                       ('text',{'encoding':'high-bit ASCII, $8D CR, semicolon before CR suppresses newline','strings':literals}),
                       ('parameters',parameters)]:
        (output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    print(f'Indexed {len(result)} scripts, {len(literals)} text literals, {len(vocabulary)} vocabulary groups, {len(objects)} objects')


if __name__=='__main__':main()
