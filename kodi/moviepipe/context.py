# the menu (c) of a film, show, season or episode (addon.xml): "Download…"
# with its tmdb id, "Delete from disk" with its id in kodi's library, and
# "Subtitles" on a film: russian ones next to it (./subs.py).
# ./actions.py does download and delete
import sys

from actions import delete, movie, show
from arr import Error, error
from subs import movie as subtitles


def main():
    tag = sys.listitem.getVideoInfoTag()
    kind = tag.getMediaType()
    try:
        if sys.argv[1] == "delete":
            delete(kind, tag.getDbId())
        elif sys.argv[1] == "subtitles":
            if kind == "movie":
                subtitles(int(tag.getUniqueID("tmdb")))
            else:
                error("Subtitles: films for now")
        elif kind == "movie":
            movie(int(tag.getUniqueID("tmdb")))
        elif kind == "tvshow":
            show(int(tag.getUniqueID("tmdb")), kind, None, None)
        else:
            show(int(tag.getUniqueID("tvshow.tmdb")), kind, tag.getSeason(), tag.getEpisode())
    except Error as e:
        error(e)


main()
