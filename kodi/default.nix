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
  options,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.kodi;
  shared = import ../arr/shared.nix { disk = cfg.library; };
  # http://host:port -> { host, port }
  parse =
    url:
    let
      m = if url == null then null else builtins.match "[a-z]+://([^:/]+):([0-9]+)/?" url;
    in
    if m == null then
      null
    else
      {
        host = builtins.elemAt m 0;
        port = lib.toInt (builtins.elemAt m 1);
      };
  imagesProxy = parse cfg.kodi.imagesProxy;
  kodi = import ./package.nix {
    inherit pkgs inputs imagesProxy;
    arr = shared;
    proxy = if cfg.kodi.useProxy then cfg.proxy else null;
  };
in
{
  config = lib.mkIf cfg.enable (
    {
      assertions = [
        {
          assertion = !cfg.kodi.useProxy || cfg.proxy != null;
          message = "services.kodi.kodi.useProxy needs services.kodi.proxy";
        }
        {
          assertion = options ? home-manager;
          message = "services.kodi needs home-manager's nixos module: kodi is the user's (programs.kodi)";
        }
        {
          assertion = cfg.kodi.imagesProxy == null || imagesProxy != null;
          message = "services.kodi.kodi.imagesProxy is http://host:port, not ${toString cfg.kodi.imagesProxy}";
        }
      ];

      # kodi's settings -> regional -> timezone lists the zones of
      # /usr/share/zoneinfo/zone.tab, nixos has none: the list was empty and
      # the setting looked locked to the system's (time.timeZone). kodi's own
      # zone is its alone (it sets TZ for itself)
      systemd.tmpfiles.rules = [ "L /usr/share/zoneinfo - - - - ${pkgs.tzdata}/share/zoneinfo" ];
    }
    # home-manager may not be there at all: then no mention of it, so a host
    # without it can still import this with services.kodi off
    // lib.optionalAttrs (options ? home-manager) {
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
    }
  );
}
