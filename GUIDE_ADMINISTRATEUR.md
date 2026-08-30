# GUIDE ADMINISTRATEUR — AkibaCore v2.2.0

Manuel des responsables : comptes, permissions, sauvegardes,
maintenance et sécurité. À lire intégralement avant la mise en service.

---

## Sommaire

1. [Première mise en service](#1-première-mise-en-service)
2. [Gestion des utilisateurs](#2-gestion-des-utilisateurs)
3. [Rôles et permissions](#3-rôles-et-permissions)
4. [Politique de sauvegarde](#4-politique-de-sauvegarde)
5. [Restauration](#5-restauration)
6. [Paramètres financiers (onglet Paramètres → section « Financiers »)](#6-paramètres-financiers-onglet-paramètres--section--financiers-)
7. [Maintenance périodique](#7-maintenance-périodique)
7. [Sécurité](#7-sécurité)
8. [Dépannage avancé](#8-dépannage-avancé)

---

## 1. Première mise en service

1. Installez AkibaCore (README.md, sections 3-4).
2. Lancez l'application : la base `akibacore.db` se crée automatiquement.
3. Connectez-vous avec `admin` / `admin123`.
4. **L'application impose immédiatement un nouveau mot de passe** —
   c'est normal et voulu. Choisissez-le solide et notez-le dans le
   registre papier scellé de l'association (jamais sur l'ordinateur).
5. Renommez l'association par défaut si besoin :
   `sqlite3 akibacore.db "UPDATE avec SET nom='AVEC …' WHERE id=1;"`
   (à faire par une personne à l'aise, application fermée).
6. Créez les comptes de l'équipe (section 2).
7. Faites une première sauvegarde manuelle (Rapports → Sauvegarde).
8. Testez la restauration **une fois à vide** pour savoir le faire
   le jour où ce sera nécessaire (sur une copie, jamais directement).

---

## 2. Gestion des utilisateurs

Depuis la v2.1, tout se gère **dans l'application**, onglet
**Administration → Utilisateurs** (réservé à `admin`/permission
`users.*`) :

- **+ Nouvel utilisateur** : nom, identifiant, mot de passe (jamais le
  mot de passe usine), rôle, AVEC, compte actif.
- **Modifier** : nom, rôle, AVEC, statut du compte.
- **Permissions** : ajuste les permissions individuelles du compte
  (par-dessus celles de son rôle).
- **Rôles** : crée/modifie/supprime des rôles sur mesure (ensembles de
  permissions) ; les 7 rôles prédéfinis ne sont pas supprimables.
- **Activer/Désactiver** : bloque la connexion sans perdre l'historique.
- **Réinitialiser mdp** : impose un mot de passe de remplacement
  (interdiction de revenir au mot de passe usine).

Chaque action est consignée au journal d'activité (`CREER_UTILISATEUR`,
`MODIFIER_UTILISATEUR`, `DESACTIVER_UTILISATEUR`, `REINITIALISER_MDP`,
`DEFINIR_PERMISSIONS`, …).

Un administrateur ne peut pas désactiver son propre compte.

En cas de maintenance d'urgence, les mêmes opérations restent
possibles en ligne de commande (application fermée) :

```bash
python3 -c "
from main import DB, Auth
import secrets, hashlib
db = DB()
login, mdp = 'agent_marie', 'UnMotDePasseSolide2026'
sel = secrets.token_hex(16)
ph  = hashlib.pbkdf2_hmac('sha256', f'{mdp}{sel}'.encode(), sel.encode(), 100000).hex()
db.exec('INSERT INTO utilisateur(nom,login,pwd_hash,sel,role,avec_id) VALUES(?,?,?,?,?,1)',
        ('Marie N.', login, ph, sel, 'agent'))
db.commit()
print('Compte créé :', login)
"
```

Désactiver : `sqlite3 akibacore.db "UPDATE utilisateur SET actif=0 WHERE login='agent_marie';"`
Un compte désactivé ne peut plus se connecter ; ses actions passées
restent dans le journal d'audit.

---

## 3. Rôles et permissions

### 3.1 Sept rôles prédéfinis

| Rôle | Domaine |
|---|---|
| **admin** | Toutes les permissions (42) |
| **agent** | Toutes les opérations courantes + reçus + sauvegarde manuelle + vue des comptes |
| **caissier** | Épargne, remboursements, reçus imprimés |
| **gestionnaire_credit** | Crédits et remboursements |
| **secretaire** | Membres, sessions, génération de documents |
| **auditeur** | Lecture + rapports + journal d'activité |
| **lecteur** | Consultation seule |

### 3.2 Permissions granulaires (42)

Chaque action métier correspond à une permission du type
`module.ressource.action`, regroupée par domaine :

- **Membres** : `members.view / create / edit`
- **Épargnes** : `savings.view / create / cancel`
- **Crédits** : `loans.view / create / edit / cancel`
- **Remboursements** : `repayments.view / create / cancel`
- **Comptes** : `accounts.view`, `accounts.block` (geler/réactiver les comptes)
- **Sessions** : `sessions.view / create / close`
- **Rapports** : `reports.view / generate / export`
- **Reçus** : `receipts.view / print / reprint`
- **Documents** : `documents.view / add_template / edit_template / delete_template / generate / print / export`
- **Utilisateurs** : `users.view / create / edit / disable / permissions`
- **Sauvegardes** : `backup.create / restore`
- **Audit / Paramètres** : `audit.view`, `settings.view / edit`, `settings.financial.edit` (taux, devises autorisées, types de crédit)

### 3.3 Garanties techniques (vérifiées par tests)

- Le rôle `admin` dispose de **toutes** les permissions, quel que soit le
  catalogue. Modifier le rôle d'un utilisateur met immédiatement à jour
  ses droits.
- Les autres comptes = permissions de leur **rôle** + permissions
  **individuelles** (`user_permission`). Les pages (onglets, boutons,
  actions) restent masquées ou inaccessibles en l'absence du droit.
- Le contrôle est **dans la logique métier**, pas seulement à l'écran :
  même en contournant l'interface, une action interdite est refusée et
  consignée au journal (`REFUS_ACTION` avec la permission concernée).
- Les onglets **Comptes**, **Administration**, **Documents** et
  **Paramètres** n'apparaissent dans la barre latérale que si le compte
  y a droit.

Recommandation AVEC : 1-2 comptes `admin` (président/trésorier),
un compte `caissier` par caissier (reçus), ou `agent`, un compte
`auditeur`/`lecteur` pour les consultations en assemblée.

---

## 4. Politique de sauvegarde

**Automatique (intégré) :**

| Déclencheur | Destination |
|---|---|
| Toutes les 30 min pendant l'utilisation | `sauvegardes/` |
| À chaque fermeture propre | `sauvegardes/` |
| Bouton manuel (onglet Rapports) | `sauvegardes/` |

Fichiers : `akibacore_AAAAMMJJ_HHMMSS.db`, rotation sur 15 fichiers.
Les sauvegardes intègrent un checkpoint WAL : même les écritures de la
minute écoulée sont incluses.

**Règles minimales recommandées :**

1. Copie USB **après chaque réunion** (le trésorier l'emporte).
2. Une copie conservée **hors du bâtiment** (chez un second responsable).
3. Vérification mensuelle : ouvrez une copie USB avec AkibaCore
   (copiez-la en `akibacore.db` dans un dossier de test) et comparez
   le bilan au registre papier.

**Ce qu'il ne faut pas faire :**

- Ne stockez jamais l'unique copie sur le même disque que l'application.
- N'utilisez pas de services cloud : le logiciel est conçu hors ligne
  et les données financières doivent rester sous contrôle de l'AVEC.

---

## 5. Restauration

### 5.1 Restauration assistée (base corrompue)

Si `akibacore.db` est corrompu, au démarrage l'application détecte le
problème et propose : *« Une sauvegardu … est disponible. Voulez-vous
la restaurer maintenant ? »*. Acceptez → la base est remplacée par la
dernière sauvegarde → l'application redémarre normalement.
La base endommagée est écrasée uniquement après votre confirmation.

### 5.2 Restauration manuelle

1. Fermez l'application.
2. `sauvegardes/` → repérez la sauvegarde cible (date dans le nom).
3. Copiez-la vers le dossier principal en remplaçant `akibacore.db`.
4. Supprimez les éventuels `akibacore.db-wal` et `akibacore.db-shm`.
5. Relancez et contrôlez : bilan financier, nombre de membres,
   dernières opérations.

### 5.3 Migration vers un nouvel ordinateur

1. Sur l'ancien : Rapports → Sauvegarde, puis fermez.
2. Copiez sur clé USB : `akibacore.db` **ou** la dernière sauvegarde.
3. Sur le nouveau : installez AkibaCore, lancez-le une fois, fermez-le.
4. Remplacez le `akibacore.db` neuf par celui de la clé USB (comme en 5.2).
5. Relancez, connectez-vous : tout y est (membres, comptes, historiques).

---

## 6. Paramètres financiers (onglet Paramètres → section « Financiers »)

Réservée aux comptes disposant de `settings.financial.edit`
(généralement les administrateurs), cette section contrôle la politique
financière de l'AVEC :

| Champ | Effet |
|---|---|
| **Taux d'intérêt** (Ordinaire / Urgence / Investissement) | % annuel appliqué à chaque **nouveau** crédit selon son type |
| **Taux de pénalité** | % mensuel de pénalité de retard par défaut |
| **Devises autorisées** | CDF et/ou USD acceptées dans les opérations |
| **Types de crédit** | types utilisables à l'octroi (Ordinaire, Urgence, Investissement…) |

**Règle essentielle : les taux sont figés à l'octroi.** Chaque crédit
mémorise son taux au moment de sa création (`taux_penalite` incluse) :
modifier ces paramètres par la suite **n'affecte jamais** les crédits
déjà accordés, il ne s'applique qu'aux nouveaux.

Chaque modification est consignée au journal avec l'ancienne et la
nouvelle valeur (`MODIFIER_PARAMS_FINANCIERS`).

---

## 7. Maintenance périodique

| Fréquence | Action |
|---|---|
| Chaque réunion | Sauvegarde manuelle + copie USB |
| Mensuelle | Test de restauration d'une sauvegarde ; revue du journal d'audit |
| Trimestrielle | Mise à jour des statuts membres (`suspendu`/`sorti`) ; vérification des crédits EN RETARD |
| Annuelle | Archivage des rapports HTML imprimés ; rotation des clés USB (remplacer les plus vieilles) |

**Intégrité de la base** (en cas de doute, application fermée) :

```bash
python3 -c "
import sqlite3
c = sqlite3.connect('akibacore.db')
print('intégrité :', c.execute('PRAGMA integrity_check').fetchone()[0])
print('clés étrangères :', 'OK' if not c.execute('PRAGMA foreign_key_check').fetchall() else 'PROBLÈME')
"
```

Résultat attendu : `intégrité : ok`.

---

## 8. Sécurité

**Mots de passe** : PBKDF2-SHA256, 100 000 itérations, sel unique par
compte. Aucun mot de passe n'apparaît en clair dans la base ni dans les
journaux. Le mot de passe d'usine est mort-né : il doit être changé au
premier login (imposé).

**Anti-intrusion local** : 5 échecs de connexion → verrouillage 30 s.
Les tentatives restent silencieuses dans les logs (pas de fuite d'indice).

**Journal d'audit** : chaque opération sensible est enregistrée
(connexion, ajout membre, dépôt, crédit, remboursement, export,
sauvegarde…) avec auteur, date et détails. Exportez-le régulièrement
(Rapports → Journal d'audit → CSV) et relisez-le en bureau.

**Données personnelles** : la base contient téléphones/adresses des
membres. L'ordinateur et les clés USB doivent être physiquement
sécurisés (armoire fermée, accès réservé aux responsables).

**Traçabilité technique :**
- Base SQLite en mode WAL + clés étrangères activées ;
- Toutes les requêtes paramétrées (aucune injection SQL possible via l'interface) ;
- Application 100 % locale : aucun envoi réseau, testé hors connexion.

---

## 9. Dépannage avancé

| Symptôme | Cause probable | Action |
|---|---|---|
| « Compte bloqué » répété | Quelqu'un essaie des mots de passe | Attendre 30 s ; identifier qui ; changer les mots de passe |
| Fenêtre ne s'ouvre plus après coupure | WAL non purgé (rare) | Rouvrir : WAL se rejoue seul. Sinon restauration 5.2 |
| Message « base illisible/corrompue » sans sauvegarde | Aucun backup disponible | NE PAS SUPPRIMER `akibacore.db`. Copier le dossier entier et consulter une personne compétente ; tenter `PRAGMA integrity_check` |
| Chiffres incohérents entre onglets | Statuts non recalculés | Rouvrir l'onglet Crédits (recalcul automatique) ; sinon redémarrer |
| Exports CSV vides | Aucune donnée correspondante | Normal si aucune ligne ; vérifier la période |
| Lenteur générale | Fichier base géant ou antivirus | Vérifier taille de `akibacore.db` (< 100 Mo = normal pendant des années) ; exclure le dossier de l'antivirus temps réel |
| Mot de passe admin unique perdu | — | Restaurer une sauvegarde **antérieure** au changement de mot de passe perdu |

**En dernier recours**, le dossier `sauvegardes/` contient jusqu'à 15
états successifs : vous pouvez revenir au plus proche état correct
(en comparant le bilan au registre papier).

---

*Pour toute intervention au-delà de ce guide (SQL direct, réparation),
faites appel à la personne ayant installé le logiciel — et gardez toujours
une sauvegarde AVANT toute manipulation.*
