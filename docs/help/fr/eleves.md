# Gérer les élèves

Cette page te permet de consulter et gérer les fiches de tous les emprunteurs de la bibliothèque.

---

## Étape 1 — Rechercher un élève

Utilise la barre de recherche pour trouver un élève par son nom, prénom ou numéro d'emprunteur.
Tu peux aussi filtrer par classe en utilisant le menu déroulant des classes.

![Liste des élèves avec barre de recherche](../images/borrowers-01-list.png)

> **Conseil :** Clique sur l'en-tête d'une colonne pour trier la liste par nom, classe ou nombre d'emprunts.

## Étape 2 — Consulter la fiche d'un élève

Clique sur un élève pour ouvrir sa fiche.
Tu y trouves ses informations, ses emprunts en cours et son historique.

![Fiche détail d'un élève avec ses emprunts](../images/borrowers-02-detail.png)

## Étape 3 — Bloquer ou débloquer un élève

Dans la fiche de l'élève, clique sur « Bloquer » pour l'empêcher d'emprunter de nouveaux livres.
Indique la raison du blocage (perte de livre, trop de retards, etc.).
Pour lever le blocage, clique sur « Débloquer ».

![Bouton de blocage d'un emprunteur](../images/borrowers-03-block.png)

> **Conseil :** Un emprunteur bloqué peut toujours rendre des livres, mais ne peut pas en emprunter de nouveaux.

## Étape 4 — Importer des élèves (début d'année)

Pour importer une nouvelle liste d'élèves depuis un fichier CSV, clique sur le menu « Admin » puis « Importer ».
Le fichier doit contenir au minimum : nom, prénom, classe.

![Interface d'import CSV des emprunteurs](../images/borrowers-04-import.png)

---

## Actions du menu Admin

Le menu **Admin** en haut à droite donne accès aux actions d'administration :

| Action | Description |
|--------|-------------|
| **Ajouter un emprunteur** | Crée manuellement une nouvelle fiche emprunteur (élève, enseignant, ou personnel). |
| **Importer emprunteurs** | Importe une liste depuis un fichier CSV avec le format décrit ci-dessous. |
| **Exporter emprunteurs** | Exporte la liste complète en CSV pour consultation ou sauvegarde. |
| **Édition groupée** | Déplace les emprunteurs sélectionnés vers une autre classe en une seule opération. |
| **Imprimer fiches de référence** | Imprime une fiche récapitulative par classe avec les noms et numéros des élèves. Utile pour les enseignants en salle. |
| **Imprimer cartes de bibliothèque** | Génère des cartes plastifiables avec code-barres individuel pour les élèves sélectionnés. |

### Édition groupée — opération disponible

L'édition groupée pour les emprunteurs permet de **changer la classe** de tous les élèves sélectionnés en même temps.
Cela est utile en début d'année pour faire passer une classe entière d'un niveau au suivant.

> **Conseil :** Coche d'abord tous les élèves de la classe concernée (utilise le filtre par classe pour les trouver facilement), puis clique sur « Édition groupée » et sélectionne la nouvelle classe.

### Format du fichier CSV d'import

Le fichier d'import est un simple tableau que tu peux préparer avec **Excel** ou **LibreOffice Calc**.

**Comment préparer le fichier avec Excel :**

1. Ouvre un nouveau classeur Excel.
2. En **ligne 1**, tape exactement ces en-têtes de colonnes (attention aux minuscules et aux underscores `_`) :

| Colonne à saisir | Ce que ça contient | Obligatoire |
|------------------|--------------------|-------------|
| `borrower_id` | Numéro de l'élève (ex : 12345) | Oui |
| `first_name` | Prénom | Oui |
| `last_name` | Nom de famille | Oui |
| `class_name` | Nom de la classe, tel qu'il existe dans BCD (ex : CM1-A) | Non |
| `role` | Laisser vide pour les élèves. Écrire `teacher` pour les enseignants. | Non |
| `active` | Laisser vide (compte actif par défaut) | Non |

3. Remplis les lignes suivantes avec les données des élèves.
4. Clique sur **Fichier → Enregistrer sous**, puis choisis le format **CSV UTF-8 (délimité par des virgules)**.

> **Conseil :** Le nom de la classe dans le fichier doit correspondre exactement au nom affiché dans BCD (majuscules comprises). Vérifie dans la page Classes avant d'importer.

> **Conseil :** Pour imprimer les cartes ou utiliser l'édition groupée, coche d'abord les cases à gauche des élèves concernés.

---

## RGPD — Protection des données personnelles

### Ce que BCD stocke

BCD enregistre pour chaque emprunteur : **nom**, **prénom**, **classe** et **numéro d'emprunteur**.
L'historique des prêts (titre emprunté, dates de prêt et de retour) est lié à chaque fiche.

### Obligations légales (Délibération CNIL n° 99-27)

La réglementation française (applicable dans le cadre du RGPD) impose :

- **Données de prêt** : à détruire dans les **4 mois suivant le retour** du document.
- **Identité des emprunteurs** : à supprimer au plus tard **1 an après le dernier prêt**.

En milieu scolaire, la CNIL tolère que cette suppression soit effectuée **en fin d'année scolaire** plutôt qu'au fil de l'eau.

### Comment BCD gère la conformité

**BCD supprime définitivement** les données de chaque emprunteur.

> Quand tu supprimes un emprunteur, **toutes ses données sont effacées immédiatement et définitivement** : fiche personnelle, emprunts en cours, et historique complet des prêts. Il n'y a pas de récupération possible.

Cette suppression garantit la conformité RGPD sans procédure complexe.

### Procédure de fin d'année

**En fin d'année scolaire**, il est recommandé de supprimer les fiches des élèves qui quittent l'école :

1. **CM2 partants** : filtre la liste par classe CM2, coche tous les élèves, clique sur « Supprimer la sélection » dans le menu Admin.
2. **Élèves inactifs depuis plus d'un an** : si des élèves d'autres classes n'ont pas eu d'emprunt depuis la rentrée précédente, supprime leurs fiches également.

> **Important :** Avant de supprimer des élèves, vérifie qu'ils n'ont pas de **prêt en cours** (livre non rendu). Si c'est le cas, enregistre d'abord le retour (ou constate la perte), puis supprime la fiche.

> **Conseil :** Le flux habituel en début d'année est : **supprimer les CM2** → **importer la nouvelle liste** → **faire la promotion des classes** (CE1 devient CE2, etc.) via l'édition groupée.

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| L'élève n'apparaît pas dans la liste | Vérifie les filtres actifs — clique sur « Réinitialiser » pour afficher tous les élèves. |
| Impossible de bloquer un élève | Seul un administrateur peut bloquer un emprunteur. Vérifie tes droits d'accès. |
| L'import CSV échoue | Vérifie que le fichier a bien été enregistré au format **CSV UTF-8** (dans Excel : Fichier → Enregistrer sous → CSV UTF-8). Les noms de colonnes doivent être exactement ceux indiqués ci-dessus. |
