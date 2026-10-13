local json = require('json')
local fields = {}
for tag, port in pairs(manager.machine.ioport.ports) do
    for _, field in pairs(port.fields) do
        fields[#fields+1] = {port=tag, name=field.name}
    end
end
print('MASK KEYBOARD ' .. json.stringify(fields))
emu.register_frame_done(function() manager.machine:exit() end, 'mask-inspect')
