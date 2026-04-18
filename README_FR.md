# BCD — Bibliothèque que Claude a Développée

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

**Client Godot** (interface pour CP-CM2) :
- Télécharger depuis [Releases](https://github.com/Filirom1/bcd/releases) (Windows/Linux)
- Découverte automatique des serveurs BCD sur le réseau (mDNS)
- Nécessite un serveur BCD API en cours d'exécution

Voir [`bcd_kids/README.md`](bcd_kids/README.md) pour les détails.

---

## Clients

### Interface web (par défaut)

L'interface web principale s'exécute dans le navigateur et offre toutes les fonctionnalités de gestion de bibliothèque pour les bibliothécaires et le personnel.

### Client Godot (enfants)

![Client Godot](docs/screenshots/13-godot-client.png)

Interface colorise et tactile Godot 4.6, conçue pour les élèves de primaire (6-11 ans) :

**Fonctionnalités** :
- Découverte automatique des serveurs BCD sur le réseau (mDNS)
- Emprunter des livres (scan de code-barres)
- Rendre des livres
- Rechercher dans le catalogue avec filtres
- Gérer les réservations
- Bilingue (FR/EN)

**Plateformes** : Windows (`.exe` 64 bits), Linux (`.x86_64` 64 bits)

**Prérequis** : Un serveur BCD API doit être en cours d'exécution sur le réseau.

**Documentation** : [`bcd_kids/README.md`](bcd_kids/README.md)

---

## Fonctionnalités

### Prêt

![Prêt](docs/screenshots/01-checkout.png)

Scanner la carte d'élève pour charger sa fiche, puis scanner chaque code-barres de livre — le prêt est immédiat, aucune confirmation nécessaire. Le panneau gauche affiche la liste complète de la classe pour sélectionner un élève d'un clic.

La fiche emprunteur affiche les prêts en cours, les dates d'échéance et les réservations prêtes à être retirées. Les alertes de retard et de limite de prêt s'affichent automatiquement.

[→ Aide détaillée](docs/help/fr/emprunter.md)

### Retour

![Retour](docs/screenshots/02-return.png)

Scanner les codes-barres des livres un par un — sans avoir besoin de sélectionner l'emprunteur. Chaque retour est immédiat. Le système affiche qui avait le livre et s'il était en retard.

[→ Aide détaillée](docs/help/fr/retourner.md)

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

[→ Aide détaillée](docs/help/fr/catalogue.md)

---

### Ajouter des livres (Catalogage)

![Catalogage](docs/screenshots/04-cataloging.png)

Flux de travail en trois étapes :

1. **Recherche ISBN / ISSN** — scanner ou saisir l'ISBN (livres) ou l'ISSN (revues / périodiques) ; les informations sont récupérées automatiquement depuis la Bibliothèque nationale de France (BNF). Cette étape peut être ignorée pour les livres sans identifiant.
2. **Vérifier les métadonnées** — modifier titre, auteur, éditeur, catégorie, genre, langue, public cible et autres champs.
3. **Créer les exemplaires** — scanner le code-barres de chaque exemplaire physique pour l'enregistrer. Plusieurs exemplaires peuvent être ajoutés en une seule session.

**Import en masse** : déposer un fichier CSV Dublin Core pour importer des centaines de livres en une fois. Les exports BiblioPuce sont également pris en charge (détection automatique du format).

[→ Aide détaillée](docs/help/fr/catalogage.md)

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

**RGPD** : BCD stocke le nom, le prénom, la classe et le numéro d'emprunteur. Les données de prêt doivent être supprimées dans les 4 mois suivant le retour (délibération CNIL n° 99-27). Utiliser la suppression groupée dans la liste des emprunteurs pour purger les fiches en fin d'année.

[→ Aide détaillée](docs/help/fr/eleves.md)

---

### Classes

![Classes](docs/screenshots/06-classes.png)

Créer, modifier et supprimer les classes. Chaque classe contient le nom, le niveau scolaire, l'année en cours et le nom de l'enseignant référent. Les classes permettent de filtrer les emprunteurs sur toutes les pages et de regrouper les rapports de retard par classe.

[→ Aide détaillée](docs/help/fr/classes.md)

---

### Inventaire

La page Inventaire permet d'effectuer le récolement physique et le désherbage du fonds :

- **Onglet Scanner** — scanner les codes-barres un par un pour marquer les exemplaires comme vérifiés ; le scanner garde le focus pour des scans rapides successifs
- **Onglet Importer un fichier** — importer un fichier texte de codes-barres (un par ligne) depuis une douchette portable
- **Onglet Rechercher** — trouver des exemplaires avec des filtres avancés (statut, état, jamais inventorié, faible rotation, type de support, public, genre, langue, année de publication) et les ajouter à la table de travail

La **table de travail** persiste dans le navigateur. On peut y faire une modification groupée (statut, état, emplacement, type de support, genre, niveau, public), supprimer des exemplaires et des notices orphelines, et exporter un rapport d'inventaire en CSV.

[→ Aide détaillée](docs/help/fr/inventaire.md)

---

### Rapports

**Retards** — tous les livres en retard regroupés par classe, avec noms des emprunteurs et nombre de jours de retard. Filtrable par classe. Prêt à imprimer.

![Rapport retards](docs/screenshots/07-reports-overdue.png)

**Les plus empruntés** — classement des titres les plus circulés sur une période donnée. Aide à identifier les achats à réaliser.

![Les plus empruntés](docs/screenshots/08-reports-most-borrowed.png)

**Prêts en cours** — liste complète de tous les exemplaires actuellement empruntés, avec emprunteur, date d'échéance et statut de retard. Utile pour un bilan rapide du fonds.

**Réservations** — liste de toutes les réservations actives avec leur statut (en attente / prête / expirée).

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

[→ Aide détaillée](docs/help/fr/rapports.md)

---

### Fonds (bibliothèques en réseau)

La page Fonds découvre automatiquement les autres bibliothèques BCD sur le même réseau scolaire (via mDNS — aucune configuration nécessaire). Chaque bibliothèque découverte s'affiche sous forme de carte ; cliquer sur **Ouvrir Fond** pour parcourir son catalogue dans un nouvel onglet.

Utile pour éviter les achats en double entre bâtiments et pour coordonner les prêts inter-bibliothèques.

[→ Aide détaillée](docs/help/fr/fonds.md)

---

### Paramètres et sauvegardes

![Paramètres](docs/screenshots/10-settings.png)

Configurer le système : durée de prêt, limite de renouvellement, limite de prêt (élèves et enseignants), expiration des réservations, dates de l'année scolaire, nom de la bibliothèque, préfixes de codes-barres, langue et format de date.

La section **Sauvegardes** affiche la date de la dernière sauvegarde et liste toutes les sauvegardes existantes. Créer une sauvegarde, en télécharger une, restaurer depuis une sauvegarde ou supprimer les anciennes — tout depuis l'interface web.

[→ Aide détaillée](docs/help/fr/parametres.md)

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
