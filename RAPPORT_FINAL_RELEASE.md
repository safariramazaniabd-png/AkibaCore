# AKIBACORE v2.0.0 — RAPPORT FINAL DE LIVRAISON

**Date :** 2026-08-22

---

## 1. Verdict

```
AKIBACORE v2.0.0
FINAL RELEASE REPORT

STATUS:                PRODUCTION READY (sur Linux)
Linux:                 TESTED
Windows:               NOT TESTED — build préparé, non exécutable ici
Tests:                 192 passed / 0 failed / 0 blocked
                       (+ GUI 22/22, rôles 9/9, perf, crash, corruption)
Modules:               13/13 validés
Backup:                PASS (WAL checkpoint vérifié)
Restore:               PASS (assistée au démarrage + manuelle testées)
Security:              PASS (SQL paramétré, PBKDF2, audit, zéro réseau,
                       verrou anti-force-brute, mdp d'usine mort-né)
Financial calculations:PASS (intérêts, pénalités, imputation, échéances,
                       années bissextiles — 61/61)
Regression:            PASS (192/192 re-vérifiés après chaque correction)
```

---

## 2. Matrice de validation finale

| # | Élément | Linux | Windows |
|---|---|---|---|
| 1 | Tests unitaires moteurs financiers (61) | ✅ PASS | ⬜ Non exécutés |
| 2 | Tests métier complets (131) | ✅ PASS | ⬜ Non exécutés |
| 3 | Premier lancement propre (schéma + seeds) | ✅ PASS | ⬜ Non testé |
| 4 | Changement de mot de passe forcé | ✅ PASS (GUI réelle) | ⬜ Non testé |
| 5 | Parcours complet utilisateur (22 étapes) | ✅ PASS | ⬜ Non testé |
| 6 | Permissions 3 rôles (boutons retirés) | ✅ PASS | ⬜ Non testé |
| 7 | Blocage 2ᵉ crédit actif | ✅ PASS | ⬜ Non testé |
| 8 | Imputation remboursement (pén→int→cap) | ✅ PASS | ⬜ Non testé |
| 9 | Double clôture session bloquée | ✅ PASS | ⬜ Non testé |
| 10 | Exports CSV UTF-8 BOM (accents) ×5 | ✅ PASS | ⬜ Non testé |
| 11 | Rapport HTML (KPI, SVG, échappement) | ✅ PASS | ⬜ Non testé |
| 12 | Sauvegarde auto + manuelle (checkpoint WAL) | ✅ PASS | ⬜ Non testé |
| 13 | Restauration assistée base corrompue | ✅ PASS | ⬜ Non testé |
| 14 | Restauration manuelle (purge wal/shm) | ✅ PASS | ⬜ Non testé |
| 15 | Interruption brutale kill -9 → intégrité | ✅ PASS | ⬜ Non testé |
| 16 | Performance réaliste (~5 ms requêtes critiques) | ✅ PASS | ⬜ Non testé |
| 17 | Chemins portables (lancement hors dossier) | ✅ PASS | ⬜ Non testé |
| 18 | Build PyInstaller (spec corrigé, exe nommé AkibaCore) | ✅ PASS (29 Mo) | 🟡 Script prêt, **non exécuté** |
| 19 | Exécutable autonome testé depuis CWD étranger | ✅ PASS | ⬜ Non testé |
| 20 | Lanceurs (.sh/.bat) + .desktop + icône | ✅ PASS | 🟡 .bat écrit, non testé |
| 21 | Documentation (README, 2 guides, release notes, licence) | ✅ Complète | ✅ Complète |
| 22 | Checksums SHA-256 livrable | ✅ 19 fichiers | — |

Légende : ✅ exécuté et validé · 🟡 préparé uniquement · ⬜ non exécuté dans cet environnement.

---

## 3. Corrections incluses dans cette livraison

| Gravité | Correction |
|---|---|
| P0 | Crash à la connexion (sélection d'onglet avant création du conteneur) — corrigé + validé GUI |
| P1 | Attribut inexistant lors du changement de mot de passe initial (`self.db` → `self.auth.db`) |
| P1 | Module `html` exclu du build packagé (rapport HTML cassé en autonome) — spec corrigé |
| P2 | Sauvegardes WAL non consolidées ; résidus `-wal/-shm` après restauration |
| Amélioration | Chemins portables (`sys.frozen`/`__file__`), restauration assistée au démarrage, changement de mot de passe obligatoire au premier login, lanceurs + icône + .desktop, Makefile/tests documentés |

---

## 4. Problèmes connus (non bloquants)

1. **Build Windows non produit** dans cet environnement : exécuter `build_windows.bat` sur une machine Windows puis tester l'exe généré.
2. La CI GitHub compile sans `.spec` et n'exécute pas les tests (artefacts bruts).
3. Architecture monofichier `main.py` : dette de maintenabilité pour évolutions majeures futures.
4. UI en français uniquement ; comptes gérés par commandes techniques (documentées).
5. `AkibaCore_SAUVEGARDE/` (64 Mo) et `AkibaCore app.exe/` (50 Mo) présents sur disque mais ignorés par git — archivables/supprimables à discrétion du propriétaire.

---

## 5. Livrables

**Package : `AkibaCore-v2.0.0/`** (29 Mo, 20 fichiers, checksums `SHA256SUMS.txt`)

```
AkibaCore-v2.0.0/
├── README.md                  ← vue d'ensemble + installation (20 sections)
├── GUIDE_UTILISATEUR.md       ← pas-à-pas quotidien
├── GUIDE_ADMINISTRATEUR.md    ← comptes, sauvegardes, restauration, dépannage
├── RELEASE_NOTES_v2.0.0.md    ← nouveautés, corrections, validation
├── LICENSE                    ← MIT
├── SHA256SUMS.txt             ← empreintes des 19 autres fichiers
├── linux/                     ← binaire autonome testé + launcher + .desktop + icône + README
├── windows/                   ← launcher .bat + script de build + README détaillé
├── source/                    ← main.py + avec_bukavu.spec + requirements.txt
├── tests/                     ← test_finance.py (61) + test_complet.py (131)
└── build/                     ← build_linux.sh
```

Dépôt git : branche `main`, modifications prêtes à committer
(README, main.py, AGENTS.md, Makefile, .gitignore, launchers remplacés,
4 nouveaux documents, test_complet.py).

---

## 6. Prochaines étapes recommandées

1. **Commit git** de la livraison (fichiers listés ci-dessus) puis tag `v2.0.0`.
2. Sur une machine Windows : `build_windows.bat`, tester l'exe (installation, parcours rapide, sauvegarde/restauration), mettre à jour la matrice §2.
3. Distribuer le package (clé USB) avec copie des guides imprimés.
4. Formation : 30 min GUIDE_UTILISATEUR + 1 h GUIDE_ADMINISTRATEUR (sauvegarde/restauration en pratique).
5. Après 1 mois d'utilisation réelle : retour terrain → v2.0.1 si nécessaire.
