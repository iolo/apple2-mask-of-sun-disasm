#!/usr/bin/env python3
"""Compare commands, displayed text, world state and selected native scene pages."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original',type=Path);parser.add_argument('rebuilt',type=Path)
    parser.add_argument('--prompts',type=int,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    def commands(directory):
        return [r['reason'] for line in (directory/'replay-inputs.jsonl').read_text().splitlines()
                if 'reason' in (r:=json.loads(line)) and r['reason']!='pagination']
    def output(directory):
        return ''.join(chr(json.loads(line)['value']&127) for line in
                       (directory/'output-characters.jsonl').read_text().splitlines())
    checks={'same_command_sequence':commands(args.original)==commands(args.rebuilt),
            'same_output_text':output(args.original)==output(args.rebuilt)}
    checkpoints=[]
    for number in args.prompts:
        samples=[]
        for directory in (args.original,args.rebuilt):
            matches=list(directory.glob(f'*-prompt-{number:02d}-ram.bin'))
            if len(matches)!=1:raise ValueError(f'expected one prompt{number} in {directory}')
            samples.append(matches[0].read_bytes())
        a,b=samples;page=0x4000 if a[0x346] else 0x2000
        pixels=[a[page:page+0x2000],b[page:page+0x2000]]
        world=[a[0x6000:0x67fe],b[0x6000:0x67fe]]
        checkpoint={'prompt':number,'room':[a[0x600d],b[0x600d]],
            'same_draw_page':a[0x346]==b[0x346],
            'same_rendered_scene':pixels[0]==pixels[1],
            'same_world_state':world[0]==world[1],
            'scene_sha256':[hashlib.sha256(p).hexdigest() for p in pixels],
            'world_sha256':[hashlib.sha256(w).hexdigest() for w in world]}
        checkpoint['pass']=all(checkpoint[key] for key in ('same_draw_page','same_rendered_scene','same_world_state'))
        checkpoints.append(checkpoint)
    report={'pass':all(checks.values()) and all(c['pass'] for c in checkpoints),'checks':checks,
        'checkpoints':checkpoints,'sessions':[str(args.original),str(args.rebuilt)],
        'scope':'Commands, high-bit-normalized emitted text, scalar/object/room state and displayed native scenes; encoded disk/code identity is not checked'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'pass':report['pass'],'checks':checks,'failed':[c['prompt'] for c in checkpoints if not c['pass']]}))
    return not report['pass']


if __name__=='__main__':sys.exit(main())
