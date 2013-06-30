import sys
from platform import system
import os
from os.path import sep, expanduser, join as join_path
from glob import glob
from collections import defaultdict

import pygame as pg

from . import settings
from .util import dd


class Conf (object):

    # the Game instance; should only really be used to load media with caching
    GAME = None
    IDENT = 'game'
    FPS = dd(60) # per-backend
    DEBUG = False

    # paths
    # need to take care to get unicode path
    if system() == 'Windows':
        try:
            import ctypes
            n = ctypes.windll.kernel32.GetEnvironmentVariableW(u'APPDATA',
                                                               None, 0)
            if n == 0:
                raise ValueError()
        except Exception:
            # fallback (doesn't get unicode string)
            CONF_DIR = os.environ[u'APPDATA']
        else:
            buf = ctypes.create_unicode_buffer(u'\0' * n)
            ctypes.windll.kernel32.GetEnvironmentVariableW(u'APPDATA', buf, n)
            CONF_DIR = buf.value
        CONF_DIR = join_path(CONF_DIR, IDENT)
    else:
        CONF_DIR = join_path(os.path.expanduser(u'~'), '.config', IDENT)
    CONF = join_path(CONF_DIR, 'conf')
    DATA_DIR = os.path.dirname(sys.argv[0])
    if DATA_DIR:
        DATA_DIR += sep
    EVT_DIR = DATA_DIR + 'evt' + sep
    IMG_DIR = DATA_DIR + 'img' + sep
    SOUND_DIR = DATA_DIR + 'sound' + sep
    MUSIC_DIR = DATA_DIR + 'music' + sep
    FONT_DIR = DATA_DIR + 'font' + sep

    # input
    GAME_EVENTS = '''
button _game_quit DOWN
    [ALT] kbd F4

button _game_minimise DOWN
    kbd F10

button _game_fullscreen DOWN
    kbd F11
    [ALT] kbd RETURN
    [ALT] kbd KP_ENTER
'''

    # display
    WINDOW_ICON = None
    WINDOW_TITLE = ''
    MOUSE_VISIBLE = dd(False) # per-backend
    FLAGS = 0
    FULLSCREEN = False
    RESIZABLE = False # also determines whether fullscreen togglable
    RES_W = (960, 540)
    RES_F = None
    MIN_RES_W = (320, 180)
    ASPECT_RATIO = None

    # audio
    MUSIC_AUTOPLAY = False # just pauses music
    MUSIC_VOLUME = dd(.5) # per-backend
    SOUND_VOLUME = .5
    EVENT_ENDMUSIC = pg.USEREVENT
    SOUND_VOLUMES = dd(1)
    # generate SOUNDS = {ID: num_sounds}
    SOUNDS = {}
    ss = glob(join_path(SOUND_DIR, '*.ogg'))
    base = len(join_path(SOUND_DIR, ''))
    for fn in ss:
        fn = fn[base:-4]
        for i in xrange(len(fn)):
            if fn[i:].isdigit():
                # found a valid file
                ident = fn[:i]
                if ident:
                    n = SOUNDS.get(ident, 0)
                    SOUNDS[ident] = n + 1

    # text rendering
    # per-backend, each a {key: value} dict to update Game.fonts with
    REQUIRED_FONTS = dd({})


def _translate_dd (d):
    if isinstance(d, defaultdict):
        return defaultdict(d.default_factory, d)
    else:
        # should be (default, dict)
        return dd(*d)


conf = dict((k, v) for k, v in Conf.__dict__.iteritems()
            if k.isupper() and not k.startswith('__'))
_types = {
    defaultdict: _translate_dd
}
conf = settings.SettingsManager(conf, Conf.CONF, (), _types)
