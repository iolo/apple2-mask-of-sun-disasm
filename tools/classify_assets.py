#!/usr/bin/env python3
"""Account for every exported region using current source and runtime findings."""
import argparse
import json
from pathlib import Path
from dos_disk import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'assets/classification.json')
    args=parser.parse_args()
    build=json.loads((args.build/'build.json').read_text())
    manifest=json.loads((ROOT/'assets/raw/manifest.json').read_text())
    constructed={r['asset'] for r in build['constructed_regions']}
    pictures={r['asset'] for r in build['encoded_picture_collections']}
    sources={}
    for module in build['assembled']:
        for span in module['spans']:
            sources.setdefault(span['asset'],[]).append({'source':module['source'],**span})
    zeros={}
    for span in build['generated_zero_spans']:
        zeros.setdefault(span['asset'],[]).append(span)
    regions=[]
    for disk in manifest['disks']:
        vtoc=(ROOT/f'assets/raw/{disk["side"]}/metadata/vtoc.bin').read_bytes()
        for region in disk['regions']:
            path=region['path'];entry={'side':disk['side'],'path':path,
                'length':region['length'],'reference_sha256':region['sha256'],
                'disk_slices':[{'track':s['track'],'sector':s['sector'],'region_offset':s['region_offset']}
                               for s in disk['sectors'] if s['path']==path]}
            if path in pictures:
                entry.update({'kind':'editable-vector-data','authority':'assets/decoded/pictures/manifest.json',
                              'reference_only':True,'documentation':'docs/pictures.md'})
            elif region['role'].startswith('dos-'):
                entry.update({'kind':region['role'],'authority':'assets/raw/manifest.json',
                    'reference_only':region['role']=='dos-ts-list','documentation':'docs/disk-layout.md',
                    'retention_reason':'TS chains, catalog live entries/links and allocation bitmap generated from manifest. Catalog/VTOC inactive fields retain native data; TS exports are reference only.'})
                if region['role']!='dos-ts-list':entry['native_data_seed']=path
            elif path in constructed:
                entry.update({'kind':'assembled-code-and-explicit-data','sources':sources.get(path,[]),
                              'generated_zeros':zeros.get(path,[]),'reference_only':True,
                              'documentation':'docs/disk-layout.md'})
            elif region['role'] in ('startup-text','interpreted-script'):
                entry.update({'kind':region['role'],'authority':path,'documentation':'docs/world.md',
                              'retention_reason':'Native high-bit script format remains supported; all live text has decoded line views.'})
            elif region['role']=='engine-parameters':
                entry.update({'kind':'engine-parameters','authority':path,'documentation':'assets/decoded/world/parameters.json',
                              'retention_reason':'Structured non-executable prompt, pointers, errors and chain table; fully decoded.'})
            elif path in ('assets/raw/a/system/track-18.bin','assets/raw/a/system/track-22.bin'):
                for s in entry['disk_slices']:
                    bitmap=int.from_bytes(vtoc[0x38+4*s['track']:0x3a+4*s['track']],'big')
                    if not bitmap & (1<<s['sector']):raise ValueError('inactive sector is not free in VTOC')
                entry.update({'kind':'inactive-deleted-data','authority':path,'documentation':'docs/disk-layout.md',
                    'retention_reason':'Free sectors outside boot/TS chains and snapshot tracks; old DEATH text/TS residue on18 and tokenized EXEC START BASIC residue on22. Never executed or loaded by current game; retained only as historical disk data.'})
            else:raise ValueError(f'unclassified region: {path}')
            regions.append(entry)
    report={'format':1,'scope':'Current build authority; raw manifest roles preserve initial extraction classification',
            'unclassified_regions':[],'regions':regions}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Classified {len(regions)} regions; no unknown or raw executable dependency')


if __name__=='__main__':main()
