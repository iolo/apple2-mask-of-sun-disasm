#!/usr/bin/env python3
"""Supply exactly one operator action to an owned manual MAME session.

This tool never chooses/queues a route, dismisses pages or swaps media itself.
It waits for the matching capture/ack and reports the observed native screen.
"""
import argparse
import json
from pathlib import Path
import time
import uuid


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session',type=Path)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--command');action.add_argument('--keys')
    action.add_argument('--observe',action='store_true');action.add_argument('--mount',choices=('a','b','save'))
    action.add_argument('--press');action.add_argument('--finish',action='store_true')
    parser.add_argument('--label');parser.add_argument('--condition',default='ready')
    parser.add_argument('--maximum',type=float,default=120);parser.add_argument('--minimum',type=float,default=1)
    args=parser.parse_args()
    if not 0<=args.minimum<=args.maximum<=300:parser.error('bounded emulated wait 0..300 required')
    request={'id':str(uuid.uuid4()),'condition':args.condition,'label':args.label,
             'maximum':args.maximum,'minimum':args.minimum}
    if args.command is not None or args.keys is not None:
        request.update(kind='input',text=args.command+'\r' if args.command is not None else args.keys)
    elif args.observe:request['kind']='observe'
    elif args.press:request.update(kind='physical-key',key=args.press)
    elif args.mount:request.update(kind='mount',side=args.mount)
    else:request['kind']='finish'
    if request['kind'] in ('input','observe','physical-key') and not args.label:
        parser.error('capture label required')
    if args.label and (args.session/(args.label+'.json')).exists():parser.error('capture label already exists')
    temporary=args.session/'manual-request.tmp';temporary.write_text(json.dumps(request))
    temporary.replace(args.session/'manual-request.json')
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        try:ack=json.loads((args.session/'manual-ack.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):ack={}
        if ack.get('id')==request['id']:
            if args.label:
                capture=json.loads((args.session/(args.label+'.json')).read_text())
                ram=(args.session/(args.label+'-ram.bin')).read_bytes()
                print(json.dumps({'label':args.label,'time':capture['time'],'room':ram[0x600d],
                    'script_pc':ram[0xd2]+256*ram[0xd3],'D':ram[0x6003],
                    'screen':[row.rstrip() for row in capture['graphics_text']
                              if row.strip() and row.count('?')<10]},ensure_ascii=False))
            else:print(json.dumps({'ack':request['kind'],'side':args.mount}))
            return
        time.sleep(0.05)
    parser.error('manual request still pending; inspect owned session log/capture before another action')


if __name__=='__main__':main()
