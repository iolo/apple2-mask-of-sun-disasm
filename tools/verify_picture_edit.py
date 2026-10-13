#!/usr/bin/env python3
"""Verify an added PIC1 outline layer through the native fixture and game loader."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from picture_assets import ROOT, encode_all


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline',type=Path)
    parser.add_argument('edited',type=Path)
    parser.add_argument('baseline_preview',type=Path)
    parser.add_argument('edited_preview',type=Path)
    parser.add_argument('--edited-data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    a,b=[(d/'001-waiting-01-ram.bin').read_bytes() for d in (args.baseline,args.edited)]
    old,new=[p.read_bytes() for p in (args.baseline_preview,args.edited_preview)]
    game_delta=bytes(x^y for x,y in zip(a[0x4000:0x6000],b[0x4000:0x6000]))
    preview_delta=bytes(x^y for x,y in zip(old,new))
    edited_data=args.edited_data.read_bytes()
    restored=encode_all(ROOT/'assets/decoded/pictures')['assets/raw/a/files/p1-1.bin']
    changes=[index for index,value in enumerate(game_delta) if value]
    allowed=set()
    for y in range(10,31):
        for column in range(31,38):
            allowed.add((y&7)*0x400+((y>>3)&7)*0x80+(y>>6)*40+column)
    checks={'same-game-target-page':a[0x346]==b[0x346]==1,
            'added-native-layer-loaded':b[0x9c0c]==a[0x9c0c]+1,
            'edited-collection-loaded':b[0x9c00:0x9c00+len(edited_data)]==edited_data,
            'visible-edit':bool(changes),
            'game-matches-native-preview-edit':game_delta==preview_delta and len(game_delta)==8192,
            'edit-confined-to-rectangle':set(changes)<=allowed,
            'baseline-svg-restored':restored==(ROOT/'assets/raw/a/files/p1-1.bin').read_bytes()}
    report={'pass':all(checks.values()),'checks':checks,
            'edit':'PIC1 extra color127 outline: M110,10 L130,10 L130,30 L110,30 L110,10',
            'changed_hgr_bytes':len(changes),'changes':changes,
            'delta_sha256':hashlib.sha256(game_delta).hexdigest(),
            'sessions':[str(args.baseline),str(args.edited)]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'pass':report['pass'],'checks':checks},indent=2))
    return not report['pass']


if __name__=='__main__':sys.exit(main())
