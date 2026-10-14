-- Boot original DOS before exercising candidate loader on synthetic resources.
local json=require('json')
local root=assert(os.getenv('MASK_PROJECT_ROOT'))
local fixture=assert(os.getenv('MASK_KOREAN_PROBE'))
local cpu=manager.machine.devices[':maincpu'];local space=cpu.spaces.program
local function bytes(path)
    local f=assert(io.open(path,'rb'));local data=f:read('a');f:close();return data
end
local build=json.parse(bytes(fixture..'/build.json'))
local native=bytes(root..'/build/korean/english-baseline/interpreter.bin')
local runtime=bytes(fixture..'/runtime/messages.bin')
local function load(path,address)
    local data=bytes(path);for i=1,#data do space:write_u8(address+i-1,data:byte(i)) end
end
local function word(a)return space:read_u8(a)+256*space:read_u8(a+1) end
local phase='start';local boot_bp,check_bp;local finished=false
local reports={};local rom={};local last=0
local previous_script
local previous_pool=string.rep(string.char(0x69),1024)
local function ram(address,length)
    local values={}
    for i=0,length-1 do values[#values+1]=string.char(space:read_u8(address+i)) end
    return table.concat(values)
end
local function finish(pass,reason)
    local report={pass=pass,reason=reason,phase=phase,time=manager.machine.time:as_double(),
                  pc=cpu.state.PC.value,case=space:read_u8(0x02e1),cases=reports}
    local f=assert(io.open('loader-probe.json','w'));f:write(json.stringify(report));f:close()
    manager.machine.screens[':screen']:snapshot('loader-probe.png')
    print('KOREAN_LOADER_PROBE '..json.stringify(report));finished=true;manager.machine:exit()
end
local function compare(data,base,report,kind)
    for i=1,#data do
        local got=space:read_u8(base+i-1)
        if got~=data:byte(i) then
            report.pass=false
            if #report.checks<12 then table.insert(report.checks,{kind=kind,address=base+i-1,expected=data:byte(i),actual=got}) end
        end
    end
end
emu.register_periodic(function()
    if finished then return end
    local stopped=manager.machine.debugger.execution_state=='stop'
    local now=manager.machine.time:as_double()
    if now>180 then finish(false,'emulated-time deadline');return end
    if phase=='start' and stopped then
        boot_bp=cpu.debug:bpset(0x0800,'1','')
        phase='boot';cpu.debug:go()
    elseif phase=='boot' and stopped then
        local matches=cpu.state.PC.value==0x0800
        for i=5,20 do if space:read_u8(0x0800+i-5)~=native:byte(i) then matches=false end end
        if not matches then cpu.debug:go();return end
        cpu.debug:bpclear(boot_bp)
        for _,a in ipairs({0xfca8,0xfca9,0xfded,0xfdee,0xfffc,0xfffd}) do table.insert(rom,{address=a,value=space:read_u8(a)}) end
        load(fixture..'/probe.bin',0x5000);load(fixture..'/runtime/messages.bin',0x9400)
        load(root..'/build/korean/english-baseline/chargen.bin',0xadfc)
        space:write_u8(0x02e0,0);space:write_u8(0x02e1,0)
        space:write_u8(0x67ff,0x5a)
        previous_script=ram(0x6800,0x2c00)
        check_bp=cpu.debug:bpset(build.checkpoint,'1','')
        cpu.state.SP.value=0x1ff;cpu.state.PC.value=0x5000
        phase='cases';cpu.debug:go()
    elseif phase=='cases' and stopped then
        if cpu.state.PC.value~=build.checkpoint then finish(false,'unexpected debugger stop');return end
        local n=space:read_u8(0x02e1);local spec=build.cases[n]
        if not spec or n~=last+1 then finish(false,'case sequence mismatch');return end
        last=n
        local report={number=n,name=spec.name,pass=true,checks={},carry=space:read_u8(0x02e2),
                      error=space:read_u8(0x02e3),room_size=word(build.reader_symbols.ko_room_size),
                      print_success=space:read_u8(0x02e4),time=now,stack=cpu.state.SP.value}
        report.irq_mask=space:read_u8(0x02e5)
        -- On success native RWTS stores an unspecified A value at IOB+13.
        -- Carry is authoritative; inspect this byte only for an expected error.
        report.rwts_status_raw=space:read_u8(0x0bb8)
        if report.carry~=(spec.error==0 and 1 or 0) or report.error~=spec.error or
           report.room_size~=(spec.error==0 and spec.pool_bytes or 0) or report.stack~=0x1fd or
           report.irq_mask~=(spec.interrupts_enabled and 0 or 4) then report.pass=false end
        if spec.expected_rwts_error and report.rwts_status_raw~=spec.expected_rwts_error then report.pass=false end
        for _,check in ipairs(rom) do if space:read_u8(check.address)~=check.value then report.pass=false end end
        if space:read_u8(0x67ff)~=0x5a then report.pass=false end
        for _,range in ipairs(build.code_ranges) do
            compare(runtime:sub(range[1]-0x9400+1,range[2]-0x9400),range[1],report,'runtime code')
        end
        if spec.error==0 then
            compare(bytes(fixture..'/case-'..n..'-script.bin'),spec.destination,report,'script')
            space:read_u8(0xc080)
            compare(bytes(fixture..'/case-'..n..'-pool.bin'),0xd000,report,'room pool')
            space:read_u8(0xc082)
        elseif spec.partial_script_bytes then
            compare(bytes(fixture..'/case-'..n..'-script.bin'):sub(1,spec.partial_script_bytes),spec.destination,report,'partial script')
            if spec.partial_pool_bytes then
                space:read_u8(0xc080)
                compare(bytes(fixture..'/case-'..n..'-pool.bin'):sub(1,spec.partial_pool_bytes),0xd000,report,'partial pool invalidated')
                space:read_u8(0xc082)
            end
        elseif spec.name~='missing script EOF' then
            compare(previous_script,0x6800,report,'rejected load preserves script/library')
        end
        previous_script=ram(0x6800,0x2c00)
        space:read_u8(0xc080)
        if spec.error~=0 and not spec.partial_pool_bytes then
            compare(previous_pool,0xd000,report,'rejected load preserves LC payload')
        end
        previous_pool=ram(0xd000,1024)
        space:read_u8(0xc082)
        space:read_u8(0xc088);compare(string.rep(string.char(0x69),4096),0xd000,report,'resident preserved')
        space:read_u8(0xc080);compare(string.rep(string.char(0x69),3072),0xd400,report,'bank2 guard')
        compare(string.rep(string.char(0x69),8192),0xe000,report,'common font preserved');space:read_u8(0xc082)
        if spec.print_text then
            if report.print_success~=1 then report.pass=false end
            compare(bytes(fixture..'/expected-hgr.bin'),0x2000,report,'loaded message HGR')
        end
        reports[#reports+1]=report
        if not report.pass then finish(false,'case failed');return end
        if n==#build.cases then cpu.debug:bpclear(check_bp);phase='finish' end
        cpu.debug:go()
    elseif phase=='finish' and space:read_u8(0x02e0)~=0 then
        finish(space:read_u8(0x02e0)==0xa5,'completed')
    end
end)
