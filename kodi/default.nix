# kodi: the library of services.kodi.library, posters and plots from tmdb
# (its scrapers come with kodi). a video plays in mpv, in mpv's own window
# with mpv's config, scripts and keys, tv and streams in kodi's player.
# majan, tmdb helper, the downloads of ../arr in the menu of a film or a
# show and on enter in tmdb helper, tv channels (./addons.nix), other
# add-ons from inside kodi. it's the user's, through home-manager
#
# ./package.nix: the kodi package with the add-ons, ./userdata.nix: what
# kodi reads in its userdata, ./majan.nix and ./moviepipe: the skin and the
# add-on of the downloads
inputs:
{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.kodi;
  shared = import ../arr/shared.nix { disk = cfg.library; };
  kodi = import ./package.nix {
    inherit pkgs inputs;
    arr = shared;
    proxy = if cfg.kodi.useProxy then cfg.proxy else null;
  };
in
{
  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !cfg.kodi.useProxy || cfg.proxy != null;
        message = "services.kodi.kodi.useProxy needs services.kodi.proxy";
      }
    ];

    # kodi's settings -> regional -> timezone lists the zones of
    # /usr/share/zoneinfo/zone.tab, nixos has none: the list was empty and
    # the setting looked locked to the system's (time.timeZone). kodi's own
    # zone is its alone (it sets TZ for itself)
    systemd.tmpfiles.rules = [ "L /usr/share/zoneinfo - - - - ${pkgs.tzdata}/share/zoneinfo" ];

    home-manager.users.${cfg.user} = {
      imports = [ (import ./userdata.nix { inherit (kodi) addonIds; }) ];

      programs.kodi = {
        enable = true;
        inherit (kodi) package;
        # set what each one is once in kodi: movies -> set content ->
        # movies, series -> tv shows. kodi keeps that in its database
        sources.video.source = [
          {
            name = "Movies";
            path = "${shared.movies}/";
            allowsharing = "true";
          }
          {
            name = "Series";
            path = "${shared.series}/";
            allowsharing = "true";
          }
        ];
      };
    };
  };
}
