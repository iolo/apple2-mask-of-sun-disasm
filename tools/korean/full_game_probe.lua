-- Read-only game observation. All progress is physical/natural keyboard input
-- and one-drive media changes; no CPU, script, world or keyboard-buffer writes.
dofile(assert(os.getenv('MASK_PROJECT_ROOT'))..'/tools/mame_control.lua')
local json=require('json')
local function bytes(path)local f=assert(io.open(path,'rb'));local d=f:read('a');f:close();return d end
local config=json.parse(bytes(assert(os.getenv('MASK_KOREAN_GAME_CONFIG'))))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local labels=config.labels
local index=1;local frames=0;local last=0;local stable=0;local prior=''
local mounted='extra';local pending_media;local pending_message;local seen={};local events={};local finished=false
local glyph_count=0;local bad_references=0;local taps={};local asset_checks=0
local room_pool_checks=0;local pools={};local ending_seen_at;local last_message
for key,spec in pairs(config.pools) do pools[key]=bytes(spec.path):sub(spec.offset+1,spec.offset+spec.bytes) end
local function word(a)return space:read_u8(a)+256*space:read_u8(a+1) end
local function filename()
 local s='';for i=0,9 do s=s..string.char(space:read_u8(labels.ko_retry_name+i)&127) end
 return s:gsub(' +$','')
end
local function tap(address,name,fn)
 taps[#taps+1]=space:install_read_tap(address,address,name,function(_,data,_)
  if cpu.state.PC.value==address or cpu.state.CURPC.value==address then fn() end
 end)
end
tap(labels.ko_print_message,'ko-game-message',function()
 local id=cpu.state.A.value+256*cpu.state.X.value
 last_message=id
 seen[filename()..':'..id]=true
 if id>=0x8000 then seen['*:'..id]=true end
 for _,key in ipairs(config.ending_messages or {}) do
  if seen[key] and not ending_seen_at then ending_seen_at=manager.machine.time:as_double() end
 end
 local event=config.media_messages[tostring(id)]
 if event then pending_media=event;pending_message=id end
end)
tap(labels.ko_glyph_valid,'ko-game-glyph',function()glyph_count=glyph_count+1 end)
tap(labels.ko_bad_reference,'ko-game-bad-reference',function()bad_references=bad_references+1 end)
local function finish(pass,reason)
 if finished then return end
 finished=true
 mask.capture(pass and 'complete' or 'failure')
 local f=assert(io.open('full-game-probe.json','w'))
 f:write(json.stringify({pass=pass,reason=reason,commands=index-1,events=events,
                        glyph_count=glyph_count,bad_references=bad_references,asset_checks=asset_checks,room_pool_checks=room_pool_checks,
                        room=space:read_u8(0x600d),side=space:read_u8(0x601c),
                        filename=filename(),seen_messages=seen,time=manager.machine.time:as_double()}));f:close()
 for _,t in ipairs(taps) do t:remove() end
 print('KOREAN_FULL_GAME '..reason..' commands='..(index-1));mask.exit()
end
local function game_side()return space:read_u8(0x601c)>=2 and 'b' or 'a' end
local function mount(side)
 if side==mounted then return end
 local path=assert(config.media[side]);local drive=assert(manager.machine.images[':sl6:diskiing:0:525'])
 drive:load(path);assert(drive.filename:sub(-#path)==path)
 mounted=side;events[#events+1]={kind='mount',side=side,before_command=index,time=manager.machine.time:as_double()}
end
local resident=bytes(config.resident):sub(17);local font=bytes(config.font):sub(17)
local function compare(data,address)
 for i=1,#data do if space:read_u8(address+i-1)~=data:byte(i) then return false end end
 return true
end
local function assets_ok(include_room)
 space:read_u8(0xc088)
 local ok=compare(resident,0xd000) and compare(font,0xe000)
 if include_room then
  local expected=pools[game_side()..'/'..filename()]
  space:read_u8(0xc080)
  ok=ok and expected~=nil and word(labels.ko_room_size)==#expected and compare(expected,0xd000)
  room_pool_checks=room_pool_checks+1
 end
 space:read_u8(0xc082);asset_checks=asset_checks+1
 return ok
end
local function send(text,reason,now,physical_key)
 events[#events+1]={kind='key',text=text,reason=reason,before_command=index,
                   room=space:read_u8(0x600d),file=filename(),time=now}
 if physical_key then mask.press(physical_key,0.08) else mask.keys(text) end
 last=now
end
emu.register_frame_done(function()
 if finished then return end
 frames=frames+1
 local candidate=config.commands[index]
 local urgent=type(candidate)=='table' and candidate.urgent
 if not urgent and frames%6~=0 then return end
 local now=manager.machine.time:as_double();local pc=cpu.state.PC.value
 if now>config.timeout then finish(false,'emulated deadline');return end
 if bad_references>0 then finish(false,'message reference failure');return end
 if ending_seen_at and now-ending_seen_at>=3 and not (pc>=0x9400 and pc<0x9c00) then
  finish(index>#config.commands,'ending observed');return
 end
 if manager.machine.natkeyboard.is_posting or not manager.machine.natkeyboard.empty then return end
 local boot_wait=pc>=labels.ko_wait_game_media and pc<labels.ko_wait_game_media+12
 local restore_wait=pc>=labels.ko_save_wait and pc<labels.ko_save_wait+12
 if (boot_wait or restore_wait) and now-last>=3 then
  if not assets_ok() then finish(false,'LC assets changed');return end
  if config.runtime_game_prompts then
   local side=game_side()
   if last_message~=config.runtime_game_prompts[side] then finish(false,'wrong game disk prompt');return end
   local capture=string.format('media-%s-%03d-%04d',side,index,#events)
   mask.capture(capture);mask.resume()
   events[#events+1]={kind='runtime_prompt',side=side,message_id=last_message,
                     capture=capture,before_command=index,restore=restore_wait}
  end
  mount(game_side());send('\r','runtime game media',now);return
 end
 local pointer=word(0xd2)
 local pagination=pointer>=config.pagination[1] and pointer<config.pagination[2]
 if not pagination and config.waiting_glyphs then
  local base=space:read_u8(0x0346)==0 and 0x2000 or 0x4000
  local normal,inverse=true,true
  for column,glyph in ipairs(config.waiting_glyphs) do
   for n=0,7 do
    local expected=type(glyph)=='number' and space:read_u8(0xb300+glyph*8+n) or glyph[n+1]
    local y=180+n
    local address=base+((y&7)<<10)+(((y>>3)&7)<<7)+(y>>6)*40+column-1
    local actual=space:read_u8(address)&127
    normal=normal and actual==(expected&127)
    inverse=inverse and actual==((expected&127)~127)
   end
  end
  pagination=normal or inverse
 end
 local rows=mask.graphics_text();local screen=table.concat(rows,'\n')
 if screen~=prior then stable=now;prior=screen end
 if not urgent and (now-last<3 or now-stable<0.5) then return end
 if pagination then
  local capture=string.format('page-%03d-%04d',index,#events)
  mask.capture(capture);mask.resume()
  if pending_media then
   events[#events+1]={kind='media_instruction',side=pending_media,message_id=pending_message,
                     capture=capture,before_command=index}
   mount(pending_media=='game' and game_side() or pending_media);pending_media=nil;pending_message=nil
  end
  send(' ','pagination',now);return
 end
 local custom_ready=false
 if type(candidate)=='table' then
  for _,key in ipairs(candidate.ready_messages or {}) do if seen[key] then custom_ready=true end end
  for _,condition in ipairs(candidate.ram_equals or {}) do
   assert(condition.address>=0 and condition.address<0xc000)
   if space:read_u8(condition.address)~=condition.value then return end
  end
  if candidate.script_range and (pointer<candidate.script_range[1] or pointer>candidate.script_range[2]) then return end
 end
 if not rows[16]:find('OK>^',1,true) and not custom_ready then return end
 -- LC bank reads below are safe only after any in-progress runtime renderer
 -- has returned to ROM mapping. Never interrupt its mapped glyph-copy loop.
 if pc>=0x9400 and pc<0x9c00 then return end
 if type(candidate)=='table' and candidate.wait_messages then
  local ready=false
  for _,key in ipairs(candidate.wait_messages) do if seen[key] then ready=true end end
  if not ready then return end
 end
 if not assets_ok(true) then finish(false,'LC assets or current room pool changed');return end
 mask.capture(string.format('prompt-%03d',index));mask.resume()
 if index>#config.commands then
  finish(space:read_u8(0x600d)==34 and space:read_u8(0x601c)==2 and glyph_count>0,'route completed');return
 end
 local command=type(candidate)=='table' and candidate.command or candidate
 local suffix=type(candidate)=='table' and candidate.no_return and '' or '\r'
 send(command..suffix,command,now,type(candidate)=='table' and candidate.physical_key or nil);index=index+1
end)
