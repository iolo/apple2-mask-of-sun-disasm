-- Operator-stepped recording. No route list, command choice, pagination or swap
-- automation: each action/observation is explicitly supplied in the Lua console.
dofile(assert(os.getenv('MASK_PROJECT_ROOT')) .. '/tools/mame_control.lua')
local json=require('json')
manual={}
local log=assert(io.open('manual-inputs.jsonl','w'))
local text_log=assert(io.open('output-characters.jsonl','w'))
local cpu=manager.machine.devices[':maincpu']
local space=cpu.spaces.program
local pending
local tap=space:install_read_tap(0xb317,0xb317,'manual-output',function()
    if cpu.state.PC.value==0xb317 then
        text_log:write(json.stringify({time=manager.machine.time:as_double(),value=cpu.state.A.value})..'\n')
        text_log:flush()
    end
end)
local function record(event)
    event.time=manager.machine.time:as_double()
    log:write(json.stringify(event)..'\n');log:flush()
end
function manual.observe(label,condition,maximum,minimum)
    assert(not pending,'finish prior observation')
    local now=manager.machine.time:as_double()
    pending={label=label,condition=condition or 'ready',deadline=now+(maximum or 120),earliest=now+(minimum or 1)}
    record({kind='observe',label=label,condition=pending.condition,maximum=maximum or 120,minimum=minimum or 1})
    mask.resume()
end
function manual.action(text,label,condition,maximum)
    assert(not pending,'finish prior observation')
    record({kind='input',label=label,text=text})
    mask.keys(text);manual.observe(label,condition,maximum)
end
function manual.swap(side)
    assert(not pending,'finish prior observation')
    record({kind='mount',side=side});mask.swap(side)
end
function manual.recover(path)
    assert(not pending,'finish prior observation')
    record({kind='native-checkpoint-load',path=path})
    manager.machine:load(path)
end
function manual.press(key,label,condition,maximum)
    assert(not pending,'finish prior observation')
    record({kind='physical-key',key=key,label=label,seconds=0.08})
    mask.press(key,0.08);manual.observe(label,condition,maximum)
end
function manual.finish()
    assert(not pending,'finish prior observation')
    record({kind='finish'});log:close();text_log:close();tap:remove();mask.exit()
end
emu.register_frame_done(function()
    if not pending then return end
    local now=manager.machine.time:as_double()
    if now<pending.earliest then return end
    local keyboard=manager.machine.natkeyboard
    if keyboard.is_posting or not keyboard.empty then return end
    local rows=mask.graphics_text();local screen=table.concat(rows,'\n')
    local ready
    if pending.condition=='ready' then
        -- Timed prompts use a native WAIT loop, rather than the normal reader.
        ready=rows[16]:find('OK>%^') or rows[16]:find('%[ waiting %]')
        -- The answer reader can place its cursor after a question, without OK>.
        if space:read_u8(0x2a)==0x78 and space:read_u8(0x2b)==2 then
            ready=ready or (cpu.state.PC.value>=0xcbc and cpu.state.PC.value<=0xcc1)
        end
    elseif pending.condition=='safe-jump' then
        local pointer=space:read_u8(0xd2)+256*space:read_u8(0xd3)
        ready=space:read_u8(0x6003)==1 and pointer>=0x6c8c and pointer<=0x6d26
    else ready=screen:find(pending.condition,1,true) end
    if ready or now>=pending.deadline then
        local observation=pending;pending=nil
        record({kind='capture',label=observation.label,condition=observation.condition,timeout=not not (not ready)})
        -- Save all emulator/device state without modifying native game RAM.
        -- This is recovery evidence, separate from the game's SAVE command.
        -- schedule_save resumes the machine; capture must pause it afterwards.
        manager.machine:save(observation.label)
        mask.capture(observation.label)
        manual.last_capture=observation.label
        print('MASK MANUAL_CAPTURE_COMPLETE '..observation.label)
    end
end,'mask-manual-record')
mask.capture('manual-start')
print('MASK MANUAL_READY')
