# Plan — #6 : Feuillets de retard imprimables

**Feature :** Ajouter un bouton "Imprimer feuillets" dans le rapport Retards, qui génère des petits avis à découper (un par élève), regroupés par classe, 2 colonnes par page A4.

---

## 1. Existant

- `OverdueReport.js` : données groupées par classe, `printReport()` = `window.print()`
- `ReportHeader.js` : 1 bouton "Imprimer" (émet `@print`)
- `print-labels.css` : infrastructure `@media print` déjà en place (`.class-section { page-break-before: always }`)
- API `GET /reports/overdue` retourne par item : `borrower_name`, `class_name`, `item_id`, `title`, `checkout_date`, `due_date`, `days_overdue`

**Aucune modification backend nécessaire.**

---

## 2. Approche : nouvelle route `/reports/overdue/notices`

Page dédiée (pas un modal) qui :
1. Charge les données au montage (`GET /reports/overdue?limit=500`)
2. Lance `window.print()` automatiquement après chargement
3. Affiche les feuillets en grille 2 colonnes, saut de page entre classes

**Workflow utilisateur :**
1. Rapports → En retard
2. Clic **"Imprimer feuillets"** (nouveau bouton, à côté du bouton Imprimer existant)
3. `window.open('/reports/overdue/notices', '_blank')` → nouvelle page
4. Dialogue d'impression s'ouvre automatiquement

---

## 3. Mockup feuillet

```
┌─────────────────────────────────────────────────────┐
│  BCD — Rappel de retour de livre                    │
│                                                     │
│  Élève : Marie Dupont (CE2-A)                       │
│                                                     │
│  « Les Misérables Illustrés » (n°00123)             │
│  Emprunté le 15/03/2026                             │
│  À rendre le  29/03/2026                            │
│                                                     │
│  En retard de 18 jours                              │
│                                                     │
│  Merci de faire rendre ce livre dès que possible.   │
└─────────────────────────────────────────────────────┘
```

**Disposition sur A4 :**
- 2 feuillets côte à côte (grille 2 colonnes)
- Ligne tiretée entre feuillets (`border: 1px dashed #999`)
- Saut de page forcé entre chaque classe
- Titre de classe en pleine largeur en haut de chaque groupe

```
Page 1 — CE1-A (3 retards)
┌────────────────────────┐  ┌────────────────────────┐
│ feuillet 1             │  │ feuillet 2             │
└────────────────────────┘  └────────────────────────┘
┌────────────────────────┐
│ feuillet 3             │
└────────────────────────┘

--- saut de page ---

Page 2 — CE2-B (2 retards)
┌────────────────────────┐  ┌────────────────────────┐
│ feuillet 4             │  │ feuillet 5             │
└────────────────────────┘  └────────────────────────┘
```

---

## 4. Fichiers à créer / modifier

### 4.1 Nouveau : `OverdueNotices.js`

**Chemin :** `src/bcd_web_vue/js/components/reports/OverdueNotices.js`

Composant page autonome :

```js
setup() {
  const { t, d } = useI18n();
  const groupedData = ref({});
  const loading = ref(true);

  onMounted(async () => {
    const response = await apiClient.get('/reports/overdue', { limit: 500 });
    const items = response.data || response.items || [];
    // grouper par class_name
    items.forEach(item => {
      const cls = item.class_name || t('reports.overdue.noClass');
      if (!groupedData.value[cls]) groupedData.value[cls] = [];
      groupedData.value[cls].push(item);
    });
    loading.value = false;
    await nextTick();
    window.print();
  });

  return { t, d, groupedData, loading };
}
```

Template :
```html
<div v-if="loading">Chargement...</div>
<div v-else>
  <div class="notice-toolbar no-print">
    <button @click="window.print()">Imprimer</button>
  </div>
  <div v-for="(items, className) in groupedData" class="notice-class-group">
    <div class="notice-grid">
      <div class="notice-class-title">{{ className }} — {{ items.length }} retard(s)</div>
      <div v-for="item in items" class="notice-slip">
        <div class="notice-slip-title">{{ t('reports.overdue.noticeTitle') }}</div>
        <p><strong>{{ t('reports.overdue.noticeBorrower') }} :</strong> {{ item.borrower_name }}</p>
        <p>« {{ item.title }} » (n°{{ item.item_id }})</p>
        <p>{{ t('reports.overdue.noticeBorrowedOn') }} : {{ d(new Date(item.checkout_date), 'short') }}</p>
        <p>{{ t('reports.overdue.noticeDueOn') }} : {{ d(new Date(item.due_date), 'short') }}</p>
        <p class="notice-overdue"><strong>{{ t('reports.overdue.noticeOverdueBy', { days: item.days_overdue }) }}</strong></p>
        <p class="notice-message">{{ t('reports.overdue.noticeMessage') }}</p>
      </div>
    </div>
  </div>
</div>
```

---

### 4.2 Modifier : `router.js`

**Chemin :** `src/bcd_web_vue/js/router.js`

Ajouter avant ou après la route `/reports/:type?` :

```js
import OverdueNotices from './components/reports/OverdueNotices.js';

{ path: '/reports/overdue/notices', name: 'overdue-notices', component: OverdueNotices }
```

> **Attention :** cette route doit être déclarée **avant** `/reports/:type?` pour ne pas être capturée par le paramètre `:type`.

---

### 4.3 Modifier : `ReportHeader.js`

**Chemin :** `src/bcd_web_vue/js/components/ui/ReportHeader.js`

Ajouter prop `showNotices` + 2e bouton :

```js
props: {
  title: String,
  showNotices: { type: Boolean, default: false }
}

// dans template :
<button v-if="showNotices" @click="$emit('print-notices')" class="btn btn-outline-primary">
  <i class="bi bi-scissors me-2"></i>
  {{ t('reports.overdue.printNotices') }}
</button>
<button @click="handlePrint" class="btn btn-primary">
  <i class="bi bi-printer me-2"></i>
  {{ t('reports.print') }}
</button>
```

---

### 4.4 Modifier : `OverdueReport.js`

**Chemin :** `src/bcd_web_vue/js/components/reports/OverdueReport.js`

Ajouter dans `setup()` :

```js
const printNotices = () => window.open('/reports/overdue/notices', '_blank');
return { ..., printNotices };
```

Dans le template, `<report-header>` :

```html
<report-header
  :title="t('reports.overdue.title')"
  :show-notices="true"
  @print="printReport"
  @print-notices="printNotices"
/>
```

---

### 4.5 Modifier : `print-labels.css`

**Chemin :** `src/bcd_web_vue/css/print-labels.css`

Ajouter à la fin :

```css
/* --- Feuillets de retard --- */

.notice-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4mm;
}

.notice-class-title {
    grid-column: 1 / -1;
    font-weight: bold;
    font-size: 12pt;
    padding: 4mm 0 2mm 0;
    border-bottom: 2px solid #333;
    margin-bottom: 4mm;
}

.notice-slip {
    border: 1px dashed #999;
    padding: 6mm;
    font-size: 10pt;
    line-height: 1.5;
}

.notice-slip .notice-slip-title {
    font-weight: bold;
    font-size: 11pt;
    margin-bottom: 4mm;
    border-bottom: 1px solid #ccc;
    padding-bottom: 2mm;
}

.notice-slip .notice-overdue {
    color: #c00;
}

.notice-slip .notice-message {
    margin-top: 4mm;
    font-style: italic;
}

.notice-class-group {
    margin-bottom: 8mm;
}

@media screen {
    .notice-grid {
        background: #f0f0f0;
        padding: 20px;
        border-radius: 4px;
    }
    .notice-slip {
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,.15);
        border-radius: 2px;
    }
}

@media print {
    .notice-toolbar {
        display: none !important;
    }
    .notice-class-group {
        break-before: page;
    }
    .notice-class-group:first-child {
        break-before: avoid;
    }
    .notice-slip {
        break-inside: avoid;
    }
}
```

---

### 4.6 Modifier : traductions

**`src/bcd_web_vue/locales/fr.json`** — ajouter sous `reports.overdue` :

```json
"printNotices": "Imprimer feuillets",
"noticesPageTitle": "Feuillets de retard",
"noticeTitle": "BCD — Rappel de retour de livre",
"noticeBorrower": "Élève",
"noticeBorrowedOn": "Emprunté le",
"noticeDueOn": "À rendre le",
"noticeOverdueBy": "En retard de {days} jour(s)",
"noticeMessage": "Merci de faire rendre ce livre dès que possible."
```

**`src/bcd_web_vue/locales/en.json`** — même clés en anglais :

```json
"printNotices": "Print notices",
"noticesPageTitle": "Overdue notices",
"noticeTitle": "Library — Overdue notice",
"noticeBorrower": "Student",
"noticeBorrowedOn": "Borrowed on",
"noticeDueOn": "Due on",
"noticeOverdueBy": "{days} day(s) overdue",
"noticeMessage": "Please return this book as soon as possible."
```

---

## 5. Résumé

| Fichier | Action | Lignes |
|---|---|---|
| `components/reports/OverdueNotices.js` | Créer | ~80 |
| `router.js` | +2 lignes | 2 |
| `components/ui/ReportHeader.js` | +prop +bouton | ~8 |
| `components/reports/OverdueReport.js` | +fonction +prop | ~5 |
| `css/print-labels.css` | +classes notices | ~55 |
| `locales/fr.json` + `en.json` | +8 clés × 2 | 16 |

**Effort estimé : ~1h30. Aucune modification backend.**
