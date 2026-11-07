# "Subtitles" on a film (its menu, ./context.py; More on its page) or on a
# show, a season, an episode (the pack = the show's menu): russian ones
# next to the files through bazarr (its providers, opensubtitles.com's
# account in secrets), an english one after. every download bazarr makes
# goes through its post-processing (../../arr/subtitles.py add), so an
# english one with no russian next to it translates in a couple of minutes
# on its own. mpv takes them up on the next play.
import ast
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcgui

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


def bazarr(path, timeout=180, method="PATCH", **query):
    # bazarr's own api (not servarr's): the key arr-keys made, apikey in
    # the query (utilities/helper.py would also take a header or a form).
    # a patch is form-encoded, a get is just the query
    if not C.get("bazarr"):
        raise Error("bazarr: the add-on has no port for it (addons.nix)")
    try:
        with open(f"{C['keys']}/bazarr") as f:
            key = f.read().strip()
    except OSError:
        raise Error(f"bazarr: no key in {C['keys']}")
    query["apikey"] = key
    url = f"http://127.0.0.1:{C['bazarr']}/api{path}?" + urlencode(query)
    body = None if method == "GET" else urlencode({k: v for k, v in query.items() if k != "apikey"}).encode()
    headers = {"Content-Type": "application/x-www-form-urlencoded"} if body else {}
    req = urllib.request.Request(url, body, headers, method=method)
    try:
        with OPENER.open(req, timeout=timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise Error(f"bazarr: {e.code} {e.read().decode(errors='replace')[:200]}")
    except OSError as e:
        if isinstance(e, TimeoutError) or isinstance(getattr(e, "reason", None), TimeoutError):
            raise Error(f"bazarr didn't answer in {timeout} s")
        raise Error("bazarr doesn't answer")
    return data


def urlencode(query):
    return urllib.parse.urlencode(query)


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


def choose(options, heading="Subtitles"):
    return xbmcgui.Dialog().select(heading, options)


def movie(tmdb):
    radarr = Api("radarr")
    found = radarr.get("/movie", tmdbId=tmdb)
    if not found:
        raise Error("Not in Radarr: Download… it first")
    video = (found[0] or {}).get("path", "")
    near = neighbours(video) if video else None
    choices = ["Russian", "English", "Russian, then English"]
    pick = choose(choices)
    if pick < 0:
        return

    def get(pattern, language, label):
        if near and have(near, pattern):
            notify("Subtitles", f"{label} subtitles are already there")
            return True
        try:
            download(found[0]["id"], language)
        except Error as e:
            error(e)
            return False
        if near is None:
            notify("Subtitles", "Bazarr is on it, they land next to the film in a minute")
            return True
        if poll(video, pattern):
            notify("Subtitles", f"{label} subtitles downloaded")
            return True
        notify("Subtitles", "Nothing found, try another time")
        return False

    if pick in (0, 2):
        got = get(RUSSIAN, "ru", "Russian")
        if pick == 0:
            return
    if pick == 1 or (pick == 2 and not got):
        get(ENGLISH, "en", "English")


# shows: sonarr's series by its tmdb id, bazarr's episodes of it


def series(tmdb):
    found = Api("sonarr").get("/series", tmdbId=tmdb)
    if not found:
        raise Error("Not in Sonarr: Download… it first")
    return found[0]


def episodes_of(seriesid):
    # every episode sonarr has for it, with what's missing (a python-literal
    # list of languages bazarr still looks for: "['ru']"). bazarr has
    # answered both a bare list and {"data": [...]} depending on the version
    raw = json.loads(bazarr("/episodes", timeout=60, method="GET", **{"seriesid[]": seriesid})) or []
    if isinstance(raw, dict):
        raw = raw.get("data") or []
    if not isinstance(raw, list):
        raw = []
    for e in raw:
        missing = e.get("missing_subtitles")
        if isinstance(missing, str):
            try:
                missing = ast.literal_eval(missing)
            except (ValueError, SyntaxError):
                missing = []
        if not isinstance(missing, list):
            missing = []
        e["missing"] = [
            m.get("code") if isinstance(m, dict) else m for m in missing
        ]
    return raw


def episode(s, ep):
    langs = [lang for lang in ("ru", "en") if lang in ep["missing"]]
    if not langs:
        notify("Subtitles", "Subtitles are already there")
        return
    labels = {"ru": "Russian", "en": "English"}
    pick = choose([labels[lang] for lang in langs], f"S{ep['season']:02}E{ep['episode']:02}")
    if pick < 0:
        return
    language = langs[pick]
    bazarr("/episodes/subtitles", seriesid=s["id"], episodeid=ep["sonarrEpisodeId"],
           language=language, forced="False", hi="False")
    notify("Subtitles", f"Bazarr is on it, {labels[language].lower()} lands next to the file in a minute")


def season(s, eps, number):
    missing = [e for e in eps if e["season"] == number and e["missing"]]
    if not missing:
        notify("Subtitles", "Subtitles are already there")
        return
    labels = [f"All missing in season {number}"] + [
        f"S{e['season']:02}E{e['episode']:02} · {e.get('title') or ''}" for e in missing
    ]
    pick = choose(labels, f"Season {number}")
    if pick < 0:
        return
    if pick == 0:
        for e in missing:
            language = "ru" if "ru" in e["missing"] else "en"
            bazarr("/episodes/subtitles", seriesid=s["id"], episodeid=e["sonarrEpisodeId"],
                   language=language, forced="False", hi="False")
        notify("Subtitles", f"Bazarr: {len(missing)} episodes missing subtitles, they land in a couple of minutes")
    else:
        episode(s, missing[pick - 1])


def pack(tmdb, season_number, episode_number):
    s = series(tmdb)
    eps = episodes_of(s["id"])
    if episode_number is not None:
        ep = next((e for e in eps if (e["season"], e["episode"]) == (season_number, episode_number)), None)
        if not ep:
            raise Error(f"sonarr: no episode S{season_number:02}E{episode_number:02}")
        episode(s, ep)
        return
    missing = [e for e in eps if e["missing"]]
    if not missing:
        notify("Subtitles", "Subtitles are already there")
        return
    if season_number is None:
        seasons = sorted({e["season"] for e in missing})
        if len(seasons) > 1:
            labels = ["All missing episodes (Bazarr)"] + [
                f"Season {n} · {sum(1 for e in missing if e['season'] == n)} missing" for n in seasons
            ]
            pick = choose(labels, s["title"])
            if pick < 0:
                return
            if pick == 0:
                waiting("Bazarr", f"Searching subtitles for {s['title']}…",
                        lambda: bazarr("/series", seriesid=s["id"], action="search-missing", timeout=30))
                notify("Subtitles", "Bazarr: russian for every episode missing, an english one translates after")
                return
            season_number = seasons[pick - 1]
        else:
            season_number = seasons[0]
    season(s, eps, season_number)
