# Paramètres

Cette page te permet de configurer les règles de prêt et les options de la bibliothèque.

---

## Étape 1 — Paramètres de prêt

Ces paramètres définissent les règles d'emprunt appliquées à tous les nouveaux prêts.

![Page des paramètres principaux](../images/settings-01-main.png)

### Détail de chaque paramètre

| Paramètre | Rôle | Valeur par défaut |
|-----------|------|-------------------|
| **Durée de prêt (jours)** | Nombre de jours avant la date de retour prévue. S'applique à tous les nouveaux emprunts. | 14 jours |
| **Limite de prêt (élèves)** | Nombre maximum de livres qu'un élève peut avoir simultanément. | 3 livres |
| **Limite de prêt (enseignants)** | Nombre maximum de livres qu'un enseignant peut avoir simultanément. | 10 livres |
| **Renouvellements maximum** | Nombre de fois qu'un emprunt peut être prolongé sans retour physique. Mets 0 pour interdire les renouvellements. | 2 |
| **Expiration des réservations (jours)** | Nombre de jours pendant lesquels un élève peut venir chercher un livre mis de côté pour lui avant que la réservation soit annulée. | 3 jours |
| **Réservations actives max par élève** | Nombre maximum de réservations simultanées qu'un élève peut avoir en attente ou prêtes. | 1 |
| **Année scolaire en cours** | Étiquette de l'année scolaire (ex : 2024-2025). Utilisée dans les rapports. | — |

> **Conseil :** Les modifications de durée ou de limite de prêt ne s'appliquent pas aux emprunts déjà en cours.

## Étape 2 — Format des codes-barres

Ces paramètres permettent au scanner de distinguer automatiquement les cartes élèves des codes-barres des livres.

| Paramètre | Rôle | Exemple |
|-----------|------|---------|
| **Préfixe emprunteur** | Caractère(s) ajoutés avant le numéro d'emprunteur sur les cartes. | `%` → carte lue comme `%12345` |
| **Préfixe article** | Caractère(s) ajoutés avant le numéro d'inventaire sur les étiquettes des livres. | `.` → étiquette lue comme `.00785` |
| **Format d'identifiant** | Format de validation des numéros d'emprunteurs (numérique, alphanumérique, personnalisé). | numérique |

> **Conseil :** Si ta douchette ne lit pas de préfixe (numéro brut), laisse les champs de préfixe vides.

## Étape 3 — Listes de classification

Ces listes définissent les valeurs suggérées dans les formulaires de catalogage et dans l'édition groupée.

| Paramètre | Rôle |
|-----------|------|
| **Types de support** | Liste des types de support (ex : Livre, BD, Revue, CD, DVD). |
| **Langues** | Liste des codes de langue ISO 639-1, séparés par des virgules (ex : `fr, en, es, de, ar`). Ces codes sont utilisés dans les formulaires de catalogage et les filtres d'inventaire. |

> **Conseil :** Ces listes sont utilisées comme suggestions — tu peux toujours saisir une valeur qui n'y figure pas.

**Bonnes pratiques pour maintenir la cohérence du catalogue :**

Les listes de classification jouent le rôle de référentiel pour tout le fonds. Plus elles sont rigoureusement respectées lors du catalogage, moins il y aura de variantes à corriger ensuite (ex : `policier`, `Policier`, `Roman policier` pour la même chose).

- **Définir les listes une bonne fois pour toutes** avant de commencer à cataloguer
- **Choisir des noms simples et sans majuscule superflue** pour éviter les doublons (ex : `Policier` et non `Roman policier`)
- **Vérifier régulièrement** via Catalogue → filtres avancés → type de support vide ou inhabituel → corriger en édition groupée
- Si une valeur est saisie hors liste par erreur, elle restera dans la base jusqu'à ce qu'on la corrige manuellement via l'édition groupée dans le catalogue

## Étape 4 — Couleurs Dewey

La **marguerite des couleurs** associe une couleur à chacune des 10 grandes classes Dewey (000 à 900). Ces couleurs apparaissent sur les étiquettes de cote dans le catalogue et l'inventaire pour repérer d'un coup d'œil la section d'un livre.

| Classe | Thème |
|--------|-------|
| **000** | Généralités, dictionnaires, informatique |
| **100** | Philosophie, psychologie |
| **200** | Religion |
| **300** | Sciences sociales, éducation |
| **400** | Langues |
| **500** | Sciences naturelles, mathématiques |
| **600** | Technologie, médecine, cuisine |
| **700** | Arts, musique, sport, loisirs |
| **800** | Littérature |
| **900** | Histoire, géographie, biographies |

**Pour chaque classe, tu peux :**
- **Activer ou désactiver** la couleur avec la case à cocher (si désactivée, la cote s'affiche sans couleur)
- **Choisir la couleur** avec le sélecteur de couleur

Les couleurs par défaut suivent la **marguerite des couleurs** utilisée dans les bibliothèques scolaires françaises.

> **Conseil :** Si tu colories déjà les étiquettes physiques sur tes livres, configure ici les mêmes couleurs pour que l'affichage à l'écran corresponde à ce que les élèves voient sur les étagères.

## Étape 5 — Emplacements de rayonnage

Cette liste définit les **emplacements physiques** de ta bibliothèque (Romans, Albums, Bandes dessinées, Documentaires…). Chaque emplacement peut avoir une couleur distincte.

Ces emplacements apparaissent comme des badges colorés dans :
- Le **catalogue** (résultats de recherche et fiche d'un livre)
- L'**inventaire** (liste des exemplaires)
- Le formulaire de **catalogage** (sélecteur d'emplacement au lieu d'un champ texte libre)

**Pour gérer la liste :**
- **Ajouter** un emplacement : clique sur « + Ajouter un emplacement »
- **Nommer** chaque emplacement dans le champ texte (ex : `Romans`, `Albums`)
- **Colorier** (optionnel) : coche la case puis choisis une couleur avec le sélecteur
- **Supprimer** un emplacement : clique sur l'icône corbeille

> **Conseil :** Utilise les mêmes noms que les panneaux physiques sur tes étagères. Les élèves retrouveront plus facilement les livres si les noms à l'écran correspondent à ce qu'ils voient dans la bibliothèque.

## Étape 6 — Sauvegarder les paramètres

Clique sur **« Enregistrer »** pour appliquer tous les changements.
Un message de confirmation apparaît en haut de l'écran.

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| La nouvelle durée de prêt ne s'applique pas aux anciens emprunts | Les paramètres ne s'appliquent qu'aux nouveaux emprunts. Les anciens conservent leur date d'échéance. |
| Le scanner ne distingue pas les cartes des livres | Vérifie que les préfixes emprunteur et article sont bien configurés et différents. |
| Les modifications ne sont pas sauvegardées | Clique sur le bouton « Enregistrer » pour valider les changements. |
