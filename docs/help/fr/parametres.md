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

## Étape 6 — Règles de génération automatique des cotes

Ces règles permettent de pré-remplir automatiquement la **cote** d'un livre lors du catalogage en fonction de son type de support et/ou de son emplacement de rayonnage. 

Le système applique la **première règle correspondante (de haut en bas)**.

### Support du caractère joker (wildcard `*`)
Pour éviter de dupliquer les règles lorsque vous avez des sous-emplacements ou des types de supports personnalisés, vous pouvez utiliser le caractère `*` comme joker sur l'emplacement ou le type de support :
- Un emplacement configuré comme `Documentaires*` s'appliquera automatiquement à `Documentaires`, `Documentaires - Sciences`, `Documentaires - Nature`, etc.
- Un type de support configuré comme `Livre*` s'appliquera à `Livre`, `Livre audio`, etc.
- Une valeur configurée comme `*` s'appliquera à n'importe quel texte.

### Variables disponibles dans les modèles (pattern) :
- `{AUT1}` / `{AUT3}` : 1 ou 3 premières lettres du nom de l'auteur (majuscules, nettoyées de tout accent et article).
- `{SER1}` / `{SER3}` : 1 ou 3 premières lettres de la collection/série (ou de l'auteur si absente).
- `{TIT1}` / `{TIT3}` : 1 ou 3 premières lettres du titre (ignorant les articles de début).
- `{DEWEY}` : L'indice de classification Dewey (utilisé pour les documentaires).

## Étape 7 — Sauvegarder les paramètres

Clique sur **« Enregistrer »** pour appliquer tous les changements.
Un message de confirmation apparaît en haut de l'écran.

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| La nouvelle durée de prêt ne s'applique pas aux anciens emprunts | Les paramètres ne s'appliquent qu'aux nouveaux emprunts. Les anciens conservent leur date d'échéance. |
| Le scanner ne distingue pas les cartes des livres | Vérifie que les préfixes emprunteur et article sont bien configurés et différents. |
| Les modifications ne sont pas sauvegardées | Clique sur le bouton « Enregistrer » pour valider les changements. |

---

## Étape 8 — Paramètres avancés (Fichier de configuration .env)

Pour les écoles gérant elles-mêmes leur installation ou souhaitant personnaliser le dossier de sauvegarde, de stockage des images ou la base de données, BCD propose d'éditer directement son fichier de configuration.

![Fichier de configuration .env](../images/settings-env.png)

### Pourquoi modifier ces paramètres ?
Ce volet s'adresse aux personnes qui s'occupent de l'installation informatique de l'école (enseignant référent pour le numérique, équipe technique de la mairie, etc.). Il permet par exemple de :
* **Changer de base de données** : pour passer d'un fonctionnement local à une base partagée entre plusieurs ordinateurs de l'école (PostgreSQL).
* **Déplacer les dossiers de stockage** : si vous préférez enregistrer vos sauvegardes automatiques ou vos couvertures d'images sur une clé USB ou un disque réseau plutôt que sur l'ordinateur principal.

### Comment modifier un paramètre ?
1. Modifiez ou ajoutez les lignes de configuration dans la zone de texte. Les lignes commençant par un `#` sont de simples commentaires informatifs.
2. Cliquez sur **« Enregistrer »**.
3. **IMPORTANT :** Vous devez redémarrer complètement le logiciel BCD pour que ces nouveaux dossiers ou configurations soient pris en compte.

### Tous les paramètres du .env expliqués

Voici la liste complète des paramètres personnalisables dans votre fichier `.env`, classés par catégorie :

#### 1. Base de données et dossiers de stockage personnalisés
*Utile pour déplacer vos données sur un disque réseau, une clé USB, ou utiliser un serveur externe de base de données PostgreSQL.*

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| **`DATABASE_URL`** | `sqlite:///./data/bcd.db` | **URL de connexion à la base de données.** SQLite : `sqlite:///chemin/vers/bcd.db`. PostgreSQL : `postgresql://utilisateur:motdepasse@serveur:port/nom_base`. |
| **`DATA_DIR_PATH`** | `data` | **Dossier des données.** Emplacement où est stockée la base de données SQLite locale et les fichiers associés. |
| **`CONFIG_DIR_PATH`** | `.` | **Dossier de configuration.** Emplacement où se trouve le fichier `.env` de configuration. |
| **`LOG_DIR_PATH`** | `logs` | **Dossier des journaux (logs).** Où sont écrits les fichiers d'erreur et d'activité du logiciel. |
| **`COVERS_DIR_PATH`** | `data/covers` | **Dossier des couvertures.** Où sont stockées les images de couvertures de livres téléchargées automatiquement. |
| **`BACKUPS_DIR_PATH`** | `backups` | **Dossier des sauvegardes.** Où sont exportées les sauvegardes automatiques de la base de données. |

#### 2. Configuration réseau et serveur

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| **`API_HOST`** | `127.0.0.1` | **Adresse d'écoute du serveur.** `127.0.0.1` n'autorise que l'ordinateur local. Mettez `0.0.0.0` pour que le serveur accepte les connexions des autres ordinateurs du réseau de l'école. |
| **`API_PORT`** | `8888` | **Port réseau.** Port utilisé par le serveur BCD pour communiquer. |
| **`CORS_ORIGINS`** | `http://localhost:3000, http://localhost:8888` | Origines Web autorisées à communiquer avec l'API (essentiellement utilisé pour le développement). |

#### 3. Options du Client et du Mode Portable

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| **`CLIENT_ONLY`** | `false` | **Mode client uniquement.** Si `true`, cette machine n'exécutera aucun serveur local ni base de données. Elle agira comme une station cliente et lancera l'interface choisie (`UI_MODE`) connectée directement au serveur distant spécifié dans `API_HOST`. |
| **`UI_MODE`** | `webview` | **Interface au démarrage.** Choix de la fenêtre qui s'ouvre au lancement :<br>- `webview` : Fenêtre applicative native pour le poste gestion.<br>- `browser` : Ouvre le portail de gestion dans le navigateur web par défaut.<br>- `kids` : Ouvre directement le client ludique BCD Kids pour les élèves. |
| **`KIDS_CLIENT_PATH`** | *(vide)* | **Chemin du client enfants.** Chemin absolu ou relatif vers l'application élève BCD Kids (ex: `BCD-Kids.exe` ou `./BCD-Kids.x86_64`). |
| **`AUTO_UPDATE`** | `true` | **Mises à jour automatiques.** Si `true`, BCD vérifie la présence d'une nouvelle version au démarrage (connexion internet requise) et propose de l'installer automatiquement. |

#### 4. Sécurité et Authentification

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| **`AUTH_USERNAME`** | *(vide)* | **Nom d'utilisateur admin.** Renseignez ce champ pour activer la demande d'identifiants à l'ouverture du logiciel gestion. |
| **`AUTH_PASSWORD`** | *(vide)* | **Mot de passe admin.** Doit être défini avec le nom d'utilisateur pour que la sécurité soit activée. |
| **`AUTH_SCHEME`** | `basic` | **Protocole de sécurité.** Choix entre `basic` (standard et hautement compatible) et `digest` (plus sécurisé pour les connexions sans HTTPS). |

#### 5. Moteurs de recherche externes (Catalogage automatique par ISBN)
*Activez ou désactivez ces sources pour optimiser la recherche d'informations sur les livres.*

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| **`BNF_ENABLED`** | `true` | Active ou désactive la recherche sur le catalogue de la Bibliothèque Nationale de France (BnF). |
| **`BNF_API_URL`** | `https://catalogue.bnf.fr/api/SRU` | URL de l'API BnF. |
| **`BNF_RATE_LIMIT`** | `1` | Limite de requêtes sur l'API BnF (requêtes par seconde, maximum 1/s autorisé par la BnF). |
| **`GOOGLE_BOOKS_ENABLED`** | `true` | Active ou désactive la recherche sur Google Books. |
| **`GOOGLE_BOOKS_API_KEY`** | *(vide)* | Clé d'API Google Books (optionnelle, pour augmenter les quotas de recherche). |
| **`GOOGLE_BOOKS_RATE_LIMIT`** | `1` | Limite de requêtes Google Books (requêtes par seconde). |
| **`SUDOC_ENABLED`** | `true` | Active ou désactive la recherche sur le catalogue universitaire français SUDOC (idéal pour les périodiques). |
| **`SUDOC_API_URL`** | `https://www.sudoc.abes.fr/cbs/sru/` | URL de l'API SUDOC. |
| **`SUDOC_RATE_LIMIT`** | `1` | Limite de requêtes SUDOC (requêtes par seconde). |

#### 6. Diagnostics et Logs

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| **`LOG_LEVEL`** | `INFO` | Niveau de détail des journaux d'activité (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| **`ENVIRONMENT`** | `production` | En mode `development`, active le rechargement automatique du code à chaud et les outils de débogage poussés. |



