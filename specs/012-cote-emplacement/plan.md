# Plan — #12 : Cote + Emplacement dans le catalogue

**Feature :** Afficher la cote et l'emplacement dans les résultats de recherche, filtrer par rayon, et afficher l'emplacement de remise lors d'un retour.

---

## 1. Contexte et inspiration

### Ce que font les autres SGB

| Système | Cote (call number) | Emplacement (shelving location) | Filtre | Retour |
|---|---|---|---|---|
| **BCDI** | Cote E. (30c) — auto-remplie depuis la notice, modifiable par exemplaire | Emplacement (30c) — affiché dans e-sidoc (portail OPAC) | Index sur Emplacement | Situation → Disponible automatiquement |
| **Koha** | `952$o` fullcallnumber — affiché OPAC si `OpacItemLocation` activé | `952$c` location — facette dédiée, filtre onglet "Shelving location" dans la recherche avancée | Onglet + facette "Locations" | `UpdateItemLocationOnCheckin` peut changer l'emplacement au retour |
| **PMB** | Affiché dans les résultats catalog | Affiché dans les résultats catalog | Filtres par section | — |

**Enseignement clé :** Dans les 3 systèmes, la cote et l'emplacement sont des champs **exemplaire** (pas notice) affichés dans les résultats OPAC. Koha le rend configurable via la préférence `OpacItemLocation`.

### État actuel de BCD4

| Élément | État |
|---|---|
| `item.call_number` (String 50) | ✅ existe en base |
| `item.shelf_location` (String 100) | ✅ existe en base |
| i18n `catalog.shelf_location` | ✅ déjà présent (fr+en) |
| Recherche API — filtre `shelf_location` | ❌ absent |
| Résultats de recherche — cote/emplacement | ❌ absent |
| Retour — `shelf_location` dans la réponse | ❌ absent |

---

## 2. Découpage en sous-features

```
#12
├── A — Cote + emplacement dans les résultats de recherche
├── B — Filtre par rayon (emplacement) dans la recherche
└── C — Emplacement de remise lors d'un retour
```

**Ordre d'implémentation recommandé :** A → C → B (complexité croissante)

---

## 3. Sous-feature A — Cote + emplacement dans les résultats

### 3.1 Comportement

- Afficher, sous le titre dans les résultats, la **cote du premier exemplaire disponible**.
- Afficher l'**emplacement** (ou les emplacements distincts si plusieurs).
- Si aucun exemplaire disponible → afficher quand même cote + emplacement du premier exemplaire.
- Si 0 exemplaire → ne rien afficher.

```
Comportement "emplacement" :
  - 1 emplacement distinct  → l'afficher directement
  - 2+ emplacements distincts → afficher tous séparés par " · "
  - Tous null/vides → ne rien afficher
```

### 3.2 Mockup — Résultats de recherche

```
┌─────────────────────────────────────────────────────────────────────┐
│ ☐ │ Titre          │ Auteur     │ Éditeur │ Année │ Dispo          │
├───┼────────────────┼────────────┼─────────┼───────┼────────────────┤
│ ☐ │ Harry Potter   │ Rowling    │ Folio   │ 1998  │ ● Disponible   │
│   │ et la Pierre…  │            │         │       │ 3/3 exemplaires│
│   │ ┌─────────────────────────┐ │         │       │                │
│   │ │ ⊙ 821 ROW              │ │         │       │                │
│   │ │ 📍 Romans ado          │ │         │       │                │
│   │ └─────────────────────────┘ │         │       │                │
├───┼────────────────┼────────────┼─────────┼───────┼────────────────┤
│ ☐ │ Le Petit Prince│ St-Exupéry │ Folio   │ 1943  │ ○ Emprunté    │
│   │                │            │         │       │ 0/1 exemplaire │
│   │ ┌─────────────────────────┐ │         │       │                │
│   │ │ ⊙ 843 SAI              │ │         │       │                │
│   │ │ 📍 Albums · Contes     │ │         │       │                │
│   │ └─────────────────────────┘ │         │       │                │
├───┼────────────────┼────────────┼─────────┼───────┼────────────────┤
│ ☐ │ Astérix T.1    │ Goscinny   │ Dargaud │ 1961  │ ● Disponible   │
│   │                │            │         │       │ 2/2 exemplaires│
│   │   (pas de cote ni emplacement renseignés)      │                │
└───┴────────────────┴────────────┴─────────┴───────┴────────────────┘
```

**Affichage compact sous le titre (sans colonne séparée) :**
- Icône `⊙` pour la cote (discret, gris)
- Icône `📍` ou badge pour l'emplacement (couleur secondaire)
- Sur la même ligne ou deux lignes minuscules sous le titre
- Absent si champs vides

### 3.3 Modifications backend

**Fichier : `src/bcd_api/api/v1/catalog.py`**

**Approche : 2 requêtes groupées sur tous les IDs de la page** (pas de requêtes en boucle).

Le code actuel boucle déjà sur `records` et fait 3 requêtes par résultat (total_count, available_count, active_holds_count). Ajouter des requêtes en boucle serait O(N) supplémentaire. À la place, récupérer tout en une passe **avant** la boucle :

```python
# Collecter les IDs de la page
record_ids = [r.id for r in records]

# Requête 1 : premier exemplaire par notice (prefer available, fallback any)
# Sous-requête : min(id) par bibliographic_record_id pour chaque statut
from sqlalchemy import case, func as sqlfunc

first_items_query = (
    db.query(Item)
    .filter(Item.bibliographic_record_id.in_(record_ids))
    .order_by(
        Item.bibliographic_record_id,
        # available en premier, puis les autres
        case((Item.status == ItemStatus.AVAILABLE.value, 0), else_=1),
        Item.id
    )
    .all()
)
# Garder le premier par record_id
first_item_by_record: dict[int, Item] = {}
for item in first_items_query:
    if item.bibliographic_record_id not in first_item_by_record:
        first_item_by_record[item.bibliographic_record_id] = item

# Requête 2 : emplacements distincts par notice
shelf_rows = (
    db.query(Item.bibliographic_record_id, Item.shelf_location)
    .filter(
        Item.bibliographic_record_id.in_(record_ids),
        Item.shelf_location.isnot(None),
        Item.shelf_location != ""
    )
    .distinct()
    .all()
)
shelf_locations_by_record: dict[int, list[str]] = {}
for rec_id, loc in shelf_rows:
    shelf_locations_by_record.setdefault(rec_id, []).append(loc)
```

Dans la boucle de construction de `record_dict`, ajouter :

```python
first_item = first_item_by_record.get(r.id)
record_dict.update({
    "call_number": first_item.call_number if first_item else None,
    "shelf_locations": sorted(shelf_locations_by_record.get(r.id, [])),
})
```

**Résultat :** 2 requêtes pour toute la page, quelle que soit la taille (vs N×2 requêtes auparavant).

### 3.4 Modifications frontend

**Fichier : `src/bcd_web_vue/js/components/catalog/SearchResults.js`**

Le composant a **deux modes d'affichage** : `table` et `cards`. Les deux doivent être mis à jour.

**Mode table** — dans le `<td v-if="isColumnVisible('title')">`, après le bloc subtitle :

```html
<!-- Cote + emplacement -->
<div v-if="record.call_number || record.shelf_locations?.length" class="mt-1 small text-muted">
  <span v-if="record.call_number" class="me-2">
    <i class="bi bi-bookmarks"></i> {{ record.call_number }}
  </span>
  <span v-if="record.shelf_locations?.length" class="text-primary-emphasis">
    <i class="bi bi-geo-alt"></i>
    {{ record.shelf_locations.join(' · ') }}
  </span>
</div>
```

**Mode cartes** — dans le `card-body`, après le bloc publisher/year :

```html
<!-- Cote + emplacement -->
<p v-if="record.call_number || record.shelf_locations?.length" class="card-text small text-muted mb-2">
  <span v-if="record.call_number" class="me-2">
    <i class="bi bi-bookmarks"></i> {{ record.call_number }}
  </span>
  <span v-if="record.shelf_locations?.length" class="text-primary-emphasis">
    <i class="bi bi-geo-alt"></i>
    {{ record.shelf_locations.join(' · ') }}
  </span>
</p>
```

**Pas de nouvelle colonne** — affichage sous le titre pour conserver la densité du tableau et la lisibilité sur petits écrans.

---

## 4. Sous-feature B — Filtre par rayon

### 4.1 Comportement

- Nouveau filtre "Rayon" (emplacement) dans le panneau filtres avancés.
- Liste déroulante des valeurs distinctes d'`item.shelf_location` existantes en base.
- Sélectionner un rayon → filtre les notices ayant au moins un exemplaire avec cet emplacement.
- Vide = pas de filtre (comportement habituel).

### 4.2 Mockup — Filtres avancés

```
┌─────────────────────────────────────────────────────┐
│ FILTRES AVANCÉS                            [Réinit] │
├─────────────────────────────────────────────────────┤
│ Disponibilité        [Tous ▼]                       │
│ Catégorie            [Toutes ▼]                     │
│ Genre                [Tous ▼]                       │
│ Type de document     [Tous ▼]                       │
│ Langue               [Toutes ▼]                     │
│ ─────────────────────────────────────────────────── │
│ Rayon / Emplacement  [Tous ▼]              ← NOUVEAU │
│                       ┌─────────────────┐           │
│                       │ (Tous)          │           │
│                       │ Albums          │           │
│                       │ BDs             │           │
│                       │ Contes          │           │
│                       │ Documentaires   │           │
│                       │ Romans ado      │           │
│                       │ Romans juniors  │           │
│                       └─────────────────┘           │
└─────────────────────────────────────────────────────┘
```

### 4.3 Modifications backend

**Nouvel endpoint : `GET /catalog/locations`**

```python
# src/bcd_api/api/v1/catalog.py
@router.get("/locations")
def get_shelf_locations(db: Session = Depends(get_db)):
    """Returns distinct non-empty shelf_location values, sorted."""
    results = (
        db.query(Item.shelf_location)
        .filter(Item.shelf_location.isnot(None), Item.shelf_location != "")
        .distinct()
        .order_by(Item.shelf_location)
        .all()
    )
    return {"locations": [r[0] for r in results]}
```

**Filtre dans `search_bibliographic_records`** (`catalog_service.py`) :

```python
# Ajouter le paramètre
def search_bibliographic_records(
    db: Session,
    ...
    shelf_location: Optional[str] = None,   # ← nouveau
    ...
):
    # Ajouter le filtre (EXISTS subquery)
    if shelf_location:
        query = query.filter(
            exists().where(
                and_(
                    Item.bibliographic_record_id == BiblographicRecord.id,
                    Item.shelf_location == shelf_location
                )
            )
        )
```

**Paramètre dans l'endpoint** (`catalog.py`) :

```python
shelf_location: Optional[str] = Query(None, description="Filter by shelf location"),
```

### 4.4 Modifications frontend

**`src/bcd_web_vue/js/pages/CatalogPage.js`** — trois changements :

1. Ajouter dans `filters` :

```js
shelf_location: '',
```

2. Charger les emplacements depuis l'API dans `onMounted` (ou au premier appel) et les passer à `AdvancedFilters` comme prop :

```js
const shelfLocations = ref([]);

// dans onMounted ou à l'init :
const data = await apiClient.get('/catalog/locations');
shelfLocations.value = data.locations || [];
```

3. Passer `shelf_location` dans `performSearch` :

```js
if (filters.shelf_location) {
    params.shelf_location = filters.shelf_location;
}
```

**`src/bcd_web_vue/js/components/catalog/AdvancedFilters.js`** — quatre changements :

1. Ajouter la prop `shelfLocations` :

```js
shelfLocations: { type: Array, default: () => [] }
```

2. Calculer les options pour le select :

```js
const locationOptions = computed(() =>
    props.shelfLocations.map(loc => ({ value: loc, label: loc }))
);
```

3. Mettre à jour `clearFilters` pour inclure `shelf_location` :

```js
const clearFilters = () => {
    const clearedFilters = {
        availability: 'all',
        genre: '',
        level: '',
        language: '',
        medium_type: '',
        shelf_location: ''   // ← ajouter
    };
    ...
};
```

4. Ajouter dans le template (section filtres avancés) — utiliser `FilterSelect` déjà importé. **Attention :** la prop est `placeholder` (pas `all-label`) et `showPlaceholder` (booléen) :

```html
<div class="col-md-3">
  <label class="form-label">{{ t('catalog.filter_location') }}</label>
  <filter-select
    :model-value="filters.shelf_location"
    :options="locationOptions"
    :placeholder="t('catalog.all_items')"
    :show-placeholder="true"
    @update:model-value="updateFilter('shelf_location', $event)"
  />
</div>
```

**i18n** — clé à ajouter (`fr.json` + `en.json`) :

```json
"filter_location": "Rayon / Emplacement"
```

---

## 5. Sous-feature C — Emplacement de remise lors d'un retour

### 5.1 Comportement

Après le scan d'un code-barres pour un retour, afficher dans la confirmation :
- La cote (déjà présente via `call_number`)
- **L'emplacement de remise** → indique au bibliothécaire où ranger le livre

S'inspire de Koha (retour avec instruction de rangement) et BCDI (Situation → Disponible).

### 5.2 Mockup — Confirmation de retour

```
┌────────────────────────────────────────────────────────────┐
│ ✅ Retour enregistré                                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Harry Potter et la Chambre des Secrets                    │
│  Rowling J.K. · Folio Junior                               │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Cote      : 821 ROW                                 │  │
│  │  📍 Rayon  : Romans ado  ← NOUVEAU                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  Rendu par   : Amira BENALI (CE2-A)                       │
│  Date retour : 15/06/2026                                  │
│  Statut      : ✓ Dans les délais                          │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ⚡ Réservation prête pour Sophie MARTIN (CM1-B)     │  │
│  │  Mettre de côté jusqu'au 22/06/2026                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Règle d'affichage :**
- `shelf_location` présent → afficher dans un badge sous la cote
- `shelf_location` null/vide → ne pas afficher (ne pas casser l'existant)

### 5.3 Modifications backend

**Fichier : `src/bcd_api/services/circulation_service.py`**

Dans `return_items()`, ajouter `shelf_location` dans le dict `returned_items` (ligne ~342). Vérification du code actuel : `call_number` est déjà présent, `shelf_location` manque :

```python
returned_items.append({
    "item_id": item.item_id,
    "title": transaction.bibliographic_record.title,
    "call_number": item.call_number,
    "shelf_location": item.shelf_location,   # ← ajouter
    "display_title": _display_title(transaction.bibliographic_record.title, item.call_number),
    ...
})
```

**Note :** Le schéma `ReturnResponse` utilise `list[dict]` pour `items` donc aucune modification de schema Pydantic nécessaire.

### 5.4 Modifications frontend

**Fichier : `src/bcd_web_vue/js/pages/CirculationPage.js`**

**Attention :** La fonction `performReturn` (lignes ~294-304) construit l'objet pushé dans `scannedItems`. Actuellement, ni `call_number` ni `shelf_location` n'y figurent. Il faut les deux :

```js
scannedItems.value.push({
    item_id: transaction.item_id,
    barcode: barcode,
    title: transaction.display_title || transaction.title || 'Unknown',
    author: transaction.author,
    call_number: transaction.call_number,       // ← ajouter
    shelf_location: transaction.shelf_location, // ← ajouter
    returned_date: transaction.return_date,
    returned: true,
    was_overdue: transaction.was_overdue,
    days_overdue: transaction.days_overdue,
    hold_ready: transaction.hold_ready
});
```

Dans le **template** de la liste de retours (dans le `<td>` titre, après `item.was_overdue`), ajouter :

```html
<div v-if="item.shelf_location" class="badge bg-primary-subtle text-primary-emphasis mt-1">
  <i class="bi bi-geo-alt-fill"></i>
  {{ t('catalog.shelf_location') }} : {{ item.shelf_location }}
</div>
```

**i18n :** La clé `catalog.shelf_location` est déjà présente en fr (`"Emplacement"`) et en (`"Location"`).

---

## 6. Résumé des fichiers modifiés

| Fichier | Sous-feature | Type de changement |
|---|---|---|
| `src/bcd_api/api/v1/catalog.py` | A + B | Enrichir dict résultats + nouveau endpoint + nouveau paramètre |
| `src/bcd_api/services/catalog_service.py` | B | Nouveau paramètre `shelf_location` dans `search_bibliographic_records` |
| `src/bcd_api/services/circulation_service.py` | C | Ajouter `shelf_location` dans `returned_items` dict |
| `src/bcd_web_vue/js/components/catalog/SearchResults.js` | A | Afficher cote + emplacement sous le titre (mode table ET cartes) |
| `src/bcd_web_vue/js/components/catalog/AdvancedFilters.js` | B | Nouveau filtre Rayon + prop `shelfLocations` + clearFilters |
| `src/bcd_web_vue/js/pages/CatalogPage.js` | B | `shelf_location` dans `filters`, chargement locations API, passer prop |
| `src/bcd_web_vue/js/pages/CirculationPage.js` | C | Ajouter `call_number`+`shelf_location` dans `scannedItems`, afficher dans template |
| `src/bcd_web_vue/locales/fr.json` | B | `"filter_location"` |
| `src/bcd_web_vue/locales/en.json` | B | `"filter_location"` |

**Migrations Alembic :** Aucune — les champs `call_number` et `shelf_location` existent déjà en base.

**Tests :** Ajouter dans `tests/integration/services/` :
- `test_search_bibliographic_records_filter_by_shelf_location`
- `test_return_items_includes_shelf_location`

---

## 7. Ordre d'implémentation

```
1. [C] Backend: +shelf_location dans return_items (5 min — 1 ligne)
2. [C] Frontend: Afficher emplacement dans CirculationPage (15 min)
3. [A] Backend: Enrichir dict search avec call_number + shelf_locations (20 min)
4. [A] Frontend: Afficher sous le titre dans SearchResults (20 min)
5. [B] Backend: GET /catalog/locations + filtre search (30 min)
6. [B] Frontend: Filtre Rayon dans AdvancedFilters + CatalogPage (30 min)
7. [*] Tests + i18n (30 min)
```

**Effort total estimé :** ~2h30

---

## 8. Points d'attention

1. **Performance A :** Requêtes groupées (`IN` list) — 2 requêtes pour toute la page au lieu de N×2. Le code actuel dans `catalog.py` fait déjà 3 requêtes/résultat pour total/available/holds ; on ne doit pas en ajouter d'autres en boucle.

2. **SearchResults — deux modes :** Le composant a une vue `table` et une vue `cards`. Les deux doivent afficher cote + emplacement (sinon incohérence UX selon le mode actif).

3. **AdvancedFilters — `FilterSelect` props :** Le composant `FilterSelect` n'a pas de prop `all-label`. Utiliser `placeholder` + `showPlaceholder: true`. Les `options` ont le format `{value, label}`.

4. **AdvancedFilters — `clearFilters` :** Doit inclure `shelf_location: ''` pour que le reset du filtre fonctionne.

5. **CirculationPage — `scannedItems` :** Ni `call_number` ni `shelf_location` ne sont actuellement copiés de `transaction` vers `scannedItems`. Les deux doivent être ajoutés côté frontend ET côté backend.

6. **Chargement des locations (B) :** Se fait dans `CatalogPage` (pas dans `AdvancedFilters`) pour rester cohérent avec l'architecture — les composants ne font pas d'appels API directement.

7. **Emplacement vide :** Par convention, si `shelf_location` est null ou `""` → ne rien afficher. Ne jamais afficher `"null"` ou `"-"`.

8. **Client Godot Kids :** Les enfants n'ont pas besoin de voir la cote/emplacement dans `SSearch`. Le libraire utilise l'interface web. Pas de modifications côté `bcd_kids/`.
