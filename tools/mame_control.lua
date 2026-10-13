-- Project-specific baseline recording. CPU-visible memory only; never read I/O.
-- Commands execute through the owned MAME Lua console, not a network service.
local json = require('json')
mask = {}
local function machine() return manager.machine end
local function cpu() return machine().devices[':maincpu'] end
local function bytes(address, length)
    assert(address >= 0 and address + length <= 0xc000, 'RAM range required')
    local result = {}
    for offset = 0, length - 1 do
        result[#result + 1] = string.char(cpu().spaces.program:read_u8(address + offset))
    end
    return table.concat(result)
end
function mask.text()
    local rows = {}
    for row = 0, 23 do
        local address = 0x400 + (row % 8) * 128 + math.floor(row / 8) * 40
        local text = {}
        for c in bytes(address, 40):gmatch('.') do
            local value = c:byte() % 128
            if value < 32 then value = value + 64 end
            text[#text + 1] = string.char(value)
        end
        rows[#rows + 1] = table.concat(text)
    end
    return rows
end
function mask.graphics_text()
    local space = cpu().spaces.program
    local font = {}
    for code = 32, 126 do
        local glyph = {}
        for n = 0, 7 do glyph[#glyph+1] = string.char(space:read_u8(0xb300 + code*8 + n) & 0x7f) end
        font[table.concat(glyph)] = string.char(code)
    end
    local rows = {}
    local base = space:read_u8(0x0346) == 0 and 0x2000 or 0x4000
    for row = 0, 15 do
        local text, inverted = {}, {}
        local unknown, inverted_unknown = 0, 0
        for column = 0, 39 do
            local glyph = {}
            for n = 0, 7 do
                local y = row*12+n
                local address = base + ((y & 7) << 10) + (((y >> 3) & 7) << 7) + (y >> 6)*40 + column
                glyph[#glyph+1] = string.char(space:read_u8(address) & 0x7f)
            end
            local code = font[table.concat(glyph)] or '?'
            text[#text+1] = code
            if code == '?' then unknown = unknown + 1 end
            for n = 1, #glyph do glyph[n] = string.char(glyph[n]:byte() ~ 0x7f) end
            code = font[table.concat(glyph)] or '?'
            inverted[#inverted+1] = code
            if code == '?' then inverted_unknown = inverted_unknown + 1 end
        end
        rows[#rows+1] = table.concat(inverted_unknown < unknown and inverted or text)
    end
    return rows
end
function mask.capture(name)
    assert(name:match('^[%w_-]+$'), 'checkpoint name must be a simple filename')
    emu.pause()
    local record = {name=name, version=emu.app_version(), driver=machine().system.name,
                    time=machine().time:as_double(), text=mask.text(), graphics_text=mask.graphics_text(), registers={}, media={}}
    for key, state in pairs(cpu().state) do record.registers[key] = state.value end
    for tag, image in pairs(machine().images) do
        record.media[#record.media + 1] = {tag=tag, filename=image.filename}
    end
    for _, range in ipairs({{0,0xc000,'ram'}, {0,0x400,'low'}, {0x400,0x400,'text'},
                             {0x2000,0x2000,'hgr1'}, {0x4000,0x2000,'hgr2'}}) do
        local f = assert(io.open(name .. '-' .. range[3] .. '.bin', 'wb'))
        f:write(bytes(range[1], range[2])); f:close()
    end
    local f = assert(io.open(name .. '.json', 'w'))
    f:write(json.stringify(record)); f:close()
    machine().screens[':screen']:snapshot(name .. '.png')
    print('MASK ' .. json.stringify(record))
    return record
end
function mask.keys(text)
    machine().natkeyboard:post(text)
    print('MASK keys ' .. json.stringify({time=machine().time:as_double(), text=text}))
end
function mask.swap(side)
    assert(side == 'a' or side == 'b' or side == 'save', 'side must be a, b or save')
    local drive = assert(machine().images[':sl6:diskiing:0:525'])
    local filename = side == 'save' and 'save.dsk' or 'side-' .. side .. '.dsk'
    local result = drive:load(filename)
    assert(drive.filename:sub(-#filename) == filename, 'requested copied media did not mount')
    print('MASK mount ' .. json.stringify({side=side, result=result, filename=drive.filename}))
end
function mask.resume() emu.unpause() end
function mask.go() cpu().debug:go() end
-- A bounded emulated-time run pauses itself; host/tool latency cannot extend
-- a gameplay timer after the selected recording interval.
local pending
local held_key
function mask.release()
    if held_key then held_key.field:clear_value(); held_key = nil end
end
function mask.exit() mask.release(); machine():exit() end
function mask.press(field_name, seconds)
    assert(not held_key, 'release the previous physical key first')
    local found, found_tag
    for tag, port in pairs(machine().ioport.ports) do
        for _, field in pairs(port.fields) do
            if field.name == field_name then
                assert(not found, 'physical field name is ambiguous')
                found, found_tag = field, tag
            end
        end
    end
    assert(found, 'physical key field unavailable')
    assert(seconds > 0 and seconds <= 1, 'bounded physical key duration required')
    found:set_value(1)
    held_key = {field=found, deadline=machine().time:as_double()+seconds}
    print('MASK physical-key ' .. json.stringify({name=field_name, port=found_tag, seconds=seconds}))
end
function mask.run(seconds, name)
    assert(type(seconds) == 'number' and seconds > 0 and seconds <= 300)
    assert(not pending, 'a capture is already scheduled')
    pending = {deadline=machine().time:as_double() + seconds, name=name}
    emu.unpause()
end
function mask.send(text, seconds, name)
    mask.keys(text)
    mask.run(seconds, name)
end
emu.register_frame_done(function()
    if held_key and machine().time:as_double() >= held_key.deadline then
        held_key.field:clear_value()
        held_key = nil
    end
    if pending and machine().time:as_double() >= pending.deadline then
        local name = pending.name
        pending = nil
        mask.capture(name)
    end
end, 'mask-baseline')
print('MASK console helpers loaded')
