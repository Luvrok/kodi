# collections: the library's movie sets and tmdb's, as a wall of posters
# (resources/skins/Default/1080i/moviepipe-sets.xml). library: what kodi
# scraped, by name or by the number of films, a text keeps the ones whose
# name has it; tmdb: what its collection search finds. enter opens the
# collection's films in videos, esc comes back here. the COLLECTIONS chip
# of discover (./discover.py) opens it
import urllib.parse

import xbmc
import xbmcgui

from arr import Error, notify
from kodi import files, rpc
from tmdb import HELPER
from windows import window

LIBRARY, TMDB, SEARCH, TITLE, FILMS = 101, 102, 103, 111, 112
PANEL = 301


def library():
    # kodi's movie sets and how many films each has. the label is the set's
    # name (kodi has it for every one), the art its poster
    sets = rpc("VideoLibrary.GetMovieSets", properties=["art"]).get("sets") or []
    films = rpc("VideoLibrary.GetMovies", properties=["setid"]).get("movies") or []
    counts = {}
    for film in films:
        setid = film.get("setid")
        if setid:
            counts[setid] = counts.get(setid, 0) + 1
    return [
        {
            "label": s.get("label") or "",
            "poster": (s.get("art") or {}).get("poster") or "",
            "films": counts.get(s.get("setid"), 0),
            "target": f"videodb://movies/sets/{s['setid']}/?setid={s['setid']}",
        }
        for s in sets
    ]


def found(query):
    # tmdb's collections by a name: its search, a folder of the collection
    # for the films (the path tmdb helper gives)
    path = f"{HELPER}?{urllib.parse.urlencode({'info': 'search', 'tmdb_type': 'collection', 'query': query})}"
    out = []
    for item in files(path):
        file = item.get("file") or ""
        # the next page's tile is a folder too, not a collection
        if "info=collection" not in file:
            continue
        art = item.get("art") or {}
        out.append(
            {
                "label": item.get("label") or "",
                "poster": art.get("poster") or art.get("thumb") or "",
                "films": 0,
                "target": file,
            }
        )
    return out


class Sets(xbmcgui.WindowXMLDialog):
    # the mode (library, tmdb), the order (title, films), the text of a
    # search; the wall is filled here, kodi's list isn't a plugin's folder
    def onInit(self):
        if getattr(self, "started", False):
            return
        self.started = True
        self.show()
        # an empty wall can't take the focus: the chips can
        self.setFocusId(PANEL if self.items else LIBRARY)

    def show(self):
        self.setProperty("mode", self.mode)
        self.setProperty("sort", self.sort)
        self.setProperty("query", f"«{self.query}»" if self.query else "")
        try:
            rows = found(self.query) if self.mode == "tmdb" else library()
        except Error as e:
            notify("Collections", str(e))
            rows = []
        if self.mode == "library":
            text = self.query.casefold()
            if text:
                rows = [r for r in rows if text in r["label"].casefold()]
            if self.sort == "films":
                rows.sort(key=lambda r: (-r["films"], r["label"].casefold()))
            else:
                rows.sort(key=lambda r: r["label"].casefold())
        self.items = []
        self.targets = []
        for r in rows:
            li = xbmcgui.ListItem(r["label"])
            li.setArt({"poster": r["poster"]})
            li.setProperty("films", f"{r['films']} films" if r["films"] else "")
            self.items.append(li)
            self.targets.append(r["target"])
        control = self.getControl(PANEL)
        control.reset()
        control.addItems(self.items)
        self.setProperty(
            "count", f"{len(rows)} collection" + ("" if len(rows) == 1 else "s")
        )
        self.setProperty(
            "empty",
            ""
            if rows
            else (
                "Nothing found"
                if self.query or self.mode == "tmdb"
                else "No collections in the library"
            ),
        )

    def search(self, tmdb=False):
        # a name: the library's, or tmdb's collections when the search is
        # tmdb's. cancelled: the library, all of it
        query = (
            xbmcgui.Dialog()
            .input(
                "Search TMDb collections"
                if tmdb
                else "Search the library's collections",
                self.query,
            )
            .strip()
        )
        self.query = query
        if tmdb:
            self.mode = "tmdb" if query else "library"
        elif not query:
            self.mode = "library"
        self.show()
        # the results are what was asked for: the wall, not the chip
        if self.items:
            self.setFocusId(PANEL)

    def onClick(self, cid):
        if cid == LIBRARY:
            self.mode = "library"
            self.show()
        elif cid == TMDB:
            if self.query and self.mode == "tmdb":
                self.show()
            else:
                self.search(tmdb=True)
        elif cid == SEARCH:
            self.search(tmdb=self.mode == "tmdb")
        elif cid in (TITLE, FILMS):
            self.sort = "films" if cid == FILMS else "title"
            self.show()
        elif cid == PANEL:
            at = self.getControl(PANEL).getSelectedPosition()
            if 0 <= at < len(self.targets):
                # the films in videos, this window under them: back is here
                xbmc.executebuiltin(f"ActivateWindow(Videos,{self.targets[at]},return)")

    def onAction(self, action):
        a = action.getId()
        if a in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            self.close()


def collections():
    w = window(
        Sets,
        "moviepipe-sets.xml",
        mode="library",
        sort="title",
        query="",
        items=[],
        targets=[],
    )
    w.doModal()
    del w
