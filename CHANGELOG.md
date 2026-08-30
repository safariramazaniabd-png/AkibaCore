# CHANGELOG — AkibaCore

## [2.2.0] — 2026-08-30

### Corrections (production)

- **CORRECTION CRITIQUE — « Page blanche » pour les utilisateurs non
  administrateurs.** La fonction de filtrage de la navigation
  (`_page_autorisee`) parcourait le catalogue `PERMISSIONS` comme une
  liste de **chaînes** alors que ce sont des **tuples**
  `(code, libelle, groupe)`. L'appel `p.startswith(...)` sur un tuple
  levait `AttributeError` lors de la construction de la fenêtre pour
  **chaque** utilisateur non-admin, provoquant une fenêtre blanche
  (les administrateurs étaient épargnés car `est_admin` court-circuite
  le calcul). Corrigé : itération sur `code` (premier élément du tuple).
  Un utilisateur non-admin se connecte et navigue désormais normalement.
- **Robustesse de navigation.** `_naviguer` est désormais protégé : si
  la construction d'une page échoue, l'erreur est journalisée dans
  `erreur_demarrage.log` avec une référence `AKB-XXXX`, un contenu
  minimal est affiché (fini la page blanche) et un message clair est
  présenté à l'utilisateur.
- **Données jamais bloquées par « Program Files ».** Le dossier des
  données (base, sauvegardes, documents) est choisi automatiquement :
  à côté du programme si celui-ci est accessible en écriture (portable),
  sinon dans le dossier utilisateur (`%LOCALAPPDATA%\AkibaCore` sous
  Windows). Une installation dans `C:\Program Files\AkibaCore` (protégé
  par Windows) ne peut plus provoquer d'échec d'écriture.

### Nouveautés

- **Type de compte du membre à l'ajout.** La fenêtre « Ajouter un membre »
  demande désormais le **type de compte** (épargne, courant, bloqué,
  crédit). La valeur est stockée dans `membre.type_compte` (informatif)
  et affichée dans le dossier du membre. Migration `user_version` 2 → 3
  (colonne ajoutée sur les bases existantes, défaut `epargne`, aucune
  donnée perdue).
- L'icône d'application `AkibaCore.ico` est référencée dans la
  configuration PyInstaller (exécutable Windows).
- Script de création de la **version portable Windows**
  (`setup_windows/creer_portable_windows.bat` → `AkibaCore_Portable_v2.2.0_Windows.zip`).
- Script d'**installateur Windows** Inno Setup
  (`setup_windows/AkibaCore_installer.iss` → `AkibaCore_Setup_v2.2.0_Windows_x64.exe`).
- La CI exécute désormais la suite de tests complète avant compilation.

### Tests

- Ajout de la suite `test_administration.py` (32 tests) couvrant la
  cause racine de la page blanche, la navigation filtrée, la gestion
  des utilisateurs/rôles/permissions, la séparation des devises, les
  comptes membres, le snapshot des taux et la portabilité du dossier
  de données.
- Ajout de `test_scenario.py` : scénario utilisateur réel de bout en
  bout hors ligne (épargne → reçu → crédit → remboursement → comptes →
  rapport → sauvegarde → restauration).
- **Total : 276 tests verts.**

## [2.1.0] — 2026-08 (résumé)

- Multi-devises (CDF / USD) : séparation stricte des soldes par devise,
  configuration des devises autorisées par AVEC.
- Comptes membres (épargne, crédit, courant, bloqué) + statuts
  (bloquer/débloquer/suspendre/réactiver) et historique.
- Taux d'intérêt et pénalités configurables, **figés à l'octroi** de
  chaque crédit (snapshot `taux_penalite`).
- Permissions granulaires (42), 7 rôles, permissions individuelles,
  journal `REFUS_ACTION`.
- Module **Administration** (utilisateurs, rôles, permissions, journal).
- Module **Documents** : modèles DOCX/ODT/HTML/TXT, variables
  dynamiques `{{...}}`, modèle par défaut, génération/impression/PDF.
- Numérotation unique des reçus `REC-AAAA-NNNNNN`.

## [2.0.0] — 2026-08-22

Première version « produit » : voir `RELEASE_NOTES_v2.0.0.md`.
- Mot de passe initial forcé, chemins portables, restauration assistée,
  sauvegardes fiables (checkpoint WAL), lanceurs + icône,
  exécutable autonome corrigé, documentation utilisateur.
