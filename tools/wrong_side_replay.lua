-- Bound a side-B boot attempt; inspect firmware text and the actual halt PC.
dofile(assert(os.getenv('MASK_PROJECT_ROOT')) .. '/tools/mame_control.lua')
local complete = false
emu.register_frame_done(function()
    if not complete and manager.machine.time:as_double() >= 5 then
        complete = true
        mask.capture('wrong-side'); mask.exit()
    end
end, 'mask-wrong-side')
