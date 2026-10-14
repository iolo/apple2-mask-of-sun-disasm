#!/usr/bin/env python3
"""Exercise synthetic same-session/fresh-boot restore, wrong ID and partial I/O failure."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from catalog import ROOT, digest, write_json
from build_messages import labels
sys.path.insert(0,str(ROOT/'tools'))
from dos_disk import offset


def capture(session,index):
    paths=list(session.glob(f'*-prompt-{index:02d}.json'))
    if len(paths)!=1:raise ValueError(f'expected one prompt {index}: {paths}')
    return paths[0].with_name(paths[0].stem+'-ram.bin').read_bytes()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rompath',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,default=ROOT/'docs/evidence/korean/save-probe.json')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);fixture=out/'fixture'
    subprocess.run([sys.executable,str(ROOT/'tools/korean/startup_disk.py'),'--output',str(fixture)],check=True)
    subprocess.run(['a2kit','mkdsk','--os','dos33','--type','do','--volume','254','--dimg',str(fixture/'blank-save.dsk')],check=True)
    built=json.loads((fixture/'startup-build.json').read_text());symbols=labels(fixture/'runtime/messages.lbl')
    boot={'command':'','ready_text':'INSERT GAME DISK A/B AND PRESS RETURN.'}
    recovery={'command':'','ready_text':'RESTORE ERROR. RETRY: RETURN'}
    opening=[boot,'LOOK','INVENTORY','EXIT PLANE','GET MAP','ENTER JEEP']
    game_event={'when':'Place THE MASK OF THE SUN disk, side','side':'b'}
    extra_event={'when':boot['ready_text'],'side':'b'}
    reports=[]
    for profile in ('same-session','wrong-id','fault','write-fault'):
        ending=None
        if profile=='same-session':
            commands=opening+['SAVE GAME','Y','SE','RESTORE GAME','Y',boot,'LOOK','INVENTORY']
            events=[extra_event,{'when':'Place an initialized disk into Drive #1','side':'save'},game_event,
                    {'when':'Place SAVE GAME disk into Drive #1','side':'save'},extra_event,game_event]
            save_disk=fixture/'blank-save.dsk';restored_index=13
        elif profile=='write-fault':
            commands=opening+['SAVE GAME','Y','RESTORE GAME','Y']
            events=[extra_event,{'when':'Place an initialized disk into Drive #1','side':'save'},game_event,
                    {'when':'Place SAVE GAME disk into Drive #1','side':'save'}]
            save_disk=fixture/'blank-save.dsk';ending=recovery['ready_text']
        else:
            commands=[boot,'LOOK','RESTORE GAME','Y',recovery,boot,'LOOK','INVENTORY']
            events=[extra_event,{'when':'Place SAVE GAME disk into Drive #1','side':'save'},extra_event,game_event]
            save_disk=fixture/(profile+'-save.dsk');restored_index=7
        route=out/(profile+'-route.json');write_json(route,{'timeout':500,'commands':commands,'media_events':events,'ending_text':ending})
        session=out/profile
        cmd=[sys.executable,str(ROOT/'tools/mame_session.py'),'--rompath',str(args.rompath.resolve()),
             '--disk-a',str(fixture/'synthetic-startup.dsk'),'--disk-b',str(fixture/'synthetic-a.dsk'),
             '--save-disk',str(save_disk),'--output',str(session),'--headless','--fast','--language-card',
             '--script',str(ROOT/'tools/korean/save_probe.lua'),'--route',str(route)]
        log_path=out/(profile+'.log')
        with log_path.open('w') as log:
            subprocess.run(cmd,env=dict(os.environ,MASK_KOREAN_PROBE=str(fixture),MASK_KOREAN_SAVE_PROFILE=profile),
                           stdout=log,stderr=subprocess.STDOUT,timeout=90,check=True)
        if ('MASK FULL_REPLAY_COMPLETE' if ending else 'MASK OPENING_REPLAY_COMPLETE') not in log_path.read_text():raise ValueError('incomplete replay: '+profile)
        observer=json.loads((session/'save-probe.json').read_text())
        assert observer['asset_checks']>0 and not observer['failures'],observer
        assert observer['total_extension_fetches']>0
        if profile=='write-fault':
            failed=(session/'save.dsk').read_bytes()
            assert failed[offset(22,15):offset(22,15)+256]==bytes(256)
            assert observer['fault_injected'] and observer['rwts_error']==0x20
            assert observer['recovery_wait_seen'] and observer['restore_sector_reads']==0
            assert 1<len(observer['write_sectors'])<146
            reports.append({'profile':profile,'pass':True,'observer':observer,'invalid_commit_rejected':True,
                            'session':json.loads((session/'session.json').read_text())})
            continue
        restored=capture(session,restored_index)
        pool_size=int.from_bytes(restored[symbols['ko_room_size']:symbols['ko_room_size']+2],'little')
        assert restored[0x600d]==3 and pool_size==118
        assert restored[0x6020:0x650c]==capture(out/'same-session',7)[0x6020:0x650c]
        # Reopening the saved package must not overwrite its macro-mutated script.
        disk=(out/'same-session/save.dsk').read_bytes()
        snapshot=b''.join(disk[offset(t,s):offset(t,s)+256] for t in range(23,32) for s in range(16))
        assert restored[0x6800:0x7000]==snapshot[0x4800:0x5000]
        assert observer['unsafe_extension_fetches']==0
        if profile=='same-session':
            assert capture(session,10)[0x600d]==2
            valid=(session/'save.dsk').read_bytes();assert valid[offset(22,15):offset(22,15)+16].hex()==built['save_id']
            (fixture/'valid-save.dsk').write_bytes(valid)
            wrong=bytearray(valid);wrong[offset(22,15)+4]^=1;(fixture/'wrong-id-save.dsk').write_bytes(wrong)
            poisoned=bytearray(valid)
            for address in range(0x9400,0x9c00,256):
                page=(address-0x2000)//256;start=offset(23+page//16,page%16);poisoned[start:start+256]=b'\xcc'*256
            (fixture/'fault-save.dsk').write_bytes(poisoned)
            blank=(fixture/'blank-save.dsk').read_bytes()
            changed=[(t,s) for t in range(35) for s in range(16) if valid[offset(t,s):offset(t,s)+256]!=blank[offset(t,s):offset(t,s)+256]]
            expected={(22,15)}|{(t,s) for t in range(23,32) for s in range(16)}
            assert set(changed)<=expected and (22,15) in changed
            assert {tuple(pair) for pair in observer['write_sectors']}==expected
            assert len(observer['write_sectors'])==146
        elif profile=='wrong-id':
            assert observer['recovery_wait_seen'] and observer['world_unchanged'] and observer['room_pool_before_restore']==774
        else:
            assert observer['fault_injected'] and observer['rwts_error']==0x20
            assert observer['extension_poisoned'] and observer['recovery_wait_seen'] and observer['recovered'],observer
            assert observer['restore_sector_reads']==173
        reports.append({'profile':profile,'pass':True,'observer':observer,'restored_room':3,'pool_bytes':pool_size,
                        'script_preserved':True,'object_state_preserved':True,
                        'session':json.loads((session/'session.json').read_text())})
    result={'pass':True,'build':built,'runs':reports,'save_sha256':digest((fixture/'valid-save.dsk').read_bytes()),
            'changed_sectors':changed,'scope':'Synthetic opening on DOS, room 3 save, room 2 same-session restore, two fresh boots, incompatible save-ID rejection and retry, real RWTS volume-error injection after poisoned extension pages load, full retry, LC resident preservation and room pool reload; failed save leaves an invalid commit rejected before restore. No translated drafts. Not side-B save, final media identity, whole-game timing, or hardware validation.'}
    write_json(args.evidence,result);print('PASS: '+str(args.evidence))


if __name__=='__main__':main()
