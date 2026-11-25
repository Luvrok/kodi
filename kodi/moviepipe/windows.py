# the add-on's windows' base, majan-like (resources/skins/Default/1080i):
# a kodi window from the add-on's skin, one control id (50) for the rows of
# the two list windows (./releases.py, ./downloads.py)
import os

import xbmcgui

from arr import HERE

# 0.png .. 100.png, a bar per 5% (../addons.nix)
BARS = os.path.join(HERE, "resources", "skins", "Default", "media", "bars")


class Window(xbmcgui.WindowXMLDialog):
    def rows(self):
        return self.getControl(50)


def window(cls, xml, **attrs):
    w = cls(xml, HERE, "Default", "1080i")
    for k, v in attrs.items():
        setattr(w, k, v)
    return w
