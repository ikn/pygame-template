"""Callback-based event and input handling.

---NODOC---

TODO:
    [ESSENTIAL]
 - BUG: button events don't really do the right thing
    - should track real held state from held state of all inputs, and only send up/down if it actually changes
 - BUG: input normalisation doesn't work (button held state)
 - state that inputs/events should only have one parent (maybe protect against it)
 - eh.grab (and maybe have grab toggle for getting all input for a while)
 - eh.set_{thresholds,bdys} like deadzones (but also allow global, and same with deadzones)
    - make them setters
    - think of a nicer system for it (some sort of InputFilter, then {filter: value}?)
    - or just have .find_inputs then user can do it manually?
 - Event.disable()/enable()
 - config: can do (per-device, per-device_id/var or global) deadzones/thresholds/bdy (can already do per-input, right?)
 - conffile.generate{,_s}, eh.save{,_s}
 - config: domain filenames
    - try loading from a homedir one first, then fall back to the distributed one
    - save to the homedir one

    [FUTURE]
 - UI buttons (+ other controls?)
    - are ButtonInput
    - have any number of moveable 'cursors' in eh, with .click(), .move_by(), .move_to
        - can attach to relaxis events
    - region: InputRect, InputArea subclass
    - have a ButtonInput for cursors being in a region (specialised subclasses for mice, etc.)
        - UI button is this combined with another ButtonInput (eg. mouse click)
            - have input combiners
    - how to use in cfg (since they might be dynamic, and use input combiners)?
 - eh.postpone(), Event.postpone()
 - eh.detect_pads() (make sure to re-initialise already-initialised ones)
 - Scheme
 - tools for editing/typing text
 - input recording and playback (allow white/blacklisting by domain/registered event name)
 - eh.*monitor_deadzones
 - a way to register new input/event types (consider module data structures)
    - document using __str__ backends
    - working with config (evts/inputs have .args_from_config(*words))
 - joy ball (seems like RelAxisInput, but need a pad with a ball to test)
    - or maybe just do it and include a warning

    [config]
 - support for events as inputs
 - input groups for having the same inputs in different events, eg.

    [next]
        kbd ENTER
        kbd KP_RETURN
        kbd SPACE

    button next DOWN REPEAT .3 .1
        [next]
        kbd RIGHT

    button confirm DOWN
        [next]

    [MP example]

button pause DOWN
    kbd ESCAPE
    pad button 1

axis2 moveK1
    left kbd LEFT
    right kbd RIGHT
    up kbd UP
    down kbd DOWN
axis2 moveK2
    left kbd a
    right kbd d
    up kbd w
    down kbd s
axis2 moveC
    left right pad <x> axis 0
    up down pad <x> axis 1 .1
axis2 imoveC
    left right pad <x> axis 0
    down up pad <x> axis 1 .1

button fire1
    kbd rctrl
button fire2
    kbd space
button fire3
    pad button 0

scheme play
    # must have the same number of options in each field
    move moveK1 moveK2 moveC # if no more args, take everything this prefixes, and sort
    fire fire1 fire2 fire3 # or could do this; here, order is fixed

----

eh['pause'].cb(pause)
# call function move() with the player from players above followed by
# (horizontal, vertical) axis positions (added via scheme 'play')
eh['move'].cb(move)
# create n_players control schemes with priorities favouring gamepad over WASD
# over arrow keys
# players is list of ({action: action_id}, {device_var: device})
# priorities are high to low; omitted ones don't get used
players = eh['play'].distribute(n_players, 'C', 'K2', 'K1')

---NODOC---

"""

from .handler import *
from .inputs import *
from .evts import *
from . import conffile
