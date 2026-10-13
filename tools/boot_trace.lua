-- Read-only execution-entry observations during an unmodified fresh boot.
dofile(assert(os.getenv('MASK_PROJECT_ROOT')) .. '/tools/mame_control.lua')
local json = require('json')
local cpu = manager.machine.devices[':maincpu']
local space = cpu.spaces.program
local log = assert(io.open('boot-entries.jsonl', 'w'))
local taps, seen = {}, {}
local capturing = false
local last_rom_request
local function word(address) return space:read_u8(address)+256*space:read_u8(address+1) end
local points = {0xc600, 0xc65c, 0x0801, 0xb600, 0xb700, 0x9d00, 0x9600,
                0xa000, 0xbd00, 0x0800, 0x0d00, 0xb300, 0xb317}
local finish_pending = false
for _, address in ipairs(points) do
    taps[#taps+1] = space:install_read_tap(address, address, 'boot-entry-' .. address, function(_, _, _)
        if capturing or cpu.state.PC.value ~= address then return end
        if address == 0xc65c then
            local request = word(0x26) .. ':' .. space:read_u8(0x3d)
            if request == last_rom_request then return end
            last_rom_request = request
        end
        local repeatable = address == 0x0801 or address == 0xc65c or address == 0xbd00
        if seen[address] and not repeatable then return end
        local record = {address=address, time=manager.machine.time:as_double(), registers={},
            boot_buffer=word(0x26), boot_sector=space:read_u8(0x3d), boot_slot=space:read_u8(0x2b)}
        for key, state in pairs(cpu.state) do record.registers[key] = state.value end
        if address == 0xbd00 then
            local iob = cpu.state.Y.value+256*cpu.state.A.value
            if iob < 0xbff0 then
                record.iob = {address=iob, slot=space:read_u8(iob+1), drive=space:read_u8(iob+2),
                    track=space:read_u8(iob+4), sector=space:read_u8(iob+5),
                    buffer=word(iob+8), command=space:read_u8(iob+12)}
            end
        end
        log:write(json.stringify(record) .. '\n'); log:flush()
        if not seen[address] then
            seen[address] = true
            -- Mark first, so snapshot reads cannot recursively record this entry.
            capturing = true
            mask.capture(string.format('entry-%04x', address)); mask.resume()
            capturing = false
        end
        if address == 0xb317 then finish_pending = true end
        -- No replacement byte; observed memory and fetched instructions unchanged.
    end)
end
emu.register_frame_done(function()
    if finish_pending or manager.machine.time:as_double() > 120 then
        for _, tap in ipairs(taps) do tap:remove() end
        log:close(); mask.capture('boot-final'); print('MASK BOOT_TRACE_COMPLETE'); mask.exit()
    end
end, 'mask-boot-trace')
