-- Read-only observation except explicit one-shot RWTS fault injection in the
-- fault profile; ordinary gameplay uses the existing cold-boot replay helper.
local json=require('json')
local fixture=assert(os.getenv('MASK_KOREAN_PROBE'))
local profile=assert(os.getenv('MASK_KOREAN_SAVE_PROFILE'))
local function bytes(path)local f=assert(io.open(path,'rb'));local d=f:read('a');f:close();return d end
local build=json.parse(bytes(fixture..'/startup-build.json'))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local function word(a)return space:read_u8(a)+256*space:read_u8(a+1) end
local state={profile=profile,asset_checks=0,failures={},fault_injected=false,recovery_wait_seen=false,
             recovered=false,unsafe_extension_fetches=0,total_extension_fetches=0,restore_sector_reads=0,write_sectors={}}
local unsafe=false;local swapped=false;local last_assets=0
local function save()
 local f=assert(io.open('save-probe.json','w'));f:write(json.stringify(state));f:close()
end
local taps={}
local function tap(address,name,fn)
 taps[#taps+1]=space:install_read_tap(address,address,name,function(_,data,_)
  if cpu.state.PC.value==address or cpu.state.CURPC.value==address then fn() end
 end)
end
tap(0xbd00,'save-sector',function()
 if cpu.state.A.value~=0x0b or cpu.state.Y.value~=0xab then return end
 if space:read_u8(0x0bb7)==2 then
  state.write_sectors[#state.write_sectors+1]={space:read_u8(0x0baf),space:read_u8(0x0bb0)}
  if profile=='write-fault' and not state.fault_injected and space:read_u8(0x0bb4)==0x93 then
   space:write_u8(0x0bae,1);state.fault_injected=true;save()
  end
 end
 local sp=cpu.state.SP.value&255
 local caller=space:read_u8(0x100+((sp+1)&255))+256*space:read_u8(0x100+((sp+2)&255))
 if space:read_u8(0x0bb7)==1 and caller==0x1279 then
  state.restore_sector_reads=state.restore_sector_reads+1
  if profile=='fault' and not state.fault_injected and space:read_u8(0x0bb4)==0x93 then
   -- Ask for volume 1 on volume 254: real native RWTS returns carry/error $20.
   space:write_u8(0x0bae,1);state.fault_injected=true;unsafe=true;save()
  end
 end
end)
tap(build.save_labels.ko_snapshot_error_guard,'save-error',function()
 if state.fault_injected and not state.recovery_wait_seen then
  state.rwts_error=space:read_u8(0x0bb8);space:write_u8(0x0bae,0);save()
 end
end)
tap(0x12a8,'restore-transfer-complete',function()
 if unsafe then
  state.recovered=space:read_u8(0x0bb4)==0x1f and space:read_u8(0x0baf)==22 and space:read_u8(0x0bb0)==15
  unsafe=false;save()
 end
end)
taps[#taps+1]=space:install_read_tap(0x9400,0x9bff,'unsafe-extension',function(address,data,_)
 if cpu.state.PC.value==address or cpu.state.CURPC.value==address then
  state.total_extension_fetches=state.total_extension_fetches+1
  if unsafe then state.unsafe_extension_fetches=state.unsafe_extension_fetches+1;save() end
 end
end)
dofile(assert(os.getenv('MASK_PROJECT_ROOT'))..'/tools/opening_replay.lua')
local function compare(data,base)
 for i=1,#data do if space:read_u8(base+i-1)~=data:byte(i) then return false end end
 return true
end
local frames=0
emu.register_frame_done(function()
 assert(#taps>0) -- retain native tap handles for the whole emulation
 frames=frames+1;if frames%12~=0 then return end
 local now=manager.machine.time:as_double();local screen=table.concat(mask.graphics_text(),'\n')
 if screen:find('RESTORE ERROR. RETRY: RETURN',1,true) and not swapped then
  state.recovery_wait_seen=true;state.error_pc=cpu.state.PC.value
  if profile=='fault' then state.extension_poisoned=space:read_u8(0x9400)==0xcc end
  if profile=='wrong-id' then
   state.world_unchanged=space:read_u8(0x600d)==1
   state.room_pool_before_restore=word(build.runtime_labels.ko_room_size)
  end
  if profile~='write-fault' then
   local drive=assert(manager.machine.images[':sl6:diskiing:0:525'])
   drive:load(fixture..'/valid-save.dsk');assert(drive.filename:sub(-14)=='valid-save.dsk')
  end
  swapped=true;save()
 end
 if now-last_assets>=3 and not unsafe and screen:find('OK>^',1,true) and word(build.runtime_labels.ko_font_count)==650 then
  space:read_u8(0xc088)
  local resident=compare(bytes(fixture..'/resident-asset.bin'):sub(17),0xd000)
  local font=compare(bytes(fixture..'/font-asset.bin'):sub(17),0xe000)
  space:read_u8(0xc082)
  if not resident or not font then state.failures[#state.failures+1]='LC resident/font changed' end
  state.asset_checks=state.asset_checks+1;last_assets=now;save()
 end
end)
