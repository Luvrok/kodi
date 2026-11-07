# kodi's own skin: square, hairline, no blur, JetBrains Mono NL, the
# gruvbox of quickshell. ./skin-gruvbox/ holds the skin, this builds it and
# puts the fonts next to it (kodi reads fonts from {skin}/fonts). a sibling
# of majan in ../addons.nix, majan stays until this is complete
{
  nerd-fonts,
  python3,
  buildKodiAddon,
}:

buildKodiAddon {
  pname = "skin.gruvbox";
  namespace = "skin.gruvbox";
  # keep in step with skin-gruvbox/addon.xml (kodi shows that one)
  version = "0.1.0";
  src = ./skin-gruvbox;
  postInstall = ''
    d=$out/share/kodi/addons/skin.gruvbox
    mkdir -p $d/fonts $d/media
    cp ${nerd-fonts.jetbrains-mono}/share/fonts/truetype/NerdFonts/JetBrainsMono/JetBrainsMonoNLNerdFont-{Regular,Medium,SemiBold,Bold,ExtraBold}.ttf $d/fonts/
    ${python3}/bin/python3 ${./skin-gruvbox-media.py} $d/media
  '';
}
