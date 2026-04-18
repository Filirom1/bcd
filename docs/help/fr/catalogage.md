# Ajouter des livres

Cette page te permet d'ajouter de nouveaux livres au catalogue de la bibliothèque.

---

## Étape 1 — Saisir le numéro ISBN

Tape ou scanne le code-barres ISBN du livre (le numéro à 13 chiffres au dos du livre).
Le système cherche automatiquement la notice bibliographique auprès de la BNF (Bibliothèque nationale de France).

![Champ de saisie ISBN avec résultat BNF automatique](../images/cataloging-01-isbn.png)

> **Conseil :** Le code-barres ISBN est généralement imprimé au verso de la couverture, sous le code-barres.

## Étape 2 — Vérifier les informations

Les informations récupérées (titre, auteur, éditeur, année) s'affichent automatiquement.
Vérifie et corrige si nécessaire avant de valider.

![Formulaire pré-rempli avec les données de la BNF](../images/cataloging-02-form.png)

> **Conseil :** Si l'ISBN n'est pas reconnu par la BNF, tu peux remplir le formulaire manuellement en cliquant sur « Saisie manuelle ».

## Étape 3 — Ajouter le livre sans ISBN

Pour les vieux livres sans code-barres ISBN, clique sur « Saisie manuelle » et remplis le formulaire.
Seul le titre est obligatoire.

![Formulaire de saisie manuelle](../images/cataloging-03-manual.png)

## Étape 4 — Scanner le code-barres du livre

Après avoir validé la notice, scanne le code-barres d'inventaire collé dans le livre.
Ce code-barres est l'identifiant unique de l'exemplaire physique.

![Étape de scan du code-barres d'inventaire](../images/cataloging-04-barcode.png)

---

## Champs de la fiche bibliographique

Lors de la création ou de la modification d'une notice, voici le rôle de chaque champ :

### Informations de base

| Champ | Rôle | Obligatoire |
|-------|------|-------------|
| **ISBN ou ISSN** | Pour un livre : code ISBN à 13 chiffres (au dos de la couverture). Pour une revue ou un magazine : code ISSN au format `NNNN-NNNX` (ex : `0153-5021`). Le système détecte automatiquement le format et interroge la source appropriée. | Non |
| **Titre** | Titre principal du livre tel qu'il apparaît sur la couverture. | **Oui** |
| **Sous-titre** | Complément du titre si présent. | Non |
| **Auteur(s)** | Un auteur par ligne. Format recommandé : Nom, Prénom. | Non |
| **Illustrateur(s)** | Un illustrateur par ligne (albums, BD). | Non |

### Publication

| Champ | Rôle | Obligatoire |
|-------|------|-------------|
| **Éditeur** | Maison d'édition (ex : Gallimard, Flammarion). | Non |
| **Année de publication** | Année de parution (ex : 2023). | Non |
| **Collection/Série** | Nom de la collection ou de la série (ex : Folio Junior, Harry Potter). | Non |
| **Numéro de volume** | Rang dans la série (ex : Vol. 3). | Non |
| **Langue** | Code de langue ISO 639-1 (ex : `fr`, `en`, `es`, `de`, `ar`). Utilisée pour le filtrage dans le catalogue et l'inventaire. Remplie automatiquement via la recherche BNF. | Non |

### Classification et organisation

| Champ | Rôle | Obligatoire |
|-------|------|-------------|
| **Type de support** | Format physique du document (ex : Livre, BD, Revue, CD, DVD). | Non |
| **Genre** | Sous-catégorie littéraire (ex : Aventure, Policier, Fantastique). | Non |
| **Public cible** | Enfant (jusqu'à 8 ans) / Jeune (8–15 ans) / Adulte. Affine les recherches et les statistiques. | Non |
| **Niveau de lecture** | Niveau scolaire recommandé (ex : CP, CE1, CM2). Libre saisie. | Non |

### Description du contenu

| Champ | Rôle | Obligatoire |
|-------|------|-------------|
| **Mots-clés** | Termes de recherche supplémentaires séparés par des virgules. Améliorent la découverte dans le catalogue. | Non |
| **Description** | Résumé ou quatrième de couverture. Affiché dans la fiche détail. | Non |
| **Nombre de pages** | Nombre de pages (indicatif). | Non |
| **Avec illustrations** | Cocher si le livre contient des illustrations (albums, documentaires illustrés). | Non |

> **Conseil :** Seul le titre est obligatoire. Plus les champs sont remplis, meilleures sont les recherches dans le catalogue.

---

## Champs de l'exemplaire

Chaque exemplaire est une fiche distincte (un livre physique). Ces champs se renseignent depuis la fiche détail du catalogue → icône ✏️ sur l'exemplaire.

| Champ | Rôle |
|-------|------|
| **Code-barres** | Identifiant unique de l'exemplaire (code-barres collé sur le livre). Texte libre jusqu'à 20 caractères : numérique (`00123`), alphanumérique (`BCD001234`), ou tout autre format. |
| **Numérotation** | Pour les périodiques uniquement : numéro du fascicule (ex : `274`) ou libellé de période (ex : `Avril 2026`, `Hors-série été 2025`). Affiché dans la liste des exemplaires et dans le bilan de prêt. Champ obligatoire lors de l'ajout d'un exemplaire à une notice de type `Périodique`. |
| **Cote** | Indice de classement sur l'étagère (ex : `R DUM`, `503`). Repris automatiquement depuis la notice à la création. |
| **Emplacement** | Zone ou rayon où se trouve l'exemplaire (ex : `Romans`, `Documentaires`, `Coin lecture`, `Classe CE2`). Libre saisie. Utilisé dans les filtres d'inventaire. |
| **État** | Bon / Endommagé. |
| **Empruntable** | Décocher pour retirer un exemplaire du circuit de prêt sans le supprimer (ex : exemplaire réservé à la consultation sur place). |
| **Statut** | Disponible / En prêt / Perdu / Retiré. Géré automatiquement par le système lors des prêts et retours. |

> **Conseil :** Si tu as deux exemplaires du même livre rangés à des endroits différents (un en rayon, un dans une classe de lecture suivie), tu peux leur donner des emplacements distincts. Le filtre Inventaire → Emplacement te permet ensuite de retrouver chaque exemplaire précisément.

---

## Migration depuis un ancien logiciel

Si ta bibliothèque était déjà équipée de codes-barres avec un logiciel précédent, **il n'est pas nécessaire de recoller de nouvelles étiquettes**.

### Reprise des codes-barres existants

Le code-barres d'inventaire (`item_id`) est un champ texte libre : BCD4 accepte n'importe quel format, qu'il soit numérique pur (`00123`), préfixé (`BCD001234`), ou alphanumériques mixte. Lors du catalogage d'un exemplaire déjà équipé, scanne simplement l'ancienne étiquette — BCD4 enregistre la valeur telle quelle.

**Import BiblioPuce :** lors d'un import CSV BiblioPuce (Admin → Importer catalogue → format BiblioPuce), les codes d'inventaire de l'ancien logiciel sont rapatriés automatiquement. Aucune saisie manuelle n'est nécessaire.

### Continuer une numérotation existante

Si une partie du fonds a déjà des codes-barres numeriques et tu veux continuer dans la même séquence pour les nouveaux livres :

1. **Admin → Étiquettes**
2. Dans le champ **Commencer à partir de**, saisis le numéro suivant le dernier déjà utilisé (ex : si le dernier code-barres en service est `00847`, saisis `848`)
3. Le système génère les prochains identifiants libres à partir de ce point, en sautant ceux déjà attribués

> **Conseil :** Le générateur d'étiquettes de BCD4 produit des identifiants numériques. Si tu as besoin d'un préfixe fixe sur les étiquettes (voir section ci-dessous), configure-le dans Paramètres → Codes-barres avant d'imprimer.

### Préfixe de code-barres (convention BiblioPuce)

BiblioPuce et BCD4 utilisent la même convention de préfixe pour distinguer automatiquement les codes livres des codes élèves au banc de prêt :

| Type | Préfixe par défaut | Exemple scanné |
|------|--------------------|----------------|
| Exemplaire (livre) | `.` (point) | `.00785` |
| Emprunteur (élève) | `%` (pourcent) | `%10234` |

Lorsque la douchette lit un code, BCD4 détecte le préfixe et sait immédiatement si c'est un livre ou une carte élève — sans que l'enseignant ait à changer de champ manuellement.

**Si tu migres depuis BiblioPuce :** les codes de BiblioPuce utilisent déjà cette convention. Les étiquettes existantes sont compatibles sans modification.

**Si tu n'utilises pas de préfixe** (douchette qui renvoie le numéro brut, ou ancien système différent) : laisse les champs de préfixe vides dans les Paramètres. Le préfixe est configurable — voir la section Paramètres → Codes-barres.

> **Conseil :** Le préfixe est imprimé sur les étiquettes générées par BCD4 (Admin → Étiquettes). Si tu changes le préfixe dans les Paramètres après avoir déjà imprimé des étiquettes, les anciennes étiquettes ne seront plus reconnues correctement.

---

## Cataloguer un lot d'exemplaires (lecture suivie)

Pour une lecture suivie en classe, tu as besoin de plusieurs exemplaires du même livre. Dans BCD4, une seule notice bibliographique peut avoir autant d'exemplaires que nécessaire.

**Comment procéder :**

1. Catalogue le livre une première fois normalement (ISBN → BNF → scan du premier code-barres).
2. Pour ajouter les exemplaires suivants : dans le catalogue, ouvre la fiche du livre, puis clique sur **« Ajouter un exemplaire »**.
3. Scanne le code-barres de chaque exemplaire supplémentaire l'un après l'autre.

> **Conseil :** Utilise une série d'étiquettes codes-barres consécutives (ex : `00120`, `00121`, `00122`…) pour faciliter le suivi du lot.

---

## Cataloguer une revue ou un magazine (périodique)

Dans BCD4, **une revue = une notice** dans le catalogue, et **chaque numéro physique reçu = un exemplaire** rattaché à cette notice. Le champ **Numérotation** de l'exemplaire identifie le numéro (ex : `274`, `Avril 2026`, `Hors-série été 2025`).

### Créer la notice d'un nouveau titre de revue

**Via le code EAN-13 du kiosque (recommandé) :**

1. Dans la page Catalogage, saisis ou scanne le code EAN-13 imprimé sur la couverture du magazine (le code à 13 chiffres commençant par `977`, ex : `9771163770025` pour Wakou).
2. Le système détecte automatiquement le préfixe `977` et extrait l'ISSN correspondant.
3. Il interroge le **SUDOC** (Système Universitaire de Documentation) pour récupérer le titre, l'éditeur et la description de la revue.
4. Vérifie les informations et valide la notice. Le **Type de support** est automatiquement réglé sur `Périodique`.
5. Scanne le code-barres d'inventaire de l'exemplaire, puis saisis la **Numérotation** (ex : `274`).

**Via l'ISSN saisi manuellement :**

1. Dans le champ **ISBN ou ISSN**, saisis le code ISSN au format `NNNN-NNNX` (ex : `1163-7706` pour *Wakou*). L'ISSN est imprimé sur la couverture ou au dos de la revue.
2. Le système reconnaît le format ISSN et interroge le SUDOC.
3. Suite identique à partir de l'étape 3 ci-dessus.

**Si la revue n'est pas trouvée dans le SUDOC :**
utilise la saisie manuelle — saisis le titre, renseigne l'ISSN si disponible, et choisis `Périodique` comme type de support.

### Bulletiner un nouveau numéro (workflow quotidien)

Quand un nouveau numéro arrive :

1. Dans le catalogue, ouvre la fiche de la revue (ex : « Wakou »).
2. Clique sur **« Ajouter un exemplaire »**.
3. Saisis la **Numérotation** (ex : `274` ou `Avril 2026`) — champ obligatoire pour les périodiques.
4. Scanne le code-barres d'inventaire de ce numéro physique.
5. L'exemplaire est immédiatement disponible au prêt.

> **Conseil :** La Numérotation s'affiche dans la fiche de la revue (colonne « Numérotation ») et dans le bilan de prêt (ex : « Wakou · n° 274 »). Utilise des numéros simples (`274`) plutôt que des libellés longs pour un affichage optimal.

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| L'ISBN n'est pas trouvé par la BNF | Utilise la saisie manuelle. Certains livres anciens ou étrangers ne sont pas dans la base BNF. |
| L'ISSN n'est pas trouvé dans le SUDOC | Utilise la saisie manuelle. Saisis le titre et l'ISSN manuellement, puis choisis `Périodique` comme type de support. |
| Le code-barres d'inventaire est déjà utilisé | Chaque exemplaire doit avoir un code-barres unique. Colle un nouveau code-barres sur ce livre. |
| Les informations récupérées sont incorrectes | Corrige manuellement les champs dans le formulaire avant de valider. |
