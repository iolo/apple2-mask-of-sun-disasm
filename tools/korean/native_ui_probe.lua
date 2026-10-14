-- Instruction-boundary test harness; not game-route evidence.
local json=require('json')
local root=assert(os.getenv('MASK_PROJECT_ROOT'))
local fixture=assert(os.getenv('MASK_KOREAN_NATIVE_UI'))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local function bytes(path)local f=assert(io.open(path,'rb'));local d=f:read('a');f:close();return d end
local build=json.parse(bytes(fixture..'/build.json'))
local function load(path,address,skip)
 local data=bytes(path);skip=skip or 0
 for i=skip+1,#data do space:write_u8(address+i-skip-1,data:byte(i)) end
end
local function compare(data,address,r,kind)
 for i=1,#data do
  local actual=space:read_u8(address+i-1)
  if actual~=data:byte(i) then
   r.pass=false
   if #r.differences<8 then r.differences[#r.differences+1]={kind=kind,address=address+i-1,expected=data:byte(i),actual=actual} end
  end
 end
end
local started=false;local finished=false;local count=0;local reports={};local bp;local rom={}
local function finish(pass,reason)
 finished=true
 local f=assert(io.open('native-ui-probe.json','w'))
 f:write(json.stringify({pass=pass,reason=reason,cases=reports,case_count=count,time=manager.machine.time:as_double(),pc=cpu.state.PC.value}));f:close()
 print('KOREAN_NATIVE_UI '..reason);manager.machine:exit()
end
emu.register_periodic(function()
 if finished then return end
 if manager.machine.time:as_double()>60 then finish(false,'deadline');return end
 if manager.machine.debugger.execution_state~='stop' then return end
 if not started then
  for _,a in ipairs({0xfca8,0xfca9,0xfded,0xfdee,0xfffc,0xfffd}) do rom[#rom+1]={address=a,value=space:read_u8(a)} end
  load(build.media..'/interpreter.bin',0x0800,4)
  load(build.media..'/intrinsics.bin',0x0cfc)
  load(build.media..'/parms.bin',0x02fc)
  load(build.media..'/runtime/messages.bin',0x9400)
  load(root..'/build/korean/english-baseline/chargen.bin',0xadfc)
  load(fixture..'/probe.bin',0x6800)
  load(fixture..'/font.bin',0x2000);load(fixture..'/resident.bin',0x4000);load(fixture..'/room.bin',0x5000)
  space:write_u8(0x02e0,0);space:write_u8(0x02e1,0)
  space:read_u8(0xc050);space:read_u8(0xc052);space:read_u8(0xc057);space:read_u8(0xc054)
  cpu.state.SP.value=0x1ff;cpu.state.PC.value=0x6800
  bp=cpu.debug:bpset(build.checkpoint,'1','');started=true;cpu.debug:go()
 else
  if cpu.state.PC.value~=build.checkpoint then finish(false,'unexpected stop');return end
  local n=space:read_u8(0x02e1);local spec=build.cases[n]
  if not spec or n~=count+1 then finish(false,'case order');return end
  count=n;local r={number=n,id=spec.id,page=spec.page,pass=true,differences={}}
  for _,v in ipairs(rom) do if space:read_u8(v.address)~=v.value then r.pass=false end end
  if space:read_u8(0x24)~=spec.end_column or space:read_u8(0x25)~=spec.end_row then r.pass=false;r.cursor={space:read_u8(0x24),space:read_u8(0x25)} end
  if cpu.state.SP.value~=0x1fd or space:read_u8(build.ko_room_size)~=0 or space:read_u8(build.ko_room_size+1)~=0 then r.pass=false end
  compare(bytes(fixture..'/expected-'..n..'.bin'),0x2000,r,'both HGR pages')
  space:read_u8(0xc088);compare(bytes(fixture..'/resident.bin'),0xd000,r,'resident')
  space:read_u8(0xc080);compare(bytes(fixture..'/room.bin'),0xd000,r,'invalid room pool')
  compare(bytes(fixture..'/font.bin'),0xe000,r,'font');space:read_u8(0xc082)
  reports[#reports+1]=r
  if not r.pass then finish(false,'screen/assets mismatch');return end
  if spec.id=='native-media-b' then manager.machine.screens[':screen']:snapshot('native-ui-page'..spec.page..'.png') end
  if n==#build.cases then cpu.debug:bpclear(bp);finish(true,'all native UI cases');return end
  cpu.debug:go()
 end
end)
