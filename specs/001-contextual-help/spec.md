# Feature Specification: Aide Contextuelle Intégrée

**Feature Branch**: `001-contextual-help`
**Created**: 2026-03-27
**Status**: Draft
**Input**: Intégration de pages d'aide (manuel utilisateur) accessibles directement sur chaque page, adressées au personnel encadrant (enseignants, non-informaticiens), avec contenu pas-à-pas en FR et EN au format markdown, illustré de captures d'écran générées avec données réelles.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Consulter l'aide sur la page Emprunter (Priority: P1)

Une maitresse arrive sur la page d'emprunt pour la première fois. Elle ne sait pas comment chercher un élève ni scanner un livre. Elle clique sur le bouton « Aide » visible dans l'en-tête de la page. Un panneau s'ouvre à droite avec des instructions numérotées, des captures d'écran annotées et des conseils pratiques pour prêter un ou plusieurs livres à un élève.

**Why this priority**: C'est l'action quotidienne la plus fréquente dans une bibliothèque scolaire. Une erreur ou une hésitation sur cette page bloque toute la classe.

**Independent Test**: Ouvrir `/checkout`, cliquer "Aide", vérifier que le panneau affiche les instructions d'emprunt pas-à-pas illustrées. Fonctionne indépendamment de toutes les autres pages.

**Acceptance Scenarios**:

1. **Given** l'enseignante est sur la page Emprunter, **When** elle clique le bouton « Aide », **Then** un panneau latéral s'ouvre depuis la droite avec le titre « Emprunter des livres » et des instructions numérotées
2. **Given** le panneau d'aide est ouvert, **When** l'enseignante fait défiler, **Then** elle voit au moins 3 étapes illustrées de captures d'écran avec données réelles (un élève nommé, un livre avec titre, une confirmation d'emprunt)
3. **Given** le panneau d'aide est ouvert, **When** l'enseignante clique en dehors du panneau ou sur le bouton fermer, **Then** le panneau se ferme et la page reste utilisable sans perte de données
4. **Given** l'interface est en français, **When** le panneau d'aide s'ouvre, **Then** le contenu est entièrement en français

---

### User Story 2 — Aide contextuelle sur chaque page principale (Priority: P1)

Chaque page de l'application (Emprunter, Retourner, Catalogue, Catalogage, Élèves, Classes, Rapports, Paramètres) dispose d'un bouton « Aide » accessible. Le contenu du panneau est spécifique à la page en cours — l'aide de la page Catalogue explique la recherche, pas les retours.

**Why this priority**: Sans aide contextuelle sur chaque page, les enseignants doivent chercher une documentation externe ou mémoriser toutes les fonctions. La contextualité est le cœur de la valeur.

**Independent Test**: Naviguer vers chaque page et vérifier que le bouton Aide est présent dans l'en-tête et ouvre un contenu différent et pertinent pour cette page.

**Acceptance Scenarios**:

1. **Given** l'enseignante est sur n'importe laquelle des 8 pages principales, **When** elle cherche le bouton Aide, **Then** elle le trouve dans l'en-tête de la page sans avoir à faire défiler
2. **Given** l'enseignante passe de la page Emprunter à la page Retourner, **When** elle ouvre l'aide sur chaque page, **Then** les contenus sont différents et spécifiques à chaque fonctionnalité
3. **Given** le panneau d'aide est ouvert sur une page, **When** l'enseignante navigue vers une autre page, **Then** le panneau se ferme automatiquement

---

### User Story 3 — Aide disponible en français et en anglais (Priority: P2)

L'interface BCD supporte le français et l'anglais. Le contenu d'aide suit la langue choisie par l'utilisateur. Quand l'interface passe en anglais, les instructions d'aide passent en anglais.

**Why this priority**: Les écoles bilingues et les enseignants anglophones doivent pouvoir utiliser l'aide dans leur langue. Priorité secondaire car la majorité des utilisateurs est francophone.

**Independent Test**: Changer la langue de l'interface en anglais, ouvrir l'aide sur n'importe quelle page, vérifier que le contenu est en anglais.

**Acceptance Scenarios**:

1. **Given** l'interface est configurée en anglais, **When** l'enseignante ouvre l'aide, **Then** le titre, les instructions et les légendes des captures sont en anglais
2. **Given** le panneau d'aide est ouvert en français, **When** l'enseignante change la langue vers l'anglais, **Then** le contenu du panneau se met à jour automatiquement en anglais sans fermer le panneau
3. **Given** le contenu d'aide en français est indisponible pour une section, **When** l'aide est demandée, **Then** le contenu anglais est affiché sans message d'erreur bloquant

---

### User Story 4 — Captures d'écran avec données réalistes (Priority: P2)

Les captures d'écran illustrant l'aide montrent de vrais élèves, de vrais livres, de vrais prêts — pas des interfaces vides. Un script génère automatiquement ces captures après avoir peuplé la base avec 9 mois d'activité simulée couvrant tous les cas décrits dans l'aide.

**Why this priority**: Des captures vides ne correspondent pas à ce que voit l'enseignante et créent de la confusion. La reconnaissance visuelle est essentielle pour un public non-technique.

**Independent Test**: Lancer le script de génération et vérifier que les images produites montrent des données reconnaissables (noms d'élèves, titres de livres, dates de retour).

**Acceptance Scenarios**:

1. **Given** la base de données contient des données simulées réalistes, **When** le script de capture est exécuté, **Then** les images montrent des élèves nommés, des livres avec titres et auteurs, et des dates de prêt cohérentes
2. **Given** les captures sont régénérées, **When** elles s'affichent dans le panneau d'aide, **Then** chaque capture correspond exactement à l'étape décrite dans le texte adjacent
3. **Given** le script de simulation est lancé, **When** il se termine, **Then** la base contient au minimum : des prêts en retard actifs, des élèves bloqués manuellement, des réservations en attente (waiting et ready), des articles en réparation, des prêts renouvelés, un enseignant avec plusieurs livres empruntés

---

### User Story 5 — Régénérer les captures après mise à jour (Priority: P3)

L'administrateur système peut régénérer les captures en exécutant un script unique, sans connaissance technique approfondie. Le script documente son propre usage.

**Why this priority**: Les captures doivent rester à jour si l'interface évolue. Priorité basse car la régénération est un acte administratif ponctuel.

**Independent Test**: Exécuter `python scripts/generate_help_screenshots.py` seul et vérifier que les images sont mises à jour dans le bon dossier.

**Acceptance Scenarios**:

1. **Given** le serveur BCD est lancé avec des données simulées, **When** l'administrateur exécute le script de capture, **Then** toutes les captures sont régénérées sans intervention manuelle supplémentaire
2. **Given** le script échoue sur une capture spécifique, **When** il se termine, **Then** il liste les échecs et continue les autres captures (pas d'arrêt brutal)

---

### Edge Cases

- Que se passe-t-il si le fichier markdown met du temps à charger (réseau lent) ? → Afficher un indicateur de chargement, puis le contenu quand disponible
- Que se passe-t-il si un fichier markdown est absent (section sans aide rédigée) ? → Afficher un message informatif « Aide non disponible pour cette page »
- Que se passe-t-il si les captures d'écran ne se chargent pas (images absentes) ? → Le texte reste lisible et utile sans les images
- Que se passe-t-il si le script de capture échoue sur une page spécifique ? → Le script continue les autres captures et liste les échecs en fin d'exécution
- Que se passe-t-il si la fenêtre est trop étroite pour le panneau latéral ? → Le panneau s'adapte à la largeur disponible sans masquer les contrôles essentiels

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Chaque page principale (Emprunter, Retourner, Catalogue, Catalogage, Élèves, Classes, Rapports, Paramètres) DOIT afficher un bouton « Aide » dans son en-tête de page
- **FR-002**: Le bouton Aide DOIT ouvrir un panneau latéral sans quitter la page ni interrompre le travail en cours
- **FR-003**: Le panneau DOIT afficher du contenu spécifique à la page en cours (contenu distinct pour chacune des 8 pages)
- **FR-004**: Le contenu DOIT être structuré en étapes numérotées avec titres de sections, rédigé par des développeurs et versionné dans le dépôt git ; le markdown complet (tableaux, HTML inline, images) est admissible
- **FR-005**: Chaque étape clé DOIT être illustrée d'une capture d'écran montrant l'interface avec des données réalistes
- **FR-006**: Le panneau DOIT afficher le contenu dans la langue active de l'interface (français ou anglais)
- **FR-007**: Un changement de langue DOIT mettre à jour le contenu du panneau d'aide automatiquement
- **FR-008**: Un script de génération de captures DOIT exister et s'exécuter de bout en bout sans intervention manuelle au-delà du lancement
- **FR-009**: Le script de simulation (`reset_and_simulate.py`) DOIT générer au minimum les états suivants : prêts actifs en retard, élèves bloqués manuellement, réservations en file d'attente (statut waiting), réservations prêtes à retirer (statut ready), articles en réparation, prêts renouvelés au moins une fois, enseignants avec plusieurs livres empruntés simultanément
- **FR-010**: Les captures DOIVENT être accessibles via l'URL de l'application sans configuration supplémentaire du serveur ; elles sont chargées à la demande (au clic sur Aide, pas au démarrage de l'application) au format PNG pleine résolution
- **FR-011**: Le contenu d'aide DOIT rester lisible et utile si les captures d'écran ne se chargent pas (dégradation gracieuse)

### Key Entities

- **HelpSection** : Identifiant de page (ex : `checkout`) + langue (fr/en) + contenu markdown + liste de captures associées. Existe en deux langues pour chacune des 8 pages principales.
- **HelpScreenshot** : Image de capture générée automatiquement, nommée de façon descriptive, associée à une étape spécifique de l'aide d'une page.
- **SimulationScenario** : État base de données représentant un cas d'utilisation spécifique (ex : prêt en retard, élève bloqué, réservation prête…) nécessaire à la cohérence visuelle des captures.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Une enseignante sans formation préalable peut compléter son premier emprunt de livre en moins de 3 minutes en consultant uniquement le panneau d'aide
- **SC-002**: Les 8 pages principales ont toutes un bouton Aide fonctionnel et un contenu distinct
- **SC-003**: Le contenu d'aide est disponible en français et en anglais pour toutes les sections
- **SC-004**: Les captures d'écran montrent des données reconnaissables (noms, titres, dates) et non des états vides
- **SC-005**: Le script de génération de captures s'exécute en moins de 5 minutes et produit des images pour toutes les sections sans erreur
- **SC-006**: Le script de simulation couvre les 7 scénarios listés en FR-009 (vérifiable par inspection de la base de données après exécution)
- **SC-007**: Le panneau d'aide s'ouvre en moins de 2 secondes sur le matériel cible (ordinateur de 5 ans, accès local)

---

## Assumptions

- Les captures d'écran sont en français uniquement (une série partagée entre les deux versions du manuel) car la majorité des utilisateurs est francophone et les captures restent compréhensibles visuellement
- Les fichiers d'aide sont servis statiquement via le même serveur que l'application (pas d'API dédiée)
- Les fichiers markdown d'aide sont maintenus par les développeurs et versionnés dans le dépôt git ; les enseignants n'ont pas d'accès direct à ces fichiers
- Les captures sont régénérées manuellement par un développeur après chaque mise à jour majeure de l'interface (pas de régénération automatique en CI)
- L'aide ne couvre pas les pages d'impression (`/print/*`) car elles sont des utilitaires rarement utilisés de façon autonome
- Le rendu du contenu markdown est réalisé côté navigateur

---

## Clarifications

### Session 2026-03-27

- Q: Qui rédige et maintient les fichiers markdown du contenu d'aide ? → A: Développeurs uniquement — fichiers édités et versionnés dans le dépôt git
- Q: Format et chargement des captures d'écran ? → A: PNG pleine résolution, chargement à la demande (lazy load au clic sur Aide)

---

## Dependencies

- Bootstrap 5.3 offcanvas (déjà inclus dans le projet via `vendor/js/bootstrap.bundle.min.js`)
- Bibliothèque de rendu markdown (à ajouter comme dépendance vendorisée, fonctionnement hors-ligne)
- Playwright (déjà utilisé pour les tests E2E du projet, à réutiliser pour le script de captures)
- `scripts/reset_and_simulate.py` (à enrichir pour couvrir les scénarios FR-009)
