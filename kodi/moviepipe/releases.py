# the releases to pick one of ("Download…", ./actions.py): the trackers'
# list, sdr first, then as radarr or sonarr rank it; enter downloads the one
# picked. ./windows.py is the base, ./labels.py what a row says
import xbmcgui

from arr import gb, notify, waiting
from labels import AMBER, GREY, LANGUAGES, age, color, dynamic, quality, reason
from windows import Window, window

# the releases' columns (moviepipe-releases.xml): the button of each, its
# name, how its rows sort, which way first (True: the most first). ties
# keep radarr's or sonarr's order
COLUMNS = {
    101: ("quality", lambda e: e["weight"], True),
    102: ("sdr / hdr", lambda e: e["rank"], False),
    103: ("size", lambda e: e["size"], True),
    104: ("seeds", lambda e: e["seeders"], True),
    105: ("tracker", lambda e: e["tracker"].casefold(), False),
    106: ("group", lambda e: (not e["group"], e["group"].casefold()), False),
    107: (
        "language",
        lambda e: (" RU" not in f" {e['language']}", e["language"]),
        False,
    ),
    108: ("age", lambda e: e["age"], False),
    109: ("why ✗", lambda e: e["order"], False),
}
SEARCH = 110


class Releases(Window):
    # enter on a column's name sorts by it, again the other way. those of
    # another film or show stay last
    def onInit(self):
        if self.rows().size():
            return
        self.setProperty("heading", self.heading)
        self.setProperty("hint", self.hint)
        self.sorted, self.most, self.text = 102, False, ""
        self.show()
        self.setFocusId(50)

    def show(self):
        _, key, _ = COLUMNS[self.sorted]
        text = self.text.casefold()
        shown = [e for e in self.entries if text in e["text"]]
        shown.sort(key=key, reverse=self.most)
        shown.sort(key=lambda e: e["other"])
        self.order = shown
        for cid, (name, _, _) in COLUMNS.items():
            arrow = (" ↓" if self.most else " ↑") if cid == self.sorted else ""
            self.setProperty(f"h{cid}", name + arrow)
        self.setProperty("sorted", str(self.sorted))
        self.setProperty(
            f"h{SEARCH}", f"search: {self.text}" if self.text else "search"
        )
        self.setProperty("filter", f"«{self.text}»" if self.text else "")
        self.setProperty("empty", "" if shown else "Nothing found")
        self.rows().reset()
        self.rows().addItems([e["item"] for e in shown])
        self.rows().selectItem(0)

    def onClick(self, control):
        if control in COLUMNS:
            if control == self.sorted:
                self.most = not self.most
            else:
                self.sorted, self.most = control, COLUMNS[control][2]
            self.show()
        elif control == SEARCH:
            self.text = (
                xbmcgui.Dialog()
                .input("Search: title, group, tracker", self.text)
                .strip()
            )
            self.show()
        elif control == 50:
            at = self.rows().getSelectedPosition()
            if 0 <= at < len(self.order):
                self.picked = self.order[at]["release"]
                self.close()


def entry(r, n, other):
    # n: its place in radarr's or sonarr's order, 0 their own pick
    qname = r["quality"]["quality"]["name"]
    range_, rank = dynamic(r["title"], qname)
    rejections = r.get("rejections", []) if r.get("rejected") else []
    tracker = r["indexer"].replace(" (Prowlarr)", "")
    group = r.get("releaseGroup") or ""
    language = " ".join(
        LANGUAGES.get(x["name"], x["name"][:2].upper())
        for x in r.get("languages", [])
        if x.get("id", 0) > 0
    )
    li = xbmcgui.ListItem(r["title"])
    li.setProperties(
        {
            "mark": color("✗", GREY) if rejections else "●" if n == 0 else "",
            "why": "; ".join(rejections),
            "whyline": color("; ".join(rejections), AMBER) if rejections else "",
            "reason": color(reason(rejections), AMBER),
            "quality": quality(qname),
            "range": range_,
            "size": gb(r["size"]) if r.get("size") else "—",
            "seeders": str(r.get("seeders") or 0)
            if r.get("protocol") == "torrent"
            else "",
            "tracker": tracker,
            "group": group,
            "language": language,
            "age": age(r.get("age")),
        }
    )
    return {
        "release": r,
        "item": li,
        "order": n,
        "other": other,
        "rank": rank,
        "weight": r.get("qualityWeight") or 0,
        "seeders": r.get("seeders") or 0,
        "size": r.get("size") or 0,
        "age": r.get("ageMinutes", r.get("age")) or 0,
        "tracker": tracker,
        "group": group,
        "language": language,
        "text": " ".join((r["title"], group, tracker, qname)).casefold(),
    }


def choose(api, title, **query):
    # the releases the trackers have, sdr first, then as radarr or sonarr
    # rank them: those they'd take first, in their order (quality, their
    # score, the tracker's priority, seeders), the first the one they'd
    # download themselves. the ones they took for another film or show
    # last (the trackers are searched with no year, ../../arr/setup.py).
    # the one picked is downloaded even when they'd reject it, for this
    # film or show (query's ids)
    found = waiting(
        title,
        "Searching the trackers…",
        lambda: api.get("/release", timeout=300, **query),
    )
    if found is None:
        return None
    if not found:
        notify(title, "No releases")
        return None
    mapped = [
        r for r in found if r.get("mappedMovieId", r.get("mappedSeriesId")) is not None
    ]
    others = [r for r in found if r not in mapped]
    ranked = (
        [r for r in mapped if not r.get("rejected")]
        + [r for r in mapped if r.get("rejected")]
        + others
    )
    app = api.app.capitalize()
    w = window(
        Releases,
        "moviepipe-releases.xml",
        heading=f"{title}: releases",
        hint=f"enter — download    ↑ to the column names — sort, search    ● — {app} would grab it itself    ✗ — it wouldn't    esc — cancel",
        entries=[entry(r, n, r in others) for n, r in enumerate(ranked)],
        picked=None,
    )
    w.doModal()
    r = w.picked
    del w
    if r is None:
        return None
    ids = {k: v for k, v in query.items() if k in ("movieId", "seriesId", "episodeId")}
    api.post(
        "/release", {"guid": r["guid"], "indexerId": r["indexerId"], **ids}, timeout=120
    )
    notify(title, f"Downloading: {r['quality']['quality']['name']}, {gb(r['size'])}")
    return r
