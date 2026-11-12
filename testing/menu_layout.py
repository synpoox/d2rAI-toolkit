"""Where the buttons of D2R's menus are, as fractions of the game window's client area.

Measured on D2R 3.3 with a 1920x1080 client (the testing config's `game.client_size` scaled to that aspect ratio; the
fractions hold for any 16:9 client). `game_ctl.Game.click(fx, fy)` takes these pairs. A different D2R version can move
them: re-measure with `game_ctl.py shot` and change them here, in one place.

Pure data, no game. Used by lod_checks.py.
"""
from __future__ import annotations

D2R_VERSION = "3.3"
CLIENT = (1920, 1080)

# character select
CREATE_NEW = (0.896, 0.869)
PLAY = (0.395, 0.898)           # with exactly one character, it is selected already

# create-character screen
NAME_FIELD = (0.5, 0.83)
CREATE = (0.893, 0.932)
VERSION_LIST = (0.958, 0.863)   # the "Game Version" drop-down
EXPANSION = (0.867, 0.812)      # its "Expansion" entry: a Lord of Destruction character

# class portraits on the create-character screen (index = the class byte of the save, 0x18)
CLASSES = {
    "barbarian": (4, (0.448, 0.46)),
}

# in the Esc menu of a running game
SAVE_AND_EXIT = (0.5, 0.44)
