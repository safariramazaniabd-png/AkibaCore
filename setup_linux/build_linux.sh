#!/bin/bash
# ============================================================
#  Script de compilation AkibaCore v2.2.0 -> exécutable Linux
#  Usage : ./build_linux.sh
#  Prérequis : Python 3.8+ et python3-tk installés
#  On compile depuis la racine du projet (parents de setup_linux/)
# ============================================================

set -e
cd "$(dirname "$0")/.."

echo "=== Vérification de Python ==="
python3 --version || { echo "ERREUR : Python 3 non installé."; exit 1; }

echo ""
echo "=== Vérification de Tkinter ==="
python3 -c "import tkinter" 2>/dev/null \
    || { echo "ERREUR : tkinter manquant."; echo "Installez-le avec : sudo apt install python3-tk"; exit 1; }

echo ""
echo "=== Installation de PyInstaller ==="
pip3 install --user pyinstaller --upgrade 2>/dev/null || pip3 install pyinstaller --upgrade

echo ""
echo "=== Compilation de l'exécutable (une seule fichier) ==="
pyinstaller avec_bukavu.spec --clean --noconfirm

echo ""
echo "=== Nettoyage ==="
rm -rf build __pycache__

chmod +x dist/AkibaCore 2>/dev/null || true

echo ""
echo "============================================================"
echo " SUCCÈS !"
echo ""
echo " Votre exécutable se trouve dans : dist/AkibaCore"
echo ""
echo " Pour le distribuer :"
echo "   - Copiez dist/AkibaCore dans un dossier vide"
echo "   - Rendez-le exécutable : chmod +x AkibaCore"
echo "   - Lancez-le : ./AkibaCore"
echo ""
echo " La base akibacore.db sera créée automatiquement"
echo " dans le même dossier que l'exécutable au premier lancement."
echo "============================================================"
