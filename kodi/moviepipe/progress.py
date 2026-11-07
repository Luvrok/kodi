# mpv's progress in kodi's library (../mpv-progress.lua and ../userdata.nix).
#
# mpv is an external player: kodi never learns where a film stopped, so its
# resume markers, watched flags and "in progress" lists stay empty. The lua
# script in the mpv wrapper writes path, position and duration to a small
# JSON file; this thread maps the path to kodi's file id and writes the same
# rows kodi would: lastPlayed, the type 1 bookmark (the resume point) and, at
# 90% or on end, playCount. Everything in the skin uses those (progress bars,
# Continue watching, Next up), so the skin needs no special case.
#
# The kodi database is written directly: there is no json-rpc call for a
# resume point. Writes are short and retried; a locked database just skips a
# tick.
import glob
import json
import os
import re
import sqlite3
import threading
import time

import xbmc
import xbmcgui
import xbmcvfs

POLL = 2
WRITE = 10  # while playing, write the bookmark at most this often
RETURN = 3  # after mpv stops updating, refresh the lists this soon once kodi is back
STALE = 30  # an mpv state not updated for this long is treated as stopped
CLEAN = 86400


def state_dir():
    return os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "kodi-mpv")


class Progress(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.monitor = xbmc.Monitor()
        self.home = xbmcgui.Window(10000)
        self.seen = {}
        self.pending = 0
        self.database = None

    def log(self, message, bad=False):
        xbmc.log(f"moviepipe progress: {message}", xbmc.LOGWARNING if bad else xbmc.LOGINFO)

    def run(self):
        while not self.monitor.abortRequested():
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001 - it runs till kodi quits
                self.log(f"{e}", True)
            if self.monitor.waitForAbort(POLL):
                break

    def active(self):
        return xbmc.getCondVisibility("Window.IsActive(home) | Window.IsActive(videos)")

    def tick(self):
        directory = state_dir()
        now = time.time()
        # a write happened while mpv was up: refresh once kodi is back,
        # even when the state has already stopped changing
        if self.pending and now - self.pending > 1 and self.active():
            self.refresh()
        if not os.path.isdir(directory):
            return
        for name in glob.glob(os.path.join(directory, "*.json")):
            try:
                with open(name) as f:
                    state = json.load(f)
            except (OSError, ValueError):
                continue
            path = state.get("path") or ""
            if not path or "://" in path:
                continue
            key = (path, state.get("started") or 0)
            entry = self.seen.get(key)
            updated = float(state.get("updated") or 0)
            # a state nobody has touched for STALE is a killed or finished
            # mpv: its last position is the final one. While the file is
            # still fresh the write repeats every WRITE seconds, so the
            # refresh below still runs after the user is back in kodi.
            final = now - updated > STALE
            # returning from mpv to the film/show page leaves a stale
            # snapshot there: close it, the list behind is then refreshed
            if not final and now - updated > RETURN and xbmc.getCondVisibility("Window.IsActive(movieinformation)"):
                xbmc.executebuiltin("Action(Close)")
            returned = not final and now - updated > RETURN and self.active()
            if entry:
                if entry["final"]:
                    continue
                if not final and not returned and now - entry["written"] < WRITE:
                    continue
            result = self.write(state)
            if result is True:
                self.refresh()
                self.seen[key] = {"written": now, "final": final}
            elif result is None:
                # not a library file (a trailer, a stream, a deleted film):
                # nothing to write, do not look again
                self.seen[key] = {"written": now, "final": True}
            elif not entry:
                # a locked database: try again on the next tick, even for a
                # final state, so the last position is not lost
                self.seen[key] = {"written": 0, "final": False}
        # forget old sessions and their files
        for key, entry in list(self.seen.items()):
            if now - entry["written"] > CLEAN:
                del self.seen[key]
        for name in glob.glob(os.path.join(directory, "*.json")):
            try:
                if now - os.path.getmtime(name) > CLEAN:
                    os.remove(name)
            except OSError:
                pass

    def db(self):
        directory = xbmcvfs.translatePath("special://database/")
        if not os.path.isdir(directory):
            return None
        files = glob.glob(os.path.join(directory, "MyVideos*.db"))
        if not files:
            return None
        version = max(
            files,
            key=lambda p: int(m.group(1)) if (m := re.search(r"MyVideos(\d+)\.db$", p)) else 0,
        )
        self.database = version
        return version

    def write(self, state):
        database = self.db()
        if not database:
            return False
        path = state["path"]
        try:
            position = max(0.0, float(state.get("position") or 0))
            duration = max(0.0, float(state.get("duration") or 0))
        except (TypeError, ValueError):
            return False
        if duration <= 0:
            return False

        con = sqlite3.connect(database, timeout=10)
        try:
            con.execute("PRAGMA busy_timeout=10000")
            row = con.execute(
                "SELECT f.idFile FROM files f JOIN path p ON p.idPath=f.idPath "
                "WHERE p.strPath || f.strFileName = ? LIMIT 1",
                (path,),
            ).fetchone()
            if not row:
                return None
            file_id = row[0]
            played = time.strftime("%Y-%m-%d %H:%M:%S")
            watched = state.get("ended") is True or position / duration >= 0.9
            position = min(position, duration)
            con.execute("UPDATE files SET lastPlayed=? WHERE idFile=?", (played, file_id))
            if watched:
                con.execute(
                    "UPDATE files SET playCount=MAX(COALESCE(playCount,0),1) WHERE idFile=?",
                    (file_id,),
                )
                con.execute("DELETE FROM bookmark WHERE idFile=? AND type=1", (file_id,))
            else:
                bookmark = con.execute(
                    "SELECT idBookmark FROM bookmark WHERE idFile=? AND type=1", (file_id,)
                ).fetchone()
                if bookmark:
                    con.execute(
                        "UPDATE bookmark SET timeInSeconds=?, totalTimeInSeconds=?, player='mpv' "
                        "WHERE idBookmark=?",
                        (position, duration, bookmark[0]),
                    )
                elif position > 0:
                    con.execute(
                        "INSERT INTO bookmark "
                        "(idFile, timeInSeconds, totalTimeInSeconds, thumbNailImage, player, playerState, type) "
                        "VALUES (?, ?, ?, '', 'mpv', '', 1)",
                        (file_id, position, duration),
                    )
            con.commit()
            return True
        finally:
            con.close()

    def refresh(self):
        # Home's TV Next up path ends with majan.reload: a new stamp makes it
        # fetch again. The lists refresh when they are reopened; this also
        # refreshes the focused one while mpv is fresh and after it ends.
        self.home.setProperty("majan.reload", time.strftime("%H:%M:%S"))
        if self.active():
            self.pending = 0
            xbmc.executebuiltin("Container.Refresh")
        else:
            self.pending = time.time()
