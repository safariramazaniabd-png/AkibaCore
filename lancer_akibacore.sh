#!/bin/bash
# ============================================================
#  AkibaCore v2.0.0 — Script de lancement (Linux / macOS)
#  Usage : ./lancer_akibacore.sh   (ou double-clic)
# ============================================================

# Toujours travailler dans le dossier du script (base de données locale)
cd "$(dirname "$0")" || exit 1

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║       AkibaCore v2.0.0 — Démarrage       ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ── Exécutable autonome présent ? → priorité au binaire ──
if [ -x "./AkibaCore" ]; then
    echo "  Lancement de l'application..."
    exec ./AkibaCore
fi

# ── Sinon : lancement via Python ──
if ! command -v python3 &> /dev/null; then
    echo "  ERREUR : python3 n'est pas installé."
    echo "  Installez-le avec : sudo apt install python3 python3-tk"
    echo "  (Ubuntu / Debian / Linux Mint)"
    read -r -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  ERREUR : le module graphique tkinter est manquant."
    echo "  Installez-le avec : sudo apt install python3-tk"
    read -r -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

if [ ! -f "./main.py" ]; then
    echo "  ERREUR : main.py introuvable dans $(pwd)"
    read -r -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

echo "  Lancement..."
exec python3 main.py
