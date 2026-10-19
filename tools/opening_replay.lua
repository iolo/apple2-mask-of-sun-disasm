-- Reproducible fresh-boot exploration of the supplied original disks.
-- Captures every pagination screen and command response. Never changes game RAM.
dofile(assert(os.getenv('MASK_PROJECT_ROOT')) .. '/tools/mame_control.lua')
local json = require('json')
local commands = {
    'LOOK', 'INVENTORY', 'FERNAP', 'GET', 'GET LAMP', 'FERNAP GUN',
    'EXIT PLANE', 'GET MAP', 'ENTER JEEP', 'W', 'TAKE ALL', 'EXIT JEEP',
    'GO HUT', 'GIVE FOOD', 'EXIT HUT', 'ENTER JEEP', 'W', 'NW',
    'DROP ALL', 'GET BOTTLE', 'EXIT JEEP', 'LOOK BEHIND STATUE',
    'GET HEAD', 'PLACE HEAD ON STATUE', 'ENTER JEEP'
}
local route_path = os.getenv('MASK_ROUTE')
-- An optional route may be passed directly when another startup script loads us.
local selected_route = ...
if type(selected_route) ~= 'table' then selected_route = nil end
local timeout = 600
local ending_text
local media_events = {}
local media_index = 1
if selected_route or route_path then
    local route = selected_route
    if not route then
        local f = assert(io.open(route_path, 'r'))
        route = json.parse(f:read('a')); f:close()
    end
    assert(type(route.commands) == 'table' and #route.commands > 0, 'replay route needs commands')
    commands = route.commands
    timeout = route.timeout or 1200
    ending_text = route.ending_text
    media_events = route.media_events or {}
    print('MASK replay route loaded: ' .. #commands .. ' commands')
end
local index, serial, frames = 1, 0, 0
local last_action, last_screen, stable_since = 0, '', 0
local wait_seen = {}
local mounted_side = 'a'
local function stamp(kind)
    serial = serial + 1
    return string.format('%03d-%s-%02d', serial, kind, index)
end
local log = assert(io.open('replay-inputs.jsonl', 'w'))
-- Observe entry to the native COUT handler without modifying fetched bytes.
-- Captures dialogue that immediately transitions into the next room/animation.
local text_log = assert(io.open('output-characters.jsonl', 'w'))
local native_cpu = manager.machine.devices[':maincpu']
local keyboard_log, keyboard_tap
if os.getenv('MASK_KEYBOARD_TRACE') then
    keyboard_log = assert(io.open('keyboard-reads.jsonl', 'w'))
    local previous_key
    keyboard_tap = native_cpu.spaces.program:install_read_tap(0xc000, 0xc010, 'mask-keyboard', function(address, data, _)
        local space = native_cpu.spaces.program
        if space:read_u8(0x600d) == 49 and (address == 0xc010 or (address == 0xc000 and data ~= previous_key)) then
            keyboard_log:write(json.stringify({time=manager.machine.time:as_double(), address=address,
                value=data, pc=native_cpu.state.PC.value, script_pc=space:read_u8(0xd2)+256*space:read_u8(0xd3)}) .. '\n')
        end
        if address == 0xc000 then previous_key = data end
    end)
end
local output_tap = native_cpu.spaces.program:install_read_tap(0xb317, 0xb317, 'mask-cout', function(_, data, _)
    if native_cpu.state.PC.value == 0xb317 or native_cpu.state.CURPC.value == 0xb317 then
        text_log:write(json.stringify({time=manager.machine.time:as_double(), value=native_cpu.state.A.value}) .. '\n')
    end
    -- No integer is returned, so the emulated data is left unchanged.
end)
local function send(text, reason, now, physical_key)
    log:write(json.stringify({time=now, text=text, reason=reason, command_index=index, physical_key=physical_key}) .. '\n')
    log:flush()
    if physical_key then mask.press(physical_key, 0.08) else mask.keys(text) end
    last_action = now
end
local function finish(outcome)
    local result = assert(io.open('replay-result.json', 'w'))
    result:write(json.stringify({outcome=outcome, command_index=index,
        command_count=#commands, time=manager.machine.time:as_double(), side=mounted_side}) .. '\n')
    result:close()
    log:close(); text_log:close(); output_tap:remove()
    if keyboard_tap then keyboard_tap:remove(); keyboard_log:close() end
    mask.exit()
end
emu.register_frame_done(function()
    frames = frames + 1
    local candidate = commands[index]
    local urgent = type(candidate) == 'table' and candidate.urgent
    if not urgent and frames % 6 ~= 0 then return end
    local now = manager.machine.time:as_double()
    local rows = mask.graphics_text()
    local screen = table.concat(rows, '\n')
    local requested_side
    local media_event = media_events[media_index]
    if media_event and screen:find(media_event.when, 1, true) then
        requested_side = media_event.side
        media_index = media_index + 1
    end
    if screen:find('side A, turn it over to side B,', 1, true) then requested_side = 'b' end
    if screen:find('side B, turn it over to side A,', 1, true) then requested_side = 'a' end
    if requested_side and requested_side ~= mounted_side then
        mask.swap(requested_side)
        mounted_side = requested_side
        log:write(json.stringify({time=now, kind='mount', side=requested_side}) .. '\n'); log:flush()
    end
    if type(candidate) == 'table' and candidate.wait_for and screen:find(candidate.wait_for, 1, true) then
        wait_seen[index] = true
    end
    local state_ready = true
    if type(candidate) == 'table' and candidate.ram_equals then
        for _, condition in ipairs(candidate.ram_equals) do
            assert(condition.address >= 0 and condition.address < 0xc000, 'replay predicates must not read I/O')
            if manager.machine.devices[':maincpu'].spaces.program:read_u8(condition.address) ~= condition.value then
                state_ready = false
            end
        end
    end
    if type(candidate) == 'table' and candidate.script_range then
        local space = manager.machine.devices[':maincpu'].spaces.program
        local pointer = space:read_u8(0xd2) + space:read_u8(0xd3)*256
        if pointer < candidate.script_range[1] or pointer > candidate.script_range[2] then state_ready = false end
    end
    if screen ~= last_screen then last_screen = screen; stable_since = now end
    if ending_text and index > #commands and screen:find(ending_text, 1, true) and now - stable_since >= 0.5 then
        mask.capture('ending'); print('MASK FULL_REPLAY_COMPLETE'); finish('complete'); return
    end
    if now > timeout then
        mask.capture('timeout'); print('MASK FULL_REPLAY_TIMEOUT'); finish('timeout'); return
    end
    if manager.machine.natkeyboard.is_posting or not manager.machine.natkeyboard.empty then return end
    local bottom = rows[16]
    local custom_ready = type(candidate) == 'table' and candidate.ready_text and screen:find(candidate.ready_text, 1, true)
    local urgent_prompt = urgent and (bottom:find('OK>%^') or custom_ready)
    if not urgent_prompt and (now - last_action < 3 or now - stable_since < 0.5) then return end
    if bottom:find('%[ waiting %]') then
        mask.capture(stamp('waiting'))
        send(' ', 'pagination', now)
        mask.resume()
    elseif bottom:find('OK>%^') or custom_ready then
        if not state_ready then return end
        if type(candidate) == 'table' and candidate.wait_for and not wait_seen[index] then return end
        mask.capture(stamp('prompt'))
        if index > #commands then
            print('MASK OPENING_REPLAY_COMPLETE'); finish('commands-exhausted'); return
        end
        local command = type(candidate) == 'table' and candidate.command or candidate
        local suffix = type(candidate) == 'table' and candidate.no_return and '' or '\r'
        send(command .. suffix, command, now, type(candidate) == 'table' and candidate.physical_key or nil)
        index = index + 1
        mask.resume()
    end
end, 'mask-opening-replay')
