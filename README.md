# AkibaCore — Système de Gestion AVEC

**Version 2.0.0** | 100 % hors ligne | Simple, sûr, sans connexion Internet

---

## 1. Présentation

**AkibaCore** est un logiciel de gestion financière conçu pour les
**Associations Villageoises d'Épargne et de Crédit (AVEC)** d'Afrique centrale.
Le mot *akiba* signifie « épargne » en swahili.

Il permet à une AVEC de gérer ses membres, son épargne, ses crédits, ses
remboursements et ses réunions, puis d'imprimer des rapports complets —
le tout **sans aucune connexion Internet**, sur un simple ordinateur
sous Windows ou Linux.

> Ce README s'adresse aux utilisateurs. Pour les procédures pas-à-pas,
> voir `GUIDE_UTILISATEUR.md`. Pour la gestion des comptes et des
> sauvegardes, voir `GUIDE_ADMINISTRATEUR.md`.

---

## 2. Fonctionnalités

| Module | Ce que vous pouvez faire |
|---|---|
| Tableau de bord | Voir en un coup d'œil membres, épargnes, crédits actifs et en retard |
| Membres | Inscrire, modifier, rechercher, consulter l'historique complet |
| Épargnes | Enregistrer les dépôts (ordinaire, solidarité, urgence), annuler une erreur |
| Crédits | Octroyer avec calcul automatique des intérêts ; un membre ne peut avoir qu'un crédit actif à la fois |
| Remboursements | Encaisser les paiements : pénalité → intérêt → principal, statut mis à jour automatiquement |
| Sessions | Numéroter et clôturer chaque réunion de l'association |
| Rapports | Bilan financier, rapport HTML imprimable, 5 exports CSV (Excel) |
| Sécurité | Mots de passe chiffrés, journal d'audit, sauvegardes automatiques |

---

## 3. Installation Linux (Ubuntu / Debian / Linux Mint)

### Option A — Version autonome recommandée

1. Copiez le dossier livré (contenant `AkibaCore` et `lancer_akibacore.sh`)
   où vous voulez, par exemple dans votre dossier personnel.
2. Ouvrez un terminal dans ce dossier et tapez :

```bash
chmod +x AkibaCore lancer_akibacore.sh
./lancer_akibacore.sh
```

C'est tout. Aucune installation supplémentaire n'est nécessaire.

### Option B — À partir du code source

```bash
sudo apt install python3 python3-tk     # si pas déjà installé
./lancer_akibacore.sh                   # ou : python3 main.py
```

### Raccourci dans le menu (optionnel)

Copiez `akibacore.desktop` et `icone_akibacore.png` vers :

```bash
mkdir -p ~/.local/share/applications ~/.local/share/icons
cp akibacore.desktop ~/.local/share/applications/
cp icone_akibacore.png ~/.local/share/icons/
# Éditez ensuite Exec= et Path= pour pointer vers votre dossier
```

---

## 4. Installation Windows 10 / 11

### Option A — Exécutable (si fourni)

1. Copiez le dossier livré contenant `AkibaCore.exe`.
2. Double-cliquez sur `AkibaCore.exe`.

Si Windows affiche un avertissement SmartScreen, cliquez
« Informations complémentaires » puis « Exécuter quand même ».

### Option B — À partir du code source

1. Installez Python depuis https://www.python.org/downloads/
   **en cochant « Add Python to PATH »** et « tcl/tk and IDLE ».
2. Double-cliquez sur `lancer_akibacore.bat` (ou clic droit → Exécuter).

Pour créer vous-même l'exécutable `.exe`, voir `windows/README.md`
ou lancez `build_windows.bat`.

---

## 5. Premier lancement

Au premier démarrage, AkibaCore crée automatiquement :

| Élément | Emplacement |
|---|---|
| Base de données | `akibacore.db` à côté du programme |
| Dossier de sauvegardes | `sauvegardes/` |
| Compte administrateur | identifiant `admin`, mot de passe `admin123` |
| Association initiale | « AVEC Bukavu » (renommable dans la base) |

**Important : au premier login avec `admin123`, l'application EXIGE
le choix d'un nouveau mot de passe.** Le mot de passe d'usine ne peut
pas être conservé. Choisissez-en un que les responsables mémoriseront.

---

## 6. Connexion

- Lancez AkibaCore → saisissez votre identifiant et mot de passe.
- Après **5 mots de passe faux**, le compte est bloqué 30 secondes.
- La date, votre nom et votre rôle s'affichent en haut de la fenêtre.
- Pour quitter votre session : bouton « Se déconnecter » en bas à droite.

Trois rôles existent :

| Rôle | Droits |
|---|---|
| **admin** | Tout : opérations + utilisateurs + sauvegarde + paramètres |
| **agent** | Opérations courantes : membres, épargnes, crédits, remboursements, sessions, rapports |
| **lecteur** | Consultation uniquement (aucun bouton d'action visible) |

---

## 7. Gestion des utilisateurs

Seul un **admin** crée les comptes (voir GUIDE_ADMINISTRATEUR.md pour la
procédure détaillée). Recommandation : un compte `admin` pour les
responsables, un compte `agent` par caissier, `lecteur` pour les
consultations publiques en réunion.

Chaque utilisateur change son propre mot de passe via le bouton
**« Changer mot de passe »** en bas de la fenêtre.

---

## 8. Gestion des membres

Onglet **Membres** :

- **+ Ajouter** : nom (obligatoire), prénom, téléphone, adresse, numéro,
  nombre de parts, notes. Les accents et noms composés sont gérés
  correctement (ex. *M'Vuzekeli Bénédicte*).
- Recherche instantanée par nom ou numéro.
- Double-clic sur un membre : fiche complète + historique épargnes/crédits.
- Statuts : `actif` / `suspendu` / `sorti`.

---

## 9. Épargne

Onglet **Épargnes** → **+ Enregistrer dépôt** :

1. Choisir le membre, saisir le montant (FC) et la date.
2. Type : `ordinaire` / `solidarite` / `urgence`.
3. Le total des épargnes valides se met à jour immédiatement.

Une erreur ? Sélectionnez la ligne → **Annuler** : l'opération reste
dans l'historique marquée annulée (traçabilité complète).

---

## 10. Crédit

Onglet **Crédits** → **+ Octroyer crédit** :

- Montant, taux annuel (`0.10` = 10 %), durée en mois, date d'octroi.
- L'intérêt et le total à rembourser s'affichent **avant validation** :
  formule `Intérêt = Principal × Taux × Durée/12`.
- **Règle stricte : impossible d'accorder un crédit à un membre qui a
  déjà un crédit actif ou en retard.** Il doit d'abord être soldé.
- Échéance calculée automatiquement, années bissextiles gérées.

Statuts automatiques : `ACTIF` → `EN RETARD` (après échéance impayée)
→ `SOLDE` (remboursement complet). Un crédit peut aussi être annulé.

---

## 11. Remboursements

Onglet **Remboursements** → **+ Enregistrer paiement** :

1. Choisir membre → choisir le crédit (solde affiché).
2. Saisir le montant payé et la date.

L'application répartit automatiquement le paiement dans l'ordre légal :

```
1. Pénalité de retard   (2 % par mois de retard, calculée automatiquement)
2. Intérêts restants    (au prorata du restant dû)
3. Principal            (le reste)
```

Dès que le total atteint le montant dû, le crédit passe à **SOLDE**
et le membre peut demander un nouveau crédit.

---

## 12. Sessions

Onglet **Sessions** → **+ Nouvelle session** : date de la réunion
(la numérotation est automatique). Après la réunion, sélectionnez-la
→ **Clôturer**. Une session fermée ne peut plus être modifiée ni
clôturée deux fois.

---

## 13. Rapports

Onglet **Rapports** :

| Bouton | Résultat |
|---|---|
| Bilan financier | Synthèse affichée à l'écran |
| Membres / Épargnes / Crédits / Retards / Audit → CSV | Fichiers ouvrables dans Excel/LibreOffice (UTF-8, séparateur `;`) |
| Rapport complet → HTML | Page imprimable avec graphiques et tableaux |
| Sauvegarde base de données | Copie horodatée dans `sauvegardes/` |

Les exports CSV s'ouvrent directement dans Excel avec les accents corrects.

---

## 14. Sauvegarde

- **Automatique** : toutes les 30 minutes pendant l'utilisation, et à la fermeture.
- **Manuelle** : bouton « Sauvegarde base de données » (onglet Rapports).
- Les fichiers sont horodatés : `sauvegardes/akibacore_20260822_101500.db`.
- Rotation : les **15 dernières** sauvegardes sont conservées.

**Copiez régulièrement le dossier `sauvegardes/` sur une clé USB.**

---

## 15. Restauration

### Méthode automatique (si la base est endommagée)

Au démarrage, si `akibacore.db` est illisible, AkibaCore propose
lui-même de restaurer la dernière sauvegarde. Acceptez et tout revient.

### Méthode manuelle

1. Fermez AkibaCore.
2. Allez dans le dossier `sauvegardes/`.
3. Copiez la sauvegarde souhaitée (la plus récente généralement).
4. Collez-la dans le dossier principal sous le nom `akibacore.db`
   (remplacez l'ancien fichier).
5. Relancez AkibaCore : vos données correspondent à la sauvegarde.

Procédure détaillée : GUIDE_ADMINISTRATEUR.md, section Restauration.

---

## 16. Sécurité

- Mots de passe jamais stockés en clair : hachage PBKDF2-SHA256
  (100 000 itérations) + sel aléatoire.
- Blocage anti-force-brute : 5 essais → pause de 30 secondes.
- Mot de passe d'usine `admin123` doit être remplacé au premier login.
- Toutes les actions sensibles sont inscrites au journal d'audit
  (qui, quoi, quand) consultable et exportable.
- Base SQLite en mode WAL : aucune écriture partielle même en cas de
  coupure de courant (testé par interruption brutale).
- Fonctionne intégralement hors ligne : aucune donnée ne quitte l'ordinateur.

---

## 17. Dépannage

| Problème | Solution |
|---|---|
| « tkinter is missing » (Linux) | `sudo apt install python3-tk` |
| La fenêtre ne s'ouvre pas | Lancez depuis un terminal et notez le message |
| « Compte bloqué » | Attendez 30 secondes, puis réessayez |
| Mot de passe admin perdu | Restaurez une sauvegarde antérieure, ou un autre admin recrée le compte |
| Base corrompue au démarrage | Acceptez la restauration proposée, sinon voir section 15 |
| Chiffres bizarres après coupure | Vérifiez avec le bilan, restaurez la dernière sauvegarde si besoin |
| Excel affiche des symboles étranges | Ouvrez le CSV via Données → Importer en précisant UTF-8 |

Aucun message ne doit rester incompréhensible : en cas de problème,
la fenêtre explique toujours la marche à suivre.

---

## 18. Désinstallation

Supprimez simplement le dossier du programme.

**Avant de supprimer**, récupérez vos données :
copiez `akibacore.db` et le dossier `sauvegardes/` sur une clé USB.
La désinstallation ne touche à rien d'autre sur l'ordinateur.

---

## 19. Architecture technique (résumé)

| Aspect | Choix |
|---|---|
| Langage | Python ≥ 3.8, bibliothèque standard uniquement |
| Interface | Tkinter (inclus avec Python) |
| Base de données | SQLite mode WAL, clés étrangères activées, 8 tables, 8 index |
| Dépendances externes | **Aucune** — fonctionne sans Internet, sans pip |
| Structure | Application monofichier (`main.py`) |
| Packaging | PyInstaller (un exécutable autonome par système) |

Tables : `utilisateur`, `avec`, `membre`, `session`, `epargne`,
`credit`, `remboursement`, `audit_log`.

---

## 20. Tests

Le logiciel est livré avec **192 tests automatisés** (unitaires et
métier), tous passants :

```bash
python3 test_finance.py      # 61 tests — moteurs financiers et authentification
python3 test_complet.py      # 131 tests — scénarios complets, sécurité, sauvegardes
# ou : make test
```

Validation v2.0.0 effectuée sur Linux : parcours utilisateur complet
(22 étapes en interface réelle), trois rôles, interruption brutale,
base corrompue, performance sur 150 membres / 500 crédits / 2000
remboursements, exécutable autonome. Détails : `RELEASE_NOTES_v2.0.0.md`.

---

*Livraison v2.0.0 — voir RELEASE_NOTES_v2.0.0.md pour l'historique complet.*
