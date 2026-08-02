# Plan d’implémentation — Vite pour le build de production du Web UI

## 1. Décision et objectif

Adopter **Vite uniquement comme compilateur de production** du Web UI BCD.

Le fonctionnement interactif de développement doit être conservé :

- FastAPI reste le seul serveur lancé pour développer ;
- le navigateur reçoit toujours les modules source `src/bcd_web_vue/js/*.js` en ESM natif ;
- aucun `vite dev`, HMR, proxy, second port ou réglage CORS ne sera introduit ;
- une modification de JS reste visible après le rechargement normal de la page.

Vite est lancé uniquement par des commandes explicites pour :

1. fabriquer les assets de livraison ;
2. vérifier localement que la compilation est valide avant la CI ;
3. fabriquer le Web UI inclus dans les exécutables PyInstaller.

Le résultat final doit aussi supprimer la maintenance manuelle de `vendor.json` et de `scripts/download-vendor.py`.

---

## 2. Résultat attendu et critères d’acceptation

### 2.1 Deux modes explicites, jamais une détection implicite de `dist/`

| Mode | Sélection | Répertoire servi | But |
|---|---|---|---|
| source (défaut hors portable) | `WEB_ASSETS_MODE=source` ou valeur par défaut | `src/bcd_web_vue/` | développement ESM actuel |
| build (opt-in hors portable) | `WEB_ASSETS_MODE=build` | `build/web/` | test local de la livraison |
| portable | automatique, sans dépendre de `WEB_ASSETS_MODE` | ressources PyInstaller `bcd_web_vue/` | exécutable de production |

**Interdit :** choisir le build parce qu’un dossier `build/web/` existe. Un ancien build ne doit jamais masquer les modifications source d’un développeur.

### 2.2 Commandes fournies

Après `npm ci` :

```bash
# Compile le Web UI de production dans build/web/.
npm run build:web

# Commande à lancer localement avant la CI : compile puis vérifie la structure,
# le manifest et les références d’assets.
npm run verify:web-build

# Vérification navigateur optionnelle, mais recommandée avant une release :
# compile, démarre FastAPI en WEB_ASSETS_MODE=build et lance le smoke E2E dédié.
npm run test:web-production
```

`npm run verify:web-build` est **la commande demandée pour tester la compilation avant CI**. Elle ne démarre aucun serveur et doit être rapide, déterministe et utilisable sur Linux et Windows.

### 2.3 Comportement observable

- En mode source, `/` charge l’application et les modules locaux depuis `/static/js/...`, sans processus Vite.
- En mode build, `/` charge un `index.html` de production et uniquement des assets hashés sous `/static/assets/...` (plus `/locales/*.json` et le favicon, volontairement non hashés).
- En mode build, l’HTML ne contient aucune référence à `/node_modules/`, `/static/vendor/`, `/static/js/app.js` ou à un CDN externe.
- Le `library_code` est toujours visible dans l’écran de chargement et est correctement échappé dans le HTML.
- Les locales françaises et anglaises, la génération de codes-barres, l’aide Markdown et les graphiques continuent de fonctionner.
- Les packages finaux Windows et Linux ne contiennent ni `node_modules`, ni les sources JS séparées, ni le script de téléchargement vendor ; ils contiennent les seuls assets compilés nécessaires.
- Sur un cold load de l’écran d’accueil en mode build, le nombre de requêtes JS/CSS/polices nécessaires avant que `window.__BCD_APP__.ready` devienne vrai est **au plus 10** (les deux chargements de locale JSON sont comptés et documentés séparément). Ajouter un test de comptage déterministe plutôt qu’un seuil de durée fragile en CI.

---

## 3. État initial constaté

- `src/bcd_web_vue/index.html` charge 7 scripts globaux vendor et `js/app.js`.
- `app.js` et environ 84 modules s’appuient sur les globales navigateur `Vue`, `VueRouter`, `VueI18n`, `marked`, `JsBarcode` et `Chart`.
- L’arbre ESM local contient environ 119 modules ; le routeur importe toutes les pages statiquement.
- Les locales sont chargées à l’exécution via `/locales/fr.json` et `/locales/en.json`.
- FastAPI injecte le `library_code` dans la SPA et gère les en-têtes de cache.
- Le binaire PyInstaller inclut actuellement tout `src/bcd_web_vue`.
- Node 22 est déjà fourni par `shell.nix`, `package.json`/`package-lock.json` existent déjà, et la CI JavaScript utilise déjà `npm ci`.

Conséquence : Vite ne doit pas être ajouté comme un simple remplacement de balise `<script>`. Le modèle actuel de globales doit être pris en charge explicitement, sans réécrire risquement tous les composants pendant cette migration.

---

## 4. Architecture cible

### 4.1 Arborescence

Conserver les sources là où elles sont et ajouter les fichiers suivants :

```text
src/bcd_web_vue/
├── templates/
│   └── spa-shell.html             # shell commun, écran de chargement + marqueurs d’assets
├── js/
│   ├── app.js                     # entrée ESM source existante, conservée
│   └── production-entry.js         # entrée Vite, dépendances npm + bridge global
├── css/                            # CSS BCD existant
├── locales/                        # JSON source existant
└── favicon.*                       # icônes source existantes

scripts/
├── build_web.mjs                   # prépare le HTML Vite, lance Vite, copie les ressources stables
├── verify_web_build.mjs            # validation structurelle de build/web
└── test_web_production.py          # smoke E2E cross-platform en mode build

vite.config.js                      # configuration build-only
build/web/                          # sortie générée et ignorée par Git
```

`build/web/` est un artefact temporaire, jamais commité. Son contenu minimal final :

```text
build/web/
├── index.html
├── favicon.svg / favicon.ico / favicon.png
├── locales/
│   ├── fr.json
│   └── en.json
├── assets/
│   ├── <nom>-<hash>.js
│   ├── <nom>-<hash>.css
│   └── <nom>-<hash>.woff2 / .woff
└── .vite/manifest.json
```

### 4.2 Shell HTML commun et injection serveur

Éviter deux copies de l’écran de chargement (DRY) :

- Créer `src/bcd_web_vue/templates/spa-shell.html`, contenant le HTML commun et les marqueurs :
  - `<!-- BCD_HEAD_ASSETS -->` ;
  - `<!-- BCD_BODY_ASSETS -->` ;
  - `__BCD_LIBRARY_CODE__` dans le `<h1>`.
- En **mode source**, FastAPI rend ce shell en remplaçant les deux marqueurs par les liens/scripts de développement.
- Pour le build, `scripts/build_web.mjs` génère un HTML temporaire à partir de ce même shell, avec l’entrée Vite de production. Vite transforme cet HTML, émet les URLs hashées et le script déplace le HTML final vers `build/web/index.html`.
- Le token `__BCD_LIBRARY_CODE__` doit survivre au build et être remplacé par FastAPI au moment de servir l’HTML.
- Remplacer l’injection actuelle non échappée par `html.escape(_cached_library_code)`. C’est une correction de sécurité incluse dans ce chantier.

Ne pas utiliser `settings.app_version` comme cache-buster des assets Vite : les hashes de contenu le remplacent. Le HTML doit néanmoins être servi avec `Cache-Control: no-cache` afin de référencer les nouveaux hashes après une mise à jour.

### 4.3 Dépendances et bridge de compatibilité

Déclarer des versions **exactes** dans `package.json` et régénérer/committer `package-lock.json` :

- `vue` `3.4.21` ;
- `vue-router` `4.2.5` ;
- `vue-i18n` `9.14.5` ;
- `bootstrap` `5.3.3` ;
- `bootstrap-icons` `1.11.3` ;
- `jsbarcode` `3.11.6` ;
- `marked` `9.1.6` ;
- `chart.js` `4.4.3`.

Les bibliothèques requises à la compilation et à l’exécution du build seront dans `dependencies`; Vite, Vitest, JSDOM et les outils de test restent dans `devDependencies`. Ne pas ajouter de dépendance de copie ou de shell : `node:fs`, `node:path` et `node:child_process` suffisent aux petits scripts du projet.

`production-entry.js` doit :

1. importer Bootstrap CSS, Bootstrap Icons CSS, puis les trois CSS BCD dans le même ordre visuel que l’HTML actuel ;
2. importer Vue, Router, I18n, Marked, JsBarcode et Chart.js depuis npm ;
3. exposer leurs APIs compatibles dans `globalThis` (`Vue`, `VueRouter`, `VueI18n`, `marked`, `JsBarcode`, `Chart`) ;
4. seulement après ces affectations, faire `import("./app.js")`.

L’import dynamique final est impératif : les imports statiques sont évalués avant le corps du module et les modules existants destructurent `Vue` au niveau supérieur. Cette compatibilité permet de bundler toutes les dépendances sans une réécriture mécanique de dizaines de fichiers. Elle est documentée comme une transition contrôlée, pas comme un nouveau modèle à reproduire.

Avant d’importer Bootstrap JS, rechercher ses usages réels. S’il n’est jamais appelé (le code indique déjà que les modales sont « pure Vue »), ne pas l’inclure dans le bundle de production.

### 4.4 Développement sans Vite, sans vendor téléchargé

Supprimer les copies téléchargées sous `src/bcd_web_vue/vendor/` à la fin de la migration. En mode source :

- FastAPI monte `node_modules/` sous `/node_modules` **uniquement** lorsque `WEB_ASSETS_MODE=source` et hors portable ;
- les assets de développement rendus dans le shell pointent vers les builds navigateurs des dépendances dans `/node_modules/...` (Vue global, Router global, I18n global, Marked UMD, JsBarcode UMD, Chart UMD, Bootstrap CSS/JS si réellement nécessaire, Bootstrap Icons et polices) ;
- `app.js` et ses imports locaux restent exactement servis depuis `/static/js/...`.

Ainsi, après le `npm ci` déjà requis par les tests JS, le développeur continue à lancer FastAPI et à actualiser son navigateur comme aujourd’hui. Il ne lance ni Vite, ni une compilation, ni un proxy pour modifier un composant.

Le montage `/node_modules` ne doit jamais exister dans un package portable ni en mode build. Ajouter une note explicite dans la documentation : la première installation des dépendances Node nécessite le cache npm ou Internet ; l’application finale reste entièrement hors ligne.

### 4.5 Configuration Vite

Créer `vite.config.js` en ESM avec les décisions suivantes :

- `root` : `src/bcd_web_vue` ;
- `base` : `/static/`, car FastAPI expose les assets compilés sous ce préfixe ;
- entrée HTML : le fichier temporaire généré depuis `spa-shell.html` ;
- `build.outDir` : `build/web` ;
- `build.emptyOutDir` : `true` ;
- `build.manifest` : `true` ;
- `build.assetsDir` : `assets` ;
- `build.sourcemap` : `false` pour les packages de livraison ;
- `build.target` : `es2018` (l’application source exige déjà les modules ES ; ne pas ajouter un plugin legacy sans cible navigateur documentée) ;
- minification de production Vite par défaut ;
- aucun bloc `server`, `proxy`, `server.proxy`, `server.cors` ou HMR.

Ne pas forcer `manualChunks` dans le premier changement. Mesurer d’abord la taille et les requêtes réelles ; un découpage manuel prématuré peut augmenter les requêtes ou casser le cache. Le lazy loading des écrans du routeur est explicitement hors scope de cette migration et pourra former une amélioration performance séparée.

### 4.6 Ressources non importées

`scripts/build_web.mjs` doit, après le build Vite :

- copier `src/bcd_web_vue/locales/` vers `build/web/locales/` sans renommer les JSON, car `app.js` les récupère par `/locales/<lang>.json` ;
- copier les favicons à la racine de `build/web/` ;
- vérifier que les fichiers de polices importés par Bootstrap Icons ont été émis par Vite dans `assets/` ;
- supprimer tout répertoire temporaire d’entrée Vite, même en cas d’échec (`try/finally`).

La documentation `/help` et les couvertures `/covers` ne sont pas des assets Vite et conservent leurs mounts FastAPI existants.

---

## 5. Plan d’exécution détaillé

### Phase 0 — Préparation, mesure et garde-fous

1. Créer une branche dédiée, par exemple `vite-production-build`.
2. Relever et documenter dans la PR :
   - nombre de requêtes de l’écran d’accueil en mode source ;
   - poids transféré JS/CSS/polices ;
   - taille de `src/bcd_web_vue/vendor/` et du graphe source ;
   - navigateur/WebView réellement ciblé sur les postes scolaires.
3. Ajouter un court document de recherche, ou une section dans la PR, citant la documentation officielle Vite : build, `base`, `outDir`, `manifest` et `publicDir`/assets. Justifier Vite : bibliothèque maintenue, intégration Rollup/esbuild, et réduction de la maintenance du script maison.
4. Vérifier les licences des nouvelles dépendances via leurs packages npm et conserver les licences existantes. Lancer `npm audit` et traiter les vulnérabilités high/critical avant merge.
5. Ne modifier aucun flux métier/API, aucune migration de base de données et aucun texte utilisateur.

### Phase 1 — Tests d’abord

Ajouter les tests en échec avant l’implémentation :

1. **Tests unitaires Python de résolution des assets**
   - source non portable → racine `src/bcd_web_vue` et mount dev Node autorisé ;
   - build non portable avec `WEB_ASSETS_MODE=build` → racine `build/web` ;
   - portable → ressource packagée `bcd_web_vue`, quel que soit l’environnement ;
   - mode build sans `build/web/index.html` ou manifest → message d’erreur clair au démarrage, jamais fallback source silencieux ;
   - `WEB_ASSETS_MODE` invalide → validation Pydantic claire.

2. **Tests unitaires de rendu SPA**
   - les marqueurs d’assets source sont remplacés et aucun marqueur ne reste ;
   - le `library_code` est échappé (`<`, `>`, `&`, guillemets) ;
   - le rendu build conserve les URLs Vite déjà produites ;
   - l’en-tête HTML est `no-cache` en production.

3. **Tests du script de vérification web**
   - build valide accepté ;
   - `index.html`, manifest, locale, asset référencé ou favicon manquant → erreur non nulle et message utile ;
   - présence d’une URL `/node_modules/`, `/static/vendor/`, CDN ou d’un lien vers `js/app.js` dans le build → erreur.

4. **Smoke E2E mode build**
   - faire hériter `WEB_ASSETS_MODE` par le fixture `api_server` existant ;
   - ajouter un test dans `tests/e2e/test_page_loads.py` ou un fichier dédié qui confirme : application prête, écran de chargement retiré, route `/checkout` utilisable ;
   - intercepter les réponses JS/CSS/polices et vérifier le budget de requêtes défini ci-dessus ;
   - vérifier explicitement au moins un graphique, l’aide Markdown et une génération de barcode via les tests existants ou trois checks ciblés ;
   - exécuter ce test avec `WEB_ASSETS_MODE=build` seulement, afin de couvrir la livraison réelle.

5. Mettre à jour `tests/unit/test_main_cache.py` afin de remplacer l’assertion `/static/vendor/` par :
   - `/static/assets/<hash>.js|css|woff2` → `public, max-age=31536000, immutable` en production ;
   - `/locales/*.json` → `no-cache, must-revalidate` ;
   - HTML → `no-cache` ;
   - tous les assets → no-store en mode source.

Pour rendre cela testable, extraire la sélection des chemins et le rendu du shell dans un petit module sans effet de bord, par exemple `src/bcd_api/core/web_assets.py`. `main.py` ne doit conserver que la création des mounts et des routes.

### Phase 2 — Dépendances npm et développement ESM inchangé

1. Modifier `package.json` :
   - ajouter `vite` dans `devDependencies` avec une version exacte compatible Node 22 ;
   - déplacer/ajouter les dépendances Web listées en section 4.3 avec les versions alignées sur les vendors actuels ;
   - ajouter les scripts `build:web`, `verify:web-build` et `test:web-production` ;
   - ne pas remplacer ou supprimer les scripts Vitest existants.
2. Exécuter `npm install` une seule fois pour régénérer `package-lock.json`, puis vérifier que les versions lockées sont strictes et committer **package.json + package-lock.json ensemble**.
3. Créer le shell HTML commun et implémenter le rendu source avec les URLs `/node_modules/...` exactes, dans le même ordre de chargement qu’aujourd’hui : Vue, Router, I18n avant `app.js`, et les bibliothèques consommées par des composants avant l’application.
4. Ajouter le mount `/node_modules` seulement en source non portable ; vérifier que `node_modules` existe et fournir une erreur/lien de documentation clair si `npm ci` n’a pas été exécuté.
5. Vérifier manuellement :

   ```bash
   npm ci
   python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
   ```

   Modifier un composant, actualiser la page, et vérifier que le fichier modifié est celui servi. Il ne doit y avoir aucun processus Vite ni trafic vers un autre port.

### Phase 3 — Build Vite de production

1. Créer `vite.config.js` selon la section 4.5.
2. Créer `src/bcd_web_vue/js/production-entry.js` avec le bridge de compatibilité et les imports CSS. Tester dans un navigateur que `Vue`, `VueRouter`, `VueI18n`, `marked`, `JsBarcode` et `Chart` sont disponibles avant l’évaluation de `app.js`.
3. Créer `scripts/build_web.mjs` :
   - nettoie `build/web` ;
   - génère l’entrée HTML temporaire depuis le shell commun ;
   - lance Vite via l’API/CLI locale (`node_modules/.bin/vite` / `npx --no-install vite`) sans téléchargement réseau ;
   - normalise le chemin final de l’HTML vers `build/web/index.html` ;
   - copie locales/favicons ;
   - supprime les fichiers temporaires dans un `finally` ;
   - échoue si Vite échoue ou si la sortie attendue est absente.
4. Créer `scripts/verify_web_build.mjs` et faire de `npm run verify:web-build` une composition : build, puis validation structurelle.
5. Lancer `npm run verify:web-build` jusqu’à ce qu’il soit propre. Inspecter `build/web/index.html` et le manifest : les assets doivent être hashés et préfixés par `/static/`.
6. Lancer localement FastAPI ainsi :

   ```bash
   WEB_ASSETS_MODE=build ENVIRONMENT=production \
     python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
   ```

   Sous Windows, documenter l’équivalent PowerShell :

   ```powershell
   $env:WEB_ASSETS_MODE = "build"
   $env:ENVIRONMENT = "production"
   python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000
   ```

   Tester recharge, navigation, changement de langue, rapport avec Chart.js, aide Markdown, étiquette/code-barres, impression et favicon.

### Phase 4 — Intégration FastAPI et cache

1. Ajouter à `Settings` :
   - `web_assets_mode: Literal["source", "build"] = "source"` ;
   - éventuellement `web_build_dir_path` si un chemin configurable est réellement nécessaire. Préférer le chemin fixe projet `build/web` pour éviter une configuration inutile.
2. Créer `web_assets.py` qui retourne une structure immuable décrivant : racine UI, chemin HTML, chemin locales et booléen `is_built`/`is_source`.
3. Adapter `main.py` :
   - choisir la structure une fois au démarrage ;
   - monter `/static` sur la racine pertinente ;
   - monter `/locales` sur le sous-dossier locales pertinent ;
   - monter `/node_modules` seulement en source non portable ;
   - conserver l’ordre des mounts avant la route SPA catch-all ;
   - rendre le shell source ou l’`index.html` Vite buildé ;
   - injecter le code de bibliothèque de façon échappée dans les deux cas.
4. Remplacer la politique cache :
   - production `/static/assets/` : un an + `immutable` ;
   - production `/static/favicon.*` : max-age raisonnable (une heure) ou hash si ultérieurement migré ;
   - production `/locales/` : revalidation existante ;
   - production HTML SPA : `no-cache` ;
   - source : no-store pour `/static`, `/locales`, `/node_modules`, `/assets`, `/covers` ;
   - retirer la règle spéciale `/static/vendor/` à la suppression du vendor.
5. Ne pas toucher aux routes API, `/covers`, `/help`, authentification, mDNS, WebView ou Godot.

### Phase 5 — Packaging et CI

1. Modifier `bcd.spec` :
   - exiger que `build/web/index.html` et le manifest existent ;
   - inclure **`build/web` sous le nom packagé `bcd_web_vue`** ;
   - ne plus inclure `src/bcd_web_vue` entier ;
   - conserver les icônes PyInstaller depuis les fichiers source au moment du build ;
   - faire échouer clairement PyInstaller si `npm run build:web` a été oublié.
2. Modifier `.github/workflows/release.yml` :
   - le job de test installe Node 22, exécute `npm ci` et `npm run test:js` en plus des tests Python ;
   - ajouter un job `build-web` : checkout, Node 22, `npm ci`, `npm run verify:web-build`, puis upload de `build/web/` comme artefact ;
   - faire dépendre les builds PyInstaller Windows/Linux de `test` et `build-web` ;
   - télécharger le même artefact Web dans les jobs Windows/Linux avant `pyinstaller`. Les assets Vite sont indépendants de la plateforme et ne doivent pas être compilés deux fois ;
   - exécuter le smoke production (`npm run test:web-production`) dans le job Linux disposant déjà de Python/Playwright, ou ajouter un job dédié avec les mêmes dépendances ;
   - conserver les builds Godot sans les alourdir de Node sauf nécessité réelle.
3. Mettre à jour le workflow CI normal si nécessaire pour lancer `npm run verify:web-build` au moins sur Linux. Garder les tests JS indépendants.
4. Valider les exécutables PyInstaller Windows et Linux : le WebView/app navigateur ouvre l’UI, les assets hashés sont bien servis depuis `_internal/bcd_web_vue`, et le package ne contient pas `node_modules`.

### Phase 6 — Nettoyage de la solution vendor

Après succès du mode source sur les packages npm et du mode build :

1. Supprimer `scripts/download-vendor.py`.
2. Supprimer `vendor.json`.
3. Supprimer `src/bcd_web_vue/vendor/`.
4. Supprimer les références vendor dans :
   - le README des tests JS ;
   - `CLAUDE.md` ;
   - commentaires de `shell.nix` ;
   - cache headers et tests associés ;
   - toute documentation d’installation/développement.
5. Ajouter une courte section « Web UI build » dans `DEVELOPERS.md`/README :
   - `npm ci` une fois ;
   - dev FastAPI normal ;
   - `npm run verify:web-build` avant une PR/release ;
   - `npm run test:web-production` avec Playwright ;
   - `npm run build:web` est requis avant PyInstaller hors CI.
6. Rechercher avant merge :

   ```bash
   rg "download-vendor|vendor\.json|/static/vendor|src/bcd_web_vue/vendor" \
      --glob '!plan-vite.md' .
   ```

   Aucun résultat actif ne doit rester (hors historique Git ou artefacts ignorés).

---

## 6. Stratégie de test et commandes de validation finale

Exécuter, dans cet ordre :

```bash
# Dépendances exactes du lockfile
npm ci

# Tests JS source existants
npm run test:js

# Compilation/validation locale demandée
npm run verify:web-build

# Smoke Playwright contre les vrais assets de production
npm run test:web-production

# Tests Python rapides
python run_tests.py --fast

# Suite complète avant merge/release
python run_tests.py
```

Puis, lorsque l’environnement de packaging est disponible :

```bash
npm run build:web
pyinstaller --clean bcd.spec
```

Sous Windows et Linux, lancer l’exécutable produit et vérifier manuellement :

- arrivée à l’écran d’accueil en moins du budget de démarrage existant sur une machine cible ;
- fonctionnement hors ligne après installation ;
- absence d’erreurs dans la console WebView/navigateur ;
- rechargement après mise à jour (HTML frais + nouveaux assets hashés) ;
- changement de langue et impression.

Le rapport de PR doit joindre :

- le tableau avant/après des requêtes et tailles ;
- le résultat de `npm audit` ;
- les plateformes/navigateurs testés ;
- la preuve que dev utilise un seul serveur FastAPI sans proxy ;
- le résultat des builds Windows/Linux.

---

## 7. Risques, garde-fous et décisions hors scope

| Risque | Prévention / réponse |
|---|---|
| Un build ancien est servi en dev | sélection explicite `WEB_ASSETS_MODE`, jamais basée sur l’existence d’un dossier |
| `app.js` voit `Vue` indéfini en production | bridge global puis import dynamique de `app.js`; smoke test obligatoire |
| Les locales disparaissent du package | copie explicite lors du build + test de présence et E2E i18n |
| Les polices Bootstrap Icons sont cassées | import CSS via npm, validation des URLs et test navigateur |
| Cache trop agressif après auto-update | HTML no-cache, assets hashés immutable |
| PyInstaller embarque des sources ou node_modules | `bcd.spec` ne prend que `build/web`; inspection automatisée de l’artefact |
| Régression sur les PC anciens | es2018, minification, compteur de ressources, mesure manuelle sur matériel cible |
| Le dev nécessite un proxy/Vite | interdit dans la config et vérifié par documentation/tests : FastAPI seul |
| Réécriture massive des composants | bridge temporaire, aucune migration globale `Vue` → imports dans ce chantier |

Hors scope explicite :

- migration des composants `.js` vers des SFC `.vue` ;
- mise en place de `vite dev`, HMR, proxy ou CORS additionnel ;
- lazy loading du routeur et stratégie de chunks fine ;
- PWA/service worker ;
- changement de framework CSS ;
- modification fonctionnelle de l’API, du schéma de données, de Godot ou de la CLI.

Ces sujets pourront être proposés séparément après comparaison des mesures avant/après.

---

## 8. Gates Spec-Kit / constitution avant merge

Avant implémentation :

1. confirmer les versions npm disponibles et leurs builds navigateurs ;
2. faire valider le choix « FastAPI seul en dev + `node_modules` monté uniquement en source » ;
3. exécuter l’analyse pré-implémentation et résoudre toute ambiguïté critique ;
4. faire approuver les critères de requêtes et le comportement de cache.

Avant merge :

1. aucune tâche de cette liste ne contient de TODO/FIXME laissé en production ;
2. tests Python, JS, build structurel, smoke production et packaging passent ;
3. couverture appropriée des nouveaux modules Python/scripts ;
4. revue architecture : aucune détection implicite de build, aucune exposition de `node_modules` en production, aucun proxy dev ;
5. analyse post-implémentation avec zéro finding CRITICAL ou MAJOR ;
6. revue de la documentation et de la suppression complète de l’ancien workflow vendor.
