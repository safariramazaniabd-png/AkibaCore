#!/bin/bash
# ============================================================
#  AkibaCore v2.2.0 — Assemblage du dossier de livraison release/
#  Usage : ./creer_release.sh
#
#  Copie la documentation dans release/ et génère SHA256SUMS.txt.
#  Si l'installateur / la version portable Windows existent, ils
#  sont intégrés automatiquement (après build sur Windows).
# ============================================================

set -e
cd "$(dirname "$0")"

echo "=== Assemblage du dossier release/ ==="
mkdir -p release

# Documentation
for f in \
  CHANGELOG.md \
  GUIDE_UTILISATEUR.md \
  GUIDE_ADMINISTRATEUR.md \
  GUIDE_INSTALLATION_WINDOWS.md \
  RAPPORT_FINAL_V2.2.0.md \
  RELEASE_NOTES_v2.0.0.md \
  README.md; do
  if [ -f "$f" ]; then
    cp -f "$f" "release/"
    echo "  + $f"
  fi
done

# Version txt de l'installation (compatible portable / hors Markdown)
if [ -f "GUIDE_INSTALLATION_WINDOWS.md" ]; then
  cp -f GUIDE_INSTALLATION_WINDOWS.md release/GUIDE_INSTALLATION_WINDOWS.txt
  echo "  + GUIDE_INSTALLATION_WINDOWS.txt"
fi

# Installateur Windows (s'il a été produit sur une machine Windows)
if [ -f "AkibaCore_Setup_v2.2.0_Windows_x64.exe" ]; then
  cp -f "AkibaCore_Setup_v2.2.0_Windows_x64.exe" "release/"
  echo "  + AkibaCore_Setup_v2.2.0_Windows_x64.exe"
fi

# Version portable Windows (s'il a été produit)
if [ -f "AkibaCore_Portable_v2.2.0_Windows.zip" ]; then
  cp -f "AkibaCore_Portable_v2.2.0_Windows.zip" "release/"
  echo "  + AkibaCore_Portable_v2.2.0_Windows.zip"
fi

echo ""
echo "=== Génération de SHA256SUMS.txt ==="
cd release
sha256sum * > SHA256SUMS.txt
cat SHA256SUMS.txt
cd ..

echo ""
echo "============================================================"
echo " Dossier release/ prêt : $(ls -1 release | wc -l) fichier(s)"
echo "============================================================"
