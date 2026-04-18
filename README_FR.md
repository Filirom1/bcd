# BCD — Gestion de bibliothèque scolaire

> Gestion simple et rapide pour les bibliothèques d'écoles élémentaires

**Pour** : Bibliothécaires scolaires, enseignants, personnel de bibliothèque &nbsp;|&nbsp; **Langues** : Français / Anglais

---

## Démarrage rapide

**Édition portable Windows** (sans installation) :
1. Télécharger et extraire `BCD-vX.X.X-Windows.zip`
2. Double-cliquer sur `bcd.exe` — l'application s'ouvre automatiquement

**Python** (toutes plateformes) :
```bash
python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
```
Puis ouvrir **http://127.0.0.1:8000** dans le navigateur.

---

## Fonctionnalités

### Prêt

![Prêt](docs/screenshots/01-checkout.png)

Scanner la carte d'élève pour charger sa fiche, puis scanner chaque code-barres de livre — le prêt est immédiat, aucune confirmation nécessaire. Le panneau gauche affiche la liste complète de la classe pour sélectionner un élève d'un clic.

La fiche emprunteur affiche les prêts en cours, les dates d'échéance et les réservations prêtes à être retirées. Les alertes de retard et de limite de prêt s'affichent automatiquement.

### Retour

![Retour](docs/screenshots/02-return.png)

Scanner les codes-barres des livres un par un — sans avoir besoin de sélectionner l'emprunteur. Chaque retour est immédiat. Le système affiche qui avait le livre et s'il était en retard.

### Renouvellement

Cliquer sur **Tout renouveler** dans l'écran de prêt ou dans la fiche emprunteur pour prolonger tous les livres éligibles d'une période de prêt. Le renouvellement livre par livre est également disponible depuis le tableau des prêts.

### Réservations

Réserver un livre pour un emprunteur depuis l'onglet **Réservations** de la fiche catalogue — rechercher l'emprunteur par nom ou code-barres. Les réservations actives apparaissent dans la fiche emprunteur lors du prêt avec un bouton de retrait en un clic. Les réservations peuvent être annulées à tout moment.

---

### Catalogue

![Catalogue](docs/screenshots/03-catalog.png)

Rechercher par titre, auteur, ISBN ou code-barres. Filtrer par disponibilité (disponible / en prêt / réservé), catégorie, genre, langue ou type de support. Chaque résultat affiche un badge de statut coloré et le nombre d'exemplaires disponibles.

Cliquer sur une notice pour ouvrir la fiche détaillée avec trois onglets :
- **Exemplaires** — tous les exemplaires physiques, leur statut et l'emprunteur actuel
- **Réservations** — réservations actives avec noms et positions dans la file
- **Historique** — historique de circulation paginé avec filtres par date

---

### Ajouter des livres (Catalogage)

![Catalogage](docs/screenshots/04-cataloging.png)

Flux de travail en trois étapes :

1. **Recherche ISBN** — scanner ou saisir l'ISBN ; les informations sont récupérées automatiquement depuis la Bibliothèque nationale de France (BNF). Cette étape peut être ignorée pour les livres sans ISBN.
2. **Vérifier les métadonnées** — modifier titre, auteur, éditeur, catégorie, genre, langue, public cible et autres champs.
3. **Créer les exemplaires** — scanner le code-barres de chaque exemplaire physique pour l'enregistrer. Plusieurs exemplaires peuvent être ajoutés en une seule session.

**Import en masse** : déposer un fichier CSV Dublin Core pour importer des centaines de livres en une fois. Les exports BiblioPuce sont également pris en charge (détection automatique du format).

---

### Emprunteurs

![Emprunteurs](docs/screenshots/05-borrowers.png)

Parcourir la liste complète des emprunteurs, filtrée par classe, rôle ou statut. Cliquer sur un emprunteur pour ouvrir sa fiche détaillée :

- Onglet **Prêts** — prêts en cours avec dates d'échéance, mise en évidence des retards, boutons de retour et de renouvellement par livre
- Onglet **Réservations** — réservations actives avec option d'annulation
- Onglet **Historique** — historique de circulation complet et paginé avec filtres par date

**Actions disponibles** :
- Bloquer / débloquer un emprunteur (livre perdu, violation de règlement, etc.)
- Renouveler tous les prêts éligibles en un clic
- Modifier les informations de l'emprunteur
- Édition en masse des emprunteurs sélectionnés (changer de classe, supprimer)

**Import / Export** : déposer un fichier CSV pour créer ou mettre à jour des emprunteurs en masse ; exporter la liste actuelle (respecte les filtres actifs) en CSV pour les sauvegardes ou les transitions de fin d'année.

**Impression** : générer des cartes de bibliothèque prêtes à imprimer (10 par page A4) ou des fiches de référence avec codes-barres, filtrées par classe.

---

### Classes

![Classes](docs/screenshots/06-classes.png)

Créer, modifier et supprimer les classes. Chaque classe contient le nom, le niveau scolaire, l'année en cours et le nom de l'enseignant référent. Les classes permettent de filtrer les emprunteurs sur toutes les pages et de regrouper les rapports de retard par classe.

---

### Rapports

**Retards** — tous les livres en retard regroupés par classe, avec noms des emprunteurs et nombre de jours de retard. Filtrable par classe. Prêt à imprimer.

![Rapport retards](docs/screenshots/07-reports-overdue.png)

**Les plus empruntés** — classement des titres les plus circulés sur une période donnée. Aide à identifier les achats à réaliser.

![Les plus empruntés](docs/screenshots/08-reports-most-borrowed.png)

**CREW - Désherbage** — évaluation systématique de la collection selon la méthode CREW. Six modes d'évaluation :
- **Jamais emprunté** — exemplaires jamais empruntés depuis leur acquisition
- **Faible rotation** — exemplaires avec ≤2 emprunts sur les 2 dernières années
- **Abîmés + anciens** — exemplaires abîmés présents depuis 3+ ans
- **Score élevé (≥5)** — candidats prioritaires au désherbage tous critères confondus
- **Jamais inventorié** — exemplaires jamais vérifiés physiquement (potentiellement manquants)
- **Doublons peu demandés** — titres avec 3+ exemplaires et faible rotation moyenne

Chaque exemplaire reçoit un score CREW (0-7+) basé sur l'âge dans la collection, la condition physique, l'année de publication et l'historique de circulation. Des badges de couleur (vert=conserver, orange=examiner, rouge=désherber) aident à prioriser les décisions. Des filtres avancés permettent d'affiner les résultats par catégorie, genre, niveau, public et type de support.

![CREW - Désherbage](docs/screenshots/09-reports-never-borrowed.png)

Tous les rapports ont un bouton d'impression pour une impression instantanée.

---

### Paramètres et sauvegardes

![Paramètres](docs/screenshots/10-settings.png)

Configurer le système : durée de prêt, limite de renouvellement, limite de prêt (élèves et enseignants), expiration des réservations, dates de l'année scolaire, nom de la bibliothèque, préfixes de codes-barres, langue et format de date.

La section **Sauvegardes** affiche la date de la dernière sauvegarde et liste toutes les sauvegardes existantes. Créer une sauvegarde, en télécharger une, restaurer depuis une sauvegarde ou supprimer les anciennes — tout depuis l'interface web.

---

### Impression

**Cartes de bibliothèque** (Admin → Imprimer les cartes) : grille de cartes d'identité (10 par page A4) avec nom, classe, identifiant et code-barres de l'élève. Filtrer par classe avant l'impression.

![Cartes élèves](docs/screenshots/11-print-cards.png)

**Étiquettes codes-barres** (Admin → Imprimer les étiquettes) : planches d'étiquettes compatibles Avery. Saisir l'identifiant de départ et la quantité ; le système réserve les identifiants et génère les étiquettes.

![Étiquettes](docs/screenshots/12-print-labels.png)

**Fiches de référence** (Admin → Imprimer les fiches) : regroupées par classe, avec l'identifiant et le code-barres de chaque emprunteur — utiles pour les enseignants lors des visites à la bibliothèque.

---

## Import et export

| Données | Format d'import | Format d'export |
|---------|----------------|----------------|
| Catalogue | CSV Dublin Core, CSV BiblioPuce | CSV Dublin Core |
| Emprunteurs | CSV BCD (borrower_id, first_name, last_name, class, role) | CSV BCD |

Les résultats d'import indiquent exactement combien de notices ont été créées, mises à jour, ignorées ou rejetées, avec le détail des erreurs par ligne.

L'export respecte toujours le filtre actif — exporter les emprunteurs d'une seule classe ou tout le catalogue.

---

## Configuration requise

- Navigateur moderne (Chrome, Firefox, Safari, Edge)
- Lecteur de codes-barres USB ou Bluetooth (optionnel — les codes-barres peuvent être saisis au clavier)
- Accès Internet uniquement pour la recherche ISBN via la BNF (optionnel)

---

## Sauvegarde et restauration

**Interface web** : Paramètres → section Sauvegardes → Créer une sauvegarde / Restaurer.

**CLI** (installation Python) :
```bash
bcd-cli admin backup
bcd-cli admin list-backups
bcd-cli admin restore backups/bcd_backup_20260205_143022.db --confirm
```

---

## Langue

Basculer entre le français et l'anglais avec le bouton FR / EN dans la barre de navigation. Le français est la langue par défaut.

---

## Licence

MIT — voir le fichier `LICENSE` pour les détails.
