# what downloads (6, ./default.py, and the home's row): radarr's and
# sonarr's queues with qbittorrent's numbers for their torrents, a row
# each. right on a row: its button (pause, go on), left: the row again;
# space works the button, v marks a row (and goes to the next), d removes
# the marked ones or the one in focus, r asks the three again. ./windows.py
# is the base, ./labels.py what a row says
import threading
import time

import xbmc
import xbmcgui

from arr import Api, Error, error, gb, qbittorrent
from keys import letter
from labels import (
    AMBER,
    ARR_STATES,
    GREEN,
    LOADING,
    QBT_STATES,
    ROSE,
    STOPPED,
    color,
    duration,
    dynamic,
    quality,
    speed,
    timeleft,
)
from windows import BARS, Window, window


def name(app, records):
    q = records[0]
    if app == "radarr" and "movie" in q:
        return f"{q['movie']['title']} ({q['movie']['year']})"
    if app == "sonarr" and "series" in q and "episode" in q:
        if len(records) > 1:
            seasons = sorted({r["episode"]["seasonNumber"] for r in records})
            return f"{q['series']['title']}, season {', '.join(map(str, seasons))} ({len(records)} episodes)"
        return f"{q['series']['title']} S{q['episode']['seasonNumber']:02}E{q['episode']['episodeNumber']:02}"
    return q["title"]


def row(app, records, torrent):
    q = records[0]
    size = q.get("size") or 0
    left = q.get("sizeleft") or 0
    seconds = timeleft(q.get("timeleft"))
    rate = seeders = ""
    if torrent:
        size = torrent["size"] or size
        left = size - int(torrent["progress"] * size)
        seconds = torrent["eta"]
        state = QBT_STATES.get(torrent["state"], color("downloaded", GREEN))
        if torrent["state"] in LOADING:
            rate = speed(torrent["dlspeed"])
            # connected, of the swarm's
            seeders = f"{torrent['num_seeds']} ({max(torrent['num_complete'], 0)})"
    else:
        state = ARR_STATES.get(q.get("status"), q.get("status", ""))
    tracked = q.get("trackedDownloadState")
    if tracked in ("importPending", "importing"):
        state = color("importing", GREEN)
    elif tracked == "importBlocked":
        state = color("import blocked", AMBER)
    elif tracked in ("failedPending", "failed"):
        state = color("error", ROSE)
    problems = [q["errorMessage"]] if q.get("errorMessage") else []
    problems += [m for s in q.get("statusMessages", []) for m in s.get("messages", [])]
    # 0.png .. 100.png: a queue that counts a bigger size than its own
    # (sonarr's season pack) went past 100, one written before it moved
    # past 0
    percent = max(0, min(100, int(100 * (size - left) / size))) if size else 0
    qname = q["quality"]["quality"]["name"]
    return {
        "label": name(app, records),
        "mark": "!" if problems else "",
        "state": state,
        "bar": f"{BARS}/{percent // 5 * 5}.png",
        "percent": f"{percent}%",
        "done": f"{gb(size - left)} of {gb(size)}",
        "speed": rate,
        "seeders": seeders,
        "eta": duration(seconds) if left else "",
        "quality": quality(qname),
        "range": dynamic(q["title"], qname)[0],
        "tracker": (q.get("indexer") or "").replace(" (Prowlarr)", ""),
        "release": q["title"],
        "why": "; ".join(problems),
        "whyline": color("; ".join(problems), AMBER) if problems else "",
        # the row's button, majan's icons: what it does
        "toggle": (
            "icons/play.png" if torrent["state"] in STOPPED else "icons/pause.png"
        )
        if torrent
        else "",
    }


def downloads():
    # [(key, records, its torrent, row)], what didn't answer
    found, trouble = {}, []
    for app, include in (
        ("radarr", {"includeMovie": "true"}),
        ("sonarr", {"includeSeries": "true", "includeEpisode": "true"}),
    ):
        try:
            records = Api(app).get("/queue", timeout=10, pageSize=200, **include)[
                "records"
            ]
        except Error as e:
            trouble.append(str(e))
            continue
        for q in records:
            found.setdefault((app, q.get("downloadId") or str(q["id"])), []).append(q)
    torrents = {}
    if found:
        try:
            hashes = "|".join(k.lower() for _, k in found)
            # qbittorrent 5's hash is the v1 one for a v1 or hybrid torrent,
            # infohash_v1 the same (a v2-only one has neither as a download)
            for t in qbittorrent("/torrents/info", hashes=hashes):
                for hash in (t.get("hash"), t.get("infohash_v1")):
                    if hash:
                        torrents[hash.upper()] = t
        except Error as e:
            trouble.append(str(e))
    rows = []
    for key, records in found.items():
        torrent = torrents.get(key[1].upper())
        rows.append((key, records, torrent, row(key[0], records, torrent)))
    return rows, trouble


def forget(app, records):
    # what was removed here is not wanted any more: radarr and sonarr look
    # for what is monitored and has no file, so skipRedownload alone only
    # skipped the search right after the removal and the next rss sync
    # brought the same film or episode back. another release keeps it
    api = Api(app)
    if app == "radarr":
        for id in {r["movie"]["id"] for r in records if r.get("movie")}:
            movie = api.get(f"/movie/{id}")
            if movie.get("monitored"):
                movie["monitored"] = False
                api.put(f"/movie/{id}", movie)
    else:
        ids = sorted({r["episode"]["id"] for r in records if r.get("episode")})
        if ids:
            api.put("/episode/monitor", {"episodeIds": ids, "monitored": False})


class Downloads(Window):
    # right on a row: its button (pause, go on), left: the row again.
    # space (kodi's pause) works the button from either. v marks a row (and
    # goes to the next), d removes the marked ones or the one in focus, r
    # asks radarr, sonarr and qbittorrent again
    def onInit(self):
        if self.started:
            return
        self.started = True
        self.refresh()
        self.setFocusId(50)
        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        monitor = xbmc.Monitor()
        while not self.done.wait(2) and not monitor.abortRequested():
            try:
                self.refresh()
            except RuntimeError:
                return

    def refresh(self):
        with self.lock:
            found, trouble = downloads()
            if self.done.is_set():
                return
            keys = [key for key, _, _, _ in found]
            control = self.rows()
            if keys != self.keys:
                # one came or went: the list again, the focus where it was
                at = control.getSelectedPosition()
                at = self.keys[at] if 0 <= at < len(self.keys) else None
                control.reset()
                self.items = [xbmcgui.ListItem() for _ in found]
                control.addItems(self.items)
                if at in keys:
                    control.selectItem(keys.index(at))
                self.keys = keys
            self.marked &= set(keys)
            self.records = {key: records for key, records, _, _ in found}
            self.torrents = {key: torrent for key, _, torrent, _ in found}
            for li, (key, _, _, props) in zip(self.items, found):
                props = dict(props)
                li.setLabel(props.pop("label"))
                if key in self.marked:
                    props["mark"] = color("✓", GREEN)
                li.setProperties(props)
            self.setProperty("trouble", "; ".join(trouble))
            self.setProperty("empty", "" if found or trouble else "Nothing downloads")
            self.setProperty(
                "marked", f"{len(self.marked)} marked" if self.marked else ""
            )

    def onAction(self, action):
        a = action.getId()
        key = letter(action)
        rows = self.getFocusId() == 50
        if key == "r":
            self.refresh()
        elif key == "v" and rows:
            self.mark()
        elif key == "d" and rows:
            self.remove(sorted(self.marked) or [k for k in [self.focused()] if k])
        elif a in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            self.close()
        elif self.getFocusId() != 50:
            return
        elif a == xbmcgui.ACTION_MOVE_RIGHT:
            self.setProperty("onbutton", "1")
        elif a == xbmcgui.ACTION_MOVE_LEFT:
            self.setProperty("onbutton", "")
        elif a in (xbmcgui.ACTION_PAUSE, xbmcgui.ACTION_PLAYER_PLAYPAUSE):
            self.toggle(self.focused())

    def focused(self):
        at = self.rows().getSelectedPosition()
        return self.keys[at] if 0 <= at < len(self.keys) else None

    def toggle(self, key):
        # qbittorrent 5's names, 4's were resume and pause
        torrent = self.torrents.get(key)
        if not torrent:
            return
        try:
            qbittorrent(
                "/torrents/start" if torrent["state"] in STOPPED else "/torrents/stop",
                {"hashes": torrent["hash"]},
            )
        except Error as e:
            error(e)
        self.refresh()

    def mark(self):
        key = self.focused()
        if key is None:
            return
        self.marked ^= {key}
        self.refresh()
        at = self.rows().getSelectedPosition()
        if at + 1 < len(self.keys):
            self.rows().selectItem(at + 1)

    def remove(self, keys, another=False):
        # from radarr's or sonarr's queue and from qbittorrent. another:
        # this release to the blocklist, they look for the next one, and the
        # film or episode stays wanted. otherwise it's forgotten (forget):
        # skipRedownload only skipped the search right after the removal
        keys = [k for k in keys if k in self.records]
        if not keys:
            return
        names = [name(k[0], self.records[k]) for k in keys]
        shown = names[:8] + ([f"and {len(names) - 8} more"] if len(names) > 8 else [])
        if not another and not xbmcgui.Dialog().yesno(
            "Remove from downloads",
            "\n".join(shown) + "\n\nIt won't be searched for again.",
        ):
            return
        for key in keys:
            try:
                Api(key[0]).call(
                    "DELETE",
                    "/queue/bulk",
                    {"ids": [r["id"] for r in self.records[key]]},
                    removeFromClient="true",
                    blocklist="true" if another else "false",
                    skipRedownload="false" if another else "true",
                )
                if not another:
                    forget(key[0], self.records[key])
            except Error as e:
                error(e)
        self.marked -= set(keys)
        self.changed = True
        self.refresh()

    def onClick(self, control):
        key = self.focused()
        if control != 50 or key is None:
            return
        if self.getProperty("onbutton"):
            self.toggle(key)
            return
        records = self.records[key]
        torrent = self.torrents.get(key)
        actions = ["Another release", "Remove"]
        if torrent:
            actions.insert(0, "Resume" if torrent["state"] in STOPPED else "Pause")
        i = xbmcgui.Dialog().select(name(key[0], records), actions)
        if i < 0:
            return
        if actions[i] in ("Resume", "Pause"):
            self.toggle(key)
        else:
            self.remove([key], another=actions[i] == "Another release")


def show_downloads():
    w = window(
        Downloads,
        "moviepipe-downloads.xml",
        started=False,
        changed=False,
        keys=[],
        marked=set(),
        items=[],
        records={},
        torrents={},
        lock=threading.RLock(),
        done=threading.Event(),
    )
    w.doModal()
    # a refresh in its thread is on the network, maybe 30 s with a dead
    # radarr: it sees done after that and doesn't touch the window again,
    # the ui thread doesn't wait for it (it used to, closing the window froze)
    w.done.set()
    changed = w.changed
    del w
    if changed:
        # the Home preview (and the add-on listing) still shows the removed
        # rows: a new stamp makes their paths different, then the focused
        # container is fetched again (it is the row Enter opened this from)
        xbmc.executebuiltin(
            f"SetProperty(majan.reload,{time.strftime('%H:%M:%S')},home)"
        )
        xbmc.executebuiltin("Container.Refresh")
