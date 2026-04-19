# BCD Kids

Cette application permet à vos élèves (6–11 ans) d'utiliser la bibliothèque
scolaire en autonomie : emprunter des livres, les rendre, rechercher dans le
catalogue et faire des réservations.


## Comment fonctionne l'application — Pas à pas

### 1. Connexion au serveur de bibliothèque
![Écran de sélection du serveur](docs/screenshots/bcd-kids-1-select-server.png)

Au lancement, l'application trouve automatiquement le serveur de bibliothèque
sur le réseau de l'école. Si ce n'est pas le cas, voir
[Connexion manuelle](#connexion-manuelle) ci-dessous.

---

### 2. Choix de la classe
![Écran de sélection de classe](docs/screenshots/bcd-kids-2-select-class.png)

Les élèves appuient sur le nom de leur classe.

---

### 3. Saisie du prénom
![Écran de saisie du prénom](docs/screenshots/bcd-kids-3-name-input.png)

Les élèves tapent leur prénom — une liste de prénoms correspondants apparaît
pour qu'ils choisissent le leur.

---

### 4. Le profil de l'élève
![Écran emprunteur](docs/screenshots/bcd-kids-4-borrower.png)

L'élève voit ses emprunts en cours et peut accéder à toutes les
fonctionnalités depuis cet écran.

---

### 5. Emprunter un livre
![Écran d'emprunt](docs/screenshots/bcd-kids-7-checkout.png)

Scanner le code-barres sur le livre — l'emprunt est confirmé immédiatement.

---

### 6. Rechercher dans le catalogue
![Écran de recherche](docs/screenshots/bcd-kids-6-search.png)

Les élèves peuvent rechercher par titre, auteur, genre ou niveau de lecture.

---

### 7. Les réservations
![Écran des réservations](docs/screenshots/bcd-kids-5-holds.png)

Si un livre est déjà emprunté, les élèves peuvent poser une réservation.


## Démarrage rapide

1. Double-cliquer sur l'icône **BCD** sur le bureau
2. L'application se connecte automatiquement au serveur de la bibliothèque
   sur le réseau de l'école
3. Les élèves choisissent leur **classe**, puis leur **prénom** — c'est parti !

## Ce que les élèves peuvent faire

| Action | Comment |
|---|---|
| 📖 Emprunter un livre | Scanner le code-barres sur le livre |
| 🔄 Rendre un livre | Scanner le code-barres au retour |
| 🔍 Rechercher dans le catalogue | Par titre, auteur, genre ou niveau de lecture |
| 📌 Réserver un livre | Si le livre est déjà emprunté par quelqu'un d'autre |

## Connexion au serveur de bibliothèque

### Automatique *(recommandé)*
Quand votre ordinateur est connecté au réseau de l'école, l'application
trouve le serveur de bibliothèque toute seule. Il suffit de la lancer !

### Connexion manuelle
Si la connexion automatique échoue :
1. Sur l'écran de connexion, remplir le champ **« Connexion manuelle »**
2. Saisir l'adresse fournie par votre technicien informatique
   *(ex : `http://192.168.1.100:8000`)*
3. Cliquer sur **Connecter**

> 💡 Si vous n'avez pas l'adresse du serveur, contactez le support
> informatique de votre école.

## Paramètres d'affichage ⚙️

Cliquer sur le bouton **⚙️** dans l'écran de sélection de classe.

**Résolution de l'écran**

| Option | Quand l'utiliser |
|---|---|
| 1280 × 720 | Petit écran ou vieil ordinateur |
| 1920 × 1080 | Grand écran |
| **Maximisée** *(recommandé)* | S'adapte automatiquement |

**Qualité d'image**

| Option | Quand l'utiliser |
|---|---|
| **Basse** *(par défaut)* | Vieux ordinateurs — fonctionne bien |
| Haute | Ordinateurs récents — meilleure qualité d'image |

Les paramètres sont sauvegardés automatiquement.

## Résolution de problèmes

| Problème | Solution |
|---|---|
| L'application ne trouve pas le serveur | Utiliser la connexion manuelle (voir ci-dessus) |
| L'image est pixelisée | Aller dans ⚙️ → qualité **Haute** |
| L'application est lente ou se bloque | Aller dans ⚙️ → qualité **Basse**, résolution **1280×720** |
| Le scanner de codes-barres ne fonctionne pas | Vérifier qu'il est bien branché, puis réessayer |
| Changer de serveur de bibliothèque | Utiliser le bouton 🌐 dans l'écran de sélection de classe |

## Configuration minimale requise

| | Minimum |
|---|---|
| **Système d'exploitation** | Windows 10 (64 bits) ou Linux |
| **RAM** | 4 Go |
| **Espace disque libre** | 100 Mo |
| **Réseau** | Connecté au réseau local de l'école |

L'application est conçue pour fonctionner sur les vieux ordinateurs scolaires.