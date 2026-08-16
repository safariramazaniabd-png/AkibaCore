# AGENTS.md

## Vue d'ensemble

Application desktop Python monofichier (`main.py`, ~2000 lignes) de gestion des Associations Villageoises d'Epargne et de Credit (AVEC) en Afrique centrale. Interface Tkinter + SQLite. 100% hors ligne, aucune dependance externe.

- **Langue :** Francais (UI, commentaires, contenu BDD)
- **Python :** >= 3.8 requis
- **Dependances :** Aucune en dehors de la bibliotheque standard (tkinter, sqlite3, hashlib, csv, json, etc.)
- **Base de donnees :** SQLite (`akibacore.db`, auto-creee au premier lancement avec seeds : admin/admin123)

## Lancement

```bash
python3 main.py          # Linux/macOS
python main.py           # Windows
```

Linux necessite `python3-tk` : `sudo apt install python3-tk`

## Compilation en executable autonome

```bash
# Linux
pip3 install pyinstaller
pyinstaller avec_bukavu.spec --clean   # → dist/AVEC_Bukavu

# Windows
pip install pyinstaller
pyinstaller avec_bukavu.spec --clean   # → dist\AVEC_Bukavu.exe
```

CI construit aussi via PyInstaller directement : `pyinstaller --onefile --name AkibaCore main.py`

## Architecture (monofichier)

Tout le code vit dans `main.py`. Classes principales dans l'ordre :

| Classe | Role |
|--------|------|
| `DB` | Connexion SQLite, init schema, seeds, helper audit |
| `Finance` | Calculs financiers statiques purs (interets, penalites, echeances) |
| `Auth` | Connexion, changement mot de passe, verification des roles |
| `Backup` | Sauvegarde auto dans `sauvegardes/` (rotation sur 15 fichiers) |
| `EcranConnexion` | Ecran de connexion (tk.Toplevel) |
| `Dashboard` | Cartes synthetiques + journal d'audit |
| `OngletMembres` / `DlgMembre` / `DlgDetailMembre` | CRUD membres + vue detail |
| `OngletEpargnes` / `DlgEpargne` | Depot d'epargnes + annulation |
| `OngletCredits` / `DlgCredit` | Octroi de credits |
| `OngletRemboursements` / `DlgRemboursement` | Remboursements (penalite → interet → capital) |
| `OngletSessions` / `DlgSession` | Gestion des sessions/reunions |
| `OngletRapports` | Export CSV + rapport HTML + sauvegarde manuelle |
| `AkibaCore` | Fenetre principale, conteneur d'onglets, timer sauvegarde periodique |

## Pas de tests ni de linter

Il n'y a aucun test automatise, aucune config de linter, aucun type checker. La CI construit uniquement l'executable.

## Points de vigilance

- **Aucun package externe.** Ne jamais ajouter de dependances pip — l'application cible des machines sans acces internet.
- **Toutes les operations BDD passent par les methodes de la classe `DB`** (`exec`, `un`, `tous`, `valeur`). Utiliser `dict(row)` pour les objets Row.
- **`DB.audit()` ne doit jamais lever d'exception.** Elle attrape silencieusement les erreurs pour ne jamais bloquer les operations metier.
- **`Finance.maj_statuts()` est appele avant l'affichage des listes de credits.** Il modifie l'etat de la BDD (marque les credits en retard/soldes). C'est intentionnel, pas un effet de bord a supprimer.
- **Formules financieres en dur :** 10% d'interet annuel, 2%/mois de penalite. Configurables par AVEC dans la table `avec` mais les valeurs par defaut comptent.
- **Sauvegarde automatique** toutes les 30 minutes via timer `tkinter.after()` dans `Appli`.
- **Mode WAL + cles etrangeres** actives via PRAGMA a chaque connexion.
- **Identifiants admin par defaut :** admin / admin123 (PBKDF2-SHA256 + sel). Seeds sur BDD vide.

## Fichiers a ignorer

- `AkibaCore.jsx` — Composant React de presentation (pas du code de production)
- `AkibaCore_SAUVEGARDE/` — Copie de sauvegarde du projet
- `AkibaCore app.exe/` — Sortie de build Windows
- `*.spec` est dans `.gitignore` mais le fichier `avec_bukavu.spec` doit etre present localement pour la compilation
