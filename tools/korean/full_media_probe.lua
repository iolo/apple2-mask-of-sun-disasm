-- Cold boot the real extra disk, then read all resources at instruction stops.
-- The reader harness is test injection; this does not execute the game route.
local json=require('json')
local fixture=assert(os.getenv('MASK_KOREAN_FULL_MEDIA'))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local function bytes(path)local f=assert(io.open(path,'rb'));local d=f:read('a');f:close();return d end
local build=json.parse(bytes(fixture..'/build.json'))
local runtime=bytes(fixture..'/media/runtime/messages.bin')
local interpreter=bytes(fixture..'/media/interpreter.bin')
local resident=bytes(fixture..'/media/resident-asset.bin'):sub(17)
local font=bytes(fixture..'/media/font-asset.bin'):sub(17)
local phase='start';local boot_bp,check_bp;local finished=false;local last=0
local reports={};local mounts={};local previous_script,previous_pool;local rom={}
local function word(a)return space:read_u8(a)+256*space:read_u8(a+1) end
local function ram(address,length)
 local result={};for i=0,length-1 do result[#result+1]=string.char(space:read_u8(address+i)) end
 return table.concat(result)
end
local function compare(data,address,report,kind)
 for i=1,#data do
  local actual=space:read_u8(address+i-1)
  if actual~=data:byte(i) then
   report.pass=false
   if #report.checks<10 then report.checks[#report.checks+1]={kind=kind,address=address+i-1,expected=data:byte(i),actual=actual} end
  end
 end
end
local function finish(pass,reason)
 finished=true
 local f=assert(io.open('full-media-probe.json','w'))
 f:write(json.stringify({pass=pass,reason=reason,phase=phase,case=last,cases=reports,
                        mounts=mounts,time=manager.machine.time:as_double(),pc=cpu.state.PC.value}));f:close()
 print('KOREAN_FULL_MEDIA '..reason..' cases='..last);manager.machine:exit()
end
local function mount(side)
 local path=side=='a' and 'side-b.dsk' or fixture..'/reader-b.dsk'
 local drive=assert(manager.machine.images[':sl6:diskiing:0:525'])
 drive:load(path);assert(drive.filename:sub(-#path)==path)
 mounts[#mounts+1]={side=side,before_case=last+1,time=manager.machine.time:as_double()}
end
emu.register_periodic(function()
 if finished then return end
 local stopped=manager.machine.debugger.execution_state=='stop'
 if manager.machine.time:as_double()>1800 then finish(false,'emulated deadline');return end
 if phase=='start' and stopped then
  boot_bp=cpu.debug:bpset(0x0800,'1','');phase='boot';cpu.debug:go()
 elseif phase=='boot' and stopped then
  if cpu.state.PC.value~=0x0800 or ram(0x0800,16)~=interpreter:sub(5,20) then cpu.debug:go();return end
  cpu.debug:bpclear(boot_bp)
  local check={pass=true,checks={}}
  for _,range in ipairs(build.code_ranges) do compare(runtime:sub(range[1]-0x9400+1,range[2]-0x9400),range[1],check,'boot runtime code') end
  local identity=build.reader_symbols.ko_media_id
  compare(runtime:sub(identity-0x9400+1,identity-0x9400+12),identity,check,'boot media ID')
  if word(build.build.runtime_labels.ko_resident_size)~=4096 or word(build.build.runtime_labels.ko_font_count)~=650 then check.pass=false end
  space:read_u8(0xc088);compare(resident,0xd000,check,'boot resident');compare(font,0xe000,check,'boot font')
  space:read_u8(0xc080);previous_pool=ram(0xd000,4096);space:read_u8(0xc082)
  if not check.pass then reports[#reports+1]=check;finish(false,'startup assets mismatch');return end
  for _,a in ipairs({0xfca8,0xfca9,0xfded,0xfdee,0xfffc,0xfffd}) do rom[#rom+1]={address=a,value=space:read_u8(a)} end
  local code=bytes(fixture..'/reader.bin');for i=1,#code do space:write_u8(0x5000+i-1,code:byte(i)) end
  previous_script=ram(0x6800,0x2c00)
  mount('a');check_bp=cpu.debug:bpset(build.checkpoint,'1','')
  cpu.state.SP.value=0x1ff;cpu.state.PC.value=0x5000;phase='cases';cpu.debug:go()
 elseif phase=='cases' and stopped then
  if cpu.state.PC.value~=build.checkpoint then finish(false,'unexpected stop');return end
  local n=space:read_u8(0x02e1);local spec=build.cases[n]
  if not spec or n~=last+1 then finish(false,'case sequence');return end
  last=n
  local r={number=n,side=spec.side,name=spec.name,pass=true,checks={},time=manager.machine.time:as_double(),
           carry=space:read_u8(0x02e2),error=space:read_u8(0x02e3),pool_size=word(build.reader_symbols.ko_room_size)}
  if r.carry~=1 or r.error~=0 or r.pool_size~=spec.pool_bytes or cpu.state.SP.value~=0x1fd then r.pass=false end
  compare(bytes(fixture..'/case-'..n..'-script.bin'),spec.destination,r,'script')
  local prefix=spec.destination-0x6800;local finish_at=prefix+spec.script_bytes
  compare(previous_script:sub(1,prefix),0x6800,r,'main prefix guard')
  compare(previous_script:sub(finish_at+1),0x6800+finish_at,r,'main suffix guard')
  previous_script=ram(0x6800,0x2c00)
  space:read_u8(0xc080)
  compare(bytes(fixture..'/case-'..n..'-pool.bin'),0xd000,r,'LC pool')
  compare(previous_pool:sub(spec.pool_bytes+1),0xd000+spec.pool_bytes,r,'LC tail guard')
  previous_pool=ram(0xd000,4096)
  space:read_u8(0xc088);compare(resident,0xd000,r,'resident preserved');compare(font,0xe000,r,'font preserved')
  space:read_u8(0xc082)
  for _,range in ipairs(build.code_ranges) do compare(runtime:sub(range[1]-0x9400+1,range[2]-0x9400),range[1],r,'runtime code') end
  for _,v in ipairs(rom) do if space:read_u8(v.address)~=v.value then r.pass=false end end
  reports[#reports+1]=r
  if not r.pass then finish(false,'resource read failed');return end
  if n==#build.cases then cpu.debug:bpclear(check_bp);phase='finish'
  elseif build.cases[n+1].side~=spec.side then mount(build.cases[n+1].side) end
  cpu.debug:go()
 elseif phase=='finish' and space:read_u8(0x02e0)==0xa5 then finish(true,'all resources read') end
end)
