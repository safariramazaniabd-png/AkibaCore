# GUIDE D'INSTALLATION WINDOWS — AkibaCore v2.2.0

Système de gestion financière pour Associations Villageoises d'Épargne
et de Crédit (AVEC). **100 % hors ligne** — aucune connexion Internet
requise.

Deux façons d'installer selon ce que vous avez reçu.

---

## OPTION A — Installateur (recommandé)

Fichier : **AkibaCore_Setup_v2.2.0_Windows_x64.exe**

1. **Téléchargez** le fichier `AkibaCore_Setup_v2.2.0_Windows_x64.exe`
   sur le PC (par exemple sur le Bureau).
2. **Double-cliquez** sur le fichier.
   - Si Windows affiche « Windows a protégé votre PC », cliquez sur
     **Plus d'informations** → **Exécuter quand même** (le logiciel est
     signé par nos soins ; il est sûr).
3. L'**assistant d'installation** s'ouvre. Cliquez **Suivant** jusqu'au bout.
4. À la fin, laissez la case « Lancer AkibaCore » cochée et cliquez
   **Terminer**.
5. Des **raccourcis** sont créés automatiquement :
   - sur le **Bureau** ;
   - dans le **Menu Démarrer** → AkibaCore.
6. L'application s'ouvre sur l'écran de **connexion**.

**Première connexion :**
- Identifiant : `admin`
- Mot de passe : `admin123`
- L'application vous impose immédiatement de **choisir un nouveau mot
  de passe**. C'est normal et voulu.

### Où sont mes données ?

L'application est installée dans `C:\Program Files\AkibaCore\` (dossier
protégé en écriture par Windows). **Vos données** (la base `akibacore.db`,
les sauvegardes, les documents) sont automatiquement placées dans votre
dossier utilisateur, ici :

```
C:\Users\VotreNom\AppData\Local\AkibaCore\
    ├── akibacore.db
    ├── sauvegardes\
    ├── documents\
    ├── modeles\
    ├── exports\
    └── logs\
```

AkibaCore le fait tout seul dès le premier lancement. Vous n'avez rien
à configurer.

### Désinstallation

- **Menu Démarrer** → dossier AkibaCore → **Désinstaller AkibaCore**.
- La désinstallation ne supprime **jamais** vos données (dossier
  utilisateur ci-dessus). Elles restent intactes.

---

## OPTION B — Version portable (sans installation)

Fichier : **AkibaCore_Portable_v2.2.0_Windows.zip**

1. **Double-cliquez** sur le ZIP → **Extraire tout**.
2. Choisissez un dossier de destination (par exemple `Mes Documents`).
3. Ouvrez le dossier extrait `AkibaCore_Portable\` puis `AkibaCore\`.
4. **Double-cliquez sur `AkibaCore.exe`**.
5. Connectez-vous avec `admin` / `admin123`, puis changez le mot de passe.

Dans la version portable, **toutes les données restent à côté de
l'exécutable** dans le dossier portable :

```
AkibaCore\
    ├── AkibaCore.exe
    ├── data\
    ├── sauvegardes\
    ├── documents\
    ├── modeles\
    ├── exports\
    └── logs\
```

Vous pouvez copier tout le dossier sur une clé USB : il fonctionne sur
n'importe quel PC Windows 10/11. Aucune installation requise.

---

## Vérification des fichiers téléchargés

Le fichier `SHA256SUMS.txt` contient l'empreinte (hash) de chaque
fichier livré. Vous pouvez vérifier l'intégrité avec :

```powershell
Get-FileHash "AkibaCore_Setup_v2.2.0_Windows_x64.exe" -Algorithm SHA256
```

Comparez le résultat avec la valeur indiquée dans `SHA256SUMS.txt`.

---

## Configurer son AVEC après connexion

1. Onglet **Paramètres** → renseignez le **nom**, l'**adresse**, le
   **téléphone** et le **logo** de votre AVEC.
2. Dans la section **Financiers**, choisissez la **devise principale**
   (CDF ou USD) et les devises autorisées.
3. Créez vos utilisateurs : onglet **Administration** → Utilisateurs.
4. Commencez à saisir vos **membres** : onglet **Membres** → Ajouter.

---

## Problèmes fréquents

| Problème | Solution |
|---|---|
| « Windows a protégé votre PC » | Plus d'informations → Exécuter quand même |
| Aucune imprimante disponible | L'impression des reçus est ignorée sans erreur : utilisez « Voir » ou « PDF » |
| Mot de passe admin oublié | Restaurez une sauvegarde antérieure au changement |

En cas de doute, conservez toujours une copie du dossier
`sauvegardes\`. L'application sauvegarde automatiquement toutes les
30 minutes et à la fermeture.
