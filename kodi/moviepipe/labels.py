# what the releases and the downloads' rows say: the colours, sdr or hdr,
# quality, size, age, speed, state. no kodi in here, so it can be tried on
# its own (../test/test_labels.py); ./releases.py and ./downloads.py put it
# in their list items
import re

# majan's accent_amber, accent_mint and accent_rose halfway to its grey,
# its text_primary and text_tertiary
AMBER = "ffc69e53"
GREEN = "ff65b48e"
ROSE = "ffc67488"
WHITE = "ffecebe7"
GREY = "ff8d8b85"
LANGUAGES = {
    "Russian": "RU",
    "English": "EN",
    "Ukrainian": "UK",
    "German": "DE",
    "French": "FR",
    "Spanish": "ES",
    "Italian": "IT",
    "Japanese": "JA",
    "Korean": "KO",
    "Chinese": "ZH",
}


def color(text, argb):
    return f"[COLOR {argb}]{text}[/COLOR]"


def dynamic(title, qname):
    # sdr or hdr as the title says, and its place in "SDR first": "DV"
    # alone is dolby vision with no hdr10 under it. a title with neither:
    # sdr up to 1080p (a blu-ray, so a bdrip, is sdr; hdr is uhd
    # blu-ray's), a 2160p one may be either
    t = re.sub(r"[._\[\](),/]", " ", title)
    found = []
    if re.search(r"\b(dv|dovi|dolby ?vision)\b", t, re.I):
        found.append("DV")
    if re.search(r"\bhdr10(\+|p\b|plus\b)", t, re.I):
        found.append("HDR10+")
    elif re.search(r"\bhdr10\b", t, re.I):
        found.append("HDR10")
    elif re.search(r"\bhdr\b", t, re.I):
        found.append("HDR")
    if re.search(r"\bhlg\b", t, re.I):
        found.append("HLG")
    if found:
        return color("+".join(found), AMBER), 2
    if re.search(r"\bsdr\b", t, re.I) or "2160" not in qname:
        return color("SDR", GREEN), 0
    return color("HDR?", AMBER), 1


def quality(name):
    # radarr's and sonarr's names as on the trackers: a bdrip up to 1080p,
    # the profile's best, stands out
    shown = re.sub(
        r"-(\d+p)$",
        r" \1",
        re.sub(r"^Bluray-", "BDRip-", name.replace("WEBDL-", "WEB-DL-")),
    )
    if name in ("Bluray-1080p", "Bluray-720p"):
        return color(shown, WHITE)
    return shown


# why radarr or sonarr wouldn't take a release, short
REASONS = [
    (r"not wanted in profile", "quality not in profile"),
    (r"^Unknown (Movie|Series)", "unknown title"),
    (r"^Wrong ", "wrong title"),
    (r"Not enough seeders", "few seeders"),
    (r"blocklisted", "blocklisted"),
    (r"in queue", "already downloading"),
    (r"^Existing file", "already downloaded"),
    (r"grab event in history", "grabbed before"),
    (r"considered available", "not out yet"),
    (r"not monitored", "not monitored"),
    (r"^Indexer .* blocked", "tracker paused"),
    (r"smaller than minimum", "too small"),
    (r"larger than maximum", "too big"),
    (r"Custom Formats? .*\bHDR\b.* below", "HDR"),
    (r"Custom Formats? .* below", "low score"),
    (r"is wanted, but found", "wrong language"),
    (r"Hardcode subs", "hardcoded subs"),
    (r"^Sample", "sample"),
    (r"^Raw ", "disc image"),
    (r"terms", "word filter"),
    (r"minutes old", "too new"),
]


def reason(rejections):
    out = []
    for text in rejections:
        short = next((ru for rx, ru in REASONS if re.search(rx, text, re.I)), text[:40])
        if short not in out:
            out.append(short)
    return ", ".join(out)


def age(days):
    if days is None:
        return ""
    if days < 1:
        return "today"
    if days < 60:
        return f"{days} d"
    if days < 730:
        return f"{days // 30} mo"
    return f"{days // 365} y"


def duration(seconds):
    if seconds is None or seconds >= 8640000:
        return "∞"
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min"
    if seconds < 86400:
        return f"{seconds // 3600} h {seconds % 3600 // 60:02} min"
    return f"{seconds // 86400} d {seconds % 86400 // 3600} h"


def timeleft(text):
    # servarr's "[d.]hh:mm:ss"
    m = re.match(r"(?:(\d+)\.)?(\d+):(\d+):(\d+)", text or "")
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def speed(rate):
    if rate >= 1024**2:
        return f"{rate / 1024**2:.1f} MB/s"
    return f"{rate // 1024} KB/s"


# what downloads, every 2 s while the window is open: radarr's and
# sonarr's queues, qbittorrent's numbers for their torrents. a season in
# one torrent is a record per episode in sonarr's queue, a row here
QBT_STATES = {
    "downloading": "downloading",
    "forcedDL": "downloading",
    "metaDL": "metadata",
    "forcedMetaDL": "metadata",
    "stalledDL": color("no peers", AMBER),
    "queuedDL": "queued",
    "pausedDL": "paused",
    "stoppedDL": "paused",
    "checkingDL": "checking",
    "checkingResumeData": "checking",
    "moving": "moving",
    "error": color("error", ROSE),
    "missingFiles": color("files missing", ROSE),
}
LOADING = ("downloading", "forcedDL", "stalledDL", "metaDL", "forcedMetaDL")
STOPPED = ("pausedDL", "stoppedDL", "pausedUP", "stoppedUP")
ARR_STATES = {
    "queued": "queued",
    "paused": "paused",
    "delay": "waiting",
    "downloading": "downloading",
    "completed": color("downloaded", GREEN),
    "warning": color("problem", AMBER),
    "failed": color("error", ROSE),
    "downloadClientUnavailable": color("qbittorrent is down", ROSE),
}
