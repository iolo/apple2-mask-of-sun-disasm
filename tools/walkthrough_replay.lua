-- MAME -autoboot_script entry point for a complete Mask of the Sun playthrough.
-- Launch with tools/mame_session.py so side-a.dsk and side-b.dsk are isolated copies.
-- The route is based on mask-of-sun-walkthrough.pdf and its verified native inputs.

local root = assert(os.getenv('MASK_PROJECT_ROOT'),
    'launch through tools/mame_session.py to set MASK_PROJECT_ROOT')
local route_path = root .. '/docs/full-route.json'
local json = require('json')
local file = assert(io.open(route_path, 'r'))
local route = json.parse(file:read('a'))
file:close()
assert(route.ending_text == 'Watch for the next Ultrasoft adventure.',
    'full route must include the ending marker')
assert(type(route.commands) == 'table' and #route.commands > 0,
    'full route must include commands')

-- The replay controller reads each native screen, advances pagination, handles
-- timed prompts, swaps disk sides, and stops only after the ending appears.
local controller = assert(loadfile(root .. '/tools/opening_replay.lua'))
controller(route)
