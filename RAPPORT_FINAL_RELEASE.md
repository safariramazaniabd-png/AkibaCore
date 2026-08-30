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

---

## 7. Addendum — Livraison v2.1.0

**Date :** 2026-08-30

### 7.1 Nouveautés

| Fonctionnalité | Description |
|---|---|
| **Comptes multiples** | Nouvel onglet Administration : création/modification/désactivation des comptes, réinitialisation des mots de passe, le tout dans l'interface (fini les commandes SQLite). |
| **Rôles et permissions** | 7 rôles prédéfinis (admin, agent, caissier, gestionnaire_credit, secretaire, auditeur, lecteur) + rôles personnalisés + 39 permissions granulaires (`module.ressource.action`), ajustables par compte. |
| **Contrôle dans la logique métier** | Les pages, onglets et actions masqués, et toute action interdite est refusée puis consignée au journal (`REFUS_ACTION` + permission). |
| **Reçus** | Numérotés `REC-AAAA-NNNNNN`, **jamais réutilisés** (compteur persistant par année, table `compteur`), en-tête de l'AVEC, impression / aperçu / PDF, réimpression, option d'impression automatique. |
| **Modèles de documents** | Import DOCX / ODT / HTML / TXT (gérés localement, stdlib seule), champs `{{VARIABLE}}` remplacés, modèle par défaut par type, générer / prévisualiser / imprimer / exporter / historique. |
| **Onglet Paramètres enrichi** | Coordonnées AVEC (adresse, téléphone, email, devise, logo), parts, taux, impression auto, sauvegarde / restauration en un clic. |
| **Migration automatique** | Anciennes bases v2.0.0 passées en v2.1.0 à la volée (`PRAGMA user_version` 0→1) **sans perte de données** et sans toucher au mot de passe des comptes existants. |

### 7.2 Validation v2.1.0

```
STATUS:                PRODUCTION READY (sur Linux)
Bases existantes:       migration v0→v1 validée sur copie réelle
                        (150 membres, 500 crédits), integrity_check ok,
                        authenticité des comptes préservée byte-for-byte
Tests:                 242 passed / 0 failed / 0 blocked
                       (61 finance + 132 complet + 18 permissions
                        + 15 reçus + 16 modèles)
Backup/Restore:        round-trip validé sur base migrée (compteurs,
                        tables, FK) — PASS
Windows:               NOT TESTED — script d'impression os.startfile
                        préparé, non exécutable ici
```

### 7.3 Corrections incluses

| Type | Correction |
|---|---|
| Critique | ORDER des seeds : l'AVEC est inséré avant le compte admin (dépendance FK `utilisateur.avec_id`) — bug de premier lancement v2.1 en cours de dev |
| Critique | `INSTR(recu_no,'-',5)` illégal en SQLite → compteur persistant `compteur` remplacant un MAX() (numéros jamais réutilisés) |
| Mineur | Code mort retiré (`ajouter_modele` à double contrôle, INSERT `WHERE 1=0`, boucle morte Paramètres, `recu_pdf`) |
| Régressions | Test tables 8 → 16 ; CHECK rôle supprimé (rôles libres) au profit de la validation applicative + FK `avec_id` |

### 7.4 Évolution du schéma (16 tables)

Anciennes 8 tables enrichies (`utilisateur` : rôle libre, `avec_id`,
`derniere_connexion` ; `avec` : adresse/téléphone/email/devise/logo/
`impression_auto`) + 8 nouvelles : `permission`, `role`,
`role_permission`, `user_permission`, `receipt`, `document_template`,
`document_genere`, `compteur`.

### 7.5 Problèmes connus (non bloquants)

1. **Windows non testé** : `os.startfile(path, 'print')` et le build `.exe` restent à valider sur machine Windows.
2. Barre latérale dynamique : un compte sans aucune permission ne voit que le Tableau de bord.
3. Le rôle `agent` hérite de `backup.create` : c'est voulu (sauvegarde manuelle par les agents de terrain).

### 7.6 Documentation

README (fonctionnalités, rôles, reçus/documents, 16 tables, 242 tests),
GUIDE_ADMINISTRATEUR (gestion des comptes dans l'interface, 39 permissions,
rôles) et AGENTS.md mis à jour pour la v2.1.0.

---

## 8. Addendum — Livraison v2.2.0

**Date :** 2026-08-30

### 8.1 Nouveautés

| Fonctionnalité | Description |
|---|---|
| **Multi-devises CDF / USD** | Épargnes, crédits, remboursements, reçus et comptes portent chacun une `devise` (`DEVISES`). L'AVEC définit une devise principale (`avec.devise`, défaut CDF) et une liste `devises_autorisees` ; les soldes et totaux sont **toujours additionnés par devise** (jamais mélangés). |
| **Comptes membres** | Nouvel onglet **Comptes** (permissions `accounts.view` / `accounts.block`) : soldes par type (épargne, courant, bloqué, crédit) et par devise, statuts `actif / bloqué / suspendu`, actions Bloquer/Débloquer/Suspendre/Réactiver avec historique `compte_evenement` et mouvements `compte_mouvement` (via `Finance.solde_compte` / `impliquer_compte` / `compte_bloque`). |
| **Taux par type de crédit (figés)** | Taux d'intérêt distincts Ordinaire / Urgence / Investissement + taux de pénalité, configurables dans les Paramètres financiers (`settings.financial.edit`, audit `MODIFIER_PARAMS_FINANCIERS`). Chaque crédit **fige** son taux à l'octroi (`credit.taux_penalite`) : modifier les paramètres n'affecte jamais les crédits existants. |
| **Type et devise à l'octroi** | `DlgCredit` sélectionne la devise et le type du crédit ; les pénalités de remboursement utilisent le snapshot `taux_penalite` du crédit ; les reçus portent la devise. |
| **Rapports multi-devises** | Dashboard, OngletRapports (bilan, CSV, rapport HTML), OngletMembres et détail membre : totaux et cartes calculés **par devise**. |

### 8.2 Validation v2.2.0

```
STATUS:                PRODUCTION READY (sur Linux)
Bases neuves:           user_version 2, 19 tables, devise AVEC = CDF
                        (corrigé : le DEFAULT 'FC' de la migration v1
                        n'étant plus hérité par le seed)
Bases existantes:       migration v1→v2 validée sur copie de production
                        (150 membres, 500 crédits, 2004 remboursements)
                        integrity_check ok, foreign_key_check ok,
                        devise historique FC migrée en CDF,
                        pénalités snapshotées par crédit
Tests:                 243 passed / 0 failed / 0 blocked
                       (61 finance + 132 complet + 19 permissions
                        + 15 reçus + 16 modèles)
Smoke UI réels:        OngletComptes (soldes/devises/boutons), OngletDocuments,
                       DlgGenererDocument (variables DEVISE, SESSION_NUMERO,
                       DATE_REUNION, PENALITE) — PASS
Windows:               NOT TESTED — script d'impression os.startfile
                       préparé, non exécutable ici
```

### 8.3 Corrections incluses

| Type | Correction |
|---|---|
| Critical | `avec.devise` valait encore `'FC'` sur **base neuve** (DEFAULT posé en migration v1) → défaut corrigé en `'CDF'` ; assertion `test_modeles` alignée |
| Ingénierie | `_pdf` du générateur de documents robuste (repli sur `contenu`, gestion OSError), aperçu en lecture seule, variables du modèle listées depuis `Modeles.NAUT` (plus de liste tronquée) |
| Documentation | Raccourcis double-clic (modifier modèle / voir reçu), filtres reçus non tronqués, boutons de statut de compte activés selon la sélection, doublon devise supprimé dans DlgRemboursement, FC → CDF dans README/guides |
| Audit | `settings.financial.edit` et `accounts.view` / `accounts.block` (42 permissions total) ; rôles `agent` et `auditeur` obtiennent `accounts.view` |

### 8.4 Évolution du schéma (16 → 19 tables)

Migration v2 ajoute : colonnes `devise` sur `epargne`, `credit`,
`remboursement`, `receipt` ; `credit.type_credit` et `credit.taux_penalite`
(snapshot) ; `avec.taux_interet_urgence`, `taux_interet_investissement`,
`devises_autorisees`, `types_credit` ; tables **`compte`, `compte_evenement`,
`compte_mouvement`** (avec 5 index).

### 8.5 Problèmes connus (non bloquants)

1. **Windows non testé** : `os.startfile(path, 'print')` et le build `.exe` restent à valider sur machine Windows.
2. Documents : `SESSION_NUMERO` / `DATE_REUNION` sont remplis depuis la **dernière session** de l'AVEC lors de la génération via l'interface Documents (pas de sélecteur dédié).
3. Les comptes épargne/crédit n'ont pas de « mouvements » dans `compte_mouvement` : leurs soldes sont dérivés des tables métier (choix assumé, mentionné dans l'aide de l'onglet).

---

## 9. Rapport final v2.2.0 — synthèse en 16 sections

### 9.1 Objet du rapport
Document synthétique de clôture des livraisons v2.0.0, v2.1.0 et
v2.2.0 d'AkibaCore, gestionnaire AVEC 100 % hors ligne.

### 9.2 Périmètre fonctionnel
Membres, épargnes, crédits (types, taux par type, pénalités figées),
remboursements (pénalité → intérêt → capital), comptes membres par type
et par devise, sessions, rapports, reçus, modèles de documents,
utilisateurs/rôles/permissions, paramètres financiers, sauvegardes.

### 9.3 Environnement et contraintes
Python ≥ 3.8, Tkinter + SQLite (stdlib seule), Linux/Windows, aucun
package externe, aucun accès réseau. Multi-devises CDF/USD.

### 9.4 Fonctionnalités livrées (v2.2.0)
Multi-devises sur toutes les opérations ; onglet **Comptes** ; taux par
type de crédit configurables et figés à l'octroi ; rapport/bilan par
devise ; documents enrichis (`{{DEVISE}}`, `{{SESSION_NUMERO}}`,
`{{DATE_REUNION}}`, pénalité/intérêt/principal/solde).

### 9.5 Multi-devises
Chaque épargne, crédit, remboursement, reçu et compte porte une
`devise` (paramètres : `avec.devise`, `devises_autorisees`). Soldes et
totaux strictement séparés par devise ; défaut CDF (historique FC migré).

### 9.6 Comptes membres
`compte`, `compte_evenement`, `compte_mouvement` ; `Finance.solde_compte`,
`impliquer_compte`, `compte_bloque` ; statuts actif/bloqué/suspendu ;
actions gated `accounts.block`, lecture `accounts.view`.

### 9.7 Taux financiers
Taux d'intérêt annuels par type + pénalité mensuelle, dans la table
`avec` ; **snapshot à l'octroi** (`credit.taux_penalite`) ; les
modifications ultérieures n'affectent jamais les crédits existants.

### 9.8 Reçus et documents
Numérotation `REC-AAAA-NNNNNN` jamais réutilisée (table `compteur`),
devise portée par le reçu, ticket/PDF/impression ; modèles
DOCX/ODT/HTML/TXT, substitution `{{VARIABLE}}`, génération/PDF/
impression avec audit.

### 9.9 Permissions et audit
42 permissions (`module.ressource.action`), 7 rôles prédéfinis,
permissions individuelles, contrôle métier `Auth.exiger` → `REFUS_ACTION`
traçé. Actions auditées incluant `MODIFIER_PARAMS_FINANCIERS`
(avant/après) et `MODIFIER_COMPTE`.

### 9.10 Migration et schéma
`PRAGMA user_version` 0→2 : 19 tables, device/type/perte d'historique
préservés, contrôles `foreign_key_check` après chaque version,
migration idempotente. Défaut de devise corrigé sur base neuve (CDF).

### 9.11 Tests
**243 tests** (61 finance + 132 complet + 19 permissions + 15 reçus +
16 modèles) tous verts via `make test` ; `py_compile` ok ; fumées UI
réelles (Dashboard/onglets, OngletComptes, OngletDocuments,
DlgGenererDocument).

### 9.12 Validation sur données réelles
Copie de production (150 membres, 500 crédits, 2004 remboursements) :
migration v1→v2 sans perte, intégrité et FK ok, FC→CDF, pénalités
snapshotées. Base neuve : version 2, devise CDF, 19 tables.

### 9.13 Corrections notables
Page blanche Administration ; `avec.devise` en FC sur base neuve ;
`_pdf` Documents fragile ; liste des variables tronquée ; doublon devise
dans le détail de remboursement ; codes morts (Finance.avoir_compte).

### 9.14 Problèmes connus
Windows non testé ; variables de session rattachées à la dernière
session ; comptes dérivés sans mouvements `compte_mouvement`.

### 9.15 Documentation
README, GUIDE_UTILISATEUR (12 sections), GUIDE_ADMINISTRATEUR
(9 sections), AGENTS.md et RAPPORT_FINAL_RELEASE mis à jour v2.2.0
(243 tests, 42 permissions, 19 tables, CDF/USD).

### 9.16 Verdict
**PRODUCTION READY (Linux).** La livraison v2.2.0 étend AkibaCore en
plateforme financière locale multi-devises et multi-comptes sans rien
casser de la v2.1.0 ; toutes les preuves de validation sont reproductibles
par `make test` et les cas de validation documentés ci-dessus.
