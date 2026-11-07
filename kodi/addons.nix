# the add-ons kodi gets: the gruvbox skin (./skin-gruvbox.nix), tmdb helper
# (films, shows and people from tmdb, with the menu of ./moviepipe on
# them), Movie pipe, youtube for the trailers. the github ones are flake
# inputs, pinned to a commit each (this repo's flake.nix)
{
  inputs,
  # ../arr/shared.nix: its ports and the keys' folder (./test: the mock's)
  arr ? import ../arr/shared.nix { },
  # { host, port } for tmdb's pictures (./moviepipe/images.py), null: straight
  imagesProxy ? null,
  kodi,
  lib,
  buildKodiAddon,
  callPackage,
  writeText,
  requests,
  signals,
  xdg-utils,
  youtube,
}:

let
  # the version an add-on's own addon.xml gives, kodi shows that one: a
  # derivation's shouldn't drift from it
  addonVersion =
    path:
    let
      root = builtins.head (
        builtins.filter (line: lib.hasInfix "<addon " line) (lib.splitString "\n" (builtins.readFile path))
      );
    in
    builtins.head (builtins.match ".*version=\"([^\"]+)\".*" root);

  infotagger = buildKodiAddon {
    pname = "infotagger";
    namespace = "script.module.infotagger";
    version = inputs.kodi-infotagger.shortRev;
    src = inputs.kodi-infotagger;
    passthru.pythonPath = "resources/modules";
  };

  jurialmunkey = buildKodiAddon {
    pname = "jurialmunkey";
    namespace = "script.module.jurialmunkey";
    version = inputs.kodi-jurialmunkey.shortRev;
    src = inputs.kodi-jurialmunkey;
    propagatedBuildInputs = [
      requests
      infotagger
    ];
    passthru.pythonPath = "resources/modules";
  };

  # kodi's repository has it as a module of its own, here it's nixpkgs'
  # python one, the python kodi runs. pil comes with kodi
  module =
    namespace: version: package:
    buildKodiAddon {
      pname = namespace;
      inherit namespace version;
      dontUnpack = true;
      installPhase = ''
        d=$out/share/kodi/addons/${namespace}
        mkdir -p $d/lib
        ln -s ${package}/${kodi.pythonPackages.python.sitePackages}/* $d/lib/
        cat > $d/addon.xml <<EOF
        <?xml version="1.0" encoding="UTF-8"?>
        <addon id="${namespace}" version="${version}" name="${package.pname}" provider-name="nixpkgs">
          <requires><import addon="xbmc.python" version="3.0.0"/></requires>
          <extension point="xbmc.python.module" library="lib"/>
          <extension point="xbmc.addon.metadata"><platform>all</platform></extension>
        </addon>
        EOF
      '';
      passthru.pythonPath = "lib";
    };

  tmdbhelper = buildKodiAddon {
    pname = "themoviedb-helper";
    namespace = "plugin.video.themoviedb.helper";
    version = inputs.kodi-tmdbhelper.shortRev;
    src = inputs.kodi-tmdbhelper;
    propagatedBuildInputs = [
      requests
      signals
      jurialmunkey
      infotagger
      (module "script.module.qrcode" "6.1.0" kodi.pythonPackages.qrcode)
    ];
  };

  moviepipe = buildKodiAddon {
    pname = "moviepipe";
    namespace = "plugin.video.moviepipe";
    # its addon.xml has it: kodi shows that one, so it can't drift from the
    # derivation's
    version = addonVersion ./moviepipe/addon.xml;
    src = ./moviepipe;
    postInstall = ''
      d=$out/share/kodi/addons/plugin.video.moviepipe
      cp ${
        writeText "arr.json" (
          builtins.toJSON {
            inherit (arr)
              radarr
              sonarr
              qbittorrent
              keys
              ;
            library = {
              radarr = arr.movies;
              sonarr = arr.series;
            };
            images_proxy =
              if imagesProxy == null then
                null
              else
                [
                  imagesProxy.host
                  imagesProxy.port
                ];
          }
        )
      } $d/arr.json
      substituteInPlace $d/browser.py --replace-fail 'OPENER = "xdg-open"' 'OPENER = "${xdg-utils}/bin/xdg-open"'
      mkdir -p $d/resources/skins/Default/media/bars
      ${kodi.pythonPackages.python.interpreter} ${./moviepipe-bars.py} $d/resources/skins/Default/media/bars
    '';
  };
in
[
  (callPackage ./majan.nix { inherit inputs jurialmunkey infotagger; })
  (callPackage ./skin-gruvbox.nix { })
  tmdbhelper
  moviepipe
  # trailers: the films' trailers are its plugin:// links (the scrapers')
  youtube
]
