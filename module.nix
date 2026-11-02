# services.kodi: kodi with its library (./kodi), and the downloads for it
# (./arr): radarr, sonarr, prowlarr, bazarr, qbittorrent, flaresolverr and
# rutracker-proxy. one switch turns all of it on or off, arr.enable the
# downloads alone. kodi is the user's, through home-manager
inputs:
{ config, lib, ... }:

{
  imports = [
    (import ./kodi inputs)
    (import ./arr inputs)
  ];

  options.services.kodi = {
    enable = lib.mkEnableOption "kodi with its library and the downloads for it";
    user = lib.mkOption {
      type = lib.types.str;
      description = "Whose kodi it is (home-manager's programs.kodi), and whose the library's files are.";
    };
    library = lib.mkOption {
      type = lib.types.str;
      default = "/media/outer-1";
      description = "The disk of the library: movies/, series/ and downloads/ on it, one disk for the hardlinks.";
    };
    proxy = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "http://127.0.0.1:10808";
      description = "http://host:port for radarr, sonarr, prowlarr and bazarr (qbittorrent goes straight), and kodi with kodi.useProxy.";
    };
    kodi.useProxy = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Kodi's tmdb through the proxy too. No internet in kodi while the proxy is down.";
    };
    kodi.imagesProxy = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = config.services.kodi.proxy;
      defaultText = lib.literalExpression "config.services.kodi.proxy";
      example = "http://127.0.0.1:10808";
      description = "http://host:port for tmdb's posters and backdrops (movie pipe keeps a few connections through it open). null: straight to image.tmdb.org.";
    };
    arr = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = "The downloads. Off: kodi alone, its Download… menu has nothing to talk to.";
      };
      secrets = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        example = lib.literalExpression "config.sops.secrets.arr.path";
        description = ''
          A yaml read at runtime, each key optional: rutracker_username,
          rutracker_password, opensubtitles_username, opensubtitles_password,
          libretranslate_key. Its owner is services.kodi.user, a change of it
          restarts arr-setup.service.
        '';
      };
      translators = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        example = [ "https://lt.example.org/subtitle-translator" ];
        description = "subtitle-translator urls for english subtitles with no russian, tried in order.";
      };
    };
  };
}
