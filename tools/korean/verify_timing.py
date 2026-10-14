#!/usr/bin/env python3
"""Compare native snake input deadlines with reference and synthetic LC output."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from catalog import ROOT, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rompath',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT/'docs/evidence/korean/timing-probe.json')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    profiles={}
    for profile in ('native','reference','draft','stress'):
        fixture=out/(profile+'-fixture')
        subprocess.run([sys.executable,str(ROOT/'tools/korean/build_timing_probe.py'),'--profile',profile,'--output',str(fixture)],check=True)
        profiles[profile]={'build':json.loads((fixture/'timing-build.json').read_text()),'runs':{}}
        for mode in ('idle','early','late'):
            session=out/(profile+'-'+mode)
            env=dict(os.environ,MASK_KOREAN_TIMING=str(fixture))
            if mode=='early':env['MASK_KOREAN_KEY_DELAY']='0.10'
            if mode=='late':env['MASK_KOREAN_KEY_DELAY']='1.50'
            cmd=[sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(args.rompath.resolve()),
                 '--disk-a',str(fixture/'startup.dsk'),'--disk-b',str(fixture/'game.dsk'),'--output',str(session),
                 '--headless','--fast','--language-card','--script',str(ROOT/'tools/korean/timing_probe.lua')]
            with (out/(profile+'-'+mode+'.log')).open('w') as log:
                subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60,check=True)
            result=json.loads((session/'timing-probe.json').read_text())
            assert result['reason']=='scene completed',result
            assert result['disk_during_window']==0,result
            counts=result['render_counts'];assert counts['ko_bad_reference']==0
            if profile!='native':assert counts['ko_print_message']==4 and counts['ko_reference_done']==4,counts
            if profile in ('native','reference'):assert counts['ko_glyph_valid']==0,counts
            else:
                shape=profiles[profile]['build']['shape']['messages']
                selected=shape[:4] if mode=='idle' else shape[:2]+shape[4:]
                assert counts['ko_glyph_valid']==sum(m['hangul'] for m in selected),counts
            assert len(result['windows'])==(8 if mode=='idle' else 5),result
            assert result['outcome']==('died' if mode=='idle' else 'survived'),result
            for window in result['windows']:
                assert window['reason']==('deadline' if mode=='idle' else 'key'),window
                window['seconds']=window['finish']['time']-window['start']['time']
            if mode!='idle':assert [w['key'] for w in result['windows']]==[ord(c)|128 for c in 'SHOOT']
            result['session']=json.loads((session/'session.json').read_text())
            profiles[profile]['runs'][mode]=result
        print('PASS:',profile,flush=True)
    native=profiles['native']['runs']['idle']['windows'];comparisons=[]
    for name,profile in profiles.items():
        values=profile['runs']['idle']['windows']
        deltas=[v['seconds']-n['seconds'] for v,n in zip(values,native)]
        # Explicit tolerance: under 1% window drift; not a frame-rounded pass.
        assert all(abs(d)<n['seconds']*.01 for d,n in zip(deltas,native)),(name,deltas)
        comparisons.append({'profile':name,'window_seconds':[v['seconds'] for v in values],
                            'delta_seconds':deltas,'max_absolute_drift_seconds':max(map(abs,deltas))})
    result={'pass':True,'profiles':profiles,'comparisons':comparisons,
            'scope':'Isolated actual snake script, native graphics/sound and physical keyboard path from cold boot. Native vs message-reference English vs draft-cell-count synthetic Hangul vs 117-glyph-per-message stress. All eight no-input windows, five accepted SHOOT letters at two delays, zero disk requests during polling. Not approved text, other timed scenes, full route or physical hardware.'}
    write_json(args.evidence,result);print('PASS: '+str(args.evidence))


if __name__=='__main__':main()
