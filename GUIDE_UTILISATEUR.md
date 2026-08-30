# GUIDE UTILISATEUR — AkibaCore v2.2.0

Manuel pas-à-pas pour l'utilisation quotidienne d'AkibaCore.
À imprimer et garder à portée de main lors des réunions.

---

## Sommaire

1. [Créer un membre](#1-créer-un-membre)
2. [Enregistrer une épargne](#2-enregistrer-une-épargne)
3. [Accorder un crédit](#3-accorder-un-crédit)
4. [Enregistrer un remboursement](#4-enregistrer-un-remboursement)
5. [Suivre les comptes membres](#5-suivre-les-comptes-membres)
6. [Clôturer une session (réunion)](#6-clôturer-une-session-réunion)
7. [Générer un rapport](#7-générer-un-rapport)
8. [Imprimer les reçus](#8-imprimer-les-reçus)
9. [Générer un document à partir d'un modèle](#9-générer-un-document-à-partir-dun-modèle)
10. [Sauvegarder les données](#10-sauvegarder-les-données)
11. [Restaurer une sauvegarde](#11-restaurer-une-sauvegarde)
12. [Changer mon mot de passe](#12-changer-mon-mot-de-passe)
13. [Administration : utilisateurs et droits](#13-administration--utilisateurs-et-droits)

---

## 1. Créer un membre

**Quand ?** Lorsqu'une nouvelle personne adhère à l'AVEC.

1. Connectez-vous (rôle `admin` ou `agent`).
2. Cliquez sur **Membres** dans la colonne de gauche.
3. Cliquez sur le bouton **+ Ajouter**.
4. Remplissez la fiche :

   | Champ | Obligatoire ? | Conseil |
   |---|---|---|
   | Nom | **Oui** | Tel qu'écrit sur sa pièce d'identité |
   | Prénom | Conseillé | — |
   | Téléphone | Conseillé | Format libre : `+243 99 123 4567` |
   | N° Membre | Conseillé | Suivez la numérotation de l'association : 001, 002… |
   | Nombre de parts | Oui (défaut 1) | Nombre de parts sociales souscrites |
   | Adhésion | Oui (date du jour) | Modifiable si adhésion antérieure |

5. Cliquez **Enregistrer**. Le membre apparaît dans la liste.

**Vérifier ensuite :** tapez son nom dans la zone de recherche pour
le retrouver, puis double-cliquez pour voir sa fiche complète
(épargnes et crédits y apparaîtront au fil du temps).

**Erreur de saisie ?** Sélectionnez le membre → **Modifier**, corrigez,
ré-enregistrez. Pour un départ définitif, mettez son statut à `sorti`
(ne jamais supprimer : l'historique financier doit être conservé).

---

## 2. Enregistrer une épargne

**Quand ?** À chaque dépôt d'épargne, idéalement pendant la réunion.

1. Onglet **Épargnes** → bouton **+ Enregistrer dépôt**.
2. Choisissez le membre dans la liste déroulante.
3. Saisissez le **montant** (chiffres seulement ; virgule acceptée :
   `50000` ou `50 000,50`), dans la **devise** de votre AVEC
   (CDF, ou USD si l'AVEC l'autorise) : la devise se choisit avant
   l'enregistrement.
4. Vérifiez la date (celle du jour est proposée).
5. Choisissez le type :
   - `ordinaire` : épargne classique hebdomadaire/mensuelle ;
   - `solidarite` : caisse de solidarité ;
   - `urgence` : fonds d'urgence.
6. Cliquez **Enregistrer**.

Le total affiché en haut de l'onglet augmente immédiatement.

À la validation, l'application propose **Imprimer / Voir / PDF** un
**reçu** numéroté (`REC-AAAA-NNNNNN`) de vérification du dépôt.

**Annuler une erreur** (mauvais montant, mauvais membre) :

1. Cliquez sur la ligne concernée dans le tableau.
2. Bouton **Annuler le dépôt** → confirmez.
3. La ligne reste visible marquée `ANNULÉ` et le total diminue.
   Rien n'est effacé : la traçabilité est préservée.

---

## 3. Accorder un crédit

**Avant tout :** le membre ne doit avoir **aucun crédit actif ni en
retard**. L'application le vérifie et refusera sinon — c'est une règle
de protection de l'association.

1. Onglet **Crédits** → **+ Octroyer crédit**.
2. Choisissez le membre.
3. Saisissez :
   - **Montant principal** (ex. `100000`) ;
   - **Taux annuel** en décimal : `0.10` = 10 % par an ;
   - **Durée** en mois (ex. `12`) ;
   - Date d'octroi (jour même par défaut).
4. **Lisez l'aperçu bleu** sous le formulaire :

   ```
   Intérêt : 10,000 CDF  |  Total : 110,000 CDF
   ```

   Formule : Intérêt = Principal × Taux × Durée ÷ 12.
   Choisissez aussi la **devise** du crédit (CDF par défaut) et le
   **type** (Ordinaire / Urgence / Investissement) : le **taux affiché
   est celui du type retenu** (configuré par l'administrateur) et sera
   **figé** pour toute la durée du crédit, même si l'AVEC change ses
   paramètres par la suite.
5. Cliquez **Octroyer**. Une confirmation récapitule tout, y compris
   la **date d'échéance** calculée automatiquement.

**Statuts que vous verrez :**

| Statut | Signification |
|---|---|
| ACTIF | En cours, pas encore d'échéance dépassée |
| EN RETARD | Échéance dépassée, solde non payé (pénalités en cours) |
| SOLDE | Entièrement remboursé |
| ANNULÉ | Annulé par l'association |

La liste se met à jour toute seule à chaque ouverture de l'onglet.

L'octroi d'un crédit produit automatiquement son **reçu** (imprimer /
voir / PDF) avec montant, intérêt, total à rembourser et échéance.

---

## 4. Enregistrer un remboursement

**Quand ?** À chaque versement du membre, même partiel.

1. Onglet **Remboursements** → **+ Enregistrer paiement**.
2. Choisissez le membre (seuls ceux ayant un crédit en cours sont listés).
3. Choisissez le crédit — le solde restant s'affiche.
4. Saisissez le **montant payé** et la date.
5. Cliquez **Enregistrer**. Une confirmation détaille la répartition :

```
Principal  : 545 CDF
Intérêt    : 55 CDF
Pénalité   : 0 CDF
Statut crédit : ACTIF
```

**Comment le paiement est réparti automatiquement :**

```
1) Pénalité de retard   → 2 % du solde par MOIS de retard complet
                          (affichée en rouge avant validation)
                          — taux figé à l'octroi du crédit
2) Intérêts restants    → au prorata du restant dû
3) Principal            → tout le reste
```

Vous n'avez aucun calcul à faire : saisissez uniquement le total versé.

**Dernier versement :** dès que le cumul atteint le montant total dû,
le crédit passe automatiquement à **SOLDE**. Le membre peut alors
demander un nouveau crédit.

Le reçu de remboursement détaille la répartition exacte (pénalité /
intérêt / principal / solde restant).

---

## 5. Suivre les comptes membres

L'onglet **Comptes** regroupe tous les comptes de chaque membre, par type
(**épargne**, **courant**, **bloqué**, **crédit**) et par **devise**
(CDF / USD) :

1. Le tableau montre le solde et le **statut** de chaque compte
   (`Actif`, `Bloqué`, `Suspendu`).
2. Sélectionnez un compte puis **Bloquer** / **Débloquer** /
   **Suspendre** / **Réactiver** pour en changer l'accès : un comprise
   bloqué ne peut plus recevoir de nouvelles opérations tant qu'il
   n'est pas débloqué.
3. **Détail** (ou double-clic) ouvre la fiche du compte : informations,
   historique des **événements** (blocage, déblocage, suspension…) et
   des **mouvements** (pour les comptes courant et bloqué).
4. La case **Rechercher** filtre par nom et la liste **Devise** par
   monnaie — les totaux sont **toujours calculés par devise**.

---

## 6. Clôturer une session (réunion)

Les sessions servent à numéroter les réunions et rattacher les opérations.

1. **Avant/après la réunion** : onglet **Sessions** → **+ Nouvelle session**.
2. Saisissez la date (proposée : aujourd'hui). Le numéro s'attribue seul
   (1, 2, 3…). Vous pouvez ajouter une note (ordre du jour, effectif…).
3. **À la fin de la réunion** : cliquez sur la session dans le tableau,
   puis **Clôturer** → confirmez.

⚠ Une session fermée ne peut plus être rouverte ni clôturée deux fois :
l'application le refuse proprement.

---

## 7. Générer un rapport

Onglet **Rapports** — tous les boutons enregistrent un fichier que vous
choisissez où placer (bureau, clé USB…).

| Besoin | Cliquer sur |
|---|---|
| Voir la situation financière globale | **Bilan financier** (affiché à l'écran) |
| Liste des membres pour Excel | **Membres → CSV** |
| Journal des dépôts | **Épargnes → CSV** |
| État des prêts | **Crédits → CSV** |
| Relancer les retardataires | **Crédits en retard → CSV** (avec jours de retard) |
| Prouver les actions en assemblée | **Journal d'audit → CSV** |
| Document imprimable officiel avec graphiques | **Rapport complet → HTML** |

**Imprimer le rapport HTML :** double-cliquez sur le fichier créé — il
s'ouvre dans votre navigateur → Ctrl+P → Imprimer (ou « Enregistrer en PDF »).

Les fichiers CSV s'ouvrent dans Excel/LibreOffice avec accents corrects.

---

## 8. Imprimer les reçus

Dès qu'un dépôt, un crédit ou un remboursement est enregistré, une
fenêtre propose **trois choix** :

| Bouton | Que se passe-t-il ? |
|---|---|
| **Imprimer** | Envoie le reçu à l'imprimante (format A6). Si l'option « impression automatique » est active dans **Paramètres**, rien à cliquer : le reçu sort tout seul. |
| **Voir** | Affiche un aperçu du reçu à l'écran, puis imprimable. |
| **Enregistrer en PDF** | Crée `documents/recus/REC-AAAA-NNNNNN.pdf` (le dossier est créé automatiquement). |

**Numérotation :** chaque reçu porte un numéro unique du type
`REC-2026-000012`. Un numéro donné n'est **jamais** réattribué, même
après suppression : les registres restent cohérents.

**Réimprimer un reçu :** onglet **Documents → Reçus** — sélectionnez
le reçu puis **Réimprimer** à tout moment.

---

## 9. Générer un document à partir d'un modèle

Votre AVEC peut utiliser ses propres documents officiels (attestation,
relevé, PV de réunion, rapport financier) préparés dans **Word (DOCX),
LibreOffice (ODT), ou un simple fichier HTML/TXT**.

**Importer un modèle :** onglet **Documents → Modèles → + Importer**,
puis choisir le fichier. Les champs `{{...}}` y sont remplacés
automatiquement par AkibaCore :

- Informations de l'AVEC : `{{AVEC_NOM}}`, `{{AVEC_ADRESSE}}`,
  `{{AVEC_TELEPHONE}}`, `{{AVEC_EMAIL}}`, `{{AVEC_DEVISE}}` ;
- Membre : `{{MEMBRE_NOM}}`, `{{MEMBRE_PRENOM}}`, `{{MEMBRE_NUMERO}}`,
  `{{MEMBRE_TELEPHONE}}`, `{{MEMBRE_PARTS}}` ;
- Operation/reçu : `{{RECU_NUMERO}}`, `{{TYPE_OPERATION}}`,
  `{{MONTANT}}`, `{{DATE}}`, `{{HEURE}}` ;
- Crédit : `{{CREDIT_NUMERO}}`, `{{PRINCIPAL}}`, `{{INTERET}}`,
  `{{PENALITE}}`, `{{SOLDE}}`, `{{SESSION_NUMERO}}`.

**Définir un modèle par défaut** par type de document (Reçu, Attestation,
Rapport financier, Relevé membre, Bilan, Procès-verbal) : onglet
**Modeles → Définir comme modèle par défaut**. La prochaine génération
de ce type utilisera automatiquement votre modèle.

**Générer :** Documents → **Générer un document** → choisissez le type,
le membre/contexte (montant, crédit) puis **Générer**. Vous pouvez
**Prévisualiser**, **Imprimer**, **Exporter en PDF** ou retrouver le
document dans l'historique `document_genere`.

---

## 10. Sauvegarder les données

AkibaCore sauvegarde déjà **automatiquement toutes les 30 minutes**
et **à chaque fermeture**. Mais après une réunion importante :

1. Onglet **Rapports** → **Sauvegarde base de données**.
2. Message confirmant : `Base de données sauvegardée : sauvegardes/akibacore_…db`.

**Règle d'or : copiez le dossier `sauvegardes/` entier sur une clé USB
après chaque réunion.** Un ordinateur peut tomber en panne ; une clé USB
rangée ailleurs ne tombe jamais en panne en même temps.

Les 15 dernières sauvegardes sont gardées automatiquement, les plus
anciennes sont supprimées pour ne pas remplir le disque.

---

## 11. Restaurer une sauvegarde

**Cas 1 — L'application propose elle-même la restauration.**
Si au démarrage un message annonce que la base est endommagée et propose
« restaurer la dernière sauvegarde », acceptez. C'est terminé.

**Cas 2 — Restauration manuelle** (ordinateur changé, retour arrière souhaité) :

1. Fermez AkibaCore.
2. Ouvrez le dossier `sauvegardes/`.
3. Repérez la sauvegarde voulue — les noms contiennent la date :
   `akibacore_20260822_101500.db` = 22/08/2026 à 10h15.
4. Copiez ce fichier dans le dossier principal.
5. Renommez la copie exactement `akibacore.db`
   (acceptez de remplacer l'existant).
6. Supprimez aussi, s'ils existent, `akibacore.db-wal` et `akibacore.db-shm`.
7. Relancez AkibaCore : vos données sont celles de la sauvegarde.

---

## 12. Changer mon mot de passe

1. Bouton **Changer mot de passe** en bas de la fenêtre.
2. Saisissez votre mot de passe actuel.
3. Saisissez deux fois le nouveau (minimum 4 caractères).
4. Confirmez : « Mot de passe modifié ».

Conseils : choisissez quelque chose de mémorisable mais non évident
(évitez `1234`, le nom de l'association, la date du jour). Ne l'écrivez
jamais sur un papier laissé près de l'ordinateur ; confiez-le plutôt à
deux responsables différents.

**Oubli total ?** Seul un administrateur peut recréer un compte
(GUIDE_ADMINISTRATEUR.md). S'il n'y a qu'un compte admin perdu,
restaurez une sauvegarde antérieure à la perte.

---

* Aide-mémoire : Membre → Épargne → Crédit → Remboursement → Session →
Rapport → Sauvegarde. Chaque opération est tracée dans le journal d'audit.*

---

## 13. Administration : utilisateurs et droits

Réservée aux comptes disposant de la permission (`users.*`,
généralement l'administrateur) : onglet **Administration**.

### Utilisateurs
L'onglet **Utilisateurs** affiche tous les comptes (nom, identifiant,
rôle, statut, AVEC). Les boutons d'action :

| Bouton | Effet |
|---|---|
| **+ Nouvel utilisateur** | Crée un compte : nom, identifiant, mot de passe (jamais le mot de passe usine), rôle, AVEC. |
| **Modifier** | Change le nom, le rôle, l'AVEC d'un compte. |
| **Permissions** | Ajoute/retire des permissions individuelles (en plus de celles du rôle). |
| **Rôles** | Crée/modifie/supprime des ensembles de permissions sur mesure. |
| **Activer/Désactiver** | Bloque/relance la connexion d'un compte sans perdre son historique. (On ne peut pas désactiver son propre compte.) |
| **Réinitialiser mdp** | Impose un nouveau mot de passe à un compte. |

### Journal d'activité (audit)
L'onglet **Journal d'activité** liste chronologiquement toutes les
opérations sensibles (connexions, ajouts, dépôts, crédits,
remboursements, sauvegardes, refus d'accès…), filtrables par utilisateur
et exportables en CSV.

> Tout changement de droits, de taux ou de paramètres est enregistré :
> on sait toujours qui a fait quoi et quand.

---

*Aide-mémoire : Membre → Épargne → Crédit → Remboursement → Session →
Rapport → Sauvegarde. Chaque opération est tracée dans le journal d'audit.*
