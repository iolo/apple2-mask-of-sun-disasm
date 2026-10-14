#!/usr/bin/env python3
"""GSSquared regression: poison the initial disk side, boot and swap EXTRA to A."""
import argparse
from collections import deque
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time

from build_messages import labels
from catalog import digest, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--emulator',type=Path,required=True)
    p.add_argument('--client-src',type=Path,required=True)
    p.add_argument('--old-media',type=Path,required=True)
    p.add_argument('--media',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    sys.dont_write_bytecode=True;sys.path.insert(0,str(args.client_src.resolve()))
    import gs2debug as api
    from gs2debug.keys import SCANCODE_RETURN

    class Client(api.Client):
        def request(self,type_word,payload=b'',*,timeout=5):
            return super().request(type_word,payload,timeout=timeout)

    results=[]
    for name,media,expected in [('old-ff',args.old_media,False),('fixed-ff',args.media,True)]:
        media=media.resolve();dest=out/name;dest.mkdir()
        built=json.loads((media/'startup-build.json').read_text())
        symbols=labels(media/'runtime/messages.lbl')
        for side in ('extra','a'):
            source=media/built['disk_names'][side]
            assert digest(source.read_bytes())==built['extra' if side=='extra' else 'game_a']['sha256']
            shutil.copyfile(source,dest/(side+'.dsk'))
        client=Client();events=deque();connected=False;process=None;owned=[]
        def capture(event,sequence,data):
            if event==api.EVT_STOPPED:events.append(struct.unpack_from('<III',data))
        def stop_at(bp,timeout=90):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                while events:
                    reason,got,pc=events.popleft()
                    if got==bp:return pc
                try:client.wait_event(timeout=min(1,max(0.01,deadline-time.monotonic())))
                except TimeoutError:pass
            raise TimeoutError(f'{name}: breakpoint {bp}')
        def breakpoint(address):
            bp=client.bp_set(kind=api.BP_KIND_EXEC,address=address);owned.append(bp);return bp
        def clear(bp):client.bp_clear(bp);owned.remove(bp)
        def byte(address):return client.read_mem(api.MEM_MAIN_RAW,address,1)[0]
        client.on_event(capture)
        with tempfile.TemporaryDirectory(prefix='ko-swap-') as socket_dir,(dest/'emulator.log').open('w') as log:
            try:
                socket=str(Path(socket_dir)/'debug.sock')
                process=subprocess.Popen([str(args.emulator.resolve()),'--debug',socket,'--no-quit-confirm','-p','3','-s'],
                    cwd=dest,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    if process.poll() is not None:raise RuntimeError('GSSquared startup failed; see emulator.log')
                    try:client.connect(socket);connected=True;break
                    except (FileNotFoundError,ConnectionRefusedError):time.sleep(0.1)
                assert connected
                assert client.hello().version==1
                while True:
                    try:
                        status=client.get_status()
                        if client.get_trace(count=1).entries:break
                    except api.ProtocolError as e:
                        if e.message!='no machine':raise
                    if time.monotonic()>deadline:raise TimeoutError('machine startup')
                    time.sleep(0.1)
                assert status.platform_id==3
                client.pause()
                assert client.get_status().execution_mode==2
                bp=breakpoint(0x5000)
                assert client.mount(6,0,str(dest/'extra.dsk'))==api.MEDIA_OK
                client.reset(cold_start=True);client.continue_();stop_at(bp)
                # Controlled power-on variation only. No PC/script/loader patch.
                client.write_mem(api.MEM_MAIN_RAW,0x601c,b'\xff');assert byte(0x601c)==255
                clear(bp);bp=breakpoint(symbols['ko_wait_game_media'])
                client.continue_();stop_at(bp)
                side_before_swap=byte(0x601c)
                assert side_before_swap==(0 if expected else 255)
                assert client.mount(6,0,str(dest/'a.dsk'))==api.MEDIA_OK
                clear(bp);retry=breakpoint(symbols['ko_resource_retry'])
                client.key_down(SCANCODE_RETURN)
                client.continue_();stop_at(retry,10);client.key_up(SCANCODE_RETURN)
                clear(retry)
                target=symbols['ko_resource_ready'] if expected else symbols['ko_wait_game_media']
                bp=breakpoint(target);client.continue_();stop_at(bp)
                error=byte(symbols['ko_load_error'])
                header=client.read_mem(api.MEM_MAIN_RAW,symbols['ko_package_header'],24)
                assert error==(0 if expected else 6)
                assert header[8:20].hex()==built['media_id'] and header[20]==1
                record=dict(profile=name,platform_id=3,poisoned_side=255,side_before_swap=side_before_swap,
                    return_reached_loader=True,load_error=error,room1_accepted=expected,
                    media_id=built['media_id'],disk_sha256={k:built[k]['sha256'] for k in ('extra','game_a')})
                if expected:
                    clear(bp);bp=breakpoint(labels(media/'interpreter.lbl')['read_keyboard_wait'])
                    client.continue_()
                    # Intro pagination: natural key events only, then reach OK>.
                    deadline=time.monotonic()+90
                    while time.monotonic()<deadline:
                        try:stop_at(bp,1);break
                        except TimeoutError:
                            client.paste_text(' ')
                    else:raise TimeoutError('first command prompt')
                    assert byte(0x600d)==1
                    record['first_room_prompt']=True
                    (dest/'opening-hgr.bin').write_bytes(client.read_mem(api.MEM_MAIN_RAW,0x2000,16384))
                results.append(record);print('PASS: '+name,flush=True)
            finally:
                if connected:
                    try:
                        client.key_up(SCANCODE_RETURN)
                        for bp in owned:client.bp_clear(bp)
                        client.quit()
                    finally:client.close()
                if process is not None:
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
    write_json(out/'disk-swap.json',dict(pass_validation=True,runs=results,
        scope='GSSquared enhanced IIe, same-drive EXTRA-to-A replacement with Return. Only GE(12) poisoned before bootstrap; original code/PC preserved.',
        source_sha256=digest(Path(__file__).read_bytes())))


if __name__=='__main__':main()
