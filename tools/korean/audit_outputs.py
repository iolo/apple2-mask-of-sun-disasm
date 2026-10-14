#!/usr/bin/env python3
"""Check the reviewed source-output inventory, separately from runtime coverage."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from catalog import ROOT, DEFAULT, check_sources, digest, directive, extract, validate, write_json

SINKS={'rom_cout','rom_print_hex_byte','$fded','$fdf0','$fdda','$0bf3','$1f00',
       '(rom_output_vector)','(string_printer_vector)','(draw_character_vector)',
       'ko_native_print_script_string','ko_print_script_string','ko_print_message',
       'print_script_string','call_string_printer','dos_godsply'}


def call_sites(source, path):
    label='<start>';seen=Counter();sites=[]
    for line_no,line in enumerate(source.splitlines(),1):
        code=line.split(';',1)[0].strip()
        match=re.match(r'([A-Za-z_]\w*):\s*(.*)',code)
        if match:label,code=match.groups()
        call=re.fullmatch(r'(jsr|jmp)\s+(.+)',code,re.I)
        if not call or call[2].lower() not in SINKS:continue
        op,target=call[1].lower(),call[2].lower()
        key=f'{path}:{label}:{op}:{target}'
        seen[key]+=1
        sites.append({'id':key+f':{seen[key]}','path':path,'line':line_no,
                      'label':label,'operation':op,'target':target})
    return sites


def source_inventory():
    sources=sorted(p for p in (ROOT/'src').rglob('*') if p.suffix in ('.s','.inc'))
    hashes={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in sources}
    hashes['tools/korean/startup_disk.py']=digest((ROOT/'tools/korean/startup_disk.py').read_bytes())
    hashes['tools/korean/title_caption.py']=digest((ROOT/'tools/korean/title_caption.py').read_bytes())
    calls=[site for p in sources for site in call_sites(p.read_text(),str(p.relative_to(ROOT)))]
    return hashes,calls


def verify_policy(hashes, calls, policy, message_ids):
    if hashes!=policy['source_sha256']:
        raise ValueError('output source changed: review output policy before certifying inventory')
    classified=policy['sites']
    if {c['id'] for c in calls}!=set(classified):
        raise ValueError('missing or obsolete output call classification')
    for category,spec in policy['categories'].items():
        if not spec['treatment'] or not spec['reason']:
            raise ValueError('missing output treatment: '+category)
        for mid in spec.get('catalog_ids',[]):
            if mid not in message_ids:raise ValueError('missing output catalog item: '+mid)
    if not set(classified.values())<=set(policy['categories']):
        raise ValueError('unknown output policy category')
    for site,category in policy.get('generated_outputs',{}).items():
        if site.split(':',1)[0] not in hashes or category not in policy['categories']:
            raise ValueError('untracked generated output: '+site)
    return [dict(c,category=classified[c['id']]) for c in calls]


def audit(catalog, baseline, policy):
    validate(catalog);check_sources(catalog,baseline)
    _,extraction=extract(baseline)
    hashes,calls=source_inventory()
    calls=verify_policy(hashes,calls,policy,{m['id'] for m in catalog['messages']})
    numeric=[];selectors=[];literal_count=0
    for site in extraction['output_sites']:
        opcode,arg,_=directive(site['text'])
        value=site['text'][arg:]
        if opcode=='P':
            if value.startswith('"'):literal_count+=1
            else:numeric.append(site)
        elif opcode in ('1','2'):
            if not re.fullmatch(r'[A-Z0-9.]{2}',value):
                raise ValueError('macro selector needs new output analysis: '+str(site))
            selectors.append(site)
        elif opcode==']':
            raise ValueError('new custom prompt requires output policy review')
    if any(directive(s['text'])[0]!='P' or s['text'][directive(s['text'])[1]:]!='TV(8)' for s in numeric):
        raise ValueError('new dynamic numeric output requires layout review')
    assert literal_count==extraction['literal_reference_count']
    assert all(m['notes'] for m in catalog['messages'] if m['status']=='excluded')
    result={'kind':'reviewed source-level output inventory; not execution/layout coverage',
            'source_inventory_complete':True,'runtime_coverage_complete':False,
            'source_sha256':hashes,'policy_sha256':digest(json.dumps(policy,sort_keys=True).encode()),
            'tool_sha256':digest(Path(__file__).read_bytes()),
            'catalog_sha256':digest(json.dumps(catalog,ensure_ascii=False,sort_keys=True).encode()),
            'catalog_entries':len(catalog['messages']),
            'translated_drafts':sum(m['status']!='excluded' for m in catalog['messages']),
            'excluded':sum(m['status']=='excluded' for m in catalog['messages']),
            'assembly_output_calls':calls,'script_streams':extraction['script_count'],
            'generated_output_sites':policy.get('generated_outputs',{}),
            'literal_references':literal_count,'numeric_outputs':numeric,
            'macro_selectors':selectors,'output_opcode_counts':dict(Counter(s['opcode'] for s in extraction['output_sites'])),
            'source_roundtrip_pass':extraction['roundtrip_pass'],
            'system_scope_exclusions':policy['system_scope_exclusions'],
            'limits':['All known source literals and output classes accounted for at pinned source hashes.',
                      'Computed macro dispatch selects existing handlers; this does not prove handler reachability or dynamic cursor/page composition.',
                      'Runtime firmware/DOS shell diagnostics and legacy editor fragments retain English; no ROM localization.',
                      'No approval, production patch or full-game layout validation.']}
    extraction.update(source_inventory_complete=True,source_inventory_audit='docs/evidence/korean/output-audit.json',
                      pending_audits=['Live picture composition and Korean title-caption position',
                                      'Computed macro reachability and dynamic layout; source literal inventory is complete'])
    return result,extraction


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,default=DEFAULT)
    p.add_argument('--baseline',type=Path,default=ROOT/'build/korean/english-baseline')
    p.add_argument('--policy',type=Path,default=ROOT/'assets/korean/output-policy.json')
    p.add_argument('--output',type=Path,default=ROOT/'docs/evidence/korean/output-audit.json')
    args=p.parse_args()
    report,extraction=audit(json.loads(args.catalog.read_text()),args.baseline,json.loads(args.policy.read_text()))
    write_json(args.output,report);write_json(ROOT/'docs/korean/extraction.json',extraction)
    print(json.dumps({k:report[k] for k in ['source_inventory_complete','runtime_coverage_complete','catalog_entries','excluded','script_streams','literal_references']}))
