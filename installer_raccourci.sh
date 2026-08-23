#!/bin/bash
# ============================================================
#  AkibaCore v2.0.0 — Installation du raccourci dans le menu
#  Usage : ./installer_raccourci.sh
#
#  Crée le raccourci « AkibaCore » dans le menu des applications
#  ET sur le Bureau, avec les chemins ABSOLUS corrects.
# ============================================================

cd "$(dirname "$0")" || exit 1
DOSSIER="$(pwd)"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   AkibaCore — Installation du raccourci  ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ── Vérifications préalables ──
if [ ! -f "$DOSSIER/lancer_akibacore.sh" ]; then
    echo "  ERREUR : lancer_akibacore.sh introuvable dans $DOSSIER"
    read -r -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

chmod +x "$DOSSIER/lancer_akibacore.sh" 2>/dev/null
[ -f "$DOSSIER/AkibaCore" ] && chmod +x "$DOSSIER/AkibaCore" 2>/dev/null

APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons"
mkdir -p "$APPS" "$ICONS"

cp -f icone_akibacore.png "$ICONS/" 2>/dev/null

# ── Génération du fichier .desktop avec chemins absolus ──
cat > "$APPS/akibacore.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=AkibaCore
GenericName=Gestion AVEC
Comment=Système de gestion des Associations Villageoises d'Épargne et de Crédit
Exec=$DOSSIER/lancer_akibacore.sh
Path=$DOSSIER
Icon=$ICONS/icone_akibacore.png
Terminal=false
Categories=Office;Finance;Database;
Keywords=avec;epargne;credit;microfinance;tontine;
StartupNotify=true
EOF

update-desktop-database "$APPS" 2>/dev/null

echo "  ✔ Raccourci installé dans le menu : Applications → Bureau / Office"
echo "    ($APPS/akibacore.desktop)"
echo "    Dossier de l'application : $DOSSIER"

# ── Raccourci sur le Bureau si présent ──
for BUREAU in "$HOME/Bureau" "$HOME/Desktop"; do
    if [ -d "$BUREAU" ]; then
        cp -f "$APPS/akibacore.desktop" "$BUREAU/"
        chmod +x "$BUREAU/akibacore.desktop" 2>/dev/null
        # Confiance au raccourci (GNOME récent)
        gio set "$BUREAU/akibacore.desktop" metadata::trusted true 2>/dev/null
        echo "  ✔ Raccourci ajouté sur le Bureau : $BUREAU/akibacore.desktop"
        break
    fi
done

echo ""
echo "  Terminé. Vous pouvez lancer AkibaCore depuis le menu ou le Bureau."
read -r -p "Appuyez sur Entrée pour fermer..."
