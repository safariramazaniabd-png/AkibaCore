# AGENTS.md

## Vue d'ensemble

Application desktop Python monofichier (`main.py`, ~5800 lignes) de gestion des Associations Villageoises d'Epargne et de Credit (AVEC) en Afrique centrale. Interface Tkinter + SQLite. 100% hors ligne, aucune dependance externe.

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
pyinstaller avec_bukavu.spec --clean   # → dist/AkibaCore

# Windows
pip install pyinstaller
pyinstaller avec_bukavu.spec --clean   # → dist\AkibaCore.exe
```

CI construit aussi via PyInstaller directement : `pyinstaller --onefile --name AkibaCore main.py`

## Architecture (monofichier)

Tout le code vit dans `main.py`. Classes principales dans l'ordre :

| Classe | Role |
|--------|------|
| `DB` | Connexion SQLite, init schema, migrations (`PRAGMA user_version` 0→2), seeds, helper audit |
| `Finance` | Calculs financiers statiques purs (interets, penalites, echeances) |
| `Auth` | Connexion, changement mot de passe, verification `permis()/exiger()` (permissions + rôles, `PermissionError` + audit `REFUS_ACTION`) |
| `Backup` | Sauvegarde auto dans `sauvegardes/` (rotation sur 15 fichiers), restauration |
| `PDFGen` / `Imprimeur` | PDF minimal hors ligne (stdlib), impression CUPS Linux (`lp`/`lpr`) et Windows (`os.startfile print`) |
| `Recep` | Numérotation de reçus `REC-AAAA-NNNNNN` jamais réutilisée (table `compteur`), enregistrement, tickets (helpers `imprimer_recu` / `gerer_recu_operation`) |
| `Modeles` | Modèles de documents DOCX/ODT/HTML/TXT, substitution `{{VARIABLE}}`, génération/export |
| `EcranConnexion` | Ecran de connexion (tk.Toplevel) |
| `Dashboard` | Cartes synthetiques + journal d'audit |
| `OngletMembres` / `DlgMembre` / `DlgDetailMembre` | CRUD membres + vue detail |
| `OngletEpargnes` / `DlgEpargne` | Depot d'epargnes + annulation |
| `OngletCredits` / `DlgCredit` | Octroi de credits |
| `OngletRemboursements` / `DlgRemboursement` | Remboursements (penalite → interet → capital) |
| `OngletComptes` | Comptes membres (epargne, courant, bloque, credit) par devise : soldes, statuts (bloquer/debloquer/suspendre/reactiver), historique evenements/mouvements (permissions `accounts.view` / `accounts.block`), `Finance.solde_compte`/`impliquer_compte`/`compte_bloque` |
| `OngletSessions` / `DlgSession` | Gestion des sessions/reunions |
| `OngletRapports` | Export CSV + rapport HTML + sauvegarde manuelle |
| `OngletAdmin` | Utilisateurs, rôles, permissions individuelles, journal d'activité |
| `OngletDocuments` / `DlgGenererDocument` | Recus + modeles de documents + historique |
| `OngletParametres` | Coordonnees AVEC, devise, parts, impression auto, sauvegarde/restauration |
| `AkibaCore` | Fenetre principale, barre laterale filtree par permissions (`_page_autorisee`), timer sauvegarde periodique |

## Tests

Sept suites sans framework (bibliotheque standard `unittest`) :
`python3 test_finance.py` (61 tests), `python3 test_complet.py` (132 tests),
`python3 test_permissions.py` (19 tests), `python3 test_recus.py` (15 tests),
`python3 test_modeles.py` (16 tests), `python3 test_administration.py` (28 tests)
et `python3 test_scenario.py` (1 test) — soit **272 tests**,
ou simplement `make test`. Aucun linter ni type checker.
La CI construit l'executable **et execute la suite de tests**.

## Point de vigilance critique

- **`PERMISSIONS` est une liste de tuples `(code, libelle, groupe)`, PAS de
  chaînes.** Tout parcours qui doit préfixer un code (ex.
  `_page_autorisee` dans `_construire`) doit itérer sur `code` (l'élément
  0 du tuple) : itérer sur l'entrée elle-même provoque un
  `AttributeError` sur `p.startswith(...)` et une **fenêtre blanche pour
  tout utilisateur non-admin** (les admins sont épargnés car `est_admin`
  court-circuite). Ce bug a été corrigé et verrouillé par un test.

## Points de vigilance

- **Aucun package externe.** Ne jamais ajouter de dependances pip — l'application cible des machines sans acces internet.
- **Toutes les operations BDD passent par les methodes de la classe `DB`** (`exec`, `un`, `tous`, `valeur`). Utiliser `dict(row)` pour les objets Row.
- **`DB.audit()` ne doit jamais lever d'exception.** Elle attrape silencieusement les erreurs pour ne jamais bloquer les operations metier.
- **`Finance.maj_statuts()` est appele avant l'affichage des listes de credits.** Il modifie l'etat de la BDD (marque les credits en retard/soldes). C'est intentionnel, pas un effet de bord a supprimer.
- **Formules financieres en dur :** 10% d'interet annuel, 2%/mois de penalite par defaut. Configurables par AVEC dans la table `avec` (taux par type de credit), mais les **taux sont figes a l'octroi** dans `credit.taux_penalite` (et `taux_interet` du credit) : un changement de parametres n'affecte jamais les credits existants. Le snapshot `taux_penalite` sert au calcul des penalites dans les remboursements.
- **Multi-devises :** chaque epargne/credit/remboursement/reçu/compte porte une `devise` (CDF ou USD, valeurs dans `DEVISES`). Les soldes de chaque compteur sont **toujours additionnes par devise** ; ne jamais sommer des montants de devises differentes. L'AVEC a une devises principale (`avec.devise`, defaut CDF) et une liste `devises_autorisees` (JSON). Cote Finance : `solde_compte(membre, type, devise)`, `impliquer_compte` (creer + mouvement + evenement), `compte_bloque`.
- **Permissions (model) :** 42 codes dans `PERMISSIONS`, 7 rôles dans `ROLES_DEFAUTS`. Controle par `Auth.exiger(perm)` → `PermissionError` + audit `REFUS_ACTION`. Le role `admin` bypass systématiquement via `est_admin` (le champ `role='admin'` prime sur le contenu de `role_permission`). L'audit `REFUS_ACTION` est la seule source fiable pour suivre les tentatives refusees. **Header de fichier important :** `document_template` est une table + un concept de modele, a ne pas confondre avec la classe `Modeles`.
- **Reçus :** la numerotation repose sur la table `compteur` (nom `recu_{annee}`) initialisee par `INSERT OR IGNORE ... COALESCE(MAX(...))` — ne jamais reutiliser un numero apres suppression ; tester via `test_recus.py`.
- **PDF minimal :** `PDFGen` ne s'appuie que sur la stdlib ; le fichier se termine par `%%EOF\n` (les tests utilisent `rstrip()`).
- **Migration :** ne jamais toucher au contenu des tables existantes dans `_migrer()` ; `utilisateur.avec_id` est `NOT NULL DEFAULT 1` → l'AVEC id=1 doit exister avant tout seed utilisateur.
- **Sauvegarde automatique** toutes les 30 minutes via timer `tkinter.after()` dans `Appli`.
- **Mode WAL + cles etrangeres** actives via PRAGMA a chaque connexion.
- **Identifiants admin par defaut :** admin / admin123 (PBKDF2-SHA256 + sel). Seeds sur BDD vide.

## Fichiers a ignorer

- `AkibaCore.jsx` — Composant React de presentation (pas du code de production)
- `AkibaCore_SAUVEGARDE/` — Copie de sauvegarde du projet
- `AkibaCore app.exe/` — Sortie de build Windows
- `*.spec` est dans `.gitignore` mais le fichier `avec_bukavu.spec` doit etre present localement pour la compilation
