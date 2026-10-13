-- Reproducible fresh-boot exploration of the supplied original disks.
-- Captures every pagination screen and command response. Never changes game RAM.
dofile(assert(os.getenv('MASK_PROJECT_ROOT')) .. '/tools/mame_control.lua')
local commands = {
    'LOOK', 'INVENTORY', 'FERNAP', 'GET', 'GET LAMP', 'FERNAP GUN',
    'EXIT PLANE', 'GET MAP', 'ENTER JEEP', 'W', 'TAKE ALL', 'EXIT JEEP',
    'GO HUT', 'GIVE FOOD', 'EXIT HUT', 'ENTER JEEP', 'W', 'NW',
    'DROP ALL', 'GET BOTTLE', 'EXIT JEEP', 'LOOK BEHIND STATUE',
    'GET HEAD', 'PLACE HEAD ON STATUE', 'ENTER JEEP'
}
local index, serial, frames = 1, 0, 0
local last_action, last_screen, stable_since = 0, '', 0
local function stamp(kind)
    serial = serial + 1
    return string.format('%03d-%s-%02d', serial, kind, index)
end
local log = assert(io.open('replay-inputs.jsonl', 'w'))
local json = require('json')
local function send(text, reason, now)
    log:write(json.stringify({time=now, text=text, reason=reason, command_index=index}) .. '\n')
    log:flush()
    mask.keys(text)
    last_action = now
end
emu.register_frame_done(function()
    frames = frames + 1
    if frames % 6 ~= 0 then return end
    local now = manager.machine.time:as_double()
    local rows = mask.graphics_text()
    local screen = table.concat(rows, '\n')
    if screen ~= last_screen then last_screen = screen; stable_since = now end
    if now > 600 then
        mask.capture('timeout'); log:close(); manager.machine:exit(); return
    end
    if now - last_action < 3 or now - stable_since < 0.5 then return end
    local bottom = rows[16]
    if bottom:find('%[ waiting %]') then
        mask.capture(stamp('waiting'))
        send(' ', 'pagination', now)
        mask.resume()
    elseif bottom:find('OK>') then
        mask.capture(stamp('prompt'))
        if index > #commands then
            log:close(); print('MASK OPENING_REPLAY_COMPLETE'); manager.machine:exit(); return
        end
        send(commands[index] .. '\r', commands[index], now)
        index = index + 1
        mask.resume()
    end
end, 'mask-opening-replay')
