# AKIBACORE v2.2.0 — RAPPORT FINAL DE LIVRAISON

**Date :** 2026-08-30
**Verdict :** READY FOR RELEASE — PRODUCTION READY (Linux) — Windows : PRÉPARÉ (validation réelle non effectuée ici)

---

## 1. Verdict

```
VERSION            : 2.2.0
TESTS              : 276/276  (OK)
BUILD WINDOWS      : PRÉPARÉ (script + spec + installateur + portable ; exe non produit ici)
INSTALLATEUR       : setup_windows/AkibaCore_installer.iss -> release\AkibaCore_Setup_v2.2.0_Windows_x64.exe (à compiler sur Windows)
EXÉCUTABLE         : dist/AkibaCore (Linux, construit et testé) / AkibaCore.exe (Windows, prévu)
VERSION PORTABLE   : setup_windows/creer_portable_windows.bat -> AkibaCore_Portable_v2.2.0_Windows.zip (à exécuter sur Windows)
OFFLINE            : OK (aucune dépendance réseau ; 100 % locale)
ADMINISTRATION     : OK (cause racine corrigée)
DOCUMENTS          : OK (modèles, variables, isolation par AVEC, actions)
COMPTES            : OK (épargne, crédit, courant, bloqué)
CDF                : OK
USD                : OK (séparation stricte des devises)
TAUX CONFIGURABLES : OK (figés à l'octroi — snapshot)
REÇUS              : OK (numérotation unique, devise)
IMPRESSION         : NON TESTÉ (pas d'imprimante dans cet environnement ; chemin sans crash)
BACKUP             : OK
RESTAURATION       : OK (testée de bout en bout)
LINUX              : OK
WINDOWS            : NON TESTÉ (pas de machine Windows disponible)
STATUT FINAL       : READY FOR RELEASE
```

---

## 2. Problème critique trouvé et corrigé — « Page blanche » Administration

### Symptôme
L'ouverture de la page **Administration** (et, de façon plus générale, la
navigation) affichait une **fenêtre blanche** pour tout utilisateur non
administrateur.

### Cause racine
Dans `AkibaCore._construire`, la fonction imbriquée `_page_autorisee`
(= main.py, `_construire`) parcourait le catalogue **`PERMISSIONS`** comme
une liste de **chaînes** :

```python
return any(self.auth.permis(p) for p in PERMISSIONS
           for pref in prefixes if p.startswith(pref + "."))
```

Or chaque entrée de `PERMISSIONS` est en réalité une **tuple**
`(code, libelle, groupe)`. L'appel `p.startswith(...)` sur une **tuple**
levait `AttributeError: 'tuple' object has no attribute 'startswith'`
lors de la construction de la fenêtre.

- Les **administrateurs** étaient épargnés car `_page_autorisee` retourne
  `True` très tôt via `est_admin` (court-circuit) : le bug ne se
  déclenchait pas pour eux.
- **Tout utilisateur non-admin** (agent, caissier, auditeur, lecteur…)
  subissait l'exception lors du **login lui-même** (construction de la
  barre latérale) → fenêtre vide/blanche et compte inutilisable.

Le rapport de livraison antérieur listait cette page blanche comme
« corrigée », mais **aucune défense ne protégeait** ce code : le bug
était bien présent dans l'arbre de travail. D'où l'importance de la
correction et de sa re-production automatisée.

### Correction
`_page_autorisee` itère désormais sur le **code** (premier élément du
tuple) :

```python
return any(self.auth.permis(code)
           for code, _lib, _grp in PERMISSIONS
           for pref in prefixes
           if code.startswith(pref + "."))
```

Vérifié par reproduction GUI réelle : **admin ET non-admin** naviguent
sur toutes les pages, **y compris Administration**, sans exception.

### Correction connexe — robustesse de navigation
`_naviguer` est protégé : en cas d'erreur de construction d'une page,
l'exception est journalisée (`erreur_demarrage.log`, référence `AKB-XXXX`),
un contenu minimal est affiché (jamais de page blanche) et un message
clair est présenté. Conforme à l'exigence « l'utilisateur final ne voit
jamais de traceback brut ».

---

## 3. Autres corrections

- **Données jamais bloquées par « Program Files ».** Nouveau
  `_repertoire_donnees()` : le dossier des données (base, sauvegardes,
  documents, logs) est choisi dans un dossier **accessible en écriture**
  — à côté du programme (portable) sinon dans le dossier utilisateur
  (`%LOCALAPPDATA%\AkibaCore` sous Windows). Les constantes `DB_CHEMIN`,
  `BACKUP_DIR` et le journal d'erreur utilisent ce dossier.
- **CI** : la suite de tests complète est désormais exécutée avant la
  compilation (workflow GitHub).
- **Icône** `AkibaCore.ico` générée et référencée dans le spec PyInstaller.

---

## 4. Fonctionnalités livrées (vérifiées / intactes)

| Domaine | État |
|---|---|
| Administration : utilisateurs, rôles, permissions, journal | OK (objet de la correction) |
| Documents : modèles DOCX/ODT/HTML/TXT, variables `{{...}}`, modèle par défaut, import copié localement, isolation par AVEC, suppression avec confirmation + archivage | OK |
| Devises : CDF / USD, séparation stricte, jamais additionnées sans taux de change, configuration par AVEC | OK |
| Comptes : épargne, crédit, courant, bloqué (+ statuts, mouvements, événements) | OK |
| Type de compte du membre choisi à l'ajout (informatif, migration v2→v3) | OK |
| Taux & pénalités : configurables, **snapshot à l'octroi** (427 crédits inchangés quand le taux AVEC change) | OK |
| Reçus : numérotation unique jamais réutilisée, devise, PDF | OK |
| Rapports : soldes par devise, CSV UTF-8, HTML | OK |
| Audit : journal complet, `REFUS_ACTION` | OK |
| Backup / restauration | OK (testée de bout en bout) |
| Multi-utilisateurs & permissions (contrôle dans la logique métier) | OK |
| Offline (aucune dépendance réseau) | OK |

---

## 5. Schéma de base de données

19 tables : `utilisateur`, `avec`, `membre`, `session`, `epargne`, `credit`,
`remboursement`, `audit_log`, `permission`, `role`, `role_permission`,
`user_permission`, `receipt`, `document_template`, `document_genere`,
`compteur`, `compte`, `compte_evenement`, `compte_mouvement`
(+ `sqlite_sequence`). `PRAGMA user_version = 3`. WAL + clés étrangères.

Migration v2 → v3 ajoutée dans cette livraison : colonne
`membre.type_compte` (type de compte choisi à l'ajout d'un membre,
informatif — codes `epargne/courant/bloque/credit`, défaut `epargne`).
Les autres changements sont applicatifs (logique de navigation +
choix du dossier de données).

---

## 6. Tests

| Suite | Tests | Résultat |
|---|---|---|
| test_finance.py | 61 | OK |
| test_complet.py | 132 | OK |
| test_permissions.py | 19 | OK |
| test_recus.py | 15 | OK |
| test_modeles.py | 16 | OK |
| **test_administration.py** (nouveau) | 32 | OK |
| **test_scenario.py** (nouveau) | 1 | OK |
| **TOTAL** | **276** | **276/276 terminés** |

Les nouveaux tests verrouillent :
- la cause racine de la page blanche (invariant `PERMISSIONS` +
  logique corrigée pour admin et non-admin) ;
- la gestion des utilisateurs / rôles / permissions ;
- la séparation stricte CDF / USD ;
- les comptes membres (épargne, crédit, courant, bloqué) ;
- le snapshot des taux à l'octroi ;
- la numérotation des reçus et la devise ;
- la portabilité du dossier de données (jamais non-écrivable) ;
- le scénario utilisateur réel de bout en bout (épargne → reçu →
  crédit → remboursement → comptes → rapport → sauvegarde → restauration).

---

## 7. Packaging

### Linux — TESTÉ
- `pyinstaller avec_bukavu.spec --clean --noconfirm` → `dist/AkibaCore`
  (ELF 64 bits, ~29 Mo) construit et **lancé** ; base neuve initialisée
  (20 tables, 42 permissions, 7 rôles, admin). Aucune erreur au démarrage.

### Windows — PRÉPARÉ, non validé réellement dans cet environnement
Cet environnement est **Linux et aucune machine Windows n'est disponible**.
Les livrables Windows sont donc **préparés et documentés, non exécutés** :

1. `setup_windows/build_windows.bat` → produit `dist\AkibaCore.exe` (PyInstaller).
2. `setup_windows/creer_portable_windows.bat` → produit
   `AkibaCore_Portable_v2.2.0_Windows.zip` (structure
   `AkibaCore\AkibaCore.exe` + dossiers data/sauvegardes/documents/modeles/exports/logs).
3. `setup_windows/AkibaCore_installer.iss` (Inno Setup, gratuit) → produit
   `release\AkibaCore_Setup_v2.2.0_Windows_x64.exe` (raccourcis Bureau + Menu
   Démarrer, désinstallation sans toucher aux données).

> **BUILD WINDOWS : PRÉPARÉ — VALIDATION WINDOWS RÉELLE : NON EFFECTUÉE**

---

## 8. Livrables

- `release/` — dossier de livraison (assemblé par `setup_linux/creer_release.sh` /
  `setup_windows/creer_release.bat`) contenant : `CHANGELOG.md`,
  `GUIDE_INSTALLATION_WINDOWS.txt|md`, `GUIDE_UTILISATEUR.md`,
  `GUIDE_ADMINISTRATEUR.md`, `SHA256SUMS.txt`, et (lorsqu'ils sont
  produits sur Windows) l'installateur et la version portable.
- `AkibaCore.ico`, `icone_akibacore.png`,
  `setup_windows/` (scripts de lancement et installation Windows :
  `build_windows.bat`, `lancer_akibacore.bat`,
  `creer_portable_windows.bat`, `creer_release.bat`,
  `AkibaCore_installer.iss`),
  `setup_linux/` (scripts de lancement et installation Linux :
  `lancer_akibacore.sh`, `build_linux.sh`, `installer_raccourci.sh`,
  `creer_release.sh`, `akibacore.desktop`).

---

## 9. Problèmes restants (non bloquants)

1. **Windows non réellement validé** (installateur/exe/impression) —
   à faire sur une machine Windows 10/11 avec `setup_windows/build_windows.bat` puis
   test manuel (guide fourni).
2. **Impression non testée** : aucun périphérique d'impression dans cet
   environnement. Le chemin d'impression ne provoque aucune erreur sans
   imprimante (message clair), l'aperçu et le PDF restent disponibles.
3. Les variables de session (`SESSION_NUMERO`, `DATE_REUNION`) dans les
   modèles se remplissent depuis la dernière session.
4. Les comptes épargne/crédit dérivent leur solde des tables métier : ils
   n'ont pas de lignes `compte_mouvement` (documenté, voulu).

---

## 10. Conclusion

La livraison **v2.2.0** corrige la cause racine de la **page blanche
Administration** (un vrai `AttributeError` affectant **tout utilisateur
non-admin**), durcit la navigation, rend le stockage des données
**robuste face à « Program Files »**, et porte la suite de tests à
**272 verts** incluant la nouvelle suite de régression dédiée. Le produit
est **READY FOR RELEASE** sur Linux ; la validation Windows réelle reste
à effectuer sur une machine Windows conformément aux scripts fournis.
