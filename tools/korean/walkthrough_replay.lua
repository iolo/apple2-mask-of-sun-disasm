-- Complete the r01-extra-save Korean release from a cold EXTRA-disk boot.
-- Launch through tools/mame_session.py with --boot-extra --language-card.
-- Commands are English; screen messages are recognized by native message ID.

local root = assert(os.getenv('MASK_PROJECT_ROOT'), 'launch through tools/mame_session.py')
dofile(root .. '/tools/mame_control.lua')
local json = require('json')
local function read_json(path)
    local file = assert(io.open(path, 'r'))
    local value = json.parse(file:read('a'))
    file:close()
    return value
end

local release = root .. '/output/korean-playtest-r01-extra-save'
local build = read_json(release .. '/build-manifest.json')
assert(build.catalog_sha256 == '295b6cc8a34f09a5433e9ee33cc88499b2ee66d4b51db132a638e763230b3bc0',
    'this replay targets the r01-extra-save Korean release')
local route = read_json(root .. '/docs/full-route.json')
local commands = assert(route.commands)
local cpu = manager.machine.devices[':maincpu']
local space = cpu.spaces.program
local labels = build.runtime_labels
-- The release manifest exports the boot wait, while these two internal labels
-- are retained in the matching build's messages.lbl.
labels.ko_print_message = 38187
labels.ko_retry_name = 39530
local drive = assert(manager.machine.images[':sl6:diskiing:0:525'])
assert(drive.filename:sub(-9) == 'extra.dsk', 'boot from the copied EXTRA disk')

-- These IDs and script offsets come from this release's encoded room packages.
local waiting_id = 32779
local disk_instruction_id = 32879
local ghost_ids = {[22]=true, [24]=true}
local jump_ids = {[13]=true, [17]=true}
local ending_id = 18
local jump_first, jump_last = 27273, 27427
local more_first, more_last = 29288, 29309

local function word(address)
    return space:read_u8(address) + 256 * space:read_u8(address + 1)
end
local function room_file()
    local name = {}
    for i = 0, 9 do name[#name+1] = string.char(space:read_u8(labels.ko_retry_name+i) & 127) end
    return table.concat(name):gsub(' +$', '')
end
local function wanted_side()
    return space:read_u8(0x601c) >= 2 and 'b' or 'a'
end

local index, frames, last_action = 1, 0, 0
local last_screen, stable_since = '', 0
local mounted_side = 'extra'
local page_pending, page_since, disk_pending = false, 0, false
local ghost_faded, jump_prompt_seen, ending_at = false, false, nil
local log = assert(io.open('korean-replay-inputs.jsonl', 'w'))
local function record(value)
    log:write(json.stringify(value) .. '\n')
    log:flush()
end
local function mount(side, now)
    if side == mounted_side then return end
    mask.swap(side)
    mounted_side = side
    record({kind='mount', side=side, before_command=index, time=now})
end
local function send(value, reason, now, physical_key)
    record({kind='key', text=value, reason=reason, command_index=index, time=now})
    if physical_key then mask.press(physical_key, 0.08) else mask.keys(value) end
    last_action = now
end
local message_tap = space:install_read_tap(labels.ko_print_message, labels.ko_print_message,
    'mask-korean-walkthrough-message', function(address)
        if cpu.state.PC.value ~= address and cpu.state.CURPC.value ~= address then return end
        local id = cpu.state.A.value + 256 * cpu.state.X.value
        local name = room_file()
        local now = manager.machine.time:as_double()
        if id == waiting_id then page_pending, page_since = true, now end
        if id == disk_instruction_id then disk_pending = true end
        if name == 'ROOM 15.0' and ghost_ids[id] then ghost_faded = true end
        if name == 'ROOM 39.0' and jump_ids[id] then jump_prompt_seen = true end
        if name == 'ROOM 50.0' and id == ending_id then ending_at = now end
    end)

local function finish(pass, reason)
    mask.capture(pass and 'korean-ending' or 'korean-failure')
    local result = assert(io.open('korean-replay-result.json', 'w'))
    result:write(json.stringify({pass=pass, reason=reason, command_count=#commands,
        commands_sent=index-1, side=mounted_side, room=space:read_u8(0x600d),
        ghost_faded=ghost_faded, jump_prompt_seen=jump_prompt_seen,
        ending_message_seen=ending_at ~= nil, time=manager.machine.time:as_double()}) .. '\n')
    result:close()
    log:close()
    message_tap:remove()
    print('MASK KOREAN_WALKTHROUGH_' .. (pass and 'COMPLETE' or 'FAILED') .. ': ' .. reason)
    mask.exit()
end

emu.register_frame_done(function()
    frames = frames + 1
    local candidate = commands[index]
    local urgent = type(candidate) == 'table' and candidate.urgent
    if not urgent and frames % 6 ~= 0 then return end
    local now = manager.machine.time:as_double()
    if space:read_u8(0x600d) == 15 and space:read_u8(0x6326) == 15 then
        ghost_faded = true -- The gold bowl becomes reachable only after the ghost fades.
    end
    if ending_at and now - ending_at >= 3 then
        finish(index > #commands and mounted_side == 'b' and space:read_u8(0x600d) == 50,
            'Korean final message observed')
        return
    end
    if now > 4000 then finish(false, 'emulated-time deadline'); return end
    if manager.machine.natkeyboard.is_posting or not manager.machine.natkeyboard.empty then return end

    local pc = cpu.state.PC.value
    if pc >= labels.ko_wait_game_media and pc < labels.ko_wait_game_media + 12 and now-last_action >= 3 then
        mount(wanted_side(), now)
        send('\r', 'boot game disk', now)
        return
    end

    local pointer = word(0xd2)
    local rows = mask.graphics_text()
    local screen = table.concat(rows, '\n')
    if screen ~= last_screen then last_screen, stable_since = screen, now end
    if (page_pending or (pointer >= more_first and pointer < more_last))
            and now-last_action >= (urgent and 0.1 or 3) and now-page_since >= 0.3 then
        if disk_pending then mount(wanted_side(), now); disk_pending = false end
        record({kind='page', before_command=index, time=now})
        page_pending = false
        send(' ', 'pagination', now)
        return
    end

    local custom_ready = type(candidate) == 'table' and candidate.ready_text and jump_prompt_seen
    if not rows[16]:match('OK>%s*%^') and not custom_ready then return end
    if not urgent and (now-last_action < 3 or now-stable_since < 0.5) then return end
    if not candidate then return end
    if type(candidate) == 'table' then
        if candidate.wait_for then
            assert(candidate.wait_for == 'The apparition fades')
            if not ghost_faded then return end
        end
        for _, condition in ipairs(candidate.ram_equals or {}) do
            assert(condition.address >= 0 and condition.address < 0xc000)
            if space:read_u8(condition.address) ~= condition.value then return end
        end
        if candidate.ready_text then
            assert(candidate.ready_text == 'Press return to jump,')
            if pointer < jump_first or pointer > jump_last then return end
        end
    end

    local command = type(candidate) == 'table' and candidate.command or candidate
    local suffix = type(candidate) == 'table' and candidate.no_return and '' or '\r'
    send(command .. suffix, command, now, type(candidate) == 'table' and candidate.physical_key or nil)
    index = index + 1
end, 'mask-korean-walkthrough')
