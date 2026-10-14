-- Natural cold boot with read-only taps; no CPU/world/script injection.
dofile(assert(os.getenv('MASK_PROJECT_ROOT'))..'/tools/mame_control.lua')
local json=require('json')
local function bytes(path)local f=assert(io.open(path,'rb'));local d=f:read('a');f:close();return d end
local config=json.parse(bytes(assert(os.getenv('MASK_KOREAN_TITLE_CONFIG'))))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local taps={};local before;local after;local rwts=0;local started_at;local finished=false
local function ram(first,size)
 local result={};for a=first,first+size-1 do result[#result+1]=string.char(space:read_u8(a)) end
 return table.concat(result)
end
local function save(path,data)local f=assert(io.open(path,'wb'));f:write(data);f:close() end
local function tap(address,name,fn)
 taps[#taps+1]=space:install_read_tap(address,address,name,function(_,data,_)
  if cpu.state.PC.value==address or cpu.state.CURPC.value==address then fn() end
 end)
end
tap(config.labels.ko_print_script_string,'title-before',function()
 if not before and cpu.state.A.value+256*cpu.state.X.value==config.pointer then
  before={row=space:read_u8(0x25),column=space:read_u8(0x24),page=space:read_u8(0x346),background=space:read_u8(0x347),world=ram(0x6000,2048)}
  save('before-hgr.bin',ram(0x2000,16384));started_at=manager.machine.time:as_double()
 end
end)
tap(0xbd00,'title-rwts',function()if before and not after then rwts=rwts+1 end end)
tap(config.labels.ko_reference_done,'title-after',function()
 if before and not after and space:read_u8(0xe7)+256*space:read_u8(0xe8)==config.pointer then
  after={row=space:read_u8(0x25),column=space:read_u8(0x24),page=space:read_u8(0x346),background=space:read_u8(0x347),world_preserved=ram(0x6000,2048)==before.world,
         render_seconds=manager.machine.time:as_double()-started_at}
  save('after-hgr.bin',ram(0x2000,16384));before.world=nil
 end
end)
local function finish(pass,reason)
 finished=true
 mask.capture(pass and 'title-complete' or 'title-failed')
 local f=assert(io.open('title-probe.json','w'))
 f:write(json.stringify({pass=pass,reason=reason,before=before,after=after,rwts_during_caption=rwts,
                        time=manager.machine.time:as_double()}));f:close()
 for _,t in ipairs(taps) do t:remove() end
 print('KOREAN_TITLE '..reason);mask.exit()
end
emu.register_frame_done(function()
 if finished then return end
 local now=manager.machine.time:as_double();local pc=cpu.state.PC.value
 if now>90 then finish(false,'deadline');return end
 if after and now-started_at>2 and pc>=config.labels.ko_wait_game_media and pc<config.labels.ko_wait_game_media+12 then
  finish(after.world_preserved and rwts==0,'caption followed by normal A-media request')
 end
end)
