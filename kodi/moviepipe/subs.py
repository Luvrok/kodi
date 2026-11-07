# "Subtitles" on a film (its menu, ./context.py; More on its page): russian
# ones next to it through bazarr (its providers, opensubtitles.com's account
# in secrets), an english one after. every download bazarr makes goes
# through its post-processing (../../arr/subtitles.py add), so an english
# one with no russian around translates in a couple of minutes on its own.
# mpv takes them up on the next play.
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import xbmc

from arr import C, OPENER, Api, Error, error, notify, waiting

# what follows the video's name: .ru.srt, .rus.hi.srt... a forced one is
# only the foreign lines, it doesn't count
RUSSIAN = re.compile(r"^\.([^.]+\.)*?(ru|rus|russian)(\.(?!forced)[^.]+)*\.(srt|ass|ssa|vtt|sub)$", re.I)
ENGLISH = re.compile(r"^\.([^.]+\.)*?(en|eng|english)(\.(?!forced)[^.]+)*\.srt$", re.I)


def neighbours(video):
    # the files next to the video named like it, or {} when kodi can't
    # read the library's disk
    base = os.path.splitext(os.path.basename(video))[0]
    folder = os.path.dirname(video)
    try:
        names = os.listdir(folder)
    except OSError:
        return None
    return {os.path.join(folder, f): f[len(base):] for f in names if f.startswith(base + ".")}


def have(near, kinds):
    return next((f for f, s in near.items() if kinds.match(s)), None)


def bazarr(path, timeout=180, **query):
    # bazarr's own api (not servarr's): the key arr-keys made, apikey in
    # the query (utilities/helper.py would also take a header or a form)
    if not C.get("bazarr"):
        raise Error("bazarr: the add-on has no port for it (addons.nix)")
    try:
        with open(f"{C['keys']}/bazarr") as f:
            key = f.read().strip()
    except OSError:
        raise Error(f"bazarr: no key in {C['keys']}")
    query["apikey"] = key
    url = f"http://127.0.0.1:{C['bazarr']}/api{path}?" + urllib.parse.urlencode(query)
    body = urllib.parse.urlencode({k: v for k, v in query.items() if k != "apikey"}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/x-www-form-urlencoded"}, method="PATCH")
    try:
        with OPENER.open(req, timeout=timeout) as r:
            r.read()
    except urllib.error.HTTPError as e:
        raise Error(f"bazarr: {e.code} {e.read().decode(errors='replace')[:200]}")
    except OSError as e:
        if isinstance(e, TimeoutError) or isinstance(getattr(e, "reason", None), TimeoutError):
            raise Error(f"bazarr didn't answer in {timeout} s")
        raise Error("bazarr doesn't answer")


def download(radarrid, language):
    waiting("Bazarr", f"Searching {language} subtitles…",
            lambda: bazarr("/movies/subtitles", radarrid=radarrid, language=language,
                           forced="False", hi="False"))


def poll(video, kinds, seconds=90):
    # the video's new subtitles, None when the wait ran out (or the disk
    # isn't readable: then bazarr was still asked)
    monitor = xbmc.Monitor()
    for _ in range(max(1, seconds // 3)):
        if monitor.waitForAbort(3):
            return None
        near = neighbours(video)
        if near is None:
            return None
        found = have(near, kinds)
        if found:
            return found
    return None


def movie(tmdb):
    radarr = Api("radarr")
    found = radarr.get("/movie", tmdbId=tmdb)
    if not found:
        raise Error("Not in Radarr: Download… it first")
    video = (found[0] or {}).get("path", "")
    near = neighbours(video) if video else None
    if near and have(near, RUSSIAN):
        notify("Subtitles", "Russian subtitles are already there")
        return
    try:
        download(found[0]["id"], "ru")
    except Error as e:
        error(e)
        return
    if near is None:
        notify("Subtitles", "Bazarr is on it, they land next to the film in a minute")
        return
    if poll(video, RUSSIAN):
        notify("Subtitles", "Russian subtitles downloaded")
        return
    try:
        download(found[0]["id"], "en")
    except Error as e:
        error(e)
        return
    if poll(video, ENGLISH):
        notify("Subtitles", "Only English found: Russian translates itself in a couple of minutes")
    else:
        notify("Subtitles", "Nothing found, try another time")
