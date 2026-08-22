# NOTES DE VERSION — AkibaCore v2.0.0

**Date de livraison :** 2026-08-22
**Statut :** Production Ready (validée sur Linux ; build Windows préparé)

---

## En un coup d'œil

AkibaCore v2.0.0 est la première version « produit » : installable,
lancable par double-clic, documentée pour les utilisateurs finaux,
sécurisée contre les erreurs d'exploitation et couverte par une suite
de tests complète. Aucune dépendance externe : fonctionne hors ligne
sur un ordinateur ordinaire.

---

## Nouveautés

| Fonctionnalité | Description |
|---|---|
| Changement de mot de passe forcé | Au premier login avec le mot de passe d'usine `admin123`, l'application **exige** un nouveau mot de passe dans une fenêtre non refermable. Le mot de passe d'usine devient immédiatement inutilisable. |
| Chemins portables | La base de données et les sauvegardes sont désormais créées **à côté du programme** (ou de l'exécutable), plus jamais dans le répertoire courant du système. L'application peut être lancée depuis n'importe où. |
| Restauration assistée | Si la base est endommagée au démarrage, l'application détecte le problème, propose la dernière sauvegarde disponible et restaure en un clic (les fichiers `-wal`/`-shm` obsolètes sont nettoyés). |
| Sauvegardes fiables | Checkpoint WAL (`PRAGMA wal_checkpoint(TRUNCATE)`) avant chaque copie : même l'activité de la seconde écoulée est incluse dans la sauvegarde. |
| Lanceurs professionnels | `lancer_akibacore.sh` / `lancer_akibacore.bat` avec détection des prérequis et messages d'aide en français ; raccourci bureau `akibacore.desktop` + icône. |
| Exécutable autonome corrigé | Le fichier de construction PyInstaller excluait par erreur un module utilisé par le rapport HTML (`html`) — le rapport aurait planté en version packagée. Corrigé et validé sur le binaire réel. |
| Documentation utilisateur | README orienté utilisateur, GUIDE_UTILISATEUR pas-à-pas, GUIDE_ADMINISTRATEUR (comptes, sauvegardes, restauration, dépannage). |

---

## Corrections de bugs

| Gravité | Bug | Correction |
|---|---|---|
| **P0 — critique** | Crash silencieux à chaque connexion : la barre latérale sélectionnait l'onglet Dashboard avant que son conteneur n'existe (`AttributeError` avalé par Tk). L'utilisateur restait bloqué après login. | Réordonnancement de la construction de la fenêtre principale (conteneur créé avant la sélection initiale). Validé par parcours GUI complet. |
| P1 — majeur | Plantage lors du changement de mot de passe initial : appel à un attribut inexistant (`self.db` sur l'écran de connexion). | Appel corrigé via la chaîne d'authentification (`self.auth.db`). |
| P1 — majeur | Module `html` exclu du build packagé (rapport HTML impossible en version autonome). | Retiré de la liste d'exclusions du `.spec`. |
| P2 | Sauvegarde copiant potentiellement une base non consolidée (mode WAL) ; fichiers `-wal`/`-shm` résiduels après restauration. | Checkpoint avant copie ; purge des fichiers résiduels à la restauration. |

---

## Sécurité

- Mots de passe hachés PBKDF2-SHA256 (100 000 itérations, sel aléatoire) ;
- Verrouillage 30 s après 5 échecs de connexion ;
- Journal d'audit de toutes les opérations sensibles (nouvelle entrée : changement de mot de passe initial) ;
- Requêtes SQL 100 % paramétrées (audit statique : aucune concaténation) ;
- Zéro communication réseau (audit des imports) ;
- Mode SQLite WAL + clés étrangères : aucune écriture partielle même en cas de coupure brutale.

---

## Validation (réalisée, datée)

| Test | Résultat |
|---|---|
| Suite unitaire moteurs financiers (`test_finance.py`) | **61/61 PASS** |
| Suite métier complète (`test_complet.py`) | **131/131 PASS** |
| Parcours utilisateur réel en interface graphique (login → membre unicode → épargnes → crédit → blocage 2ᵉ crédit → remboursements partiels/complets → session → bilan → 5 exports CSV UTF-8 → rapport HTML → sauvegarde → cohérence dashboard/BDD → reconnexion) | **22/22 PASS** |
| Permissions par rôle (admin/agent/lecteur, boutons retirés pour lecture seule) | **9/9 PASS** |
| Premier lancement propre (environnement vierge, schéma + seeds) | PASS |
| Base corrompue volontairement → détection + restauration | PASS |
| Interruption brutale (kill -9 pendant transaction) → intégrité préservée | PASS |
| Performance réaliste (150 membres, 500 crédits, 2000 remboursements, 5000 lignes d'audit) : toutes requêtes critiques ≈ 5 ms cumulées | PASS |
| Exécutable autonome Linux construit puis lancé depuis un autre répertoire (base créée à côté du binaire, seeds corrects) | PASS |

---

## Compatibilité

| Système | État |
|---|---|
| Linux x86-64 (Ubuntu/Debian/Mint) | **Testé et validé** (Python 3.8+ ou binaire autonome) |
| Windows 10/11 | Script de construction fourni et vérifié syntaxiquement ; **build non exécuté dans cet environnement** — à produire sur une machine Windows (`build_windows.bat`) |
| macOS | Non testé ; sans dépendance externe, devrait fonctionner via `python3 main.py` |

Python ≥ 3.8 requis si exécution depuis la source. Aucune bibliothèque externe.

---

## Limitations connues

1. Le build Windows doit encore être généré/testé sur une machine Windows (procédure prête).
2. La CI GitHub construit l'exécutable mais n'exécute pas les tests ni le fichier `.spec`.
3. Architecture monofichier (`main.py`) : maintenabilité limitée pour de futures évolutions majeures.
4. Interface exclusivement en français ; aucun mécanisme d'internationalisation.
5. La gestion des comptes utilisateurs passe par des commandes techniques (documentées dans GUIDE_ADMINISTRATEUR.md).

---

## Installation

Voir README.md (sections 3-5). Résumé :

```bash
# Linux — binaire autonome
chmod +x AkibaCore lancer_akibacore.sh && ./lancer_akibacore.sh

# Linux/macOS — depuis la source
sudo apt install python3 python3-tk   # si besoin
python3 main.py
```

Première connexion : `admin` / `admin123` → changement de mot de passe obligatoire.
