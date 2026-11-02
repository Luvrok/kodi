# kodi

Kodi with its library and the downloads for it, as one NixOS module. A film
or a show picked in Kodi goes to Radarr or Sonarr, Prowlarr finds it on the
trackers, qBittorrent downloads it, it lands in the library named so Kodi
finds it on TMDb, and Bazarr puts Russian and English subtitles next to it.
Videos play in mpv.

NixOS only, with home-manager: Kodi is the user's (`programs.kodi`). A
host without home-manager can import the module, it only can't turn it on.

## What's in here

| Path | What |
|---|---|
| `module.nix` | `services.kodi`: the options, one switch for all of it |
| `kodi/` | Kodi itself: the package with its patch and add-ons, the majan skin, Movie pipe (the downloads' add-on), userdata, TV channels, a test stand |
| `arr/` | the downloads: qBittorrent, Radarr, Sonarr, Prowlarr, Bazarr, FlareSolverr, rutracker-proxy, `setup.py` that sets them up through their APIs, `subtitles.py` |
| `flake.nix` | Kodi's own nixpkgs and the add-ons' sources, each pinned to a commit |

How it all works, in Russian: [`arr/AGENTS.md`](arr/AGENTS.md) (the
pipeline, the keys, the proxy, the TV) and [`kodi/README.md`](kodi/README.md)
(the layout and why it is so).

## Use it

```nix
# flake.nix
inputs.kodi.url = "git+https://github.com/Luvrok/kodi?shallow=1";

# a host's modules, next to home-manager's nixos module
inputs.kodi.nixosModules.default
{
  services.kodi = {
    enable = true;
    user = "me";
    # optional
    library = "/media/outer-1";
    proxy = "http://127.0.0.1:10808";
    arr.secrets = config.sops.secrets.arr.path;
    arr.translators = [ "https://lt.example.org/subtitle-translator" ];
  };
}
```

Don't make it follow your nixpkgs: Kodi is built from source with a patch,
its own pinned nixpkgs keeps that to the updates that move it here.

`enable = false` takes all of it away, `arr.enable = false` only the
downloads.

## Options

| Option | Default | |
|---|---|---|
| `enable` | `false` | Kodi and the downloads |
| `user` | | whose Kodi it is and whose the library's files are |
| `library` | `/media/outer-1` | `movies/`, `series/`, `downloads/`, one disk for the hardlinks |
| `proxy` | `null` | `http://host:port` for Radarr, Sonarr, Prowlarr, Bazarr; qBittorrent goes straight |
| `kodi.useProxy` | `false` | Kodi's TMDb through the proxy too |
| `kodi.imagesProxy` | `proxy` | `http://host:port` for TMDb's posters and backdrops (Movie pipe keeps a few connections through it open); `null` goes straight |
| `arr.enable` | `true` | the downloads |
| `arr.secrets` | `null` | a YAML at runtime: `rutracker_username`, `rutracker_password`, `opensubtitles_username`, `opensubtitles_password`, `libretranslate_key`, each optional. Owned by `user`; restart `arr-setup.service` when it changes |
| `arr.translators` | `[ ]` | subtitle-translator URLs, tried in order |

## The web UIs

All on 127.0.0.1: qBittorrent :8140, Radarr :7878, Sonarr :8989, Prowlarr
:9696, Bazarr :6767. Nothing needs setting up in them by hand.

## Moving a pin

Change the input's `rev` in `flake.nix`, then:

```bash
nix flake lock
```

`rutracker-cf-proxy` follows its main:

```bash
nix flake update rutracker-cf-proxy
```

Then, where the module is used:

```bash
nix flake update kodi
```

## Trying a change without a switch

```bash
LIVE=1 kodi/test/run.sh start
```

A Kodi from this working tree in a window, with its own home in
`/tmp/kodi-test`. Without `LIVE=1` it runs under Xvfb against a mock of
TMDb and the downloads.
