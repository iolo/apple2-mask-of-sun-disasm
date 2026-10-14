#!/usr/bin/env python3
"""Inventory native script polling/delay sites; not a dynamic timing proof."""
import argparse
import re
from pathlib import Path
from catalog import ROOT, digest, extract, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'docs/evidence/korean/timer-inventory.json')
    args=p.parse_args();_,extraction=extract(ROOT/'build/korean/english-baseline')
    rules={'keyboard_test':re.compile(r'^\.(?:[TE] )*I Q[<>=:#]'),
           'short_delay':re.compile(r'^\.(?:[TE] )*W(?: |$)'),
           'keyboard_clear':re.compile(r'^\.(?:[TE] )*S R=0(?: |$)'),
           'timer_label':re.compile(r'^!TIME$')}
    files=[]
    for spec in extraction['files']:
        if spec['name']=='START':continue
        raw=(ROOT/spec['path']).read_bytes();body=raw.split(b'\0',1)[0];events=[];offset=0
        for n,line in enumerate(body.split(b'\x8d')):
            text=''.join(chr(c&127) for c in line)
            kinds=[name for name,pattern in rules.items() if pattern.search(text)]
            if kinds:events.append({'line':n+1,'offset':offset,'kinds':kinds,'text':text})
            offset+=len(line)+1
        if events:files.append({'side':spec['side'],'file':spec['name'],'source':spec['path'],
                               'sha256':digest(raw),'events':events})
    result={'kind':'Native source polling/delay inventory; manual loop interpretation still required',
            'script_files_examined':sum(f['name']!='START' for f in extraction['files']),
            'text_streams_in_catalog':len(extraction['files']),'files':files,
            'counts':{kind:sum(kind in e['kinds'] for f in files for e in f['events']) for kind in rules},
            'limitations':['Static sites do not prove branch reachability, input opportunity, or hardware timing.',
                           'Polling through shared native routines and calculated script calls also requires execution tracing.']}
    write_json(args.output,result);print(result['counts'])


if __name__=='__main__':main()
