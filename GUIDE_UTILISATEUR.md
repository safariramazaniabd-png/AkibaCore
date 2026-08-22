# GUIDE UTILISATEUR — AkibaCore v2.0.0

Manuel pas-à-pas pour l'utilisation quotidienne d'AkibaCore.
À imprimer et garder à portée de main lors des réunions.

---

## Sommaire

1. [Créer un membre](#1-créer-un-membre)
2. [Enregistrer une épargne](#2-enregistrer-une-épargne)
3. [Accorder un crédit](#3-accorder-un-crédit)
4. [Enregistrer un remboursement](#4-enregistrer-un-remboursement)
5. [Clôturer une session (réunion)](#5-clôturer-une-session-réunion)
6. [Générer un rapport](#6-générer-un-rapport)
7. [Sauvegarder les données](#7-sauvegarder-les-données)
8. [Restaurer une sauvegarde](#8-restaurer-une-sauvegarde)
9. [Changer mon mot de passe](#9-changer-mon-mot-de-passe)

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
3. Saisissez le **montant en FC** (chiffres seulement ; virgule acceptée :
   `50000` ou `50 000,50`).
4. Vérifiez la date (celle du jour est proposée).
5. Choisissez le type :
   - `ordinaire` : épargne classique hebdomadaire/mensuelle ;
   - `solidarite` : caisse de solidarité ;
   - `urgence` : fonds d'urgence.
6. Cliquez **Enregistrer**.

Le total affiché en haut de l'onglet augmente immédiatement.

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
   Intérêt : 10,000 FC  |  Total : 110,000 FC
   ```

   Formule : Intérêt = Principal × Taux × Durée ÷ 12.
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

---

## 4. Enregistrer un remboursement

**Quand ?** À chaque versement du membre, même partiel.

1. Onglet **Remboursements** → **+ Enregistrer paiement**.
2. Choisissez le membre (seuls ceux ayant un crédit en cours sont listés).
3. Choisissez le crédit — le solde restant s'affiche.
4. Saisissez le **montant payé** et la date.
5. Cliquez **Enregistrer**. Une confirmation détaille la répartition :

```
Principal  : 545 FC
Intérêt    : 55 FC
Pénalité   : 0 FC
Statut crédit : ACTIF
```

**Comment le paiement est réparti automatiquement :**

```
1) Pénalité de retard   → 2 % du solde par MOIS de retard complet
                          (affichée en rouge avant validation)
2) Intérêts restants    → au prorata du restant dû
3) Principal            → tout le reste
```

Vous n'avez aucun calcul à faire : saisissez uniquement le total versé.

**Dernier versement :** dès que le cumul atteint le montant total dû,
le crédit passe automatiquement à **SOLDE**. Le membre peut alors
demander un nouveau crédit.

---

## 5. Clôturer une session (réunion)

Les sessions servent à numéroter les réunions et rattacher les opérations.

1. **Avant/après la réunion** : onglet **Sessions** → **+ Nouvelle session**.
2. Saisissez la date (proposée : aujourd'hui). Le numéro s'attribue seul
   (1, 2, 3…). Vous pouvez ajouter une note (ordre du jour, effectif…).
3. **À la fin de la réunion** : cliquez sur la session dans le tableau,
   puis **Clôturer** → confirmez.

⚠ Une session fermée ne peut plus être rouverte ni clôturée deux fois :
l'application le refuse proprement.

---

## 6. Générer un rapport

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

## 7. Sauvegarder les données

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

## 8. Restaurer une sauvegarde

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

## 9. Changer mon mot de passe

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

*Aide-mémoire : Membre → Épargne → Crédit → Remboursement → Session →
Rapport → Sauvegarde. Chaque opération est tracée dans le journal d'audit.*
