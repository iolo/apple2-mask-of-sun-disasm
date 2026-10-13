-- A one-request mailbox for manual local control while emulation is paused.
-- It has no route, next-command or pagination logic. Operator supplies every act.
dofile(assert(os.getenv('MASK_PROJECT_ROOT'))..'/tools/manual_record.lua')
local json=require('json')
local current,seen
local function ack(request)
    local file=assert(io.open('manual-ack.json','w'))
    file:write(json.stringify(request));file:close()
end
emu.register_periodic(function()
    if current and manual.last_capture==current.label then
        ack(current);current=nil
    end
    if current then return end
    local file=io.open('manual-request.json','r')
    if not file then return end
    local request=json.parse(file:read('*a'));file:close()
    if request.id==seen then return end
    seen=request.id
    if request.kind=='input' then
        current=request;manual.action(request.text,request.label,request.condition,request.maximum)
    elseif request.kind=='observe' then
        current=request;manual.observe(request.label,request.condition,request.maximum,request.minimum)
    elseif request.kind=='mount' then manual.swap(request.side);ack(request)
    elseif request.kind=='physical-key' then
        current=request;manual.press(request.key,request.label,request.condition,request.maximum)
    elseif request.kind=='finish' then ack(request);manual.finish()
    else error('unsupported manual operation') end
end)
local recovery=os.getenv('MASK_MANUAL_STATE')
if recovery then
    manual.recover(recovery)
    manual.observe('recovery','ready',120,1)
else manual.observe('boot','ready',120,1) end
