# AkibaCore — Système de Gestion AVEC
## Version 2.0.0 | Production Ready | 100% Offline

---

## PRÉSENTATION

**AkibaCore** est un logiciel de gestion financière professionnel conçu spécifiquement
pour les Associations Villageoises d'Épargne et de Crédit (AVEC) opérant dans des
environnements à faible connectivité, notamment en Afrique centrale.

Le nom **Akiba** signifie "épargne" en swahili — langue dominante dans la région des Grands Lacs.

---

## ARCHITECTURE DU PROJET

```
AkibaCore/
├── main.py              # Application principale (point d'entrée unique)
├── akibacore.db         # Base de données SQLite (créée au premier lancement)
├── sauvegardes/         # Sauvegardes automatiques (créé automatiquement)
├── README.md            # Ce fichier
└── requirements.txt     # Dépendances Python
```

---

## PRÉREQUIS

- Python 3.8 ou supérieur
- Tkinter (inclus par défaut dans Python sur Windows et macOS)
- Aucune connexion Internet requise

### Vérifier Python

```bash
python --version
# ou
python3 --version
```

---

## INSTALLATION

### Windows

```bash
# 1. Installer Python depuis python.org (cocher "Add to PATH")
# 2. Ouvrir un terminal (cmd ou PowerShell) dans le dossier AkibaCore
python main.py
```

### Linux (Ubuntu / Debian / Linux Mint)

```bash
# Installer les dépendances système
sudo apt update
sudo apt install python3 python3-tk -y

# Lancer l'application
python3 main.py
```

### Créer un raccourci de lancement (Linux)

```bash
# Créer un script de lancement
echo '#!/bin/bash
cd "$(dirname "$0")"
python3 main.py' > lancer_akibacore.sh
chmod +x lancer_akibacore.sh
```

---

## PREMIER LANCEMENT

Au premier démarrage, l'application crée automatiquement :
- La base de données `akibacore.db`
- Un compte administrateur par défaut :
  - **Identifiant :** `admin`
  - **Mot de passe :** `admin123`
- Une AVEC par défaut : "AVEC Bukavu"

**IMPORTANT :** Changez le mot de passe administrateur dès le premier lancement
via la barre inférieure > "Changer mot de passe".

---

## FONCTIONNALITÉS

### Tableau de Bord
- Vue synthétique : membres, épargnes totales, portefeuille crédit, remboursements
- Indicateur des crédits en retard (alerte visuelle rouge)
- Journal des 20 dernières actions

### Membres
- Ajout, modification, consultation des membres
- Numéro de membre, téléphone, adresse, nombre de parts
- Fiche détaillée : historique épargnes + historique crédits
- Recherche en temps réel
- Statuts : Actif / Suspendu / Sorti

### Épargnes
- Enregistrement des dépôts (ordinaire, solidarité, urgence)
- Annulation d'une opération (traçabilité conservée)
- Total des épargnes valides affiché en temps réel

### Crédits
- Octroi avec calcul automatique des intérêts (intérêt simple)
- Détection automatique du membre ayant déjà un crédit actif
- Statuts automatiques : Actif / En retard / Soldé / Annulé
- Aperçu instantané intérêt + total avant validation

### Remboursements
- Imputation automatique : pénalité → intérêt → principal
- Calcul automatique des pénalités de retard (2 %/mois)
- Indication du nombre de jours de retard
- Mise à jour automatique du statut du crédit

### Sessions / Réunions
- Création et clôture des sessions de réunion
- Numérotation automatique des sessions
- Historique complet

### Rapports & Exports
- Bilan financier complet (affiché en temps réel)
- Export CSV : membres, épargnes, crédits, crédits en retard, journal d'audit
- Rapport HTML complet (imprimable, avec tableau de bord visuel)
- Sauvegarde manuelle de la base de données
- Sauvegarde automatique toutes les 30 minutes

### Sécurité
- Authentification par identifiant + mot de passe (hash SHA-256 + sel)
- Journal d'audit complet de toutes les actions
- Intégrité référentielle SQLite (clés étrangères activées)
- Mode WAL (Write-Ahead Logging) pour la fiabilité des écritures
- Sauvegardes automatiques (rotation sur 15 fichiers)

---

## CALCULS FINANCIERS

| Paramètre       | Valeur par défaut | Formule                              |
|-----------------|-------------------|--------------------------------------|
| Intérêt crédit  | 10 % / an         | Principal × Taux × (Durée / 12)      |
| Pénalité retard | 2 % / mois        | Solde × 2 % × (Jours retard / 30)    |
| Imputation      | Pénalité → Intérêt → Principal (ordre légal) |

---

## SAUVEGARDE DES DONNÉES

Les sauvegardes automatiques sont stockées dans le dossier `sauvegardes/`
avec horodatage : `akibacore_AAAAMMJJ_HHMMSS.db`

Les 15 dernières sauvegardes sont conservées (les plus anciennes sont supprimées).

Pour restaurer une sauvegarde, copiez le fichier `.db` souhaité et renommez-le
en `akibacore.db` dans le dossier principal.

---

## COMPTES UTILISATEURS

| Rôle     | Droits                                          |
|----------|-------------------------------------------------|
| admin    | Tous les droits (gestion + exports + paramètres)|
| agent    | Opérations courantes (membres, transactions)    |
| lecteur  | Consultation uniquement                         |

La gestion multi-utilisateurs est possible via la base de données SQLite partagée
sur un réseau local (partage de fichiers Windows/Samba).

---

## SUPPORT TECHNIQUE

En cas de problème :
1. Vérifiez que Python 3.8+ est installé : `python --version`
2. Sous Linux, vérifiez que tkinter est présent : `python3 -m tkinter`
3. Si la base de données est corrompue, restaurez depuis `sauvegardes/`
