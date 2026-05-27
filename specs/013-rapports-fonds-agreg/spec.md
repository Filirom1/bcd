# Feature Specification: Rapports fonds avec agrégations visuelles et filtres interactifs

**Feature Branch**: `013-rapports-fonds-agreg`
**Created**: 2026-04-22
**Status**: Draft

## Contexte

Les rapports "Jamais empruntés" et "À désherber (CREW)" sont deux vues très proches sur le même jeu de données (exemplaires de la BCD). Actuellement ils ont chacun leurs propres filtres dropdown redondants et aucune visualisation agrégée. L'objectif est de les unifier sous une même page avec des filtres interactifs visuels.

## User Scenarios & Testing

### User Story 1 — Naviguer entre les deux vues du rapport fonds (Priority: P1)

La bibliothécaire ouvre la page Rapports et souhaite basculer entre "Jamais empruntés" et "À désherber (CREW)" sans perdre ses filtres actifs.

**Why this priority**: C'est le point d'entrée de la fonctionnalité — tout le reste en dépend.

**Independent Test**: Cliquer sur le toggle bascule la liste et le titre, les filtres communs restent actifs.

**Acceptance Scenarios**:

1. **Given** la page Rapports est ouverte sur "Jamais empruntés", **When** la bibliothécaire clique sur "À désherber (CREW)", **Then** la liste se met à jour avec les exemplaires CREW et les agrégations se recalculent.
2. **Given** un filtre "Genre : Fiction" est actif, **When** la bibliothécaire bascule de vue, **Then** le filtre reste actif et s'applique à la nouvelle vue.

---

### User Story 2 — Filtrer par breakdown bar cliquable (Priority: P1)

La bibliothécaire voit la répartition par genre et clique sur "Documentaire" pour n'afficher que les documentaires jamais empruntés.

**Why this priority**: Remplace les dropdowns redondants par une interaction plus directe et informative.

**Independent Test**: Cliquer sur une ligne de breakdown filtre le tableau et les autres breakdowns se recalculent. La ligne cliquée est mise en évidence.

**Acceptance Scenarios**:

1. **Given** la page affiche 142 exemplaires avec les breakdowns, **When** la bibliothécaire clique sur "Documentaire" dans le breakdown "Par genre", **Then** le tableau n'affiche que les documentaires, les autres breakdowns (support, public, état) se recalculent sur ce sous-ensemble.
2. **Given** un filtre "Genre : Documentaire" est actif, **When** la bibliothécaire reclique sur "Documentaire", **Then** le filtre est désactivé et on retrouve l'ensemble initial.
3. **Given** un filtre breakdown est actif, **When** la bibliothécaire clique sur une autre valeur du même breakdown, **Then** le filtre est remplacé (pas cumulé).

---

### User Story 3 — Filtrer via les histogrammes interactifs (Priority: P2)

La bibliothécaire clique sur une barre de l'histogramme "Année de publication" pour isoler les livres publiés entre 2012 et 2013 (barres rouges, >10 ans).

**Why this priority**: Permet de cibler rapidement les ouvrages anciens à désherber en priorité.

**Independent Test**: Cliquer sur une barre filtre le tableau. Les barres non-sélectionnées s'estompent. Un chip apparaît dans la barre de filtres actifs.

**Acceptance Scenarios**:

1. **Given** l'histogramme "Année de publication" est affiché, **When** la bibliothécaire clique sur la barre "2013", **Then** le tableau filtre sur les ouvrages publiés dans cette plage, les autres barres s'estompent, et un chip "Publication : 2013" apparaît.
2. **Given** un filtre publication est actif, **When** la bibliothécaire clique à côté d'une barre (zone vide), **Then** le filtre est désactivé.
3. **Given** l'histogramme "Acquisitions dans le temps" est affiché, **When** la bibliothécaire clique sur la barre "2019", **Then** seuls les exemplaires acquis en 2019 sont affichés et la ligne "dont abîmés" se recalcule.

---

### User Story 4 — Gérer les filtres actifs via les chips (Priority: P2)

La bibliothécaire a plusieurs filtres actifs (genre + année publication) et souhaite en retirer un sans perdre les autres.

**Why this priority**: Cohérence avec le pattern existant de BorrowerFilters.js — l'utilisateur doit toujours voir et contrôler ses filtres actifs.

**Independent Test**: Chaque chip a un bouton × qui retire uniquement ce filtre. "Tout effacer" réinitialise tous les filtres.

**Acceptance Scenarios**:

1. **Given** deux filtres actifs (Genre : Fiction, Publication : 2013), **When** la bibliothécaire clique sur × du chip "Publication : 2013", **Then** seul ce filtre est retiré, "Genre : Fiction" reste actif.
2. **Given** plusieurs filtres actifs, **When** la bibliothécaire clique sur "Tout effacer", **Then** tous les filtres sont supprimés, les chips disparaissent, le tableau affiche tous les exemplaires.
3. **Given** aucun filtre actif, **Then** la barre de chips est masquée.

---

### User Story 5 — Filtrer via le panneau filtre simplifié (Priority: P3)

La bibliothécaire sélectionne la méthode CREW "Faible rotation" et "dans la collection depuis > 2 ans" pour cibler les livres peu empruntés et anciens.

**Why this priority**: Ces filtres structurels (méthode CREW, ancienneté) ne sont pas représentables visuellement — ils restent dans le panneau.

**Independent Test**: Changer la méthode CREW recharge les données. Changer l'ancienneté filtre côté serveur.

**Acceptance Scenarios**:

1. **Given** la méthode CREW "Jamais empruntés" est sélectionnée, **When** la bibliothécaire choisit "Faible rotation", **Then** la liste se recharge avec les exemplaires ayant ≤ 2 emprunts sur 24 mois et les agrégations se recalculent.
2. **Given** "dans la collection depuis > 1 an" est sélectionné, **When** la bibliothécaire passe à "> 3 ans", **Then** seuls les exemplaires acquis il y a plus de 3 ans sont affichés.
3. **Given** la case "Exclure périodiques" est cochée (défaut), **Then** les périodiques n'apparaissent ni dans le tableau ni dans les breakdowns.

---

### Edge Cases

- Qu'arrive-t-il si une combinaison de filtres donne 0 résultat ? → Message "Aucun ouvrage ne correspond aux filtres actifs."
- Que montrent les breakdowns si tous les exemplaires ont le même genre ? → Une seule barre à 100%.
- Que se passe-t-il si `acquisition_date` est NULL pour certains exemplaires ? → Exclus de l'histogramme acquisitions, inclus dans les autres agrégations.
- Que se passe-t-il si `publication_year` est NULL ? → Exclus de l'histogramme publications.
- Filtres croisés sur la même dimension que le graphe : le graphe affiche la distribution complète (hors filtre propre) avec les barres non-sélectionnées estompées.
- Que se passe-t-il si Chart.js n'est pas chargé (script tag manquant) ? → Les canvas restent vides, le tableau et les breakdowns continuent de fonctionner (dégradation gracieuse).

## Requirements

### Functional Requirements

**Page & navigation**

- **FR-001**: La page Rapports DOIT proposer un toggle entre "Jamais empruntés" et "À désherber (CREW)" sans rechargement complet de page.
- **FR-002**: Le toggle DOIT conserver les filtres communs actifs lors du changement de vue.

**Panneau filtre (simplifié)**

- **FR-003**: Le panneau filtre DOIT contenir uniquement : méthode CREW (radio buttons), ancienneté dans la collection (select), case "Exclure périodiques".
- **FR-004**: Les dropdowns Support / Genre / Public DOIVENT être supprimés du panneau filtre (remplacés par les breakdowns cliquables).

**Breakdown bars**

- **FR-005**: La page DOIT afficher 4 breakdown bars : par support, par genre, par public, par état.
- **FR-006**: Chaque ligne de breakdown DOIT être cliquable et appliquer un filtre sur la valeur correspondante.
- **FR-007**: Un second clic sur une ligne active DOIT désactiver le filtre (toggle).
- **FR-008**: Les breakdowns DOIVENT se recalculer sur les données filtrées (filtres croisés), sauf pour leur propre dimension qui affiche la distribution complète avec les barres non-sélectionnées estompées.

**Histogrammes**

- **FR-009**: La page DOIT afficher un histogramme "Répartition par année de publication" avec code couleur : rouge (>10 ans), jaune (5-10 ans), bleu (<5 ans).
- **FR-010**: La page DOIT afficher un histogramme "Acquisitions dans le temps" (par année) avec une ligne secondaire "dont abîmés".
- **FR-011**: Cliquer sur une barre d'histogramme DOIT appliquer un filtre sur la plage correspondante.
- **FR-012**: Les barres non-sélectionnées DOIVENT s'estomper visuellement quand un filtre est actif sur cette dimension.
- **FR-013**: Cliquer sur une zone vide du graphe DOIT désactiver le filtre de cette dimension.

**Chips filtres actifs**

- **FR-014**: Chaque filtre actif DOIT apparaître sous forme de chip supprimable dans une barre dédiée (pattern BorrowerFilters.js).
- **FR-015**: Le bouton × sur un chip DOIT retirer uniquement ce filtre.
- **FR-016**: Un bouton "Tout effacer" DOIT réinitialiser l'ensemble des filtres.
- **FR-017**: La barre de chips DOIT être masquée quand aucun filtre n'est actif.

**Agrégations serveur**

- **FR-018**: Les données des breakdowns et histogrammes DOIVENT être calculées côté serveur via un nouvel endpoint `GET /api/v1/reports/collection-stats` utilisant des requêtes SQLite (`GROUP BY`, `COUNT`, `strftime`). Le tableau des résultats continue d'utiliser l'endpoint existant `/api/v1/inventory/items/search`.
- **FR-019**: Les agrégations DOIVENT prendre en compte les filtres actifs (méthode CREW, ancienneté, exclure périodiques, et les cross-filters de dimension) transmis en paramètres de requête.
- **FR-021**: L'endpoint `/api/v1/inventory/items/search` DOIT accepter un nouveau paramètre `never_borrowed: bool` pour filtrer sur `Item.last_borrowed_at IS NULL` côté serveur (supprime le filtrage client-side existant dans `NeverBorrowedReport.js`).

**Vendoring**

- **FR-020**: Chart.js DOIT être vendoré dans `src/bcd_web_vue/vendor/js/` (pas de CDN en production). Le global `window.Chart` est utilisé directement dans les composants Vue (pattern identique à Vue, VueRouter, VueI18n).

### Key Entities

- **Exemplaire (Item)** : unité physique — barcode, état, statut, date d'acquisition, emplacement, loanable
- **Notice bibliographique (BiblographicRecord)** : titre, auteurs, genre, support, public, année de publication, cote Dewey
- **Transaction de circulation (CirculationTransaction)** : date d'emprunt, date de retour — sert à calculer le score CREW et les comptages d'agrégation

## Success Criteria

### Measurable Outcomes

- **SC-001**: La bibliothécaire peut passer de "Jamais empruntés" à "À désherber" en 1 clic sans perdre ses filtres.
- **SC-002**: Appliquer ou retirer un filtre (breakdown ou histogramme) met à jour le tableau et les agrégations en moins de 500 ms sur un vieux PC (2 GHz, 4 GB RAM, HDD).
- **SC-003**: Le panneau filtre ne contient plus que 3 contrôles (méthode CREW, ancienneté, exclure périodiques) — réduction de ~60% par rapport à l'existant.
- **SC-004**: L'ensemble des filtres actifs est visible en un coup d'œil (barre de chips) sans avoir à inspecter chaque contrôle individuellement.
- **SC-005**: Les agrégations (breakdowns + histogrammes) reflètent fidèlement les filtres croisés actifs — 0 incohérence entre le tableau et les graphes.
- **SC-006**: La page fonctionne sans connexion internet (Chart.js vendoré, pas de CDN).

## Assumptions

- `NeverBorrowedReport.js` est remplacé par `CollectionReport.js` — pas de duplication. Le slug de route `never-borrowed` reste inchangé pour ne pas casser les favoris existants.
- Un seul filtre par dimension est possible (pas de multi-sélection dans les breakdowns).
- Le **tableau** charge ses données depuis `/inventory/items/search` avec `never_borrowed=true` (nouveau param). Les **agrégations** (breakdowns + histogrammes) passent par le nouvel endpoint `/reports/collection-stats`.
- Chart.js v4 est la version à vendorer. Il s'enregistre sur `window.Chart` — les composants Vue l'utilisent via ce global, sans import ES module, cohérent avec le pattern des autres vendors (Vue, VueRouter, etc.).
- `publication_year` dans `BiblographicRecord` est un `INTEGER` — pas besoin de `strftime` pour l'histogramme, `GROUP BY BiblographicRecord.publication_year` suffit.
- `acquisition_date` dans `Item` est une colonne `Date` stockée comme chaîne `'YYYY-MM-DD'` en SQLite — `func.strftime('%Y', Item.acquisition_date)` est utilisé pour grouper par année.
- La détection "jamais emprunté" utilise `Item.last_borrowed_at IS NULL` (champ dénormalisé) pour cohérence avec le comportement client-side actuel de `NeverBorrowedReport.js`. La subquery sur `CirculationTransaction` existante dans `report_service.get_never_borrowed_items()` n'est pas réutilisée.
- Les cross-filters (genre, medium_type, target_audience, condition, pub_year, acq_year) sont envoyés comme paramètres query à `/reports/collection-stats`. Chaque appel reçoit tous les filtres actifs ; l'estompage des barres non-sélectionnées est purement visuel côté client (opacité CSS), sans second appel API.
- Les filtres cross-dimension ne sont pas synchronisés avec l'URL (trop volatils) — seuls les filtres structurels (méthode CREW, ancienneté) pourraient l'être dans une version future.
- Le composant gère lui-même la destruction/reconstruction des instances Chart.js lors des changements de données (via `chart.destroy()` + re-init dans un `watch`).
