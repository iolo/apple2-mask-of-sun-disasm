-- Cold boot only: no executable, PC, world, or keyboard-buffer injection.
dofile(assert(os.getenv('MASK_PROJECT_ROOT'))..'/tools/mame_control.lua')
local json=require('json')
local fixture=assert(os.getenv('MASK_KOREAN_PROBE'))
local no_lc=os.getenv('MASK_KOREAN_NO_LC')=='1'
local function bytes(path)local f=assert(io.open(path,'rb'));local d=f:read('a');f:close();return d end
local build=json.parse(bytes(fixture..'/startup-build.json'))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local labels=build.runtime_labels
local phase='boot';local finished=false;local last=0;local stable=0;local previous=''
local retry_count=0;local wrong_retry;local reports={};local commands={'LOOK','INVENTORY','EXIT PLANE','GET MAP','ENTER JEEP'};local index=1
local world_before_boot;local world_boot_preserved
local function world_bytes()
 local result={}
 for a=0x6000,0x67ff do result[#result+1]=string.char(space:read_u8(a)) end
 return table.concat(result)
end
local boot_tap=space:install_read_tap(build.bootstrap_labels.bootstrap_entry,build.bootstrap_labels.bootstrap_entry,'ko-boot-world',function(_,data,_)
 if not world_before_boot and (cpu.state.PC.value==build.bootstrap_labels.bootstrap_entry or cpu.state.CURPC.value==build.bootstrap_labels.bootstrap_entry) then
  world_before_boot=world_bytes()
 end
end)
local engine_tap=space:install_read_tap(0x0800,0x0800,'ko-engine-world',function(_,data,_)
 if world_before_boot and world_boot_preserved==nil and (cpu.state.PC.value==0x0800 or cpu.state.CURPC.value==0x0800) then
  world_boot_preserved=world_bytes()==world_before_boot
 end
end)
local retry_tap=space:install_read_tap(labels.ko_resource_retry,labels.ko_resource_retry,'ko-resource-retry',function(_,data,_)
 if cpu.state.PC.value==labels.ko_resource_retry or cpu.state.CURPC.value==labels.ko_resource_retry then retry_count=retry_count+1 end
end)
local function word(a)return space:read_u8(a)+256*space:read_u8(a+1) end
local function compare(data,base)
 for i=1,#data do if space:read_u8(base+i-1)~=data:byte(i) then return false,base+i-1 end end
 return true
end
local function assets_ok()
 if word(labels.ko_font_count)~=650 or word(labels.ko_resident_size)~=4096 then return false,'asset metadata' end
 space:read_u8(0xc088)
 local resident,address=compare(bytes(fixture..'/resident-asset.bin'):sub(17),0xd000)
 local font,font_address=compare(bytes(fixture..'/font-asset.bin'):sub(17),0xe000)
 space:read_u8(0xc082)
 if not resident then return false,'resident mismatch '..address end
 if not font then return false,'font mismatch '..font_address end
 return true
end
local function capture(name)
 local record=mask.capture(name);reports[#reports+1]={name=name,time=record.time,room=space:read_u8(0x600d),
  room_pool=word(labels.ko_room_size),error=space:read_u8(labels.ko_load_error),graphics_text=record.graphics_text}
 mask.resume()
end
local function finish(pass,reason)
 if finished then return end
 if pass and not no_lc and world_boot_preserved~=true then pass=false;reason='bootstrap changed world RAM' end
 finished=true;capture(pass and 'startup-success' or 'startup-failure')
 local f=assert(io.open('startup-probe.json','w'))
 f:write(json.stringify({pass=pass,reason=reason,no_lc=no_lc,phase=phase,retry_count=retry_count,
                         command_count=index-1,pc=cpu.state.PC.value,checkpoints=reports,
                         world_boot_preserved=world_boot_preserved}));f:close()
 retry_tap:remove();boot_tap:remove();engine_tap:remove();mask.exit()
end
local function mount(path)
 local drive=assert(manager.machine.images[':sl6:diskiing:0:525']);drive:load(path)
 assert(drive.filename:sub(-#path)==path,'media not mounted')
end
local function caption_ok()
 -- Independently compare the seven Korean glyphs on title row zero.
 local font=bytes(fixture..'/encoding/hangul-font.bin')
 local base=space:read_u8(0x346)==0 and 0x2000 or 0x4000
 for _,entry in ipairs({{0,4},{1,0},{2,3},{4,5},{5,1},{7,2},{8,6}}) do
  for row=0,7 do
   if (space:read_u8(base+row*1024+entry[1])&0x7f)~=font:byte(entry[2]*8+row+1) then return false end
  end
 end
 return true
end
local frames=0
emu.register_frame_done(function()
 if finished then return end
 frames=frames+1;if frames%6~=0 then return end
 local now=manager.machine.time:as_double();local pc=cpu.state.PC.value
 if now>240 then finish(false,'emulated-time deadline');return end
 if no_lc then
  if pc==build.bootstrap_labels.boot_no_lc_wait then
   local text=table.concat(mask.text(),'\n')
   finish(text:find('16K LANGUAGE CARD REQUIRED.',1,true)~=nil,'no-LC stop');return
  end
  return
 end
 local rows=mask.graphics_text();local screen=table.concat(rows,'\n')
 if screen~=previous then stable=now;previous=screen end
 if now-last<3 or now-stable<0.5 or manager.machine.natkeyboard.is_posting or not manager.machine.natkeyboard.empty then return end
 local waiting=pc>=labels.ko_wait_game_media and pc<labels.ko_wait_game_media+12
 if phase=='boot' and waiting then
  local ok,reason=assets_ok();if not ok then finish(false,reason);return end
  if not caption_ok() then finish(false,'synthetic Korean caption pixels');return end
  capture('startup-assets-loaded');wrong_retry=retry_count
  mount(fixture..'/wrong-english-a.dsk');mask.keys('\r');phase='wrong-media';last=now
 elseif phase=='wrong-media' and waiting and retry_count>wrong_retry then
  local ok,reason=assets_ok();if not ok then finish(false,reason);return end
  if space:read_u8(labels.ko_load_error)~=3 or word(labels.ko_room_size)~=0 then finish(false,'wrong media accepted');return end
  capture('startup-wrong-media');mount('side-b.dsk');mask.keys('\r');phase='opening';last=now
 elseif phase=='opening' then
  if waiting then finish(false,'unexpected media request after valid A');return end
  if rows[16]:find('[ waiting ]',1,true) then
   capture('startup-page-'..#reports);mask.keys(' ');last=now
  elseif rows[16]:find('OK>^',1,true) then
   local ok,reason=assets_ok();if not ok then finish(false,reason);return end
   capture('startup-command-'..index)
   if index>#commands then
    finish(space:read_u8(0x600d)==3 and word(labels.ko_room_size)>0,'opening commands completed');return
   end
   mask.keys(commands[index]..'\r');index=index+1;last=now
  end
 end
end)
