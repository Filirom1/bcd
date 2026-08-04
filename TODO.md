# Dette de maintenabilité

> Analyse du backend Python, de l'interface Web Vue, du client Godot, des tests et de la CI.  
> Cette note ne remplace pas les spécifications fonctionnelles : elle regroupe uniquement les chantiers transversaux les plus importants.

## Synthèse

L'architecture générale est saine : couche de services identifiée, injection des sessions SQLAlchemy, migrations Alembic, composants/composables Web, autoloads Godot et couverture E2E des parcours principaux. La dette se concentre toutefois sur trois points : les garde-fous qualité ne donnent pas actuellement un signal fiable, plusieurs modules centraux sont devenus trop volumineux, et les règles d'abstraction annoncées ne sont pas appliquées uniformément.

Ordre recommandé : fiabiliser d'abord les tests et la CI, puis refactoriser par petits lots couverts par des tests. Ne pas lancer une réécriture générale.

## P0 — Corriger les risques bloquants

### [x] P0.1 — Corriger la sélection des tests pytest

**Constat**

- La configuration par défaut utilise `-m "unit or integration"` dans `pyproject.toml`.
- Dans l'environnement Nix, `pytest --no-cov -q` collecte 905 tests mais en désélectionne 905 : la commande présentée comme commande générale n'exécute donc aucun test.
- La CI contourne ce problème avec `-m "unit or not unit"`, expression tautologique et peu lisible.
- Le script de quality gate annonce exécuter « unit, integration, e2e », mais hérite en réalité de la sélection par défaut.

**Risque** : faux sentiment de sécurité, comportement différent entre poste local, quality gate et CI.

**Actions**

1. Choisir une convention unique : marquer systématiquement tous les tests, ou retirer le filtre global de `addopts`.
2. Définir des commandes explicites pour la suite rapide et la suite complète (`not e2e and not slow`, puis tous les tests).
3. Aligner README, scripts, hooks et workflows sur ces commandes.
4. Ajouter un contrôle qui échoue si aucun test n'est sélectionné.

**Terminé quand**

- `pytest` exécute une suite non vide et documentée.
- La même sélection produit les mêmes résultats localement et en CI.
- Les suites unitaires, intégration, API, CLI et E2E sont chacune exécutées dans un job identifiable.

### [x] P0.2 — Faire réellement bloquer la CI sur la couverture

**Constat**

Le seuil de couverture configuré bloque désormais la CI lorsqu'il n'est pas atteint. L'objectif de long terme reste d'augmenter progressivement cette exigence, tout en conservant un garde-fou réellement utile.

**Actions**

1. Retirer `continue-on-error` du contrôle de couverture.
2. Distinguer si nécessaire la couverture globale de la couverture du code modifié.
3. Publier le rapport comme artefact sans rendre son envoi vers un service externe obligatoire.

**Terminé quand** : une couverture sous le seuil fait échouer la pull request.

### [x] P0.3 — Durcir `scripts/quality-gate.sh`

**Constat**

- Le script dépend de `rg` sans vérifier sa présence.
- Si `rg` est absent, l'erreur est redirigée puis neutralisée par `|| true`; les contrôles TODO, faux code et implémentations maison peuvent alors être déclarés réussis sans avoir été exécutés.
- Deux exécutions pytest séparées rendent le gate lent et peuvent produire des résultats différents.

**Actions**

1. Vérifier toutes les dépendances au démarrage (`command -v pytest`, `command -v rg`) et échouer explicitement si elles manquent.
2. Réutiliser un unique fichier de couverture produit par la suite prévue.
3. Tester le script lui-même dans la CI, y compris le cas d'une dépendance absente.
4. Remplacer les recherches textuelles trop larges par des contrôles ciblés et documentés.

**Terminé quand** : aucun contrôle ne peut passer parce que son outil n'a pas été exécuté.

### [I] P0.4 — Empêcher la restauration d'inventaire de modifier les données : SKIPPED

**Constat**

`composables/useInventoryTable.js` décrit `restore()` comme une lecture destinée à recharger les détails des exemplaires, mais appelle `apiClient.patch('/inventory/items/{item_id}')` pour chaque identifiant restauré. Cet endpoint ne fait pas une lecture : il marque l'exemplaire comme inventorié et met à jour `last_inventoried_at`. Le même `PATCH` est utilisé dans `pages/InventoryPage.js` après une édition pour prétendument « rafraîchir » l'exemplaire.

**Risque**

- Un rechargement de page ou un rafraîchissement local modifie silencieusement les données métier.
- Les dates de récolement ne correspondent plus à des scans réels.
- Les rapports construits à partir de `last_inventoried_at` peuvent devenir faux.
- La frontière commande/lecture est incompréhensible pour un mainteneur.

**Actions**

1. Ajouter un endpoint de lecture, de préférence groupé, permettant de résoudre une liste d'identifiants sans effet de bord.
2. Réserver `PATCH /inventory/items/{item_id}` au scan explicite.
3. Remplacer les deux usages de `PATCH` servant de lecture.
4. Centraliser la conversion d'une réponse API vers une ligne de la table d'inventaire.
5. Ajouter un test garantissant que restaurer ou rafraîchir la table ne change pas `last_inventoried_at`.

**Terminé quand** : aucune opération présentée comme lecture ou restauration ne modifie un exemplaire en base.

NE PAS FAIRE, SKIPPED

### [I] P0.5 — Supprimer les injections HTML non maîtrisées: SKIPPED

**Constat**

`components/ui/AutocompleteInput.js` injecte le résultat de `formatResult(result)` avec `v-html`. Les formateurs de `BorrowerScanner.js`, `ItemScanner.js` et `RecordDetail.js` construisent des chaînes HTML en interpolant directement des champs provenant de la base : noms, classes, titres, auteurs, types et identifiants. Le fallback d'initialisation de `app.js` injecte aussi `error.message` avec `innerHTML`. Enfin, `HelpPanel.js` injecte le résultat de `marked.parse()` sans étape explicite de sanitation.

**Risque**

- Une donnée contenant du HTML peut devenir du contenu actif dans l'application.
- Le composant générique impose à ses consommateurs de connaître et construire sa structure HTML.
- Présentation, traduction et données sont mélangées dans des chaînes difficiles à tester.
- Toute évolution visuelle exige de modifier plusieurs fonctions de formatage.

**Actions**

1. Remplacer le contrat `formatResult() -> HTML` par un slot Vue ou un composant de rendu de résultat.
2. Rendre toutes les données textuelles par interpolation Vue ou `textContent`.
3. Remplacer le fallback `innerHTML` de `app.js` par une construction DOM sûre.
4. Sanitiser le HTML produit par Markdown avec une bibliothèque vendored reconnue, ou interdire le HTML brut dans les fichiers d'aide.
5. Ajouter des tests avec des noms et titres contenant `<`, `>`, guillemets et balises HTML.

**Terminé quand** : aucun contenu variable non sanitisé n'est transmis à `v-html` ou `innerHTML`.

NE PAS FAIRE, SKIPPED

### [ ] P0.6 — Établir une stratégie de couverture et de durée de tests exploitable

**Analyse**

La couverture Python est produite par la suite rapide sur l'ensemble de `src/`. Elle regroupe l'API, les services, le CLI et les convertisseurs : les zones d'intégration, de plateforme et de conversion tirent donc le résultat global vers le bas, sans que cela signifie que les services critiques soient insuffisamment testés.

Les modules à prioriser dans les prochains lots sont notamment `updater.py`, les convertisseurs, les schémas d'export, certains routeurs, les commandes CLI et les intégrations de plateforme. Il faut conserver un profil de durée et une couverture par fichier afin de choisir les tests à ajouter selon le risque plutôt qu'au hasard.

**Constat Web JavaScript**

La couverture JS est désormais mesurée séparément par Vitest/V8, avec les rapports `coverage-js/lcov.info` et `coverage-js/index.html`. Le rapport couvre tout `src/bcd_web_vue/js/` afin de rendre visibles les composants, pages, routeur et bootstrap qui n'ont pas encore de tests directs. Le socle rapide couvre déjà le client API, le modèle d'erreur, la sélection, la pagination, les filtres, les badges, les préférences de colonnes et les utilitaires de couleur.

Les tests Playwright E2E continuent de vérifier des parcours, mais ne contribuent pas à la couverture de lignes JS et ne doivent jamais être additionnés à la couverture Python. Vitest, JSDOM et Vue sont des dépendances de développement uniquement : l'application reste vendored, hors ligne et sans build obligatoire en production.

**Constat de durée CI**

Le workflow `.github/workflows/ci.yml` est organisé en deux phases disjointes : une suite rapide `not external and not e2e and not slow` avec couverture, puis une suite complémentaire `slow or external or e2e`. Un test ne doit apparaître que dans une seule phase. Les rapports de durée permettent de suivre l'évolution des suites sans inscrire de mesure ponctuelle dans cette note.

**Actions**

1. Ajouter une étape de mesure non bloquante avec `pytest --durations=30` et publier le rapport des tests lents comme artefact.
2. Générer les couvertures Python par domaine (`services`, `api`, `cli`, `converters`) afin de distinguer le déficit de tests du poids des modules peu pertinents.
3. Faire une seule exécution de la suite Python destinée à la couverture ; garder les suites ciblées séparées uniquement pour le feedback rapide, ou les exécuter en jobs parallèles.
4. Exclure explicitement du seuil global les fichiers de bootstrap/plateforme difficiles à tester seulement si cette décision est justifiée et documentée ; ne pas masquer les modules métier.
5. Prioriser les tests unitaires rapides pour `updater`, `portable`, les convertisseurs et les schémas d'export, puis les tests de routes/CLI à faible couverture. Mesurer le gain après chaque lot.
6. [x] Ajouter un runner JS minimal (Vitest/V8, développement uniquement) pour les utilitaires purs et `ApiClient` ; publier un rapport séparé `coverage-js/`.
7. [~] Ajouter quelques tests de composants/composables pour les contrats à risque : les erreurs API, état concurrent, sélection, pagination, filtres, badges, persistance locale et le parcours checkout/return sont couverts ; annulation, normalisation des collections, i18n et autres composants montés restent à traiter, sans chercher à remplacer les E2E.
8. Définir des seuils séparés et progressifs : Python global, Python services, couverture JS des modules testés et E2E smoke. Ne pas faire dépendre le seuil Python de la couverture JS inconnue.
9. Supprimer `continue-on-error` du contrôle de couverture une fois la mesure stabilisée, et faire échouer le job sur le seuil réellement choisi.

**Première cible recommandée**

- court terme : conserver une baseline reproductible par fichier et par durée ;
- moyen terme : augmenter la couverture Python sans augmenter fortement la durée ;
- court terme : conserver un seuil CI bloquant adapté à la baseline ;
- ensuite : relever ce seuil sur le périmètre Python métier retenu ;
- en parallèle : mesurer séparément le JS avant de fixer un seuil JS.

**État** : mesure Python et durée reproductibles ; tests lents, externes et E2E marqués/séparés ; deux phases CI disjointes ; le seuil Python est bloquant. La couverture JS est publiée dans un job CI indépendant, sans seuil bloquant tant que le périmètre historique non caractérisé reste majoritaire. Un seuil JS progressif par fichiers testés reste à fixer après stabilisation de la baseline.

**Terminé quand** : un seul rapport de couverture Python reproductible est associé à une durée, les tests JS disposent d'un rapport séparé (ou l'absence de couverture JS est explicitement acceptée), et la CI n'exécute pas inutilement la même suite complète plusieurs fois.

## P1 — Réduire le coût des changements

### [x] P1.1 — Ramener les routes API à leur rôle de présentation

**Constat**

Plusieurs routes interrogent directement SQLAlchemy alors que l'architecture impose API → services → modèles. Exemples : statistiques de santé et requêtes de catalogue dans `admin.py`, enrichissement des réponses dans `borrowers.py` et `catalog.py`. Les modules `admin.py` et `catalog.py` atteignent respectivement environ 1 033 et 728 lignes.

Les endpoints de mise à jour du catalogue acceptent en outre un `dict` non structuré et capturent toute `Exception`, transformant notamment des erreurs métier attendues en HTTP 500 au lieu de laisser les gestionnaires globaux traiter les exceptions BCD.

**Actions**

1. Extraire les requêtes et agrégations restantes vers les services de domaine.
2. Remplacer les corps `dict` par des schémas Pydantic dédiés et documentés.
3. Laisser remonter les exceptions métier; ne capturer localement que les erreurs qui nécessitent réellement une traduction HTTP spécifique.
4. Découper les routeurs par sous-domaine sans changer les URL publiques.

**Terminé quand**

- Les routeurs ne contiennent plus de `db.query()` ni de logique métier.
- Les erreurs 400/404/409 restent distinguables des erreurs 500.
- Chaque endpoint d'écriture possède un schéma de requête.

### [x] P1.2 — Découper les modules Python devenus monolithiques

**Constat**

Des fichiers centraux cumulent trop de responsabilités : `catalog_service.py` (~1 051 lignes), `report_service.py` (~809), `circulation_service.py` (~735), `borrower_service.py` (~712), ainsi que `main.py` (~704). Cette taille n'est pas un défaut isolé, mais elle augmente le couplage, les imports locaux, la difficulté de revue et le rayon d'impact des changements.

**Actions**

1. Mesurer les dépendances et usages avant chaque extraction.
2. Scinder par capacité métier, par exemple notices/items/recherche externe pour le catalogue et calcul/export pour les rapports.
3. Conserver une façade compatible lorsque cela évite de modifier tous les appelants d'un coup.
4. Écrire des tests de caractérisation avant déplacement de logique.

**Terminé quand** : les responsabilités et dépendances de chaque module peuvent être décrites simplement, sans cycle d'import ni duplication créée par l'extraction.

### [x] P1.3 — Imposer le client HTTP central dans le Web UI

**Constat**

Le code Web contient 64 appels `fetch()`, répartis ainsi :

- **59 appels directs à `/api/v1`** qui contournent `ApiClient` ;
- **4 chargements de ressources statiques** (deux traductions et deux pages d'aide), qui peuvent légitimement rester hors du client REST ;
- **1 appel interne** dans l'implémentation de `ApiClient`.

Le projet utilise donc deux stratégies HTTP concurrentes alors qu'environ 70 appels passent déjà par `apiClient.get()`, `post()`, `put()`, `patch()` ou `delete()`.

**Principaux foyers**

| Zone | Appels directs | Responsabilités concernées |
|------|---------------:|----------------------------|
| `components/catalog/RecordDetail.js` | 11 | Notice, exemplaires, réservations, historique, édition et suppression |
| `components/borrowers/BorrowerDetail.js` | 11 | Emprunteur, classes, réservations, historique et circulation |
| `pages/InventoryPage.js` | 7 | Export, nettoyage, édition et suppression en masse |
| `composables/useBulkOperations.js` | 7 | Toutes les opérations groupées |
| `pages/ClassesPage.js` | 4 | CRUD des classes |
| `pages/BorrowersPage.js` | 3 | Recherche, modification et export |
| `components/borrowers/BorrowerAddForm.js` | 3 | Classes, prochain identifiant et création |
| `components/borrowers/BorrowerActions.js` | 3 | Actions de circulation |
| Autres pages/composants et bootstrap | 10 | Inventaire, filtres, étiquettes, édition et paramètres initiaux |

**Ce que les appels directs perdent**

`ApiClient` centralise déjà la construction des URL, les paramètres, `Accept-Language`, le comptage des requêtes actives, l'indicateur global de chargement, la gestion des réponses `204`, la conversion des erreurs HTTP en `ApiError` et la normalisation des erreurs réseau. Les appels directs réimplémentent ces comportements de manière incomplète et incohérente :

- certains lèvent un `Error` générique en anglais ;
- certains lisent `detail`, `error`, `message` ou `error_code` eux-mêmes ;
- certains remplacent silencieusement les données par `[]` ou `null` ;
- certains affichent une notification, d'autres écrivent seulement dans la console ;
- la plupart n'envoient pas la langue active et ne participent pas au chargement global.

Dans `useBulkOperations.js`, le même cycle chargement → sérialisation JSON → contrôle `response.ok` → conversion `ApiError` → parsing → nettoyage est répété sept fois. Dans `RecordDetail.js`, une même panne peut, selon l'opération, vider la modale, vider une liste, afficher un message local, produire une notification ou rester silencieuse.

**Limites actuelles de `ApiClient` à corriger avant migration complète**

Un remplacement mécanique de tous les appels n'est pas possible sans compléter le client :

1. `_request()` parse toujours la réponse avec `response.json()` : les exports CSV ont besoin de `blob()` ou `text()`.
2. Les méthodes publiques n'acceptent pas d'options de requête : les `AbortSignal` des recherches/autocomplétions ne sont pas transmis. Un appel existant fournit déjà un troisième argument à `apiClient.get()`, mais celui-ci est ignoré par la signature actuelle.
3. `delete()` ne permet pas d'envoyer un corps JSON, nécessaire à la suppression groupée d'inventaire.
4. `_request()` remplace les en-têtes fournis au lieu de les fusionner avec les en-têtes par défaut.
5. Le premier chargement des paramètres se déroule avant la configuration du client avec la locale et l'état global ; il faut soit configurer le client plus tôt, soit documenter cette exception de bootstrap.

**Actions**

1. **Compléter `ApiClient`** : ajouter `responseType` (`json`, `text`, `blob`), `signal`, fusion des en-têtes, corps optionnel pour `DELETE` et option documentée pour désactiver le chargement global.
2. **Tester le contrat du client** : JSON, `204`, erreur JSON/non-JSON, erreur réseau, langue, requêtes concurrentes, annulation, blob et `DELETE` avec body.
3. **Migrer les appels JSON simples** en premier : `useBulkOperations.js`, `ClassesPage.js`, `BorrowerAddForm.js` et `useBorrowerData.js`.
4. **Migrer domaine par domaine** les composants complexes : `RecordDetail.js`, `BorrowerDetail.js`, puis `InventoryPage.js`, en définissant pour chaque opération la règle UX d'erreur et de conservation des données.
5. **Migrer les téléchargements** d'inventaire, de catalogue et d'emprunteurs après ajout du support blob.
6. **Conserver `fetch()` direct uniquement pour les ressources statiques**, avec une justification claire dans le code.
7. **Ajouter un garde-fou CI** interdisant `fetch()` vers `/api/v1` en dehors de `api/client.js` et d'une éventuelle exception de bootstrap explicitement documentée.

**Terminé quand**

- aucun composant, page ou composable ne contient de `fetch()` direct vers `/api/v1` ;
- tous les appels REST transmettent la locale et produisent des `ApiError` cohérentes ;
- les chargements globaux restent corrects avec plusieurs requêtes concurrentes ;
- téléchargements, annulation et `DELETE` avec body passent par le client central ;
- les quatre accès aux ressources statiques sont clairement distingués des appels REST ;
- la CI empêche la réintroduction d'un appel API direct.

### [x] P1.4 — Décomposer les gros composants Web sans introduire de build obligatoire

**Constat**

Plusieurs composants dépassent 700 à 1 000 lignes : `CollectionReport.js`, `RecordDetail.js`, `BorrowerDetail.js`, `InventoryPage.js`, `CirculationPage.js`, `NeverBorrowedReport.js` et `SettingsForm.js`. Ils mélangent rendu, orchestration HTTP, état de modales, transformation de données et parfois règles métier. Le moteur de génération de cote est par exemple inclus dans `ItemBarcodeInput.js` (~583 lignes).

**Actions**

1. Extraire d'abord la logique pure vers des modules ES réutilisables et testables.
2. Séparer les panneaux/onglets autonomes en composants, sans multiplier les micro-composants passifs.
3. Extraire les orchestrations de données dans des composables de domaine.
4. Préserver la contrainte du projet : dépendances vendored et aucun build nécessaire pour exécuter l'application.

**Terminé quand** : les règles pures sont testables sans monter une page complète et chaque gros composant a une responsabilité dominante.

### [ ] P1.5 — Mettre le client Godot en conformité avec sa règle « zéro UI procédurale »

**Constat**

La règle du dépôt interdit la construction de layout via `Node.new()`/`add_child()` dans les scripts, mais plusieurs écrans créent encore directement labels, boutons et conteneurs : `SClassSelect.gd`, `SNameInput.gd`, `SBookDetail.gd`, `SMainMenu.gd`, `SMyHolds.gd`, `SSearch.gd`, `SCheckout.gd`, `SReturnScan.gd`, `SServerDiscovery.gd`, ainsi que `Breadcrumb.gd` et `BadgeHelper.gd`.

**Actions**

1. Créer quelques scènes réutilisables, notamment état vide, ligne de détail, badge, candidat et entrée d'historique.
2. Instancier ces scènes depuis les scripts et limiter le GDScript au binding de données/signaux.
3. Déplacer aussi l'UI globale créée dans `Mgr.gd` vers une scène racine, ou documenter explicitement une exception d'architecture.
4. Ajouter un contrôle statique ciblé qui interdit la création procédurale de types `Control` dans `src/screens` et `src/components`.

**Terminé quand** : couleurs, tailles, marges et structure visuelle peuvent être modifiées dans les `.tscn`/ressources de thème sans éditer la logique.

### [ ] P1.6 — Éliminer le N+1 du scanner Web et rendre l'annulation effective

**Constat**

`components/circulation/ItemScanner.js` lance une recherche de notices puis une requête supplémentaire par notice pour obtenir ses exemplaires, soit jusqu'à onze requêtes pour une saisie. Le composant passe `{ signal }` comme troisième argument à `apiClient.get()`, mais la signature actuelle n'accepte que l'endpoint et les paramètres : le signal est ignoré. `BorrowerScanner.js` suit le même contrat d'annulation non pris en charge.

**Risque**

- Les anciennes recherches continuent après une nouvelle frappe.
- Les réponses peuvent arriver dans le désordre.
- Le navigateur et le serveur effectuent inutilement de nombreuses requêtes.
- L'agrégation métier est réimplémentée dans le composant.
- Le comportement se dégrade particulièrement sur le matériel ancien ciblé.

**Actions**

1. Faire accepter et transmettre `AbortSignal` par toutes les méthodes de `ApiClient`.
2. Distinguer proprement une annulation d'une erreur réseau dans `ApiError`.
3. Fournir un endpoint de recherche directement exploitable par le scanner, incluant les exemplaires pertinents ou le premier exemplaire disponible.
4. Supprimer l'enrichissement N+1 du composant.
5. Tester les frappes rapides, l'annulation et l'ordre d'arrivée des réponses.

**Terminé quand** : une recherche scanner utilise un nombre constant de requêtes et une recherche remplacée ne peut plus modifier l'état courant.

### [ ] P1.7 — Normaliser les contrats de collection et de pagination

**Constat**

Un modèle de pagination existe dans `models/pagination.js`, mais les consommateurs acceptent plusieurs formes incompatibles : tableau brut, `items`, `borrowers`, `data`, `titles`, métadonnées imbriquées ou champs `total` à la racine. Des expressions comme `response.data || response.items || response.titles || []` masquent les dérives du contrat au lieu de les signaler.

**Risque**

- Une régression serveur peut être transformée silencieusement en liste vide.
- Chaque page connaît plusieurs formats historiques.
- Les modèles JSDoc ne décrivent pas le comportement réel.
- Pagination et gestion des états vides doivent être maintenues séparément dans chaque domaine.

**Actions**

1. Définir une forme canonique pour chaque endpoint de collection.
2. Normaliser les réponses dans des adaptateurs placés à la frontière API, jamais dans les composants.
3. Valider en développement les champs obligatoires des réponses.
4. Choisir et documenter les contrats page/page_size et limit/offset au lieu de les mélanger implicitement.
5. Supprimer les fallbacks historiques une fois les endpoints et consommateurs migrés.

**Terminé quand** : chaque composant consomme un modèle unique et une réponse mal formée produit une erreur explicite plutôt qu'une liste vide.

### [x] P1.8 — Initialiser les effets de l'état global une seule fois

**Constat**

Les refs module-level de `useAppState.js` constituent volontairement un état global léger, mais le `watch(locale, ...)` chargé de persister la langue est créé à l'intérieur de `useAppState()`. Plus de vingt consommateurs appellent ce composable : plusieurs watchers identiques peuvent donc observer la même ref et réécrire `localStorage` ainsi que `document.documentElement.lang` à chaque changement.

**Actions**

1. Séparer l'état global, ses actions et son initialisation.
2. Déplacer la persistance de la locale vers une fonction idempotente appelée une fois depuis `app.js`, ou vers un store singleton explicite.
3. Garantir que l'appel à `useAppState()` ne crée aucun effet secondaire ni watcher supplémentaire.
4. Tester deux montages/démontages successifs et un changement de langue.

**Terminé quand** : un changement de langue déclenche une seule persistance, quel que soit le nombre de consommateurs montés.

### [x] P1.9 — Terminer l'externalisation i18n du Web UI

**Constat**

L'infrastructure i18n est largement utilisée, mais des textes utilisateur restent codés dans les composants. Exemples vérifiés : `Unknown author`, `Unknown`, `Book`, `Available`, `On loan`, `copies` et `En cours` dans `ItemScanner.js`; `N/A` et `loans` dans `BorrowerScanner.js`; `Bloqué` et `En retard` dans `RecordDetail.js`; `Chargement...` et `Chargement de l'application...` dans `App.js`. Tous les titres de routes et donc `document.title` sont également codés en français dans `router.js`.

**Risque** : l'interface mélange les langues, la terminologie diverge entre composants et les nouveaux textes échappent facilement à la traduction française ou anglaise.

**Actions**

1. Externaliser les chaînes restantes dans `locales/en.json` et `locales/fr.json`.
2. Définir une liste courte d'exceptions autorisées : identifiants, codes et valeurs techniques.
3. Ajouter un contrôle CI de parité des clés et une recherche des chaînes utilisateur codées dans les templates/scripts.
4. Ajouter des tests des principaux parcours dans les deux langues.

**Terminé quand** : les parcours principaux n'affichent aucun texte français en anglais, aucun texte anglais en français et aucune clé brute.

### [x] P1.10 — Uniformiser le contrat d'erreur consommé par les composants

**Constat**

`ApiError` expose le statut HTTP dans `statusCode` et les composants récents utilisent cette propriété. `components/inventory/ScanTab.js` teste toutefois `err.response.status`, convention de type Axios qui n'existe pas dans le modèle courant. Un exemplaire absent ne déclenche donc pas le message 404 spécifique et tombe dans l'erreur générique. D'autres composants inspectent encore manuellement `detail`, `message`, `error` ou `error_code`.

**Actions**

1. Faire passer les erreurs de composants par `useErrorHandler()` ou des helpers fondés sur `ApiError`.
2. Remplacer les tests de formes historiques (`response.status`, champs ad hoc) par `statusCode` ou un code métier.
3. Documenter le contrat unique d'erreur côté Web.
4. Ajouter des tests pour 400, 404, 409, erreur réseau et réponse serveur non JSON.

**Terminé quand** : une même erreur métier produit le même code et le même message quel que soit le composant qui l'affiche.

### [x] P1.11 — Rétablir le flux de données unidirectionnel dans les paramètres

**Constat**

`components/settings/SettingsForm.js` modifie directement plusieurs champs de `props.settings` (`dewey_colors`, `catalog_shelf_locations`, `catalog_call_number_rules`). Le formulaire enfant altère ainsi l'état de `SettingsPage` avant l'action Enregistrer, et le parent ne dispose d'aucun événement décrivant les changements.

**Risque**

- Le formulaire est difficile à tester indépendamment.
- Annulation, validation et détection des modifications reposent sur des snapshots manuels.
- Une future validation asynchrone peut observer un état parent partiellement modifié.
- Le contrat du composant contredit le flux props → événements attendu par Vue.

**Actions**

1. Créer une copie locale explicite du formulaire.
2. Émettre un payload complet et validé lors de la sauvegarde, ou utiliser `v-model:settings` avec `update:settings` sans mutation directe.
3. Calculer l'état « modifié » à partir de la copie locale et de l'original.
4. Tester modification, annulation, sauvegarde réussie et sauvegarde échouée.

**Terminé quand** : aucun composant enfant ne modifie directement un objet reçu en prop.

### [ ] P1.12 — Garantir que la dernière requête asynchrone gagne

**Constat**

Les chargements de `RecordDetail.js` et `BorrowerDetail.js`, les recherches catalogue et certaines générations différées ne vérifient pas que la réponse reçue correspond encore à l'identifiant ou aux critères actifs. Une réponse ancienne peut donc écraser un état plus récent. Dans `AutocompleteInput.js`, le `finally` d'une requête annulée peut aussi mettre `loading` à `false` pendant qu'une nouvelle requête est active. `PrintItemLabels.js` possède un timer de régénération non nettoyé et plusieurs générations peuvent se chevaucher.

**Actions**

1. Définir un pattern partagé « latest request wins » avec compteur de requête ou identifiant attendu.
2. Transmettre `AbortSignal` jusqu'au transport HTTP et annuler à chaque remplacement, fermeture ou démontage.
3. Ne modifier `loading`, les données et les erreurs que si la requête est toujours courante.
4. Nettoyer les timers au démontage et exposer `cancel()`/`flush()` pour les actions différées.
5. Tester les réponses dans l'ordre inverse, les changements rapides d'identifiant et la fermeture pendant chargement.

**Terminé quand** : une réponse obsolète ne peut jamais modifier l'écran courant ni son indicateur de chargement.

### [x] P1.13 — Centraliser les dates civiles et leur formatage

**Constat**

Le Web mélange le formateur `vue-i18n`, `toLocaleDateString()`, `toLocaleTimeString()` et `toLocaleString()`. La locale du système peut donc être utilisée à la place de la langue choisie dans l'application. Plusieurs composants construisent aussi des dates métier avec `toISOString().split('T')[0]` ou `slice(0, 10)` : la conversion UTC peut produire le jour précédent ou suivant autour de minuit.

**Actions**

1. Créer des utilitaires distincts pour dates affichées, date/heure affichée et date civile envoyée à l'API.
2. Faire passer l'affichage par les formats `vue-i18n` et la locale active.
3. Construire les dates civiles API à partir des composantes locales sans conversion UTC.
4. Remplacer les implémentations dispersées dans circulation, emprunteurs, inventaire, sauvegardes, catalogage et rapports.
5. Tester les deux langues, les changements d'heure et les heures proches de minuit.

**Terminé quand** : la langue de l'OS n'influence plus l'affichage et une date civile locale ne change jamais de jour lors de sa sérialisation.

### [ ] P1.14 — Exposer les paramètres structurés comme des structures, pas comme du JSON texte

**Constat**

`dewey_colors`, `catalog_shelf_locations` et `catalog_call_number_rules` sont stockés comme `Text` et exposés par les schémas API comme `Optional[str]`, bien qu'ils représentent respectivement des tableaux de couleurs, d'emplacements et de règles. Le Web répète donc `JSON.parse()`/`JSON.stringify()` dans `SettingsForm.js`, `ItemBarcodeInput.js`, `ItemEditForm.js`, `BulkEditPanel.js` et `useItemBadge.js`, avec des fallbacks silencieux différents.

**Risque**

- Les frontières API ne décrivent pas les données réelles.
- Une chaîne JSON invalide n'est découverte qu'au moment du rendu.
- Valeurs par défaut, validation et récupération divergent selon le composant.
- Toute évolution du format doit modifier de nombreux parseurs dispersés.

**Actions**

1. Définir des schémas Pydantic structurés pour couleurs, emplacements et règles de cote.
2. Conserver si nécessaire le stockage SQL texte derrière une propriété/adaptation de service, sans exposer cette représentation au client.
3. Valider les données à l'écriture et retourner des listes/objets dans l'API.
4. Migrer le Web puis supprimer les parseurs et sérialisations locales.
5. Prévoir une migration/réparation des valeurs historiques invalides.

**Terminé quand** : aucun consommateur Web ne doit appeler `JSON.parse()` sur un champ de paramètres reçu de l'API.

### [ ] P1.15 — Clarifier la source de vérité de la langue et du format de date

**Constat**

Les paramètres système exposent `language` et `date_format` dans le formulaire d'administration, mais aucune autre utilisation de ces champs n'existe dans `src/`. La langue effective de l'interface provient de `bcd_locale` dans `localStorage` et les dates suivent plusieurs formateurs indépendants. Modifier ces deux réglages puis enregistrer donne donc l'impression d'une configuration active alors qu'elle n'influence pas l'application.

**Actions**

1. Décider si ces paramètres représentent une valeur par défaut serveur, une préférence globale ou des champs obsolètes.
2. S'ils restent actifs, initialiser la locale utilisateur à partir du réglage global uniquement en l'absence de préférence locale et brancher `date_format` sur le formateur commun.
3. Sinon, retirer les champs du formulaire, du schéma et du modèle via migration.
4. Documenter la priorité entre défaut serveur et préférence locale.
5. Ajouter un test démontrant l'effet réel de chaque réglage visible.

**Terminé quand** : aucun paramètre modifiable dans l'UI n'est sans effet et chaque source de configuration a une priorité documentée.

### [ ] P1.16 — Unifier le chargement et la fraîcheur des paramètres Web

**Constat**

`app.js` charge déjà les paramètres au démarrage et les place dans `useAppState()`. Malgré cela, `CirculationPage.js` maintient à la fois `appSettings` issu de l'état global et une seconde ref `settings` rechargée via `useBarcodeUtils()`/`useBorrowerData()`. Les pages d'impression rechargent elles aussi les mêmes paramètres. Il existe donc plusieurs chemins de lecture, valeurs par défaut et moments de rafraîchissement pour une même configuration.

**Risque**

- Deux parties d'un même écran peuvent utiliser des versions différentes des paramètres.
- Une modification des réglages exige de connaître tous les caches et rechargements locaux.
- Des requêtes redondantes sont exécutées au montage.
- Les fallbacks de préfixes de codes-barres divergent de l'état global.

**Actions**

1. Définir `useAppState()` ou un store léger comme source de vérité unique des paramètres.
2. Exposer une action `loadSettings({ force })` avec déduplication des requêtes concurrentes et état de fraîcheur explicite.
3. Faire consommer les préfixes, badges, impressions et formulaires depuis cette source commune.
4. Rafraîchir atomiquement le store après une sauvegarde réussie.
5. Supprimer `fetchSettings` de `useBorrowerData()` et `useBarcodeUtils()`.

**Terminé quand** : un seul service charge les paramètres et tous les composants observent la même version réactive.

## P2 — Renforcer la testabilité et la sûreté du refactoring

### [ ] P2.1 — Ajouter des tests ciblés aux couches UI

**Constat**

Le Web dispose de tests Playwright de parcours, ce qui est positif. La suite Python dispose maintenant de tests unitaires, intégration, API et CLI ciblés, ainsi que de marqueurs `slow`, `external` et `e2e`. Un socle Vitest rapide couvre désormais la logique JavaScript pure, le parcours checkout/return par composant monté et publie sa couverture séparée ; d'autres tests de composants et les tests Godot automatisés restent absents du dépôt.

**Actions**

1. Tester les modules JS purs et les contrats de `ApiClient`, tout en conservant l'exécution sans build de l'application.
2. Ajouter des smoke tests Godot headless et des tests des autoloads/utilitaires critiques.
3. Remplacer les TODO/skips E2E par un ticket référencé, un `xfail` strict et temporaire, ou un test actif.
4. Ajouter au minimum des tests bilingues, d'accessibilité clavier et d'erreurs réseau.

**Terminé quand** : un refactoring de logique UI peut échouer rapidement avant le lancement de toute la suite E2E.

### [ ] P2.2 — Réactiver progressivement le typage utile

**Constat**

Pyright est en mode `basic`, mais les diagnostics les plus utiles au refactoring (`reportGeneralTypeIssues`, arguments, retours, appels et opérateurs) sont désactivés. Des services retournent encore de nombreux dictionnaires non structurés et les endpoints de mise à jour acceptent des `dict`. Plusieurs fonctions publiques GDScript n'annoncent pas leur type de retour. Côté Web, les modèles JSDoc ne sont pas vérifiés contre OpenAPI : `models/item.js` documente notamment `damaged` comme statut et omet `on_hold`/`withdrawn`, contrairement à `ItemStatus`; `RecordDetail.js` teste aussi un statut d'article impossible `overdue`, qui appartient aux circulations.

**Actions**

1. Réactiver une catégorie Pyright à la fois, avec une baseline explicite plutôt qu'une désactivation globale.
2. Introduire des schémas Pydantic, `TypedDict` ou dataclasses aux frontières de modules.
3. Ajouter les types de retour GDScript sur les autoloads et APIs publiques.
4. Faire bloquer les nouvelles erreurs, sans exiger la correction de tout l'historique en une seule PR.
5. Générer ou valider les contrats JSDoc Web à partir d'OpenAPI afin que statuts, champs et paginations ne dérivent plus silencieusement.

**Terminé quand** : le typage détecte réellement les signatures incompatibles introduites par un changement.

### [x] P2.3 — Uniformiser la politique d'exceptions et de journalisation

**Constat**

Les exceptions métier centralisées sont un bon socle, mais de nombreux `except Exception` et quelques `except:` nus subsistent. Les cas les plus problématiques sont ceux qui avalent silencieusement une erreur de parsing ou changent toutes les erreurs en HTTP 500. À l'inverse, certaines captures larges aux frontières CLI, sauvegarde ou mise à jour automatique peuvent être légitimes si elles journalisent le contexte et conservent la cause.

**Actions**

1. Corriger en priorité les `except:` nus dans l'inventaire et la CLI avec les exceptions attendues.
2. Définir une règle par couche : services → exceptions BCD, API → handlers globaux, CLI → conversion en sortie/exit code, intégrations externes → journal + chaînage.
3. Utiliser `raise ... from exc` lors d'une traduction d'exception.
4. Ajouter identifiants métier et contexte de ligne aux erreurs d'import.

**Terminé quand** : une erreur inattendue reste visible avec sa cause, tandis qu'une erreur métier conserve son code et son message attendus.

### [x] P2.4 — Nettoyer les artefacts et documentations de dette obsolètes

**Constat**

`src/bcd_api/services/import_service.py.PERFORMANCE_TODO` affirme que l'import réalise environ 5 800 commits. L'implémentation actuelle de `dublin_core_import.py` ne contient plus qu'un `db.commit()` final; le document semble donc obsolète, mais aucune mesure de performance automatisée ne permet de le confirmer. D'autres divergences existent dans la documentation E2E, qui présente encore comme TODO des fichiers désormais présents.

**Actions**

1. Ajouter un benchmark reproductible de l'import sur 5 000 lignes et vérifier les requêtes N+1.
2. Supprimer ou réécrire le fichier `.PERFORMANCE_TODO` selon le résultat mesuré.
3. Mettre à jour les inventaires de tests et retirer les commentaires devenus faux.
4. Transformer toute dette encore valide en entrée de ce fichier ou en ticket traçable, avec critère de fermeture.

**Terminé quand** : aucun fichier parallèle au code ne décrit une implémentation qui n'existe plus.

### [x] P2.5 — Centraliser et versionner la persistance locale Web

**Constat**

`useAppState.js` fournit des accès protégés à `localStorage`, mais les préférences de colonnes, la table d'inventaire et plusieurs rapports réimplémentent directement lecture, parsing et écriture. Certaines captures d'erreurs sont entièrement vides. Les clés, valeurs par défaut et stratégies de récupération sont dispersées.

**Actions**

1. Créer un adaptateur léger commun avec `getJSON(key, fallback)`, `setJSON(key, value)` et `remove(key)`.
2. Centraliser le préfixe et l'inventaire des clés.
3. Ajouter une version aux structures susceptibles d'évoluer et une stratégie de migration ou de remise à zéro.
4. Uniformiser la journalisation des stockages bloqués ou corrompus.
5. Migrer progressivement les rapports et composables existants vers cet adaptateur.

**Terminé quand** : aucun composant ou composable métier ne parse directement une valeur `localStorage`.

### [ ] P2.6 — Factoriser les actions différées et les téléchargements Web

**Constat**

Les composants implémentent séparément leurs timers de debounce et le téléchargement blob. Le cycle création d'URL objet → création d'un lien → clic → suppression → révocation est dupliqué dans les exports inventaire, catalogue et emprunteurs. Les timers de `PrintItemLabels.js`, `SearchBar.js`, `useBulkOperations.js` et plusieurs composants n'ont pas tous une politique de nettoyage homogène.

**Actions**

1. Créer un composable `useDebouncedAction()` avec `cancel()`, `flush()` et nettoyage automatique.
2. Créer un utilitaire `downloadBlob(blob, filename)` garantissant suppression du lien et révocation de l'URL dans un `finally`.
3. Utiliser ces abstractions lors de l'ajout du support blob à `ApiClient`.
4. Tester démontage avant expiration du timer et échec pendant un téléchargement.

**Terminé quand** : aucun composant métier ne gère directement un timer de debounce ou le cycle de vie d'une URL blob.

### [ ] P2.7 — Remplacer les erreurs silencieuses et logs de développement

**Constat**

Des `catch {}` ou `.catch(() => {})` subsistent dans le catalogue, les paramètres et les rapports. Des `console.log()` de développement écrivent aussi l'initialisation, le payload complet des paramètres, les données d'exemplaire et les paramètres de rapports. Ces pratiques rendent les incidents difficiles à diagnostiquer et peuvent exposer de futures données sensibles dans la console.

**Actions**

1. Classer chaque erreur comme attendue, non bloquante, fonctionnelle ou inattendue.
2. Ajouter un commentaire et une trace debug contrôlée aux erreurs volontairement ignorées.
3. Supprimer les logs de payload et données métier.
4. Introduire, si nécessaire, un logger léger conditionné par un mode debug.
5. Faire rechercher en CI les `catch` vides et logs interdits dans le code de production.

**Terminé quand** : aucune erreur n'est avalée sans justification et aucun payload métier n'est écrit par défaut dans la console.

### [ ] P2.8 — Rendre les composants réutilisables indépendants du DOM global

**Constat**

Des composants réutilisables emploient des identifiants fixes ou des recherches globales. `AutocompleteInput.js` utilise toujours `autocomplete-dropdown` et `autocomplete-item-{index}`, alors que plusieurs autocomplétions peuvent être montées sur la même page. `HelpPanel.js` utilise un identifiant offcanvas fixe. `useBarcodeRenderer.js` rend tous les éléments `.barcode` du document au lieu d'un conteneur fourni par le composant appelant.

**Risque** : collisions d'IDs et d'attributs ARIA, rendu d'un autre composant avec de mauvaises options, tests non isolés et impossibilité de monter plusieurs instances de manière sûre.

**Actions**

1. Générer un identifiant stable unique par instance pour les relations `aria-controls`, labels, listes et modales.
2. Utiliser des refs de conteneur plutôt que `document.querySelectorAll()`/`getElementById()` dans les composants réutilisables.
3. Passer explicitement la racine de rendu à `useBarcodeRenderer()`.
4. Tester deux instances simultanées de chaque composant générique.

**Terminé quand** : deux instances d'un composant réutilisable peuvent coexister sans partager d'identifiant ni manipuler le DOM de l'autre.

### [ ] P2.9 — Extraire les parseurs et constantes Web dupliqués

**Constat**

Le même parseur de listes séparées par des virgules est redéfini dans au moins six composants. Les couleurs Dewey par défaut, la normalisation des accents et plusieurs mappings d'affichage sont également recopiés. Les statuts d'article et leurs labels/couleurs sont redéfinis dans `RecordDetail.js`, `ItemEditForm.js`, `BulkEditPanel.js` et `InventoryResults.js`. Ces fonctions et constantes sont noyées dans les composants et ne disposent pas d'une source de vérité ni de tests dédiés.

**Actions**

1. Créer des modules utilitaires ES sans dépendance Vue pour parsing, normalisation et constantes de domaine.
2. Extraire en priorité `parseCsv`, la normalisation de texte et les valeurs Dewey partagées.
3. Ajouter des tests sur espaces, valeurs vides, accents, apostrophes et caractères non latins.
4. Supprimer les variantes locales après migration.
5. Centraliser les métadonnées des statuts Web et les vérifier contre les enums publiés par l'API.

**Terminé quand** : une règle pure partagée n'existe qu'en un endroit et peut être testée sans monter un composant.

### [ ] P2.10 — Introduire un contrôle de typage statique progressif via JSDoc et tsc

**Constat**

Le projet préserve la contrainte critique de n'avoir aucun outil de build obligatoire en production (vendored browser global). Cependant, l'absence de vérification statique des contrats d'API (comme `ApiError`, les structures de notices ou les types de paramètres) augmente le risque de régressions lors des refactorisations JS, et complique la détection d'erreurs en amont.

**Actions**

1. Configurer un fichier `tsconfig.json` ou `jsconfig.json` en mode `"checkJs": true`, `"noEmit": true` pour guider le compilateur `tsc` en mode linter de types uniquement.
2. Typer progressivement les modèles centraux (`models/item.js`, `models/borrower.js`) et les signatures d'API à l'aide de blocs de commentaires standard **JSDoc** (comme `@typedef` et `@type`).
3. Activer le contrôle `@ts-check` de manière progressive fichier par fichier (en commençant par les utilitaires purs comme `utils/storage.js` et `utils/callNumber.js`).
4. Ajouter une validation `npm run type-check` lancée lors de la CI pour garantir l'absence d'incohérences de typage.

**Terminé quand** : les fichiers JS modifiés sont validés statiquement par `tsc --noEmit` en tâche de fond (CI) sans nécessiter de compilation en production.

## Points à préserver

- Séparation services/modèles déjà bien installée dans la majorité du backend.
- Sessions injectées et isolation transactionnelle des tests d'intégration.
- Migrations Alembic réversibles présentes pour les évolutions de schéma inspectées.
- Client Web vendored, exécutable hors ligne et sans étape de build.
- Composables Web et Page Objects Playwright déjà disponibles pour soutenir les extractions.
- Navigation, i18n et thèmes centralisés dans les autoloads Godot.
- Versionnement unifié et packaging multi-plateforme.

## Ordonnancement proposé

1. **PR 1 — Intégrité inventaire** : P0.4 avec test de non-régression, avant les refactorings Web.
2. **PR 2 — Rendu HTML sûr** : P0.5, sans attendre la refonte complète des composants.
3. **PR 3 — Signal qualité** : P0.1 à P0.3.
4. **PR 4 — Frontières API** : schémas de mise à jour, exceptions, premières requêtes sorties des routes.
5. **PR 5 — Client HTTP Web** : enrichissement du client, annulation effective et suppression du N+1, puis migration domaine par domaine.
6. **PR 6 — Contrats Web** : normalisation des collections/paginations, erreurs, flux des paramètres et stratégie « latest request wins ».
7. **PR 7 — Cohérence UI** : initialisation de l'état, i18n, dates et utilitaires de cycle de vie.
8. **PR 8 — Godot UI** : composants réutilisables puis migration écran par écran.
9. **PR suivantes — Découpage** : un module Python ou un gros composant Web à la fois, avec tests de caractérisation.
10. **En continu** : typage, politique d'exceptions, stockage local, nettoyage des diagnostics, documentation et benchmarks.

