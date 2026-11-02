# kodi with the add-ons of ./addons.nix, and what kodi has to turn on by
# hand afterwards (./userdata.nix). ./default.nix is the module, this is
# just the package
{
  pkgs,
  inputs,
  # services.kodi.kodi.useProxy: tmdb through services.kodi.proxy
  proxy ? null,
  # ../arr/shared.nix with the library's disk, for the downloads' add-on
  arr ? import ../arr/shared.nix { },
  # { host, port } for tmdb's pictures in movie pipe, null: straight
  imagesProxy ? null,
}:

let
  # kodi and everything it's built with from its own nixpkgs, pinned in
  # this repo's flake.nix (nixpkgs-kodi): the system's updates don't move
  # it, moving it is a change of its rev there
  kodiPkgs = import inputs.nixpkgs-kodi { inherit (pkgs.stdenv.hostPlatform) system; };

  # ./kodi-keys.patch: a ru layout's keys are the us ones in the keymaps
  # (./keyboard.xml; kodi gave every cyrillic letter one code), and
  # shift+letter goes through them too (G, the last item; it jumped to the
  # first item with that letter). kodi builds from source then, not from
  # the cache: the pin keeps that to the switch that moves it
  kodi = kodiPkgs.kodi-wayland.overrideAttrs (old: {
    patches = (old.patches or [ ]) ++ [ ./kodi-keys.patch ];
  });
  kodiPackages = kodi.packages;
  addons = kodiPackages.callPackage ./addons.nix { inherit inputs arr imagesProxy; };
  kodiWithAddons = kodi.withPackages (_: addons);

  # tmdb through a proxy when the provider breaks it: kodi's curl
  # (posters) and the scrapers' urllib take it from the environment. no
  # internet in kodi while the proxy is down
  useProxy = proxy != null;
in
{
  package =
    if useProxy then
      kodiPkgs.symlinkJoin {
        name = "kodi-xray";
        paths = [ kodiWithAddons ];
        nativeBuildInputs = [ kodiPkgs.makeWrapper ];
        postBuild = ''
          wrapProgram $out/bin/kodi \
            --set http_proxy ${proxy} \
            --set https_proxy ${proxy} \
            --set no_proxy localhost,127.0.0.1,::1
        '';
      }
    else
      kodiWithAddons;

  # the add-ons and what they need: kodi installs them switched off
  addonIds = map (a: a.namespace) (kodiPackages.requiredKodiAddons addons);
}
