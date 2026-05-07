#!/bin/bash
# AkibaCore — Script de lancement (Linux / macOS)

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║        AkibaCore v2.0 — Démarrage       ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# Aller dans le répertoire du script
cd "$(dirname "$0")"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "  ERREUR : python3 n'est pas installé."
    echo "  Installez-le avec : sudo apt install python3 python3-tk"
    exit 1
fi

# Vérifier tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  ERREUR : le module tkinter est manquant."
    echo "  Installez-le avec : sudo apt install python3-tk"
    exit 1
fi

echo "  Lancement..."
python3 main.py
