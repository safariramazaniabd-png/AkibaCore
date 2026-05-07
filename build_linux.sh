#!/bin/bash
# ============================================================
#  Script de compilation AVEC Bukavu -> binaire Linux
#  A executer UNE SEULE FOIS sur ta machine Linux (Mint/Ubuntu)
# ============================================================

set -e

echo "=== Verification de Python ==="
python3 --version || { echo "ERREUR : Python 3 non installe."; exit 1; }

echo ""
echo "=== Installation des dependances systeme (Tkinter) ==="
sudo apt-get install -y python3-tk python3-pip 2>/dev/null || true

echo ""
echo "=== Installation de PyInstaller ==="
pip3 install pyinstaller --upgrade

echo ""
echo "=== Compilation de l'executable ==="
pyinstaller avec_bukavu.spec --clean

echo ""
echo "=== Nettoyage ==="
rm -rf build __pycache__

echo ""
echo "============================================================"
echo " SUCCES !"
echo " Votre executable se trouve dans :"
echo "   dist/AVEC_Bukavu"
echo ""
echo " Pour le rendre executable :"
echo "   chmod +x dist/AVEC_Bukavu"
echo ""
echo " Pour le lancer :"
echo "   ./dist/AVEC_Bukavu"
echo ""
echo " La BD avec_bukavu.db sera creee automatiquement"
echo " dans le meme dossier que l'executable."
echo "============================================================"
