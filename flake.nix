{
  description = "kodi with its library and the downloads for it, for nixos";

  # each pinned to a commit: `nix flake update` leaves them, kodi is built
  # with a patch (kodi/kodi-keys.patch) and majan with patches that want
  # its exact xml. moving one is changing its rev here, then
  # `nix flake lock`
  inputs = {
    nixpkgs-kodi.url = "git+https://github.com/NixOS/nixpkgs?shallow=1&rev=02c087f3fe673c9e317f206a627cb6b910336dbe";
    kodi-skins.url = "git+https://github.com/KarmaMole/kodi-skins?shallow=1&rev=0f6a3246f1aa41e82f895366709d2bcaaa87e6fc";
    kodi-skins.flake = false;
    kodi-skinvariables.url = "git+https://github.com/jurialmunkey/script.skinvariables?ref=nexus&shallow=1&rev=9c20ea9bcf67fcb4370a5771da08b6cf7bdb676e";
    kodi-skinvariables.flake = false;
    kodi-tmdbhelper.url = "git+https://github.com/jurialmunkey/plugin.video.themoviedb.helper?ref=nexus&shallow=1&rev=edae17cb8bfc69d1f614ff44b2490ecd6bd5e9a0";
    kodi-tmdbhelper.flake = false;
    kodi-jurialmunkey.url = "git+https://github.com/jurialmunkey/script.module.jurialmunkey?shallow=1&rev=8f42fb5f4698f3e4552f38955964b2f3843dba69";
    kodi-jurialmunkey.flake = false;
    kodi-infotagger.url = "git+https://github.com/jurialmunkey/script.module.infotagger?shallow=1&rev=0118f53c9cf68a6625794d07af607cac1e920064";
    kodi-infotagger.flake = false;

    # rutracker through cloudflare for prowlarr (arr), follows its main:
    # `nix flake update rutracker-cf-proxy` brings new versions
    rutracker-cf-proxy.url = "git+https://github.com/rofl3228/rutracker-cf-proxy?shallow=1";
    rutracker-cf-proxy.flake = false;
  };

  outputs = inputs: {
    # services.kodi, see the readme. it needs home-manager's nixos module
    nixosModules.default = import ./module.nix inputs;
  };
}
