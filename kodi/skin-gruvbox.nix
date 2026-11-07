# kodi's own skin: a fork of majan re-skinned to the gruvbox of quickshell
# (JetBrains Mono NL, square hairlines, no blur). ./skin-gruvbox/ is the
# whole skin (fonts and media included), this builds it and the script
# skinvariables it needs. majan's build is gone: this replaces it
{
  inputs,
  buildKodiAddon,
  jurialmunkey,
  infotagger,
}:

let
  skinvariables = buildKodiAddon {
    pname = "skinvariables";
    namespace = "script.skinvariables";
    version = inputs.kodi-skinvariables.shortRev;
    src = inputs.kodi-skinvariables;
    propagatedBuildInputs = [
      jurialmunkey
      infotagger
    ];
  };
in
buildKodiAddon {
  pname = "skin.gruvbox";
  namespace = "skin.gruvbox";
  # keep in step with skin-gruvbox/addon.xml (kodi shows that one)
  version = "1.0.1";
  src = ./skin-gruvbox;
  propagatedBuildInputs = [ skinvariables ];
}
