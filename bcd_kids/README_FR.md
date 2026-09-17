# BCD Kids — Guide pour les enseignants

## À quoi sert BCD Kids ?

**BCD Kids** permet aux élèves d'emprunter, de rendre et de réserver des livres de la bibliothèque **en totale autonomie**, sans intervention de l'enseignant.

L'application fonctionne sur l'ordinateur de la bibliothèque ou sur une tablette connectée au réseau de l'école. En quelques secondes, un élève peut gérer ses emprunts de manière autonome.

---

## Premier lancement

> À effectuer **une seule fois** lors de l'installation.

1. Vérifier que le **serveur BCD est démarré** sur l'ordinateur principal.
2. Double-cliquer sur l'icône **BCD Kids** du bureau.
3. Attendre quelques secondes pendant la recherche automatique du serveur.
4. Une fois la connexion établie, ajuster les **réglages d'affichage** selon le matériel utilisé (voir [Réglages](#réglages-️)).

> 💡 En cas d'échec de la connexion, consulter la section [En cas de problème](#en-cas-de-problème).

---

## Ce que voient les élèves — pas à pas

### 1 — Choisir sa classe

Une grille affiche toutes les classes. L'élève appuie sur la classe correspondante.

### 2 — Taper son prénom

L'élève tape les premières lettres de son prénom. La liste des correspondances apparaît. Si plusieurs élèves partagent le même prénom, le nom complet doit être sélectionné dans la liste.

> ⚠️ Si le message **« Prénom non trouvé dans cette classe »** s'affiche, l'élève n'est probablement pas encore enregistré dans sa classe dans le logiciel de bibliothèque. Contacter le gestionnaire.

### 3 — Le menu personnel

L'élève voit ses livres en cours et accède à toutes les fonctions :

| Bouton | Fonction |
|---|---|
| 📖 EMPRUNTER UN LIVRE | Scanner le code-barres d'un livre pour l'emprunter |
| 🔍 CHERCHER UN LIVRE | Rechercher par titre ou auteur |
| 📌 MES RÉSERVATIONS | Consulter et annuler ses réservations |
| ✅ RENDRE PAR SCAN | Rendre un livre en scannant son code-barres |

### 4 — Emprunter un livre

L'élève passe le code-barres devant le scanner. L'emprunt est confirmé immédiatement à l'écran. Plusieurs scans peuvent être enchaînés sans quitter l'écran.

### 5 — Chercher et réserver

L'élève recherche un livre. Si le livre est **déjà emprunté**, un bouton **Réserver** apparaît. Après confirmation, l'élève revient automatiquement à son menu personnel. Le livre apparaît en **couleur réservation** lors d'une nouvelle recherche.

---

## Rôle de l'enseignant

### Gérer les réservations prêtes

Quand un élève rend un livre qui est **réservé par un autre élève**, l'application affiche automatiquement un **écran jaune** avec :
- le titre du livre ;
- le nom de l'élève qui attend ;
- sa classe.

**Action à effectuer :** mettre le livre de côté et prévenir l'élève que son livre l'attend.

### Rendre un livre rapidement

Depuis l'écran de sélection de classe, il est possible de scanner directement le code-barres d'un livre pour le rendre, **sans passer par un compte élève**. Cette fonction est pratique pour traiter rapidement un retour en début de journée.

---

## Réglages ⚙️

Cliquer sur **⚙️** depuis l'écran de sélection de classe.

### Résolution de l'écran

| Option | Quand l'utiliser |
|---|---|
| 1280×720 | Vieil écran ou petit écran |
| 1920×1080 | Grand écran |
| **Maximisée** *(recommandé)* | Adaptation automatique à l'écran |

### Qualité d'image

| Option | Quand l'utiliser |
|---|---|
| **Basse** *(par défaut)* | Vieil ordinateur — fonctionnement fluide et stable |
| Haute | Ordinateur récent — images plus nettes |

### Thème visuel

Une trentaine de thèmes sont disponibles : Minecraft, Pokémon, Barbie, Forêt enchantée, LEGO, Manga, Vaiana… Les élèves peuvent choisir leur thème.

> Les réglages sont **sauvegardés automatiquement**.

---

## Questions fréquentes

**Un élève ne trouve pas son prénom**

Il doit taper au moins 2 lettres. Si le message « Prénom non trouvé dans cette classe » s'affiche malgré tout, l'élève n'est pas enregistré dans cette classe dans le logiciel de bibliothèque. Vérifier avec le gestionnaire.

**Un élève a atteint sa limite d'emprunts**

L'application l'indique clairement. Un livre doit être rendu avant tout nouvel emprunt.

**Un élève veut réserver un livre déjà emprunté**

Le livre doit être recherché, puis le bouton **Réserver** sélectionné. La réservation est enregistrée et l'élève revient à son menu.

**Comment changer de serveur de bibliothèque ?**

Appuyer sur le bouton portant le nom de la bibliothèque, en haut à gauche de l'écran de sélection de classe. Cette action ramène à l'écran de connexion.

**L'élève est bloqué dans l'application**

Le bouton **← Retour** est présent sur chaque écran. En dernier recours, fermer puis relancer l'application.

---

## En cas de problème

| Problème | Solution |
|---|---|
| L'application ne trouve pas le serveur | Vérifier que le serveur BCD est démarré. Essayer la connexion manuelle (voir ci-dessous). |
| L'image est pixelisée | ⚙️ → Qualité **Haute** |
| L'application est lente ou se bloque | ⚙️ → Qualité **Basse**, résolution **1280×720** |
| Le scanner de codes-barres ne répond pas | Vérifier qu'il est bien branché. Relancer l'application. |
| Un prénom n'apparaît jamais | L'élève n'est pas enregistré dans sa classe dans le logiciel de bibliothèque. |
| L'écran reste figé | Fermer puis relancer BCD Kids. |

### Connexion manuelle

En cas d'échec de la connexion automatique :
1. Depuis l'écran de connexion, remplir le champ d'adresse de la bibliothèque.
2. Saisir l'adresse fournie par le technicien, par exemple : `http://192.168.1.100:8888`.
3. Cliquer sur **Se connecter**.

> 💡 Si l'adresse n'est pas disponible, contacter le support informatique de l'école.

---

## Configuration minimale requise

| | Minimum |
|---|---|
| Système d'exploitation | Windows 10 64 bits ou Linux |
| RAM | 4 Go |
| Espace disque | 100 Mo libres |
| Réseau | Connexion au réseau local de l'école |

L'application est conçue pour fonctionner sur les anciens ordinateurs scolaires.
