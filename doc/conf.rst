:mod:`conf`---game configuration
================================

.. module:: conf

This is a
:class:`settings.DummySettingsManager <engine.settings.DummySettingsManager>`
instance used for configuration.  Changes to many of these settings should
occur before the engine is initialised to take effect.

.. data:: GAME
   :annotation: = None

   The current :class:`game.Game <engine.game.Game>` instance.

.. data:: IDENT
   :annotation: = 'game'

   Game identifier, used in some filenames.

.. data:: FPS

   Frames per second to aim for, as a
   ``{`` :attr:`game.World.id <engine.game.World.id>` ``: fps}``
   defaultdict, with a default value of ``60``.

.. data:: DEBUG
   :annotation: = False

   Just a debug flag to establish convention; doesn't get used by anything in
   the engine.

Paths
-----

.. data:: CONF

   File in which settings to be saved are stored. Defaults to
   ``~/.config/<IDENT>/conf`` or ``%APPDATA\<IDENT>\conf``.

.. data:: EVT_DIR
   :annotation: = 'evt/'

   Directory to load event configuration files from.

.. data:: IMG_DIR
   :annotation: = 'img/'

   Directory to load images from.

.. data:: SOUND_DIR
   :annotation: = 'sound/'

   Directory to load sounds from.

.. data:: MUSIC_DIR
   :annotation: = 'music/'

   Directory to load music from.

.. data:: FONT_DIR
   :annotation: = 'font/'

   Directory to load fonts from.

Display
-------

.. data:: WINDOW_ICON
   :annotation: = None

   Path to image to use for the window icon.

.. data:: WINDOW_TITLE
   :annotation: = ''

.. data:: MOUSE_VISIBLE

   Whether the mouse is visible when inside the game window.  This is a
   ``{`` :attr:`game.World.id <engine.game.World.id>` ``: visible}``
   defaultdict, defaulting to ``False``.

.. data:: FLAGS
   :annotation: = 0

   Extra flags to pass to ``pygame.display.set_mode``.

.. data:: FULLSCREEN
   :annotation: = False

   Whether to start the window in fullscreen mode.

.. data:: RESIZABLE
   :annotation: = False

   Whether the window can be freel resized (also determines whether fullscreen
   mode can be toggled).

.. data:: RES_W
   :annotation: = (960, 540)

   Window resolution.

.. data:: RES_F
   :annotation: = None

   Fullscreen resolution; if ``None``, the first value in the return value of
   ``pygame.display.list_modes`` is used.

.. data:: RES

   Current game resolution, no matter the display mode.  Only exists if the
   engine is initialised.

.. data:: MIN_RES_W
   :annotation: = (320, 180)

   Minimum windowed resolution, if the window can be resized.

.. data:: ASPECT_RATIO
   :annotation: = None

   Floating-point aspect ratio to fix the window at, if it can be resized.

Audio
-----

.. data:: MUSIC_AUTOPLAY
   :annotation: = False

   If ``False``, music is loaded, but initially paused.

.. data:: MUSIC_VOLUME

   ``{`` :attr:`game.World.id <engine.game.World.id>` ``: volume}``
   defaultdict, with default value ``0.5``.

.. data:: SOUND_VOLUME
   :annotation: = 0.5

.. data:: SOUND_VOLUMES

   ``{sound_id: volume}`` defaultdict, with default value ``1``, for
   ``sound_id`` in :data:`SOUNDS`.

.. data:: SOUNDS

   Automatically generated ``{sound_id: num_sounds}`` dict for sounds present
   in :data:`SOUND_DIR`.  Finds sound files of the form
   ``<sound_id><number>.ogg`` for integer numbers starting from ``0`` with no
   gaps.

.. data:: REQUIRED_FONTS

   Fonts to automatically load as a
   ``{`` :attr:`game.World.id <engine.game.World.id>` ``: fonts}`` defaultdict,
   where ``fonts`` is a dict to update the game's
   :class:`txt.Fonts <engine.txt.Fonts>` instance with, and defaults to ``{}``.