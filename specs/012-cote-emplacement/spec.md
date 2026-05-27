# Spec — #12b : Cote Dewey + Emplacements configurables

## Contexte

### Pourquoi cette feature ?

Les enseignants qui gèrent une BCD (Bibliothèque Centre Documentaire) d'école primaire
ont deux besoins distincts :

1. **Indiquer où ranger un livre** dans leur bibliothèque physique (les "rayons") — c'est
   l'*emplacement local*, propre à chaque école.
2. **Classer les documentaires** par sujet selon un système standard (Dewey) pour que les
   élèves puissent retrouver les livres par thème.

Aujourd'hui, BCD a deux champs libres (`call_number`, `shelf_location`) sans logique ni
guidage. Le résultat : incohérence, erreurs de frappe, données inutilisables.

### Ce qu'on a appris

**La classification Dewey en BCD primaire :**
- On n'utilise que les 10 grandes classes (0–9), parfois les 100 divisions — jamais plus.
- Toute la fiction (Albums, Romans, BD, Contes, Poésie) va en classe **8** (Littérature),
  souvent notée `800`.
- Les documentaires reçoivent un indice Dewey à 3 chiffres : `551` (géosciences),
  `944` (histoire de France), etc.
- La cote complète = indice Dewey + 3 premières lettres de l'auteur : `551 VER`, `944 DUP`.
- La **marguerite des couleurs** (CRDP Grenoble) est le standard visuel français : chaque
  grande classe a une couleur, les livres portent une étiquette de cette couleur sur le dos.

**Ce que fait la BnF :**
- Le catalogue BnF contient le numéro Dewey dans le champ UNIMARC `676$a`.
- Ce champ est absent pour beaucoup de livres jeunesse anciens ou de petits éditeurs.
- Quand il est présent, c'est le Dewey complet (`551.46`, `306.850 83`) — on le garde tel
  quel, l'enseignant peut le simplifier.
- On **ne peut pas** générer le Dewey automatiquement à partir du titre/auteur de façon
  fiable. C'est un choix éditorial que fait le catalogueur.

**Ce que fait Bibliopuce (d'après leur export) :**
- Toute la fiction → `800.000` (pas de distinction Album/Roman/BD dans la cote)
- Documentaires → Dewey simplifié saisi manuellement (`551.200`, `944.000`, etc.)
- Pas de lettres auteur ajoutées à la cote
- 5054 livres, dont 1392 en `800.xxx` et 523 en documentaire

**Emplacements :**
- Il n'existe pas de standard international pour les rayons d'une bibliothèque.
- Chaque école organise ses rayons comme elle veut : "Rayons Romans", "Bacs BD",
  "Présentoir périodiques"...
- Les systèmes (Koha, BCDI) proposent tous une liste configurable localement.

---

## Ce qu'on implémente

### Vue d'ensemble

```
Notice (BiblographicRecord)
  └── dewey_number (nouveau) : "551.46"  ← extrait de la BnF au catalogage

Exemplaire (Item)
  ├── call_number : "551.46 VER"  ← généré (Dewey + AUT3), modifiable
  └── shelf_location : "Documentaires"  ← saisi librement avec suggestions

Settings
  └── catalog_shelf_locations (nouveau) : liste {label, color|null}
      ex: [{"label": "Romans", "color": "#c0392b"}, {"label": "Premières lectures", "color": null}]

Affichage
  ├── badge carré (border-radius: 4px)   = emplacement local (shelf_location)
  └── badge arrondi (border-radius: 20px) = cote Dewey (call_number)
      Les deux sont affichés simultanément quand les deux champs sont renseignés.
```

---

## Règles métier

### Cote (`call_number`)

| Situation | Cote suggérée | Exemple |
|-----------|--------------|---------|
| BnF a retourné un Dewey | `[dewey_number] [AUT3]` | `551.46 VER` |
| BnF n'a pas de Dewey | champ vide (saisie manuelle) | — |
| Périodique | numéro de fascicule libre | `1024` |

**AUT3** = 3 premières lettres du nom de famille de l'auteur principal, en majuscules,
sans accents. Exemples : "Verdet, Jean-Pierre" → `VER` ; "Éric Dupont" → `DUP` ;
"J.K. Rowling" → `ROW`.

La cote suggérée est **pré-remplie** dans le formulaire de création d'exemplaire et reste
modifiable. Elle n'est jamais imposée.

### Emplacement (`shelf_location`)

- Saisi via un `input + datalist` : saisie libre avec suggestions natives du navigateur.
- Les suggestions viennent de `catalog_shelf_locations` dans les réglages.
- Valeur vide = pas d'emplacement défini (acceptable pour les petites collections).
- Valeur stockée = le libellé (ex: `"Romans"`). Si le libellé est renommé dans les
  réglages, les anciens exemplaires gardent l'ancien libellé.

### Affichage des badges emplacement et cote

Les deux badges sont **toujours affichés simultanément** quand les champs sont renseignés.
Ils se distinguent par leur forme :

```
badge carré   (border-radius: 4px)  → shelf_location
badge arrondi (border-radius: 20px) → call_number

shelf_location renseigné ?
  → OUI : badge carré avec la couleur définie dans les réglages
           si color est null : badge gris neutre (bg-light border)
           si shelf_location ne correspond à aucun rayon : badge gris (#6c757d)
  → NON : aucun badge carré

call_number renseigné ?
  → OUI : badge arrondi avec la couleur Dewey (marguerite, selon le 1er chiffre)
           si premier caractère non numérique : badge gris
           si couleur Dewey = blanc (#ffffff) : ajouter border: 1px solid #bbb
  → NON : aucun badge arrondi
```

---

## Implémentation

### Étape 1 — BnF : extraire le champ Dewey

**Fichier :** `src/bcd_api/services/bnf_service.py`

Ajouter la lecture du champ UNIMARC `676$a` dans `parse_unimarc_xml()`, après le bloc
keywords (champ 606) :

```python
dewey_elem = marc_record.find(
    './/mxc:datafield[@tag="676"]/mxc:subfield[@code="a"]', ns
)
if dewey_elem is not None and dewey_elem.text:
    data["dewey_number"] = dewey_elem.text.strip()
```

- On stocke la valeur brute telle quelle (`"551.46"`).
- Si 676$a est absent : `dewey_number` n'est pas dans `data`, reste `None` sur la notice.
- S'il y a plusieurs occurrences de 676 : prendre la première (`find`, pas `findall`).

**Test :** Fixture XML avec `<datafield tag="676"><subfield code="a">551.46</subfield>
</datafield>` → `data["dewey_number"] == "551.46"`.

---

### Étape 2 — Modèle + migration + schémas

**Migration Alembic** (un seul fichier, dépend de `514a09aea333`) :

```python
DEFAULT_SHELF_LOCATIONS = json.dumps([
    {"label": "Romans",           "color": "#c0392b"},
    {"label": "Albums",           "color": "#e67e22"},
    {"label": "Bandes dessinées", "color": "#2980b9"},
    {"label": "Documentaires",    "color": "#27ae60"},
    {"label": "Périodiques",      "color": "#16a085"},
    {"label": "Contes",           "color": "#f39c12"},
    {"label": "Poésie",           "color": "#8e44ad"},
])

def upgrade():
    # Dewey sur la notice bibliographique
    op.add_column('bibliographic_record',
        sa.Column('dewey_number', sa.Text(), nullable=True))
    # Emplacements configurables dans les réglages
    op.add_column('system_settings',
        sa.Column('catalog_shelf_locations', sa.Text(), nullable=True,
                  server_default=DEFAULT_SHELF_LOCATIONS))

def downgrade():
    op.drop_column('bibliographic_record', 'dewey_number')
    op.drop_column('system_settings', 'catalog_shelf_locations')
```

**Modèle `BiblographicRecord`** — ajouter :
```python
dewey_number = Column(Text, nullable=True)
```

**Modèle `SystemSettings`** — ajouter :
```python
catalog_shelf_locations = Column(Text, nullable=True, default=DEFAULT_SHELF_LOCATIONS)
```

**Schémas Pydantic :**
- `BiblographicRecordBase` et `BiblographicRecordUpdate` : `dewey_number: Optional[str] = None`
- `SystemSettingsResponse` et `SystemSettingsUpdate` : `catalog_shelf_locations: Optional[str] = None`

**Service settings** — deux modifications dans `src/bcd_api/services/settings_service.py` :

1. Ajouter `"catalog_shelf_locations"` dans `allowed_fields`.

2. Ajouter l'initialisation dans `initialize_default_settings()`, comme les autres listes
   du catalogue (`catalog_genres`, `catalog_medium_types`…) :

```python
DEFAULT_SHELF_LOCATIONS_JSON = json.dumps([
    {"label": "Romans",           "color": "#c0392b"},
    {"label": "Albums",           "color": "#e67e22"},
    {"label": "Bandes dessinées", "color": "#2980b9"},
    {"label": "Documentaires",    "color": "#27ae60"},
    {"label": "Périodiques",      "color": "#16a085"},
    {"label": "Contes",           "color": "#f39c12"},
    {"label": "Poésie",           "color": "#8e44ad"},
])

# Dans initialize_default_settings() :
settings = SystemSettings(
    ...
    catalog_shelf_locations=DEFAULT_SHELF_LOCATIONS_JSON,
)
```

---

### Étape 3 — Génération de la cote (frontend)

**Fichier :** `src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js`

**Nouvelles props :**
```javascript
recordDeweyNumber: { type: String, default: null },
recordAuthors:     { type: Array,  default: () => [] }
```

**Fonction utilitaire `computeAut3(authors)` :**
```javascript
function computeAut3(authors) {
    if (!authors?.length) return null;
    const name = authors[0];
    // Format "Nom, Prénom" → prendre avant la virgule
    // Format "Prénom Nom" → prendre le dernier mot
    const commaIdx = name.indexOf(',');
    const lastname = commaIdx > 0
        ? name.slice(0, commaIdx).trim()
        : name.trim().split(/\s+/).at(-1);
    return lastname
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .toUpperCase().slice(0, 3);
}
```

**Cote suggérée :**
```javascript
const suggestedCallNumber = computed(() => {
    if (!props.recordDeweyNumber) return '';
    const aut3 = computeAut3(props.recordAuthors);
    return aut3 ? `${props.recordDeweyNumber} ${aut3}` : props.recordDeweyNumber;
});

// Pré-remplir une seule fois à l'ouverture
watch(suggestedCallNumber, (val) => {
    if (val && !callNumber.value) callNumber.value = val;
}, { immediate: true });
```

**Parent `CatalogingPage.js`** — enrichir `createdRecord` avec `dewey_number` et
`authors`, et les passer en props à `ItemBarcodeInput`. Il existe deux chemins :

- `handleRecordCreated()` : assigne `createdRecord.value = record` (objet complet renvoyé
  par l'API) → `dewey_number` et `authors` présents si l'API les retourne. ✓
- `handleExistingRecordFound()` : construit `createdRecord.value = { id, title, medium_type }`
  manuellement → ajouter `dewey_number` et `authors` ici aussi :

```javascript
createdRecord.value = {
    id: record.record_id || record.id,
    title: record.title,
    medium_type: record.medium_type,
    dewey_number: record.dewey_number || null,
    authors: record.authors || [],
};
```

**Tests AUT3 :**

| Input | Attendu |
|-------|---------|
| `["Verdet, Jean-Pierre"]` | `VER` |
| `["Éric Dupont"]` | `DUP` |
| `["J.K. Rowling"]` | `ROW` |
| `["Ségolène Martin"]` | `MAR` |
| `["Li"]` | `LI` |
| `[]` | `null` |

---

### Étape 4 — Emplacements : input + datalist dans les formulaires

**Fichiers :** `ItemBarcodeInput.js` et `ItemEditForm.js`

Les deux composants importent déjà `useAppState`. Ajouter :

```javascript
const shelfLocations = computed(() => {
    try {
        return JSON.parse(settings.value?.catalog_shelf_locations || 'null') || [];
    } catch { return []; }
});
```

Remplacer le champ libre `shelf_location` + `StickerPicker` par un `input + datalist`
(même pattern que `BulkEditModal.js`) :

```html
<input type="text"
       v-model="shelfLocation"
       class="form-control"
       list="shelf-suggestions"
       :placeholder="$t('catalog.shelf_location_placeholder')"
       :disabled="loading" />
<datalist id="shelf-suggestions">
    <option v-for="loc in shelfLocations" :key="loc.label" :value="loc.label" />
</datalist>
```

ID statique suffisant : `ItemBarcodeInput` (catalogage) et `ItemEditForm` (modale) ne
sont jamais présents dans le DOM en même temps.

Supprimer l'import `StickerPicker` des deux composants.

**Périodiques dans `ItemBarcodeInput`** : Le composant a une branche `isPeriodical` qui
affiche un champ "Numéro de fascicule" à la place du DeweyPicker. Pour les périodiques :
- Ne pas pré-remplir la cote depuis `recordDeweyNumber` (le `watch` sur `suggestedCallNumber`
  ne doit s'activer que si `!isPeriodical.value`)
- Afficher quand même le datalist emplacement (un périodique peut avoir un rayon)

**Rétrocompatibilité :** Les items existants avec une valeur libre dans `shelf_location`
(ex: `"🔴 Romans ado"`) gardent leur valeur en base. L'input affichera cette valeur ;
elle n'est écrasée que si l'utilisateur la modifie et sauvegarde.

---

### Étape 5a — Correction API : cohérence `shelf_location` / `call_number`

**Problème actuel :** L'endpoint de recherche (`GET /catalog/search`) fait deux requêtes
SQL distinctes avec une logique incohérente :
- `call_number` → premier item (disponible préféré, puis par id)
- `shelf_locations` → requête `DISTINCT` séparée sur **tous** les items → array agrégé

C'est incohérent et inutilement lourd.

**Correction dans `src/bcd_api/api/v1/catalog.py` :**

Supprimer le batch query `shelf_rows` (lignes ~225–238) et utiliser directement
`first_item.shelf_location` :

```python
# Supprimer ceci :
# shelf_rows = db.query(...).distinct().all()
# shelf_locations_by_record = ...

# Dans la construction du record_dict, remplacer :
# "shelf_locations": shelf_locations,           ← supprimer
# par :
"shelf_location": first_item.shelf_location if first_item else None,
```

**Correction dans `src/bcd_web_vue/js/components/catalog/SearchResults.js` :**

Remplacer partout `record.shelf_locations` (array) par `record.shelf_location` (string).
Supprimer le `.join(' · ')` et la vérification `.length`.

---

### Étape 5b — Affichage : deux badges simultanés

**Nouveau fichier :** `src/bcd_web_vue/js/utils/colors.js`

Extraire la fonction `autoTextColor` de `DeweyPicker.js` ici :

```javascript
export function autoTextColor(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55 ? '#000000' : '#ffffff';
}
```

Mettre à jour `DeweyPicker.js` pour importer depuis ce fichier, et ajouter une prop
`showBadge` (optionnelle, défaut `true`) pour permettre de masquer le badge coloré :

```javascript
// Nouvelle prop dans DeweyPicker
showBadge: { type: Boolean, default: true }
```

```html
<!-- Dans le template, conditionner l'affichage du badge -->
<div v-if="showBadge" class="dewey-badge ..." :style="badgeStyle">{{ badgeText }}</div>
```

Cas d'usage : dans `SettingsForm.js`, la section "Couleurs Dewey" peut proposer un
aperçu sans badge si l'utilisateur préfère une interface épurée. Dans les formulaires
d'exemplaire, le badge reste affiché par défaut (`showBadge` non passé = `true`).

**Nouveau composable :** `src/bcd_web_vue/js/composables/useItemBadge.js`

```javascript
import { computed } from 'vue';
import { autoTextColor } from '../utils/colors.js';

const DEFAULT_DEWEY_COLORS = [
    '#000000','#9e6633','#f20000','#ff9813','#ffee00',
    '#409d42','#0fafe9','#98238b','#d3d5d4','#ffffff'
];

export function useItemBadge(settings) {
    const shelfColorMap = computed(() => {
        try {
            const locs = JSON.parse(settings.value?.catalog_shelf_locations || 'null') || [];
            return Object.fromEntries(locs.map(l => [l.label, l.color]));
        } catch { return {}; }
    });

    const deweyColors = computed(() => {
        try {
            return JSON.parse(settings.value?.dewey_colors || 'null') || DEFAULT_DEWEY_COLORS;
        } catch { return DEFAULT_DEWEY_COLORS; }
    });

    // Badge carré : emplacement local
    function getShelfBadge(item) {
        if (!item.shelf_location) return null;
        const color = shelfColorMap.value[item.shelf_location];
        if (color === undefined) {
            // Rayon inconnu → gris Bootstrap
            return { label: item.shelf_location, style: { background: '#6c757d', color: '#fff' }, neutral: false };
        }
        if (!color) {
            // color: null → badge neutre (gris clair)
            return { label: item.shelf_location, style: null, neutral: true };
        }
        return { label: item.shelf_location, style: { background: color, color: autoTextColor(color) }, neutral: false };
    }

    // Badge arrondi : cote Dewey
    function getCoteBadge(item) {
        if (!item.call_number) return null;
        const first = item.call_number.trim()[0];
        const idx = (first >= '0' && first <= '9') ? parseInt(first) : null;
        if (idx === null) return { label: item.call_number, style: { background: '#6c757d', color: '#fff' }, outline: false };
        const hex = deweyColors.value[idx] ?? '#cccccc';
        const isWhite = hex === '#ffffff' || hex === '#fff';
        return {
            label: item.call_number,
            style: { background: hex, color: autoTextColor(hex) },
            outline: isWhite   // si vrai, ajouter border: 1px solid #bbb dans le template
        };
    }

    return { getShelfBadge, getCoteBadge };
}
```

**Utilisation dans `RecordDetail.js`** (items individuels — interface directe) :

```javascript
const { settings } = useAppState();
const { getShelfBadge, getCoteBadge } = useItemBadge(settings);
```

```html
<div class="d-flex gap-1 flex-wrap">
    <!-- Badge carré = emplacement -->
    <span v-if="getShelfBadge(item)"
          class="badge"
          style="border-radius: 4px;"
          :class="getShelfBadge(item).neutral ? 'bg-light text-dark border' : ''"
          :style="getShelfBadge(item).neutral ? {} : getShelfBadge(item).style">
        {{ getShelfBadge(item).label }}
    </span>
    <!-- Badge arrondi = cote Dewey -->
    <span v-if="getCoteBadge(item)"
          class="badge"
          style="border-radius: 20px;"
          :style="[getCoteBadge(item).style, getCoteBadge(item).outline ? { border: '1px solid #bbb' } : {}]">
        {{ getCoteBadge(item).label }}
    </span>
</div>
```

**Utilisation dans `SearchResults.js`** (après correction étape 5a) :

Après la correction API, `record.shelf_location` est une string (comme `record.call_number`).
L'interface est identique à RecordDetail — on passe directement le record :

```html
<div class="d-flex gap-1 flex-wrap">
    <span v-if="getShelfBadge(record)"
          class="badge"
          style="border-radius: 4px;"
          :class="getShelfBadge(record).neutral ? 'bg-light text-dark border' : ''"
          :style="getShelfBadge(record).neutral ? {} : getShelfBadge(record).style">
        {{ getShelfBadge(record).label }}
    </span>
    <span v-if="getCoteBadge(record)"
          class="badge"
          style="border-radius: 20px;"
          :style="[getCoteBadge(record).style, getCoteBadge(record).outline ? { border: '1px solid #bbb' } : {}]">
        {{ getCoteBadge(record).label }}
    </span>
</div>
```

Supprimer l'ancien affichage texte (`shelf_locations.join(' · ')` et `call_number` en
petit gris) qui sera remplacé par ces badges.

---

### Étape 6 — Réglages : section "Emplacements"

**Fichier :** `src/bcd_web_vue/js/components/settings/SettingsForm.js`

**Règle i18n — obligatoire :** toute chaîne visible dans le template doit passer par
`t()`. Aucune chaîne française hardcodée dans le composant. Cela inclut :
- Le titre de section, le texte d'aide, le placeholder du libellé, le bouton "Ajouter",
  le titre de la case à cocher couleur.
- Les clés à ajouter dans `fr.json` **et** `en.json` sont listées à l'étape 7.

**Note sur `DEFAULT_SHELF_LOCATIONS` :** les libellés par défaut (`Romans`, `Albums`…)
sont des **données utilisateur** pré-remplies, pas des chaînes d'interface. Ils sont
intentionnellement en français (la majorité des BCD sont françaises). Ils peuvent être
modifiés librement par l'enseignant dans les réglages. Ne pas les passer par `t()`.

Ajouter dans `setup()` :

```javascript
const shelfLocationsList = computed(() => {
    try {
        const p = JSON.parse(props.settings.catalog_shelf_locations || 'null');
        if (Array.isArray(p)) return p;
    } catch {}
    return [];
});

const addShelfLocation = () => {
    const list = [...shelfLocationsList.value, { label: '', color: '#888888' }];
    props.settings.catalog_shelf_locations = JSON.stringify(list);
};

const removeShelfLocation = (idx) => {
    props.settings.catalog_shelf_locations = JSON.stringify(
        shelfLocationsList.value.filter((_, i) => i !== idx)
    );
};

const updateShelfLocation = (idx, key, val) => {
    props.settings.catalog_shelf_locations = JSON.stringify(
        shelfLocationsList.value.map((item, i) =>
            i === idx ? { ...item, [key]: val } : item
        )
    );
};

const toggleShelfColor = (idx, checked) => {
    updateShelfLocation(idx, 'color', checked ? '#888888' : null);
};
```

**Template** — nouvelle section entre "Listes du catalogue" et "Couleurs Dewey".
La couleur est **optionnelle** : une case à cocher l'active ou la désactive.
Sans couleur (`color: null`) → badge gris neutre à l'affichage.

```html
<!-- Emplacements -->
<div class="col-12 mt-4">
    <h4 class="border-bottom pb-2 mb-3">
        <i class="bi bi-bookshelf"></i>
        {{ t('settings.shelf_locations') }}
    </h4>
    <p class="text-muted small">{{ t('settings.shelf_locations_help') }}</p>
</div>

<div class="col-12">
    <div class="d-flex flex-column gap-2" style="max-width: 560px;">
        <div v-for="(loc, idx) in shelfLocationsList" :key="idx"
             class="d-flex align-items-center gap-2">
            <!-- Case à cocher : activer/désactiver la couleur -->
            <input type="checkbox"
                   class="form-check-input flex-shrink-0"
                   :checked="!!loc.color"
                   @change="toggleShelfColor(idx, $event.target.checked)"
                   :title="t('settings.shelf_location_color_toggle')" />
            <!-- Sélecteur couleur (désactivé si color: null) -->
            <input type="color"
                   :value="loc.color || '#888888'"
                   class="form-control form-control-color flex-shrink-0"
                   style="width:2.5rem; height:2rem; padding:2px;"
                   :disabled="!loc.color"
                   :style="{ opacity: loc.color ? 1 : 0.3 }"
                   @input="updateShelfLocation(idx, 'color', $event.target.value)" />
            <!-- Libellé -->
            <input type="text"
                   :value="loc.label"
                   class="form-control"
                   :placeholder="t('settings.shelf_location_label_placeholder')"
                   @input="updateShelfLocation(idx, 'label', $event.target.value)" />
            <!-- Supprimer -->
            <button type="button"
                    class="btn btn-outline-danger btn-sm flex-shrink-0"
                    @click="removeShelfLocation(idx)">
                <i class="bi bi-x"></i>
            </button>
            <!-- Aperçu badge -->
            <span v-if="loc.color" class="badge flex-shrink-0"
                  style="border-radius:4px;"
                  :style="{ background: loc.color, color: autoTextColor(loc.color) }">
                {{ loc.label || '…' }}
            </span>
            <span v-else class="badge bg-light text-dark border flex-shrink-0"
                  style="border-radius:4px;">
                {{ loc.label || '…' }}
            </span>
        </div>
        <button type="button"
                class="btn btn-outline-secondary btn-sm align-self-start mt-1"
                @click="addShelfLocation">
            <i class="bi bi-plus"></i>
            {{ t('settings.shelf_location_add') }}
        </button>
    </div>
</div>
```

`autoTextColor` est importée depuis `utils/colors.js` et exposée dans le `return` du setup.

---

### Étape 7 — i18n

Ajouter dans `fr.json` et `en.json` :

**Sous `"settings"` :**

```json
// fr
"shelf_locations": "Rayons de votre BCD",
"shelf_locations_help": "Définissez les sections de votre bibliothèque (ex : Romans, Albums, Documentaires). Chaque rayon peut avoir une couleur optionnelle qui apparaîtra sur les étiquettes. Sans couleur, le badge sera gris neutre.",
"shelf_location_label_placeholder": "ex : Romans",
"shelf_location_add": "Ajouter un rayon",
"shelf_location_color_toggle": "Utiliser une couleur"

// en
"shelf_locations": "Your Library Sections",
"shelf_locations_help": "Define the sections of your library (e.g., Fiction, Picture Books, Non-fiction). Each section can have an optional color shown on labels. Without a color, the badge will be neutral grey.",
"shelf_location_label_placeholder": "e.g., Fiction",
"shelf_location_add": "Add a section",
"shelf_location_color_toggle": "Use a color"
```

**Sous `"catalog"` :**

```json
// fr
"shelf_location_placeholder": "Rayon (ex : Romans)..."

// en
"shelf_location_placeholder": "Section (e.g., Fiction)..."
```

---

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `src/bcd_api/services/bnf_service.py` | Extraire champ 676$a |
| `src/bcd_api/api/v1/catalog.py` | Supprimer requête `shelf_rows`, remplacer `shelf_locations` (array) par `shelf_location` (string) |
| `migrations/versions/<new>.py` | `dewey_number` + `catalog_shelf_locations` |
| `src/bcd_api/models/bibliographic_record.py` | Colonne `dewey_number` |
| `src/bcd_api/models/system_settings.py` | Colonne `catalog_shelf_locations` |
| `src/bcd_api/schemas/bibliographic_record.py` | Champ `dewey_number` |
| `src/bcd_api/schemas/system_settings.py` | Champ `catalog_shelf_locations` |
| `src/bcd_api/services/settings_service.py` | `allowed_fields` |
| `src/bcd_web_vue/js/utils/colors.js` | **Nouveau** — `autoTextColor` |
| `src/bcd_web_vue/js/composables/useItemBadge.js` | **Nouveau** — `getShelfBadge` + `getCoteBadge` |
| `src/bcd_web_vue/js/components/ui/DeweyPicker.js` | Import `autoTextColor` depuis utils + prop `showBadge` |
| `src/bcd_web_vue/js/pages/CatalogingPage.js` | Passer `dewey_number` + `authors` |
| `src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js` | Props + AUT3 + input/datalist |
| `src/bcd_web_vue/js/components/catalog/ItemEditForm.js` | input/datalist shelf_location |
| `src/bcd_web_vue/js/components/catalog/RecordDetail.js` | Deux badges via `useItemBadge` |
| `src/bcd_web_vue/js/components/catalog/SearchResults.js` | `shelf_locations` → `shelf_location` + deux badges |
| `src/bcd_web_vue/js/components/settings/SettingsForm.js` | Section emplacements |
| `src/bcd_web_vue/locales/fr.json` | Nouvelles clés |
| `src/bcd_web_vue/locales/en.json` | Nouvelles clés |

---

## Décisions et compromis

| Décision | Choix retenu | Alternative écartée |
|----------|-------------|-------------------|
| Dewey sur la notice ou l'exemplaire ? | **Notice** — une notice = un Dewey | Sur l'exemplaire (redondant si plusieurs copies) |
| Génération AUT3 côté client ou serveur ? | **Client** — pas d'endpoint dédié | Endpoint `/suggest-call-number` (inutilement complexe) |
| `shelf_location` : valeur stockée | **Le libellé** (ex: `"Romans"`) | Un ID numérique (fragile si renommage) |
| Saisie emplacement | **`input + datalist`** — saisie libre + suggestions natives | `<select>` (force un choix dans la liste, bloque les anciens libellés libres) |
| Affichage emplacement vs cote | **Deux badges simultanés** (carré + arrondi) | Badge unique : emplacement masque la cote |
| `color` dans shelf_locations | **Optionnelle** (`null` = badge gris neutre) | Toujours obligatoire |
| `autoTextColor` | **Extraction dans `utils/colors.js`** | Duplication dans chaque composant |
| Migration | **Un seul fichier** pour les 2 colonnes | Deux migrations séparées |
| SearchResults — badges | **Array `shelf_locations` → N badges carrés**, `call_number` → 1 badge arrondi | Un seul badge (perte d'info si plusieurs emplacements) |
| RecordDetail périodiques | **Inchangé** — colonnes périodique existantes non touchées | Fusionner avec badge (casse l'affichage numéro fascicule) |

---

## Points d'attention

1. **BnF 676 absent pour beaucoup de livres jeunesse** — le champ `dewey_number` sera
   souvent `null`. C'est normal. La cote reste saisie manuellement via le DeweyPicker.

2. **`autoTextColor` dans `DeweyPicker.js`** — la fonction existe déjà inline. La
   déplacer dans `utils/colors.js` et mettre à jour l'import dans `DeweyPicker.js`.
   Vérifier qu'aucun test ne casse.

3. **Couleur blanche** (classe 9 = blanc dans la marguerite) — `autoTextColor` retourne
   `#000000`. Le badge arrondi doit avoir `border: 1px solid #bbb` pour être visible
   sur fond blanc de page. Le flag `outline: true` dans `getCoteBadge` signale ce cas.

4. **`shelf_location` ne correspond à aucun rayon configuré** — `shelfColorMap[label]`
   retourne `undefined` (distinct de `null`). Fallback : badge gris Bootstrap `#6c757d`.
   L'étiquette s'affiche quand même. Utile pour les anciens libellés libres.

5. **`color: null` vs rayon inconnu** — distinction importante dans `getShelfBadge` :
   - `color === null` (rayon connu sans couleur) → badge neutre (`bg-light border`)
   - `color === undefined` (rayon absent de la liste) → badge gris Bootstrap

6. **Périodiques dans RecordDetail** — l'onglet exemplaires affiche actuellement une
   colonne "Numéro de fascicule" dédiée pour les périodiques. On ne touche pas à cette
   logique dans cette feature : la colonne badge "Emplacement / Cote" s'applique
   uniquement aux non-périodiques. Pour les périodiques, laisser les colonnes existantes
   inchangées.

7. **Périodiques dans SearchResults** — `call_number` d'un périodique est un numéro de
   fascicule (`"1024"`). `getCoteBadge` lira `"1"` et appliquera la couleur Dewey classe 1.
   Acceptable pour l'instant ; à améliorer ultérieurement si besoin.
