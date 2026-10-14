-- Owned synthetic test session: inject a main-RAM test binary, never game text.
local json = require('json')
local root = assert(os.getenv('MASK_PROJECT_ROOT'))
local fixture = assert(os.getenv('MASK_KOREAN_PROBE'))
local cpu = manager.machine.devices[':maincpu']
local space = cpu.spaces.program
local started, finished = false, false
local ef = assert(io.open(fixture .. '/expected.json'))
local expected = json.parse(ef:read('a')); ef:close()
local rom = {}
local function load(path, address)
    local f = assert(io.open(path, 'rb')); local data = f:read('a'); f:close()
    for i=1,#data do space:write_u8(address+i-1, data:byte(i)) end
end
-- Debugger stop is an instruction boundary; frame-time PC writes can retain
-- an in-flight 6502 instruction. Launch this probe with --debug.
emu.register_periodic(function()
    if finished then return end
    local now = manager.machine.time:as_double()
    if not started and manager.machine.debugger.execution_state == 'stop' then
        for _,address in ipairs({0xfca8,0xfca9,0xfded,0xfdee,0xfffc,0xfffd}) do
            table.insert(rom, {address=address, value=space:read_u8(address)})
        end
        load(fixture .. '/probe.bin', 0x6000)
        load(root .. '/build/korean/english-baseline/chargen.bin', 0xadfc)
        space:write_u8(0x02e0, 0)
        cpu.state.SP.value = 0x1ff
        cpu.state.PC.value = 0x6000
        started = true
        cpu.debug:go()
    elseif started and (space:read_u8(0x02e0) ~= 0 or now > 10) then
        local marker = space:read_u8(0x02e0)
        local report = {marker=marker, time=now, expect_lc=expected.expect_lc, checks={}, pc=cpu.state.PC.value}
        report.pass = marker == (expected.expect_lc and 0xa5 or 0x4e)
        if expected.expect_lc and marker == 0xa5 then
            for _,check in ipairs(expected.bytes) do
                local got = space:read_u8(check.address)
                if got ~= check.value then
                    report.pass = false
                    table.insert(report.checks, {address=check.address, expected=check.value, actual=got})
                end
            end
        end
        -- ROM must be restored even when no Language Card is present.
        for _,check in ipairs(rom) do
            if space:read_u8(check.address) ~= check.value then report.pass = false end
        end
        local f=assert(io.open('lc-probe.json','w')); f:write(json.stringify(report)); f:close()
        manager.machine.screens[':screen']:snapshot('lc-probe.png')
        print('KOREAN_LC_PROBE ' .. json.stringify(report))
        finished = true
        manager.machine:exit()
    end
end)
