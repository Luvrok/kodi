# the menu (c) of a film, show, season or episode (addon.xml): "Download…"
# with its tmdb id and "Delete from disk" with its id in kodi's library.
# ./actions.py does download and delete
import sys

import xbmcgui

from actions import delete, movie, show
from arr import Error, error


def main():
    tag = sys.listitem.getVideoInfoTag()
    kind = tag.getMediaType()
    try:
        if sys.argv[1] == "delete":
            delete(kind, tag.getDbId())
        elif kind == "movie":
            movie(int(tag.getUniqueID("tmdb")))
        elif kind == "tvshow":
            show(int(tag.getUniqueID("tmdb")), kind, None, None)
        else:
            show(int(tag.getUniqueID("tvshow.tmdb")), kind, tag.getSeason(), tag.getEpisode())
    except Error as e:
        error(e)
    except Exception as e:  # noqa: BLE001 - show what the plugin would hide
        xbmcgui.Dialog().ok("Movie pipe", f"{type(e).__name__}: {e}")


main()
