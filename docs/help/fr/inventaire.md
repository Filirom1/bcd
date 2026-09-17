# Inventaire du fonds documentaire

La page d'inventaire permet d'effectuer le récolement physique et le désherbage du fonds documentaire.

## Vue d'ensemble

Cet outil permet de :
- Suivre quels exemplaires ont été physiquement vérifiés
- Identifier les exemplaires à désherber selon la rotation, l'âge et l'état
- Modifier en lot les champs d'exemplaires et de notices
- Supprimer des exemplaires et nettoyer les notices orphelines
- Exporter des rapports d'inventaire en CSV

## Démarrage

### Onglet Scanner

Scanner les codes-barres un par un pour les marquer comme inventoriés :

1. Placer le curseur dans le champ de saisie (focus automatique)
2. Scanner un code-barres ou saisir l'identifiant
3. Appuyer sur Entrée
4. L'exemplaire apparaît dans la table de travail avec la date du jour

![Onglet Scanner](../images/inventory-01-scan.png)

**Astuces :**
- Les exemplaires déjà dans la table remontent en haut (mis en surbrillance)
- Les codes inconnus affichent une notification d'erreur
- Le scanner garde le focus pour des scans rapides successifs

### Onglet Importer un fichier

Importer une liste d'identifiants depuis un fichier texte (utile avec des scanners portables) :

1. Cliquer sur « Choisir un fichier » et sélectionner un fichier `.txt`
2. Le fichier doit contenir un code-barres par ligne
3. Le système affiche le nombre de codes valides ou inconnus
4. Cliquer sur « Importer » pour ajouter les exemplaires valides

**Format du fichier :**
```
0785
0784
0312
# Les commentaires commencent par #
```

### Onglet Rechercher

Rechercher des exemplaires avec des filtres avancés pour identifier les candidats au désherbage :

![Onglet Recherche avec filtres avancés](../images/inventory-02-search.png)

**Recherche textuelle :** Titre, auteur, ISBN ou cote

**Filtres d'exemplaire :**
- Statut (disponible, en prêt, retiré, etc.)
- État (bon, endommagé)
- Emplacement

**Filtres d'inventaire :**
- Jamais inventorié
- Pas inventorié depuis [date]

**Filtre de rotation (méthode CREW / IOUPI) :**
- Trouver les exemplaires avec moins de X prêts depuis une date donnée
- Exemple : "moins de 2 prêts depuis le 01/04/2022" identifie les exemplaires peu empruntés
- **CREW** (Continuous Review, Evaluate, Weed) est la méthode anglophone ; son équivalent
  français est **IOUPI** : Incorrect, Ordinaire/médiocre, Usé, Périmé, Inadéquat

**Filtres de notice :**
- Type de support, public cible
- Niveau de lecture, langue
- Plage d'années de publication

> **Astuce :** Pour les champs texte (emplacement, type de support, niveau, langue), saisir `__none__` pour filtrer les exemplaires dont ce champ n'est pas renseigné.

**Résultats :**
- Limités à 200 exemplaires (affiner les filtres si nécessaire)
- Sélectionner des exemplaires et cliquer sur « Ajouter à la table de travail »

## Table de travail

La table de travail persiste dans le navigateur et survit aux rafraîchissements de page.

**Actions :**
- Sélectionner/désélectionner avec les cases à cocher
- Maj+clic pour sélectionner une plage
- Vider la sélection ou tout vider

## Opérations en lot

### Modification groupée

Modifier plusieurs exemplaires et leurs notices en une fois :

1. Sélectionner des exemplaires dans la table de travail
2. Cliquer sur le menu admin (⋮) → « Modification groupée »
3. Modifier les champs d'exemplaire (statut, état, empruntable, emplacement)
4. Modifier les champs de notice (type de support, niveau, public cible)
5. Laisser les champs « — inchangé — » pour conserver les valeurs existantes
6. Sélectionner « — Vider — » dans un champ pour effacer sa valeur actuelle
7. Confirmer l'opération

**Remarques :**
- Les exemplaires en prêt ne peuvent pas changer de statut (mesure de sécurité)
- Les modifications de notice affectent tous les exemplaires du même titre
- La confirmation affiche combien d'autres exemplaires seront affectés

### Suppression groupée

Supprimer définitivement des exemplaires du système :

1. Sélectionner des exemplaires dans la table de travail
2. Cliquer sur le menu admin (⋮) → « Supprimer les exemplaires »
3. Examiner la confirmation (elle affiche les exclusions)
4. Confirmer la suppression

**Mesures de sécurité :**
- Les exemplaires en prêt sont automatiquement exclus
- Les réservations actives sont annulées
- Les notices orphelines (titres sans exemplaires restants) sont signalées

### Exporter en CSV

1. Cliquer sur le menu admin (⋮) → « Exporter en CSV »
2. Un fichier `inventory_AAAA-MM-JJ.csv` se télécharge avec 9 colonnes :
   - Code-barres, Titre, Auteur, Cote, Emplacement
   - Statut, État, Date dernier prêt, Date dernier inventaire

## Fonctions d'administration

### Supprimer les notices orphelines

Nettoyer les notices bibliographiques qui n'ont plus d'exemplaires :

1. Cliquer sur le menu admin (⋮) → « Supprimer les notices sans exemplaires »
2. Examiner la liste des notices orphelines
3. Confirmer la suppression

**Cas d'usage :** Après avoir supprimé des exemplaires en lot lors du désherbage

## Bonnes pratiques

**Inventaire annuel (Récolement) :**

L'objectif est de détecter les exemplaires absents des rayons : perdus, mal rangés ou empruntés non rendus.

**Étape 1 — Scanner un rayon**
1. Noter la date et l'heure de début (ex : 14 avril 2026)
2. Onglet Scanner → scanner tous les exemplaires du rayon choisi
3. Répétez pour chaque rayon si nécessaire

**Étape 2 — Chercher les absents**

Une fois le scan terminé, basculer sur l'onglet **Rechercher** et combiner ces filtres :
- **Emplacement** = nom du rayon scanné (ex : "Documentaires", "Romans")
- **Pas inventorié depuis** = date de début de session (ex : 14/04/2026)
- **Statut** = Disponible (pour exclure les exemplaires légitimement en prêt)

Les résultats sont les exemplaires **attendus sur ce rayon mais non scannés** : candidats à vérifier (mal rangés ou perdus).

**Étape 3 — Traiter les absents**
- Vérifier physiquement si ces exemplaires sont mal rangés ailleurs
- Pour les exemplaires introuvables → les ajouter à la table de travail → Suppression groupée
- Exporter la liste pour la documentation administrative

**Désherbage :**

Le désherbage se réalise rayon par rayon, pas en une seule fois. Traiter les documentaires et les fictions séparément — les critères sont différents.

*Documentaires (albums documentaires, encyclopédies, sciences…)*
- Deux critères combinés : **âge** du document + **rotation** faible
- Exemple de recherche : Année de publication ≤ 2018 **et** moins de 2 prêts depuis le 01/09/2022
- Les informations scientifiques, géographiques et pratiques vieillissent vite

*Fictions (romans, albums, BD, mangas…)*
- Critère principal : **état physique** et **demande** (ne pas éliminer un livre très emprunté même ancien)
- Exemple de recherche : État = Endommagé **ou** moins de 1 prêt depuis le 01/09/2021
- Conserver les classiques et les titres encore demandés malgré leur ancienneté

**Workflow désherbage :**
1. Utiliser Recherche pour identifier les candidats (filtres rotation + publication)
2. Ajouter les candidats à la table de travail
3. Examiner visuellement la liste (état, date dernier prêt, date dernier inventaire)
4. **Avant de supprimer** : exporter en CSV (⋮ → Exporter en CSV) — cette liste fait office de trace administrative
5. Supprimer en lot les exemplaires retenus
6. Si des notices orphelines apparaissent, utiliser ⋮ → « Supprimer les notices sans exemplaires »

> **Conseil** : Toujours vérifier physiquement un exemplaire avant de le supprimer. Un livre « absent » lors du scan peut être simplement emprunté, mal rangé ou en cours de consultation. Terminer le récolement d'un rayon entier avant d'agir.

**Méthode CREW :**
- C : Évaluation **C**ontinue (ne pas attendre que le fonds soit dégradé)
- R : **R**évision de la rotation et de l'état physique
- E : **É**valuation selon les critères IOUPI
- W : **W**eeding — élimination des documents qui ne servent plus le fonds

**Critères IOUPI :**
- **I** : Incorrect — l'information est fausse ou dépassée (ex : atlas avec des frontières obsolètes)
- **O** : Ordinaire — contenu superficiel, sans intérêt particulier
- **U** : Usé — état physique trop dégradé pour être emprunté
- **P** : Peu demandé — n'a pas été emprunté depuis des années
- **I** : Inadéquat — ne correspond plus au public ou aux programmes

## Raccourcis clavier

- **Navigation Tab** entre les champs de filtre
- **Entrée** dans le champ code-barres → scanner
- **Maj+Clic** dans la table → sélection de plage

## Dépannage

**"Exemplaire non trouvé" lors du scan :**
- Vérifier que le code-barres est correct
- Vérifier si l'exemplaire existe dans le catalogue

**La recherche renvoie "Affichage de 200 sur 500 résultats" :**
- Affiner les filtres pour obtenir un ensemble de résultats plus petit
- La limite de 200 évite le ralentissement du navigateur

**Avertissement d'archive avec le filtre de rotation :**
- Les historiques de prêts antérieurs à la date limite d'archivage peuvent être incomplets
- La date du filtre de rotation est antérieure à la plus ancienne transaction disponible

---

*Pour toute question ou problème, contacter l'administrateur système.*
