# Plan — #2 : Onglet Statistiques globales dans la page Rapports

**Feature :** Exposer dans l'UI le endpoint existant `/api/v1/reports/statistics` sous forme d'un onglet "Tableau de bord" dans la page Rapports.

---

## 1. Contexte et inspiration

### Ce que font les autres SIGB

#### BCDI — Indicateurs d'activité (module 6)
BCDI distingue deux grandes rubriques :
- **Fonds documentaire** (6.1) : composition du fonds, nombre d'exemplaires par support, valeur patrimoniale, registre d'inventaire
- **Activité des publics** (6.2) : tous les indicateurs de prêt
  - Documents les plus empruntés (par type : documentaires/fictions/tout ; par classe/niveau/statut)
  - Répartition des prêts par : cote, mois, nature, support, type de nature
  - Croisements : répartition par statut×cote, statut×mois, classe×cote, classe×mois, classe×support...

BCDI produit des **feuilles de calcul exportables** (format tableau), sans dashboard visuel.  
L'accent est mis sur l'analyse à la demande plutôt qu'un tableau de bord en temps réel.

#### Koha — Statistics reports
Koha expose des rapports statistiques pré-définis :
- **Circulation statistics** : pivot row/colonne configurable (item type × branch × month...), export CSV
- **Patron statistics** : patrons actifs, inactifs, par catégorie
- **Catalog statistics** : nombre d'items par type
- **Most circulated items** : top des documents empruntés
- **Patrons with most checkouts** : top des lecteurs
- **Average loan time** : durée moyenne de prêt par type de document
- **Items/Patrons with no checkouts** : jamais empruntés / jamais actifs

Koha n'a **pas de dashboard** — que des rapports tabulaires à exécuter.  
La recommandation officielle est d'utiliser les **custom SQL reports** pour les statistiques officielles de fin d'année.

#### PMB
Doc PMB inaccessible en ligne. D'après les TODO précédents, PMB expose aussi des statistiques de circulation par classe, support, période.

### Ce qui existe déjà dans BCD4

L'endpoint `GET /api/v1/reports/statistics?period=month|year|all-time` retourne :

```json
{
  "period": "Last year",
  "total_checkouts": 847,
  "items_on_loan": 23,
  "overdue_items": 4,
  "active_borrowers": 23,
  "average_loans_per_day": 2.32,
  "renewals": 45,
  "late_returns": 67,
  "late_return_rate": 12.5,
  "returned_items": 824
}
```

La page Rapports a déjà 5 onglets : **En retard**, **Emprunts en cours**, **Réservations**, **Plus empruntés**, **Jamais empruntés**.

Il n'existe **aucun composant** qui consomme `/reports/statistics` côté UI (seul `BorrowerDetail.js` appelle le endpoint par emprunteur).

---

## 2. Décision de conception

### Approche retenue : tableau de bord de synthèse (pas des tables exportables)

BCD4 s'adresse à un enseignant non technicien dans une école primaire. L'objectif n'est pas de produire des rapports CSV comme BCDI ou Koha, mais de donner une **lecture rapide de l'activité de la BCD** :
- En un coup d'œil en début de journée : "combien de prêts cette semaine ?"
- En fin d'année : "bilan de l'activité pour le CA de l'école"

Le design s'inspire des tableaux de bord Bootstrap (cartes KPI + bloc secondaire), adapté au vieux matériel (pas de graphes lourds avec Chart.js).

### Composant unique `StatisticsReport.js`

- **Sélecteur de période** : 3 boutons radio → `month` | `year` | `all-time`
- **6 cartes KPI** : métriques clés avec icône et label i18n
- **Bloc secondaire** : 3 métriques complémentaires en ligne fine
- **Pas de graphique** pour cette version (TODO #3/#4 ajouteront les ventilations par classe/type)

---

## 3. Mockup

### 3.1 Sélecteur de période + cartes KPI

```
┌───────────────────────────────────────────────────────────────────────┐
│ RAPPORTS  [En retard] [Emprunts] [Réservations] [Plus empruntés] ... [Bilan ←NOUVEAU] │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Période :  ○ Ce mois   ● Cette année   ○ Depuis le début           │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  📚         │  │  👤         │  │  ⏱          │                  │
│  │    847      │  │     23      │  │    2,3      │                  │
│  │  Prêts      │  │ Emprunteurs │  │ Prêts/jour  │                  │
│  │  effectués  │  │   actifs    │  │  en moyenne │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  📖         │  │  🔄         │  │  ⚠          │                  │
│  │     23      │  │     45      │  │     4       │                  │
│  │  En prêt    │  │Renouvelle-  │  │  En retard  │                  │
│  │  en ce moment│  │   ments    │  │ actuellement│                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                       │
│  ────────────────────────────────────────────────────────────────    │
│  Retours effectués : 824          Retours tardifs : 67 (12,5 %)      │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 État vide (base vide ou très jeune)

```
┌───────────────────────────────────────────────────────────────────────┐
│  Période : ● Ce mois ...                                              │
│                                                                       │
│        ┌─────────────────────────────────────────┐                   │
│        │  Aucune activité de prêt sur ce mois.   │                   │
│        │  Essayez "Cette année" ou "Tout".        │                   │
│        └─────────────────────────────────────────┘                   │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.3 Disposition responsive (vieux PC, écran 1024px)

```
Écran large (≥1200px) : 3 colonnes × 2 lignes de cartes
Écran moyen (768-1200) : 2 colonnes × 3 lignes
Écran étroit (<768px)  : 1 colonne × 6 lignes
```

---

## 4. Modifications à réaliser

### 4.1 Nouveau composant `StatisticsReport.js`

**Fichier :** `src/bcd_web_vue/js/components/reports/StatisticsReport.js`

```
setup():
  - period = ref('year')          // période active
  - stats = ref(null)             // données API
  - loading = ref(false)
  - error = ref(null)

  - watch(period, fetchStats)     // rechargement auto sur changement période
  - onMounted → fetchStats()

fetchStats():
  - GET /api/v1/reports/statistics?period={period.value}
  - → stats.value = response.data

Template:
  - Boutons radio période (3 options)
  - v-if="loading" → spinner
  - v-else-if="error" → message d'erreur
  - v-else-if="stats && stats.total_checkouts === 0" → état vide
  - v-else → 6 cartes + bloc secondaire
```

**6 cartes KPI (grille Bootstrap `row g-3`) :**

| N° | Champ API | Icône | i18n key |
|---|---|---|---|
| 1 | `total_checkouts` | `bi-book` | `statistics.total_checkouts` |
| 2 | `active_borrowers` | `bi-people` | `statistics.active_borrowers` |
| 3 | `average_loans_per_day` | `bi-clock-history` | `statistics.avg_per_day` |
| 4 | `items_on_loan` | `bi-journal-bookmark` | `statistics.on_loan` |
| 5 | `renewals` | `bi-arrow-repeat` | `statistics.renewals` |
| 6 | `overdue_items` | `bi-exclamation-triangle` | `statistics.overdue_items` |

**Bloc secondaire (une seule ligne, texte petit) :**
- `returned_items` — "X retours effectués"
- `late_returns` — "X retours tardifs"
- `late_return_rate` — "(X %)"

**Couleur carte `overdue_items`** → rouge si `> 0` (`text-danger` / `border-danger`), vert sinon.

**Format `average_loans_per_day`** → `toFixed(1)` + afficher `—` si `null` (période all-time).

### 4.2 Enregistrement dans `ReportsPage.js`

```js
import StatisticsReport from '../components/reports/StatisticsReport.js';
// dans components: { ..., StatisticsReport }
// dans template: <statistics-report v-else-if="activeTab === 'statistics'" />
```

Ajouter le lien d'onglet dans le menu (si une barre de navigation onglets existe dans la page, sinon via le router) : `/reports/statistics`.

### 4.3 Traductions

**`src/bcd_web_vue/locales/fr.json`** — ajouter sous `reports.tabs` :

```json
"statistics": "Bilan"
```

Ajouter une section `reports.statistics` :

```json
"statistics": {
  "title": "Bilan d'activité",
  "period_label": "Période",
  "total_checkouts": "Prêts effectués",
  "active_borrowers": "Emprunteurs actifs",
  "avg_per_day": "Prêts / jour",
  "on_loan": "En prêt en ce moment",
  "renewals": "Renouvellements",
  "overdue_items": "En retard actuellement",
  "returned_items": "Retours effectués",
  "late_returns": "Retours tardifs",
  "late_return_rate_pct": "({pct} % des retours)",
  "no_activity": "Aucune activité de prêt sur cette période.",
  "try_wider": "Essayez une période plus large.",
  "period_month": "Ce mois",
  "period_year": "Cette année",
  "period_all": "Depuis le début"
}
```

**`src/bcd_web_vue/locales/en.json`** — même structure en anglais.

### 4.4 Aide contextuelle (optionnel mais recommandé)

**`docs/help/fr/rapports.md`** — ajouter une section "Bilan d'activité" :

```markdown
## Bilan d'activité

L'onglet **Bilan** affiche une synthèse de l'activité de prêt de la BCD.

**Période** : choisissez entre *Ce mois*, *Cette année* ou *Depuis le début*.

- **Prêts effectués** : nombre total de prêts pendant la période
- **Emprunteurs actifs** : lecteurs ayant un prêt en cours à l'instant
- **Prêts / jour** : moyenne quotidienne sur la période (non disponible pour "Depuis le début")
- **En prêt en ce moment** : documents actuellement sortis
- **Renouvellements** : prêts reconduits pendant la période
- **En retard** : documents non rendus après la date prévue
```

---

## 5. Résumé des fichiers modifiés

| Fichier | Type | Effort |
|---|---|---|
| `src/bcd_web_vue/js/components/reports/StatisticsReport.js` | Nouveau | ~100 lignes |
| `src/bcd_web_vue/js/pages/ReportsPage.js` | Modification | 3 lignes |
| `src/bcd_web_vue/locales/fr.json` | Modification | +~20 clés |
| `src/bcd_web_vue/locales/en.json` | Modification | +~20 clés |
| `docs/help/fr/rapports.md` | Modification | optionnel |
| `docs/help/en/reports.md` | Modification | optionnel |

**Backend :** aucune modification — l'endpoint `/api/v1/reports/statistics` existe et est complet.

**Tests :** aucun test UI à ajouter pour cette feature (tests service déjà couverts par l'endpoint existant).

---

## 6. Hors scope (pour cette version)

Ces indicateurs nécessitent de nouveaux endpoints et sont couverts par les TODO #3, #4, #5 :

| Indicateur | TODO | Endpoint nécessaire |
|---|---|---|
| Prêts par classe | #3 | `GET /reports/loans-by-class` |
| Prêts par type de document | #4 | `GET /reports/loans-by-category` |
| Taux de rotation du fonds | #5 | Calcul côté client depuis `/reports/statistics` + `/inventory/items?count_only=true` |
| Graphique évolution mensuelle | futur | `GET /reports/loans-by-month` |

---

## 7. Ordre d'implémentation

```
1. Créer StatisticsReport.js (45 min)
2. Enregistrer dans ReportsPage.js + ajout onglet (5 min)
3. Traductions fr.json + en.json (15 min)
4. Doc aide optionnelle (15 min)
```

**Effort total :** ~1h15 (UI only — endpoint prêt)

---

## 8. Comparaison finale BCDI / Koha / BCD4

| Critère | BCDI | Koha | BCD4 cible |
|---|---|---|---|
| Vue synthétique (dashboard) | ✗ (tableaux seulement) | ✗ (rapports seulement) | ✅ cartes KPI |
| Prêts par période | ✅ date début/fin | ✅ filtres dates | ✅ 3 périodes |
| Prêts par classe | ✅ indicateur dédié | ✅ stat wizard | ❌ (TODO #3) |
| Prêts par type de doc | ✅ par support | ✅ stat wizard | ❌ (TODO #4) |
| Taux de rotation | ✅ calculé | ✅ custom SQL | ❌ (TODO #5) |
| Export CSV | ✅ Excel/Calc | ✅ CSV/ODS | ❌ hors scope |
| Temps réel (en cours) | ✗ | ✗ | ✅ items_on_loan |

**Avantage BCD4** sur BCDI et Koha : les métriques "en ce moment" (`items_on_loan`, `overdue_items`, `active_borrowers`) sont calculées sur la base en direct, pas sur des archives. BCDI et Koha donnent des rapports historiques, pas d'état instantané du fonds.
