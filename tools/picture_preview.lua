-- Isolated graphics fixtures: explicitly inject data and call the native renderer.
-- These are asset checks, not a gameplay replay; each restores a booted RAM image.
dofile(assert(os.getenv('MASK_PROJECT_ROOT')) .. '/tools/mame_control.lua')
local json = require('json')
local file = assert(io.open(assert(os.getenv('MASK_ROUTE')), 'r'))
local fixtures = json.parse(file:read('*a')); file:close()
local cpu = manager.machine.devices[':maincpu']
local space = cpu.spaces.program
local saved, active, index = nil, false, 0
local deadline
local function start_next()
    index = index + 1
    if index > #fixtures.jobs then
        local report = assert(io.open('pictures.json', 'w'))
        report:write(json.stringify(fixtures)); report:close()
        print('MASK PICTURE_PREVIEWS_COMPLETE'); mask.exit(); return
    end
    local job = fixtures.jobs[index]
    emu.pause()
    for address = 0, 0xbfff do space:write_u8(address, saved[address+1]) end
    -- White canvas, both pages, native phase bit retained. No foreign overlay base.
    for address = 0x2000, 0x5fff do space:write_u8(address, 0xff) end
    for offset, value in ipairs(job.bytes) do space:write_u8(0x9000+offset-1, value) end
    local count = job.bytes[13]
    local vectors = 0x9000+13+count
    space:write_u8(0x1691, vectors & 0xff); space:write_u8(0x1692, vectors >> 8)
    for offset = 0, 5+count do space:write_u8(0x169b+offset, job.bytes[8+offset]) end
    -- Mailbox harness avoids changing PC between calls. MAME frame boundaries can
    -- fall inside a 6502 instruction; rewriting PC then can retain in-flight work.
    -- LDA request; BEQ loop; clear request; set video; JSR draw; set done; JMP loop.
    local harness = {0xad,0x1f,0x02, 0xf0,0xfb, 0xa9,0x00, 0x8d,0x1f,0x02,
                     0xad,0x50,0xc0, 0xad,0x52,0xc0, 0xad,0x57,0xc0,
                     0x20,0x37,0x18, 0xa9,0x01, 0x8d,0x20,0x02, 0x4c,0x00,0x02}
    for offset, value in ipairs(harness) do space:write_u8(0x200+offset-1, value) end
    space:write_u8(0x220,0); space:write_u8(0x21f,1)
    if index == 1 then cpu.state.SP.value = 0x1ff; cpu.state.PC.value = 0x200 end
    active = true
    deadline = manager.machine.time:as_double()+120
    mask.resume()
end
emu.register_frame_done(function()
    local now = manager.machine.time:as_double()
    if not saved then
        if now < 25 then return end
        if space:read_u8(0x1837)~=0x20 or space:read_u8(0xb300)~=0x4c then
            if now < 60 then return end
            mask.capture('fixture-boot-failed'); mask.exit()
            error('native renderer and lookup/font not loaded before fixture setup')
        end
        saved = {}
        for address = 0, 0xbfff do saved[address+1] = space:read_u8(address) end
        start_next()
    elseif active and space:read_u8(0x220)==1 then
        active = false
        mask.capture(fixtures.jobs[index].id)
        start_next()
    elseif active and now > deadline then
        active = false; mask.capture('picture-timeout')
        mask.exit()
        error('native picture fixture timed out: ' .. fixtures.jobs[index].id)
    end
end,'mask-picture-preview')
