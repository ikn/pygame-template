from sys import argv
import os
from time import time
from random import choice, randrange
from bisect import bisect

d = os.path.dirname(argv[0])
if d: # else current dir
    os.chdir(d)

import pygame as pg
from pygame.time import wait
if os.name == 'nt':
    # for Windows freeze support
    import pygame._view

pg.mixer.pre_init(buffer = 1024)
pg.init()

from game.conf import conf
from game.level import Level
from game.util import ir, convert_sfc
from game.ext.sched import Scheduler
from game.ext import evthandler as eh
if conf.USE_FONTS:
    from game.ext.fonthandler import Fonts


def get_world_id (world):
    """Return the computed identifier of the given world (or world type).

See Game.create_world for details.

"""
    if hasattr(world, 'id'):
        return world.id
    else:
        if not isinstance(world, type):
            world = type(world)
        return world.__name__.lower()


class Game (object):
    """Handles worlds.

Takes the same arguments as the create_world method and passes them to it.
Only one game should ever exist, and it stores itself in conf.GAME.

    METHODS

create_world
start_world
get_worlds
quit_world
img
render_text
clear_caches
play_snd
find_music
play_music
run
quit
restart
set_overlay
fade
cancel_fade
colour_fade
linear_fade
refresh_display
toggle_fullscreen
minimise

    ATTRIBUTES

scheduler: sched.Scheduler instance for scheduling events.
world: the current running world.
worlds: a list of previous (nested) worlds, most 'recent' last.  Each is a dict
        with 'world', 'overlay' and 'fading' keys the same as the game's
        attributes when the world is active.
overlay: the current overlay (see Game.set_overlay).
fading: whether a fade is in progress (see Game.fade)
file_cache, img_cache, text_cache: caches for loaded image cache (before
                                   resize), images and rendered text
                                   respectively.
fonts: a fonthandler.Fonts instance, or None if conf.USE_FONTS is False.
music: filenames for known music.
screen: the main Pygame surface.

"""

    # attributes to store with worlds, and their initial values
    _world_attrs = {
        'world': None,
        'overlay': False,
        'fading': False,
        '_fade_data': None
    }

    def __init__ (self, *args, **kwargs):
        conf.GAME = self
        self.scheduler = Scheduler()
        self.scheduler.add_timeout(self._update, frames = 1, repeat_frames = 1)
        # initialise caches
        self.file_cache = {}
        self.img_cache = {}
        self.text_cache = {}
        # load display settings
        self.refresh_display()
        self.fonts = Fonts(conf.FONT_DIR) if conf.USE_FONTS else None
        # start first world
        self.worlds = []
        self._last_overlay = False
        self.start_world(*args, **kwargs)
        # start playing music
        pg.mixer.music.set_endevent(conf.EVENT_ENDMUSIC)
        self.find_music()
        self.play_music()
        if not conf.MUSIC_AUTOPLAY:
            pg.mixer.music.pause()

    def _init_world (self):
        """Set some default attributes for a new world."""
        for attr, val in self._world_attrs.iteritems():
            setattr(self, attr, val)

    def _store_world (self):
        """Store the current world in the worlds list."""
        if hasattr(self, 'world') and self.world is not None:
            data = dict((attr, getattr(self, attr)) \
                        for attr, val in self._world_attrs.iteritems())
            self.worlds.append(data)

    def _restore_world (self, data):
        """Restore a world from the given data."""
        self.__dict__.update(data)
        self._select_world(self.world)

    def _select_world (self, world, overlay = False):
        """Set the given world as the current world."""
        self._update_again = True
        self.world = world
        world.graphics.surface = self.screen
        world.graphics.dirty()
        i = get_world_id(world)
        # set some per-world things
        self.scheduler.timer.set_fps(conf.FPS[i])
        if conf.USE_FONTS:
            fonts = self.fonts
            for k, v in conf.REQUIRED_FONTS[i].iteritems():
                fonts[k] = v
        pg.mouse.set_visible(conf.MOUSE_VISIBLE[i])
        pg.mixer.music.set_volume(conf.MUSIC_VOLUME[i])

    def create_world (self, cls, *args, **kwargs):
        """Create a world.

create_world(cls, *args, **kwargs) -> world

cls: the world class to instantiate.
args, kwargs: positional- and keyword arguments to pass to the constructor.

world: the created world; should be a world.World subclass.

Optional world attributes:

    pause(): called when the window loses focus to pause the game.
    id: a unique identifier used for some settings in conf; if none is set,
        type(world).__name__.lower() will be used.

A world is constructed by:

    cls(evthandler, *args, **kwargs)

where evthandler is as taken by world.World (and should be passed to that base
class).

"""
        # create event handler for this world
        h = eh.MODE_HELD
        evthandler = eh.EventHandler({
            pg.ACTIVEEVENT: self._active_cb,
            pg.VIDEORESIZE: self._resize_cb,
            conf.EVENT_ENDMUSIC: self.play_music
        }, [
            (conf.KEYS_FULLSCREEN, self.toggle_fullscreen, eh.MODE_ONDOWN),
            (conf.KEYS_MINIMISE, self.minimise, eh.MODE_ONDOWN)
        ], False, self.quit)
        # instantiate class
        world = cls(evthandler, *args)
        return world

    def start_world (self, *args, **kwargs):
        """Create and switch to a new world.

Takes the same arguments as create_world; see that method for details.

Returns the created world.

"""
        self._store_world()
        return self.switch_world(*args, **kwargs)

    def switch_world (self, *args, **kwargs):
        """Close the current world and start a new one.

Takes the same arguments as create_world and returns the created world.

"""
        self._init_world()
        world = self.create_world(*args, **kwargs)
        self._select_world(world)
        return world

    def get_worlds (self, ident, current = True):
        """Get a list of running worlds, filtered by ID.

get_worlds(ident, current = True) -> worlds

ident: the world identifier to look for (see create_world for details).
current: include the current world in the search.

worlds: the world list, in order of time started, most recent last.

"""
        worlds = []
        current = [{'world': self.world}] if current else []
        for data in self.worlds + current:
            world = data['world']
            if get_world_id(world) == ident:
                worlds.append(world)

    def quit_world (self, depth = 1):
        """Quit the currently running world.

quit_world(depth = 1)

depth: quit this many (nested) worlds.

If this quits the last (root) world, exit the game.

"""
        if depth < 1:
            return
        if self.worlds:
            self._restore_world(self.worlds.pop())
        else:
            self.quit()
        self.quit_world(depth - 1)

    def img (self, filename, size = None, cache = True):
        """Load or scale an image, or retrieve it from cache.

img(filename[, size], cache = True) -> surface

data: a filename to load.
size: scale the image.  Can be an (x, y) size, a rect (in which case its
      dimension is used), or a number to scale by.  If (x, y), either x or y
      can be None to scale to the other with aspect ratio preserved.
cache: whether to store this image in the cache if not already stored.

"""
        # get standardised cache key
        if size is not None:
            if isinstance(size, (int, float)):
                size = float(size)
            else:
                if len(size) == 4:
                    # rect
                    size = size[2:]
                size = tuple(size)
        key = (filename, size)
        if key in self.img_cache:
            return self.img_cache[key]
        # else new: load/render
        filename = conf.IMG_DIR + filename
        # also cache loaded images to reduce file I/O
        if filename in self.file_cache:
            img = self.file_cache[filename]
        else:
            img = convert_sfc(pg.image.load(filename))
            if cache:
                self.file_cache[filename] = img
        # scale
        if size is not None and size != 1:
            current_size = img.get_size()
            if not isinstance(size, tuple):
                size = (ir(size * current_size[0]), ir(size * current_size[1]))
            # handle None
            for i in (0, 1):
                if size[i] is None:
                    size = list(size)
                    scale = float(size[not i]) / current_size[not i]
                    size[i] = ir(current_size[i] * scale)
            img = pg.transform.smoothscale(img, size)
            # speed up blitting (if not resized, this is already done)
            img = convert_sfc(img)
            if cache:
                # add to cache (if not resized, this is in the file cache)
                self.img_cache[key] = img
        return img

    def render_text (self, *args, **kwargs):
        """Render text and cache the result.

Takes the same arguments as fonthandler.Fonts.render, plus a keyword-only
'cache' argument.  If passed, the text is cached under this hashable value, and
can be retrieved from cache by calling this function with the same value for
this argument.

Returns the same value as fonthandler.Fonts

"""
        if self.fonts is None:
            raise ValueError('conf.USE_FONTS is False: text rendering isn\'t'
                             'supported')
        cache = 'cache' in kwargs
        if cache:
            key = kwargs['cache']
            del kwargs['cache']
            if key in self.text_cache:
                return self.text_cache[key]
        # else new: render
        img, lines = self.fonts.render(*args, **kwargs)
        img = convert_sfc(img)
        result = (img, lines)
        if cache:
            self.text_cache[key] = result
        return result

    def clear_caches (self, *caches):
        """Clear image caches.

    Takes any number of strings 'file', 'image' and 'text' as arguments, which
    determine whether to clear the file_cache, img_cache and text_cache
    attributes respectively (see class documentation).  If none is given, all
    caches are cleared.

    """
        if not caches:
            caches = ('file', 'image', 'text')
        if 'file' in caches:
            self.file_cache = {}
        if 'image' in caches:
            self.img_cache = {}
        if 'text' in caches:
            self.text_cache = {}

    def play_snd (self, base_ID, volume = 1):
        """Play a sound.

play_snd(base_ID, volume = 1)

base_ID: the ID of the sound to play (we look for base_ID + i for a number i,
         as many sounds as conf.SOUNDS[base_ID]).
volume: float to scale volume by.

"""
        ID = randrange(conf.SOUNDS[base_ID])
        # load sound
        snd = conf.SOUND_DIR + base_ID + str(ID) + '.ogg'
        snd = pg.mixer.Sound(snd)
        if snd.get_length() < 10 ** -3:
            # no way this is valid
            return
        volume *= conf.SOUND_VOLUME * conf.SOUND_VOLUMES[base_ID]
        snd.set_volume(volume)
        snd.play()

    def find_music (self):
        """Store a list of music files."""
        d = conf.MUSIC_DIR
        try:
            files = os.listdir(d)
        except OSError:
            # no directory
            self.music = []
        else:
            self.music = [d + f for f in files if os.path.isfile(d + f)]

    def play_music (self, event = None):
        """Play next piece of music."""
        if self.music:
            f = choice(self.music)
            pg.mixer.music.load(f)
            pg.mixer.music.play()
        else:
            # stop currently playing music if there's no music to play
            pg.mixer.music.stop()

    def _update (self):
        """Update worlds and draw."""
        self._update_again = True
        while self._update_again:
            self._update_again = False
            self.world.evthandler.update()
            # if a new world was created during the above call, we'll end up
            # updating twice before drawing
            if not self._update_again:
                self._update_again = False
                self.world.update()
        drawn = self.world.draw()
        # update display
        if drawn is True:
            pg.display.flip()
        elif drawn:
            pg.display.update(drawn)
        return True

        world = self.world
        # fade
        if self.fading:
            frame = self.scheduler.timer.frame
            data = self._fade_data['core']
            fn, duration, persist, t = data
            if duration is None:
                # cancel if returned overlay is None
                o = fn(t)
                cancel = o is None
            else:
                # cancel if time limit passed
                cancel = t + .5 * frame > duration
                if not cancel:
                    o = fn(t)
            if cancel:
                self.cancel_fade(persist)
            else:
                self.set_overlay(o)
                data[3] += frame
        # check overlay
        o0 = self._last_overlay
        o = self.overlay
        o_same = o == o0
        draw = True
        if isinstance(o, pg.Surface):
            o_colour = False
            if o.get_alpha() is None and o.get_colorkey() is None:
                # opaque: don't draw
                draw = False
        elif o is not False:
            if len(o) == 4 and o[3] == 0:
                o = False
            else:
                o_colour = True
                if len(o) == 3 or o[3] == 255:
                    # opaque: don't draw
                    draw = False
        s = self._overlay_sfc
        # draw world
        if draw:
            dirty = world.dirty
            draw = world.draw()
            # if (overlay changed or drew something but perhaps not
            # everything), and we have an overlay (we know this will be
            # transparent), then draw everything (if dirty already drew
            # everything)
            if (draw or o != o0) and o is not False and not dirty:
                world.dirty = True
                new_draw = world.draw()
                # merge draw and new_draw
                if True in (draw, new_draw):
                    draw = True
                else:
                    # know draw != False and now draw != True so is rect list
                    draw = list(draw) + (list(new_draw) if new_draw else [])
        # update overlay surface if changed
        if o not in (o0, False):
            if o_colour:
                s.fill(o)
            else:
                s = o
        # draw overlay if changed or world drew
        if o is not False and (o != o0 or draw):
            screen.blit(s, (0, 0))
            draw = True
            if o != o0:
                world.dirty = True
        self._last_overlay = self.overlay
        # update display
        if draw is True:
            pg.display.flip()
        elif draw:
            pg.display.update(draw)
        return True

    def run (self, n = None):
        """Main loop."""
        self.scheduler.run(n)

    def quit (self, event = None):
        """Quit the game."""
        self.scheduler.timer.stop()

    def restart (self, *args):
        """Restart the game."""
        global restarting
        restarting = True
        self.quit()

    def set_overlay (self, overlay, convert = True):
        """Set up an overlay for the current world.

This draws over the screen every frame after the world draws.  It takes a
single argument, which is a Pygame-style colour tuple, with or without alpha,
or a pygame.Surface, or False for no overlay.

The overlay is for the current world only: if another world is started and then
stopped, the overlay will be restored for the original world.

The world's draw method will not be called at all if the overlay to be drawn
this frame is opaque.

"""
        if isinstance(overlay, pg.Surface):
            # surface
            if convert:
                overlay = convert_sfc(overlay)
        elif overlay is not False:
            # colour
            overlay = tuple(overlay)
            # turn RGBA into RGB if no alpha
            if len(overlay) == 4 and overlay[3] == 255:
                overlay = overlay[:3]
        self.overlay = overlay

    def fade (self, fn, time = None, persist = False):
        """Fade an overlay on the current world.

fade(fn[, time], persist = False)

fn: a function that takes the time since the fade started and returns the
    overlay to use, as taken by Game.set_overlay.
time: fade duration in seconds; this is rounded to the nearest frame.  If None
      or not given, fade_fn may return None to end the fade.
persist: whether to continue to show the current overlay when the fade ends
         (else it is set to False).

Calling this cancels any current fade, and calling Game.set_overlay during the
fade will not have any effect.

"""
        self.fading = True
        self._fade_data = {'core': [fn, time, persist, 0]}

    def cancel_fade (self, persist = True):
        """Cancel any running fade on the current world.

Takes the persist argument taken by Game.fade (defaults to True).

"""
        self.fading = False
        self._fade_data = None
        if not persist:
            self.set_overlay(False)

    def _colour_fade_fn (self, t):
        """Fade function for Game.colour_fade."""
        f, os, ts = self._fade_data['colour']
        t = f(t)
        # get waypoints we're between
        i = bisect(ts, t)
        if i == 0:
            # before start
            return os[0]
        elif i == len(ts):
            # past end
            return os[-1]
        o0, o1 = os[i - 1:i + 1]
        t0, t1 = ts[i - 1:i + 1]
        # get ratio of the way between waypoints
        if t1 == t0:
            r = 1
        else:
            r = float(t - t0) / (t1 - t0)
        assert 0 <= r <= 1
        o = []
        for x0, x1 in zip(o0, o1):
            # if one is no overlay, use the other's colours
            if x0 is None:
                if x1 is None:
                    # both are no overlay: colour doesn't matter
                    o.append(0)
                else:
                    o.append(x1)
            elif x1 is None:
                o.append(x0)
            else:
                o.append(x0 + r * (x1 - x0))
        return o

    def colour_fade (self, fn, time, *ws, **kwargs):
        """Start a fade between colours on the current world.

colour_fade(fn, time, *waypoints, persist = False)

fn: a function that takes the time since the fade started and returns the
    'time' to use in bisecting the waypoints to determine the overlay to use.
time: as taken by Game.fade.  This is the time as passed to fn, not as returned
      by it.
waypoints: two or more points to fade to, each (overlay, time).  overlay is as
           taken by Game.set_overlay, but cannot be a surface, and time is the
           time in seconds at which that overlay should be reached.  Times must
           be in order and all >= 0.

           For the first waypoint, time is ignored and set to 0, and the
           waypoint may just be the overlay.  For any waypoint except the first
           or the last, time may be None, or the waypoint may just be the
           overlay.  Any group of such waypoints are spaced evenly in time
           between the previous and following waypoints.
persist: keyword-only, as taken by Game.fade.

See Game.fade for more details.

"""
        os, ts = zip(*((w, None) if w is False or len(w) > 2 else w \
                     for w in ws))
        os = list(os)
        ts = list(ts)
        ts[0] = 0
        # get groups with time = None
        groups = []
        group = None
        for i, (o, t) in enumerate(zip(os, ts)):
            # sort into groups
            if t is None:
                if group is None:
                    group = [i]
                    groups.append(group)
            else:
                if group is not None:
                    group.append(i)
                group = None
            # turn into RGBA
            if o is False:
                o = (None, None, None, 0)
            else:
                o = tuple(o)
                if len(o) == 3:
                    o += (255,)
                else:
                    o = o[:4]
            os[i] = o
        # assign times to waypoints in groups
        for a, b in groups:
            assert a != b
            t0 = ts[a - 1]
            dt = float(ts[b] - t0) / (b - (a - 1))
            for i in xrange(a, b):
                ts[i] = t0 + dt * (i - (a - 1))
        # start fade
        persist = kwargs.get('persist', False)
        self.fade(self._colour_fade_fn, time, persist)
        self._fade_data['colour'] = (fn, os, ts)

    def linear_fade (self, *ws, **kwargs):
        """Start a linear fade on the current world.

Takes the same arguments as Game.colour_fade, without fn and time.

"""
        self.colour_fade(lambda x: x, ws[-1][1], *ws, **kwargs)

    def refresh_display (self, *args):
        """Update the display mode from conf, and notify the world."""
        # get resolution and flags
        flags = conf.FLAGS
        if conf.FULLSCREEN:
            flags |= pg.FULLSCREEN
            r = conf.RES_F
        else:
            w = max(conf.MIN_RES_W[0], conf.RES_W[0])
            h = max(conf.MIN_RES_W[1], conf.RES_W[1])
            r = (w, h)
        if conf.RESIZABLE:
            flags |= pg.RESIZABLE
        ratio = conf.ASPECT_RATIO
        if ratio is not None:
            # lock aspect ratio
            r = list(r)
            r[0] = min(r[0], r[1] * ratio)
            r[1] = min(r[1], r[0] / ratio)
        conf.RES = r
        self.screen = pg.display.set_mode(conf.RES, flags)
        self._overlay_sfc = pg.Surface(conf.RES).convert_alpha()
        if hasattr(self, 'world'):
            self.world.graphics.dirty()
        # clear image cache (very unlikely we'll need the same sizes)
        self.img_cache = {}

    def toggle_fullscreen (self, *args):
        """Toggle fullscreen mode."""
        if conf.RESIZABLE:
            conf.FULLSCREEN = not conf.FULLSCREEN
            self.refresh_display()

    def minimise (self, *args):
        """Minimise the display."""
        pg.display.iconify()

    def _active_cb (self, event):
        """Callback to handle window focus loss."""
        if event.state == 2 and not event.gain:
            try:
                self.world.pause()
            except (AttributeError, TypeError):
                pass

    def _resize_cb (self, event):
        """Callback to handle a window resize."""
        conf.RES_W = (event.w, event.h)
        self.refresh_display()


if __name__ == '__main__':
    if conf.WINDOW_ICON is not None:
        pg.display.set_icon(pg.image.load(conf.WINDOW_ICON))
    if conf.WINDOW_TITLE is not None:
        pg.display.set_caption(conf.WINDOW_TITLE)
    if len(argv) >= 2 and argv[1] == 'profile':
        # profile
        from cProfile import run
        from pstats import Stats
        if len(argv) >= 3:
            t = int(argv[2])
        else:
            t = conf.DEFAULT_PROFILE_TIME
        t *= conf.FPS[None]
        fn = conf.PROFILE_STATS_FILE
        run('Game(Level).run(t)', fn, locals())
        Stats(fn).strip_dirs().sort_stats('cumulative').print_stats(20)
        os.unlink(fn)
    else:
        # run normally
        restarting = True
        while restarting:
            restarting = False
            Game(Level).run()

pg.quit()
