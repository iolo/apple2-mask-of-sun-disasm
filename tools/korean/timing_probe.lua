-- Actual ROOM 9.0 interpreter/graphics/sound/input path; no live code injection.
dofile(assert(os.getenv('MASK_PROJECT_ROOT'))..'/tools/mame_control.lua')
local json=require('json')
local fixture=assert(os.getenv('MASK_KOREAN_TIMING'))
local delay=tonumber(os.getenv('MASK_KOREAN_KEY_DELAY'))
local function read(path)local f=assert(io.open(path,'r'));local s=f:read('a');f:close();return s end
local build=json.parse(read(fixture..'/timing-build.json'))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local function word(a)return space:read_u8(a)+256*space:read_u8(a+1) end
local function matches(values)
 for i,v in ipairs(values) do if space:read_u8(0x6800+i-1)~=v then return false end end
 return true
end
local windows={};local current;local outcome;local finished=false;local mounted=false;local sent=false
local render_counts={ko_glyph_valid=0,ko_print_message=0,ko_reference_done=0,ko_bad_reference=0}
local disk_during_window=0;local scene_start;local taps={}
local function now()return manager.machine.time:as_double() end
local function event()return {time=now(),cycles=cpu.total_cycles} end
local function executing(address)return cpu.state.PC.value==address or cpu.state.CURPC.value==address end
local function finish(reason)
 if finished then return end
 finished=true
 local result={profile=build.profile,key_delay=delay,reason=reason,outcome=outcome,windows=windows,
               scene_start=scene_start,render_counts=render_counts,disk_during_window=disk_during_window,shot_queued=sent,
               time=now(),pc=cpu.state.PC.value,room=space:read_u8(0x600d)}
 local f=assert(io.open('timing-probe.json','w'));f:write(json.stringify(result));f:close()
 mask.capture('timing-'..(outcome or 'failure'))
 for _,tap in ipairs(taps) do tap:remove() end
 print('KOREAN_TIMING '..json.stringify(result));mask.exit()
end
for name,address in pairs(build.renderer_labels) do
 taps[#taps+1]=space:install_read_tap(address,address,'snake-'..name,function()
  local pointer=word(0xd2)
  if executing(address) and scene_start and space:read_u8(0x600d)==9 and pointer>=0x6800 and pointer<0x7000 then
   render_counts[name]=render_counts[name]+1
  end
 end)
end
taps[#taps+1]=space:install_read_tap(0x08a8,0x08a8,'snake-outcome',function()
 if executing(0x08a8) and word(0xd2)==0x6800 then
  if matches(build.success_prefix) then outcome='survived' end
  if matches(build.death_prefix) then outcome='died' end
 end
end)
taps[#taps+1]=space:install_read_tap(0x0d00,0x0d00,'snake-lines',function()
 if not executing(0x0d00) then return end
 local pointer=word(0xd2)-1
 if pointer==0x6800 then
  if matches(build.success_prefix) then outcome='survived';return end
  if matches(build.death_prefix) then outcome='died';return end
  if space:read_u8(0x600d)~=9 then scene_start=event() end
 end
 if not scene_start or space:read_u8(0x600d)~=9 then return end
 if pointer==build.markers.window_start then
  current={start=event(),index=#windows+1};windows[#windows+1]=current
 elseif pointer==build.markers.expire_test and space:read_u8(0x6001)==250 and current and not current.finish then
  current.finish=event();current.reason='deadline'
 end
end)
taps[#taps+1]=space:install_read_tap(0xc000,0xc000,'snake-keyboard',function(_,data,_)
 if current and not current.finish and data>=128 then
  current.finish=event();current.reason='key';current.key=data
 end
end)
taps[#taps+1]=space:install_read_tap(0xbd00,0xbd00,'snake-disk',function()
 if executing(0xbd00) and current and not current.finish then disk_during_window=disk_during_window+1 end
end)
local frames=0
emu.register_frame_done(function()
 if finished then return end
 frames=frames+1
 if outcome then finish('scene completed');return end
 if now()>240 then finish('emulated-time deadline');return end
 if current and delay and not sent and now()-current.start.time>=delay then
  mask.keys('SHOOT');sent=true
 end
 if frames%6==0 and not mounted and build.profile~='native' then
  local screen=table.concat(mask.graphics_text(),'\n')
  if screen:find('INSERT GAME DISK A/B AND PRESS RETURN.',1,true) then
   mask.swap('b');mask.keys('\r');mounted=true
  end
 end
end)
