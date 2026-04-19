# BCD Kids — Guide pour les enseignants

## À quoi ça sert ?

**BCD Kids** permet à vos élèves d'emprunter, rendre et réserver des livres de la bibliothèque **en totale autonomie**, sans avoir besoin de vous solliciter.

L'application fonctionne sur l'ordinateur de la bibliothèque (ou sur une tablette connectée au réseau de l'école). En quelques secondes, un élève peut gérer ses emprunts tout seul.

---

## Premier lancement

> À faire **une seule fois** à l'installation.

1. Assurez-vous que le **serveur BCD est démarré** sur l'ordinateur principal
2. Double-cliquez sur l'icône **BCD Kids** sur le bureau
3. L'application cherche automatiquement le serveur — patientez quelques secondes
4. Une fois connectée, ajustez les **réglages d'affichage** selon votre matériel (voir [Réglages](#réglages-️))

> 💡 Si la connexion échoue, consultez la section [En cas de problème](#en-cas-de-problème).

---

## Ce que voient vos élèves — pas à pas

### 1 — Choisir sa classe
Une grille affiche toutes les classes. L'élève appuie sur la sienne.

### 2 — Taper son prénom
L'élève tape les premières lettres de son prénom. La liste des correspondances apparaît. Si plusieurs élèves partagent le même prénom, ils choisissent leur nom complet dans la liste.

> ⚠️ Si le message **« Prénom non trouvé dans cette classe »** s'affiche, l'élève n'est probablement pas encore enregistré dans sa classe dans le logiciel de bibliothèque. Contactez le gestionnaire.

### 3 — Le menu personnel
L'élève voit ses livres en cours et accède à toutes les fonctions :

| Bouton | Ce que ça fait |
|---|---|
| 📖 EMPRUNTER UN LIVRE | Scanner le code-barres d'un livre pour l'emprunter |
| 🔍 CHERCHER UN LIVRE | Rechercher par titre, auteur ou genre |
| 📌 MES RÉSERVATIONS | Consulter et annuler ses réservations |
| ✅ RENDRE PAR SCAN | Rendre un livre en scannant son code-barres |

### 4 — Emprunter un livre
L'élève passe le code-barres devant le scanner. L'emprunt est confirmé immédiatement à l'écran. Il peut enchaîner plusieurs scans sans quitter l'écran.

### 5 — Chercher et réserver
L'élève recherche un livre. Si le livre est **déjà emprunté**, un bouton **Réserver** apparaît. Après confirmation, l'élève revient automatiquement à son menu personnel. Le livre apparaît en **couleur réservation** s'il effectue une nouvelle recherche.

---

## Ce que vous faites — le rôle de l'enseignant

### Gérer les réservations prêtes

Quand un élève rend un livre qui est **réservé par un autre élève**, l'application affiche automatiquement un **écran jaune** avec :
- le titre du livre
- le nom de l'élève qui attend
- sa classe

**Votre action :** mettez le livre de côté et prévenez l'élève que son livre l'attend.

### Rendre un livre rapidement

Depuis l'écran de sélection de classe, vous pouvez scanner directement le code-barres d'un livre pour le rendre, **sans passer par un compte élève**. Pratique pour traiter un retour rapide en début de journée.

---

## Réglages ⚙️

Cliquez sur **⚙️** depuis l'écran de sélection de classe.

### Résolution de l'écran

| Option | Quand l'utiliser |
|---|---|
| 1280×720 | Vieil écran ou petit écran |
| 1920×1080 | Grand écran |
| **Maximisée** *(recommandé)* | S'adapte automatiquement à votre écran |

### Qualité d'image

| Option | Quand l'utiliser |
|---|---|
| **Basse** *(par défaut)* | Vieil ordinateur — fluide et stable |
| Haute | Ordinateur récent — images plus nettes |

### Thème visuel

Choisissez parmi une trentaine de thèmes : Minecraft, Pokémon, Barbie, Forêt enchantée, LEGO, Manga, Vaiana… Les élèves adorent choisir.

> Les réglages sont **sauvegardés automatiquement**.

---

## Questions fréquentes

**Un élève ne trouve pas son prénom**
Il doit taper au moins 2 lettres. Si le message « Prénom non trouvé dans cette classe » s'affiche malgré tout, l'élève n'est pas enregistré dans cette classe dans le logiciel de bibliothèque. Vérifiez avec le gestionnaire.

**Un élève a atteint sa limite d'emprunts**
L'application l'indique clairement. Il doit rendre un livre avant d'en emprunter un autre.

**Un élève veut réserver un livre déjà emprunté**
Il le cherche dans la recherche, puis appuie sur **Réserver**. La réservation est enregistrée et il revient à son menu.

**Comment changer de serveur de bibliothèque ?**
Appuyez sur le bouton portant le nom de la bibliothèque (en haut à gauche de l'écran de sélection de classe). Cela ramène à l'écran de connexion.

**L'élève est bloqué dans l'application**
Le bouton **← Retour** est présent sur chaque écran. En dernier recours, fermez et relancez l'application.

---

## En cas de problème

| Problème | Solution |
|---|---|
| L'application ne trouve pas le serveur | Vérifiez que le serveur BCD est démarré. Essayez la connexion manuelle (voir ci-dessous). |
| L'image est pixelisée | ⚙️ → Qualité **Haute** |
| L'application est lente ou se bloque | ⚙️ → Qualité **Basse**, résolution **1280×720** |
| Le scanner de codes-barres ne répond pas | Vérifiez qu'il est bien branché. Relancez l'application. |
| Un prénom n'apparaît jamais | L'élève n'est pas enregistré dans sa classe dans le logiciel de bibliothèque. |
| L'écran reste figé | Fermez et relancez BCD Kids. |

### Connexion manuelle

Si la connexion automatique échoue :
1. Depuis l'écran de connexion, remplissez le champ **« Ou tape l'adresse de ta bibliothèque »**
2. Entrez l'adresse fournie par votre technicien, par exemple : `http://192.168.1.100:8000`
3. Cliquez sur **Se connecter**

> 💡 Si vous n'avez pas l'adresse, contactez le support informatique de votre école.

---

## Configuration minimale requise

| | Minimum |
|---|---|
| Système d'exploitation | Windows 10 64 bits ou Linux |
| RAM | 4 Go |
| Espace disque | 100 Mo libres |
| Réseau | Connecté au réseau local de l'école |

L'application est conçue pour fonctionner sur les vieux ordinateurs scolaires.