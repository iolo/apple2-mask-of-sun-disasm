-- Instruction-boundary synthetic runtime fixture. Owns this MAME process only.
local json = require('json')
local root = assert(os.getenv('MASK_PROJECT_ROOT'))
local fixture = assert(os.getenv('MASK_KOREAN_PROBE'))
local cpu = manager.machine.devices[':maincpu']
local space = cpu.spaces.program
local started, finished = false, false
local function bytes(path)
    local f=assert(io.open(path,'rb'));local data=f:read('a');f:close();return data
end
local function load(path,address)
    local data=bytes(path)
    for i=1,#data do space:write_u8(address+i-1,data:byte(i)) end
end
local rom={}
emu.register_periodic(function()
    if finished then return end
    local now=manager.machine.time:as_double()
    if not started and manager.machine.debugger.execution_state=='stop' then
        for _,address in ipairs({0xfca8,0xfca9,0xfded,0xfdee,0xfffc,0xfffd}) do
            table.insert(rom,{address=address,value=space:read_u8(address)})
        end
        load(fixture..'/probe.bin',0x6800)
        load(fixture..'/runtime/messages.bin',0x9400)
        -- Assembled interpreter binary includes a four-byte DOS header.
        local native=bytes(fixture..'/interpreter.bin')
        for i=5,#native do space:write_u8(0x0800+i-5,native:byte(i)) end
        load(root..'/build/korean/english-baseline/chargen.bin',0xadfc)
        load(fixture..'/font.bin',0x2000)
        load(fixture..'/resident.bin',0x4000)
        load(fixture..'/room.bin',0x5000)
        space:write_u8(0x02e0,0);space:write_u8(0x02e1,0)
        cpu.state.SP.value=0x1ff;cpu.state.PC.value=0x6800
        started=true;cpu.debug:go()
    elseif started and (space:read_u8(0x02e0)~=0 or now>10) then
        local marker=space:read_u8(0x02e0)
        local report={pass=marker==0xa5,marker=marker,case=space:read_u8(0x02e1),
                      pc=cpu.state.PC.value,time=now,checks={},checked_hgr_bytes=0,checked_lc_bytes=0}
        -- Check ROM before any debugger-side LC inspection changes the mapping.
        for _,check in ipairs(rom) do
            if space:read_u8(check.address)~=check.value then report.pass=false end
        end
        local function compare(data,base,kind)
            for i=1,#data do
                local got=space:read_u8(base+i-1)
                if got~=data:byte(i) then
                    report.pass=false
                    if #report.checks<20 then table.insert(report.checks,{kind=kind,address=base+i-1,
                        expected=data:byte(i),actual=got}) end
                end
            end
        end
        if marker==0xa5 then
            compare(bytes(fixture..'/expected-hgr.bin'),0x2000,'HGR')
            report.checked_hgr_bytes=16384
            space:read_u8(0xc088)
            compare(bytes(fixture..'/resident.bin'),0xd000,'resident')
            space:read_u8(0xc080)
            compare(bytes(fixture..'/room.bin'),0xd000,'room')
            compare(bytes(fixture..'/font.bin'),0xe000,'font')
            report.checked_lc_bytes=4096+1024+8192
            space:read_u8(0xc082)
        end
        local f=assert(io.open('message-probe.json','w'));f:write(json.stringify(report));f:close()
        manager.machine.screens[':screen']:snapshot('message-probe.png')
        print('KOREAN_MESSAGE_PROBE '..json.stringify(report))
        finished=true;manager.machine:exit()
    end
end)
