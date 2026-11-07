# 5, discover (resources/skins/Default/1080i/moviepipe-discover.xml): what
# tmdb has in rows, majan's hub rows, films or shows (the chips): trending
# the week and the month, tmdb's top 10 on a provider, top rated, coming
# soon, more like the library's newest, popular people; shows also anime
# and what's on the air. tmdb helper fills them (the rows' paths are the
# window's rown.* properties), so enter on a film is its player
# (Download…), i its page, c its menu; a show's enter is its page, a
# person's theirs (./person.py). a row that's not out yet gets a "soon"
# tag on its tiles. the last tile turns the row's page, left on the first
# one back. a row gets its path when the focus is two rows from it: tmdb
# helper asks tmdb for every poster's details the first time. SEARCH: what
# tmdb finds, back the rows again. up from the rows: the plot on top,
# enter all of it. t a trailer, o the tmdb page in the browser, r the rows
# again
import threading
import time

import xbmc
import xbmcgui

from actions import rpc
from arr import Error
from browser import browse, url
from keys import letter
from tmdb import HELPER, helper, info, settle
from trailer import trailer
from windows import window

# (the row's name, tmdb helper's list, what's on it, extra list params).
# the order here is the page's. {} in a name: the library's newest film or
# show. top 10 of a streaming service is tmdb's discover through it
# (tmdb's providers in the us), popularity desc
NETFLIX, PRIME, APPLE = 8, 9, 350


def top(region, provider):
    return {"with_watch_providers": str(provider), "watch_region": region,
            "with_id": "True", "sort_by": "popularity.desc"}


ROWS = {
    "movie": [
        ("Trending this week", "trending_week", "movie", {}),
        ("Trending this month", "trending_month", "movie", {}),
        ("Top 10 Netflix", "discover", "movie", top("US", NETFLIX)),
        ("Top 10 Prime Video", "discover", "movie", top("US", PRIME)),
        ("Top 10 Apple TV+", "discover", "movie", top("US", APPLE)),
        ("Top rated", "top_rated", "movie", {}),
        ("Because you have {}", "recommendations", "movie", {}),
        ("Popular people", "popular", "person", {}),
        ("Not out yet", "upcoming", "movie", {}),
    ],
    "tv": [
        ("Trending this week", "trending_week", "tv", {}),
        ("Trending this month", "trending_month", "tv", {}),
        ("Trending anime", "discover", "tv", {"with_genres": "16", "with_id": "True",
                                              "with_original_language": "ja", "sort_by": "popularity.desc"}),
        ("Top 10 Netflix", "discover", "tv", top("US", NETFLIX)),
        ("Top 10 Prime Video", "discover", "tv", top("US", PRIME)),
        ("Top 10 Apple TV+", "discover", "tv", top("US", APPLE)),
        ("On the air", "on_the_air", "tv", {}),
        ("Top rated", "top_rated", "tv", {}),
        ("Because you have {}", "recommendations", "tv", {}),
        ("Popular people", "popular", "person", {}),
    ],
    "search": [
        ("Films", "search", "movie", {}),
        ("TV shows", "search", "tv", {}),
        ("People", "search", "person", {}),
    ],
}
# row n is list 200 + n, 1..10 tmdb's lists (what downloads has its own
# window at 6, it isn't a row here)
FIRST, LAST = 1, 10
# the chips, the plot on top, and the rows' SendClick: 40 + n the next
# page, 50 + n back (two-digit n: 40 + 10 = 410)
MOVIES, SHOWS, SEARCH, BROWSE, PLOT = 101, 102, 103, 104, 9100
NEXTPAGES = tuple(40 + n for n in range(1, LAST + 1))
BACKPAGES = tuple(50 + n for n in range(1, LAST + 1))
# rows past the focus that get their path: each is tmdb helper asking tmdb
# for its 20 posters' details the first time
AHEAD = 1
# s: how often the focus is looked at
TICK = 0.2


def newest(kind):
    # the library's last added film or show: (title, tmdb id)
    method, key = ("VideoLibrary.GetMovies", "movies") if kind == "movie" else ("VideoLibrary.GetTVShows", "tvshows")
    try:
        found = rpc(method, properties=["title", "uniqueid"], sort={"method": "dateadded", "order": "descending"}, limits={"end": 10}).get(key) or []
    except Error:
        return None
    return next(((x["title"], x["uniqueid"]["tmdb"]) for x in found if (x.get("uniqueid") or {}).get("tmdb")), None)


class Row:
    # a row's name, tmdb helper's params for it, what's on it, its page and
    # whether its tiles carry a tag (a row that isn't out yet: "soon")
    def __init__(self, title, params, kind, tag=""):
        self.title, self.params, self.kind, self.tag, self.page = title, params, kind, tag, 1


class Discover(xbmcgui.WindowXML):
    def onInit(self):
        if getattr(self, "started", False):
            return
        self.started = True
        self.closing = False
        self.moved = False
        self.rows = {}
        self.enabled = FIRST - 1
        self.loads = 0
        self.stamp = ""
        self.query = ""
        self.mode = self.before = "movie"
        self.show("movie")
        threading.Thread(target=self.watch, daemon=True).start()

    def gone(self):
        return self.closing

    # the rows

    def show(self, mode):
        if mode != "search":
            self.before = mode
        self.mode = mode
        self.setProperty("mode", mode)
        self.setProperty("query", f"«{self.query}»" if mode == "search" else "")
        rows = []
        for title, kind, what, extra in ROWS[mode]:
            params = dict(info=kind, tmdb_type=what)
            params.update(extra)
            if kind == "recommendations":
                found = newest(what)
                if not found:
                    continue
                title = title.format(found[0])
                params["tmdb_id"] = found[1]
            if kind == "search":
                params["query"] = self.query
            rows.append(Row(title, params, what, tag="soon" if kind == "upcoming" else ""))
        self.rows = {FIRST + i: row for i, row in enumerate(rows)}
        self.loads += 1
        load = self.loads
        # the rows near the top get the new paths at once (the old posters
        # dim till the new come, majan-moviepipe.xml), the rest go
        self.enabled = FIRST - 1
        for n in range(FIRST, LAST + 1):
            self.clearProperty(f"row{n}.empty")
            if n not in self.rows or n > FIRST + AHEAD:
                for p in ("path", "title", "sub", "index", "kind", "tag", "page"):
                    self.clearProperty(f"row{n}.{p}")
        self.near(FIRST)
        threading.Thread(target=self.first, args=(load,), daemon=True).start()

    def first(self, load):
        # the first row on top once it's in (the old rows' tile stood there
        # otherwise), the focus on it unless it went elsewhere
        if not settle(200 + FIRST, lambda: self.gone() or load != self.loads) or load != self.loads:
            return
        if not 201 <= self.getFocusId() <= 200 + LAST:
            self.setProperty("row", str(200 + FIRST))
        if not self.moved:
            self.setProperty("row", str(200 + FIRST))
            xbmc.executebuiltin(f"SetFocus({200 + FIRST})")

    def near(self, focus):
        # the rows up to AHEAD past the focus get their paths
        last = min(LAST, max(focus, FIRST) + AHEAD, FIRST + len(self.rows) - 1)
        while self.enabled < last:
            self.enabled += 1
            self.put(self.enabled)

    def put(self, n):
        # row n's properties, its path last: a new path loads it
        row = self.rows[n]
        page = row.page if row.page > 1 else None
        self.setProperty(f"row{n}.index", f"{n:02}")
        self.setProperty(f"row{n}.title", row.title)
        self.setProperty(f"row{n}.sub", f"page {row.page}" if page else "TMDb")
        self.setProperty(f"row{n}.kind", row.kind)
        self.setProperty(f"row{n}.tag", row.tag)
        self.setProperty(f"row{n}.page", str(row.page))
        self.setProperty(f"row{n}.path", helper(**row.params, page=page, reload=self.stamp))
        threading.Thread(target=self.empty, args=(n, self.loads), daemon=True).start()

    def empty(self, n, load):
        # a row that came back empty goes, the focus skips it
        if not settle(200 + n, lambda: self.gone() or load != self.loads) and load == self.loads and not self.gone():
            self.setProperty(f"row{n}.empty", "1")

    def turn(self, n, by):
        # the row's next page (by 1) or the one before (-1), its first tile
        row = self.rows.get(n)
        if not row or row.page + by < 1:
            return
        row.page += by
        self.put(n)

        def first():
            if settle(200 + n, self.gone):
                try:
                    self.getControl(200 + n).selectItem(0)
                except RuntimeError:
                    pass

        threading.Thread(target=first, daemon=True).start()

    # what's in focus

    def watch(self):
        # the row whose tile is on top: the one with the focus, the last one
        # when it went up to the chips (the mouse too, it moves no action)
        monitor = xbmc.Monitor()
        while not self.closing and not monitor.waitForAbort(TICK):
            try:
                focus = self.getFocusId()
                if 200 + FIRST <= focus <= 200 + LAST and str(focus) != self.getProperty("row"):
                    self.setProperty("row", str(focus))
                    if focus > 200 + FIRST:
                        self.moved = True
                    self.near(focus - 200)
            except RuntimeError:
                return

    # keys

    def onClick(self, cid):
        if cid == MOVIES:
            self.show("movie")
        elif cid == SHOWS:
            self.show("tv")
        elif cid == SEARCH:
            query = xbmcgui.Dialog().input("Search TMDb: films, shows, people", self.query).strip()
            if query:
                self.query = query
                self.show("search")
        elif cid == PLOT:
            row = self.getProperty("row")
            if row:
                xbmcgui.Dialog().textviewer(info(f"Container({row}).ListItem.Label"), info(f"Container({row}).ListItem.Plot"))
        elif cid == BROWSE:
            self.leave()
            xbmc.executebuiltin(f"ActivateWindow(Videos,{HELPER},return)")
        elif cid == 410:
            self.turn(10, 1)
        elif cid == 510:
            self.turn(10, -1)
        elif cid in NEXTPAGES:
            self.turn(cid - 40, 1)
        elif cid in BACKPAGES:
            self.turn(cid - 50, -1)

    def onAction(self, action):
        a = action.getId()
        key = letter(action)
        focus = self.getFocusId()
        if a in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            self.moved = True
        elif key == "r":
            # every row again, tmdb helper asked anew
            self.stamp = str(time.time())
            for n in range(FIRST, self.enabled + 1):
                self.put(n)
        elif key == "o" and 201 <= focus <= 200 + LAST:
            # its tmdb page in the browser: a film's, a show's, a person's
            item = f"Container({focus}).ListItem"
            kind = "person" if info(f"{item}.Property(tmdb_type)") == "person" else "tv" if info(f"{item}.DBType") == "tvshow" else "movie"
            browse(url("tmdb", kind, info(f"{item}.UniqueID(tmdb)") or info(f"{item}.Property(tmdb_id)")))
        elif key == "t" and 201 <= focus <= 200 + LAST:
            tmdb = info(f"Container({focus}).ListItem.UniqueID(tmdb)") or info(f"Container({focus}).ListItem.Property(tmdb_id)")
            kind = "tv" if info(f"Container({focus}).ListItem.DBType") == "tvshow" else "movie"
            if tmdb:
                trailer(kind, tmdb)
        elif a in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            if self.mode == "search":
                # back from what was found: the rows of before
                self.show(self.before)
            else:
                self.leave()

    def leave(self):
        self.closing = True
        self.close()


def discover():
    w = window(Discover, "moviepipe-discover.xml")
    w.doModal()
    w.closing = True
    del w
