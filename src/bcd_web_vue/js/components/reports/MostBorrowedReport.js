/**
 * Most Borrowed Report — Investment Analysis
 *
 * Investment methods:
 *   all            — all borrowed titles (no filter)
 *   most_borrowed  — ranked by total checkouts
 *   taux_rotation  — ISO 11620 (checkouts / copies) → racheter
 *   scarce         — ≤2 copies + high taux → priorité d'achat
 */

const { defineComponent, ref, computed, watch, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import { useNotification } from '../../composables/useNotification.js';
import { usePagination } from '../../composables/usePagination.js';
import { useReportFilters } from '../../composables/useReportFilters.js';
import ReportHeader from '../ui/ReportHeader.js';
import Pagination from '../ui/Pagination.js';
import BreakdownPanel from './BreakdownPanel.js';
import { getJSON, setJSON } from '../../utils/storage.js';
import FilterChips from './FilterChips.js';
import TauxRotationPanel from './TauxRotationPanel.js';
import PubYearPanel from './PubYearPanel.js';

const PANEL_IDS = ['medium_type', 'taux_rotation', 'pub_year'];
const HIDDEN_PANELS_KEY = 'most_borrowed_hidden_panels';

export default defineComponent({
    name: 'MostBorrowedReport',
    components: { ReportHeader, Pagination, BreakdownPanel, FilterChips, TauxRotationPanel, PubYearPanel },

    setup() {
        const { t } = useI18n();
        const { error: showError } = useNotification();
        const { openRecord } = useGlobalModal();

        const audienceLabel = val => {
            const map = { child: t('bibliographic.audience_child'), youth: t('bibliographic.audience_youth'), adult: t('bibliographic.audience_adult') };
            return map[val] || val;
        };

        const {
            crossFilters, hasActiveFilters, activeChips,
            toggleBreakdown, clearFilter, clearAllFilters,
            applyFilters, buildBreakdown,
        } = useReportFilters(t, audienceLabel, { pub_year_min: null, pub_year_max: null });

        // ── Panel visibility ───────────────────────────────────────────────────
        const saveHidden = hidden => setJSON(HIDDEN_PANELS_KEY, hidden);
        const loadHidden = () => getJSON(HIDDEN_PANELS_KEY, []);
        const hiddenPanels = ref(loadHidden());
        const visiblePanels = computed(() => PANEL_IDS.filter(id => !hiddenPanels.value.includes(id)));
        const showPanelDropdown = ref(false);
        const isPanelVisible = id => !hiddenPanels.value.includes(id);
        const togglePanel = id => {
            hiddenPanels.value = hiddenPanels.value.includes(id)
                ? hiddenPanels.value.filter(p => p !== id)
                : [...hiddenPanels.value, id];
            saveHidden(hiddenPanels.value);
        };
        const resetPanels = () => {
            hiddenPanels.value = [];
            showPanelDropdown.value = false;
            saveHidden([]);
        };
        const PANEL_LABELS = computed(() => ({
            medium_type:    t('reports.mostBorrowed.bySupport'),
            target_audience:t('reports.mostBorrowed.byAudience'),
            taux_rotation:  t('reports.tauxRotation.label'),
            pub_year:       t('reports.pubYear.label'),
        }));

        // ── Investment method ──────────────────────────────────────────────────
        const investmentMethod = ref('most_borrowed');
        const investmentMethods = computed(() => [
            { value: 'all',           label: t('reports.mostBorrowed.methodAll'),           desc: t('reports.mostBorrowed.methodAllDesc') },
            { value: 'most_borrowed', label: t('reports.mostBorrowed.methodMostBorrowed'),   desc: t('reports.mostBorrowed.methodMostBorrowedDesc') },
            { value: 'taux_rotation', label: t('reports.mostBorrowed.methodTauxRotation'),   desc: t('reports.mostBorrowed.methodTauxRotationDesc') },
            { value: 'scarce',        label: t('reports.mostBorrowed.methodScarce'),         desc: t('reports.mostBorrowed.methodScarceDesc') },
        ]);

        // ── Period ─────────────────────────────────────────────────────────────
        const period = ref('year');
        const periodOptions = computed(() => [
            { value: 'week',  label: t('reports.period.week') },
            { value: 'month', label: t('reports.period.month') },
            { value: 'year',  label: t('reports.period.year') },
            { value: 'all',   label: t('reports.period.all') },
        ]);

        // ── Raw data ───────────────────────────────────────────────────────────
        const allData = ref([]);
        const loading = ref(false);

        const loadReport = async () => {
            loading.value = true;
            try {
                const response = await apiClient.get('/reports/most-borrowed', { period: period.value, limit: 500 });
                allData.value = (response.titles || []).map(item => ({
                    ...item,
                    taux_rotation: item.total_copies > 0
                        ? Math.round((item.checkout_count / item.total_copies) * 10) / 10
                        : 0,
                }));
                if (currentPage.value !== 1) currentPage.value = 1;
            } catch (e) {
                console.error('most-borrowed error', e);
                showError(t('reports.loadError'));
            } finally {
                loading.value = false;
            }
        };

        // ── Base filtrée par méthode (panneaux reflètent la méthode active) ──────
        const methodBase = computed(() => {
            if (investmentMethod.value === 'scarce') return allData.value.filter(i => i.total_copies <= 2);
            return allData.value;
        });

        // ── Breakdowns ─────────────────────────────────────────────────────────
        const BREAKDOWN_COLORS = ['#4D99F2', '#1abc9c', '#e67e22', '#9b59b6', '#F2BF33', '#2ecc71', '#adb5bd'];
        const mediumTypeBreakdown = computed(() => buildBreakdown(methodBase.value, 'medium_type'));
        const audienceBreakdown   = computed(() => buildBreakdown(methodBase.value, 'target_audience'));
        // Items for breakdown histograms: filtered by all except the key itself
        const tauxHistogramItems  = computed(() => applyFilters(methodBase.value, 'taux_rotation'));
        const pubYearItems        = computed(() => applyFilters(methodBase.value, 'pub_year'));

        // ── Pagination + sort ──────────────────────────────────────────────────
        const sortColumn    = ref('checkout_count');
        const sortDirection = ref('desc');
        const { currentPage, pageSize, totalItems, totalPages, setTotalItems, goToPage, setPageSize }
            = usePagination({ pageSize: 25 });

        const processedData = computed(() => {
            let items = applyFilters(methodBase.value);

            const key = (investmentMethod.value === 'taux_rotation' && sortColumn.value === 'checkout_count')
                ? 'taux_rotation' : sortColumn.value;

            return [...items].sort((a, b) => {
                let av = a[key], bv = b[key];
                if (av == null && bv == null) return 0;
                if (av == null) return 1;
                if (bv == null) return -1;
                if (typeof av === 'string') { av = av.toLowerCase(); bv = bv.toLowerCase(); }
                const r = av < bv ? -1 : av > bv ? 1 : 0;
                return sortDirection.value === 'asc' ? r : -r;
            });
        });

        watch(processedData, items => setTotalItems(items.length), { immediate: true });
        const paginatedData    = computed(() => processedData.value.slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value));
        const maxCheckouts     = computed(() => Math.max(...processedData.value.map(i => i.checkout_count), 1));
        const maxTauxRotation  = computed(() => Math.max(...processedData.value.map(i => i.taux_rotation || 0), 1));

        const handleSort = col => {
            if (sortColumn.value === col) sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
            else { sortColumn.value = col; sortDirection.value = 'desc'; }
        };

        watch(investmentMethod, method => {
            sortColumn.value    = method === 'taux_rotation' ? 'taux_rotation' : 'checkout_count';
            sortDirection.value = 'desc';
            if (currentPage.value !== 1) currentPage.value = 1;
        });

        // ── Column visibility ──────────────────────────────────────────────────
        const COL_IDS_MB = ['rank', 'title', 'checkout_count', 'total_copies', 'taux_rotation'];
        const COL_STORAGE_KEY_MB = 'most_borrowed_cols';
        const loadVisibleColsMB = () => {
            const s = getJSON(COL_STORAGE_KEY_MB);
            if (s) return s.filter(id => COL_IDS_MB.includes(id));
            return [...COL_IDS_MB];
        };
        const visibleCols = ref(loadVisibleColsMB());
        const showColDropdown = ref(false);
        const isColVisible = id => visibleCols.value.includes(id);
        const toggleCol = id => {
            visibleCols.value = visibleCols.value.includes(id)
                ? visibleCols.value.filter(c => c !== id)
                : [...visibleCols.value, id];
            setJSON(COL_STORAGE_KEY_MB, visibleCols.value);
        };
        const resetCols = () => {
            visibleCols.value = [...COL_IDS_MB];
            showColDropdown.value = false;
            setJSON(COL_STORAGE_KEY_MB, visibleCols.value);
        };
        const allColsMB = computed(() => [
            { key: 'rank',          label: '#' },
            { key: 'title',         label: t('reports.mostBorrowed.bookTitle') },
            { key: 'checkout_count',label: t('reports.mostBorrowed.checkouts') },
            { key: 'total_copies',  label: t('reports.mostBorrowed.copies') },
            { key: 'taux_rotation', label: t('reports.tauxRotation.label') },
        ]);

        watch(period, loadReport);
        onMounted(loadReport);

        return {
            t, audienceLabel,
            investmentMethod, investmentMethods,
            period, periodOptions,
            crossFilters, hasActiveFilters, activeChips,
            toggleBreakdown, clearFilter, clearAllFilters,
            BREAKDOWN_COLORS, mediumTypeBreakdown, audienceBreakdown, tauxHistogramItems,
            loading, allData, paginatedData, processedData, totalItems, totalPages,
            currentPage, pageSize, sortColumn, sortDirection,
            handleSort, goToPage, setPageSize,
            maxCheckouts, maxTauxRotation,
            openRecord,
            PANEL_IDS, PANEL_LABELS, hiddenPanels, visiblePanels, showPanelDropdown,
            isPanelVisible, togglePanel, resetPanels,
            pubYearItems,
            COL_IDS_MB, allColsMB, visibleCols, showColDropdown, isColVisible, toggleCol, resetCols,
        };
    },

    template: `
<div>
    <report-header :title="t('reports.mostBorrowed.title')" @print="() => window.print()" />

    <!-- Method + period selector -->
    <div class="card mb-3">
        <div class="card-body py-2">
            <div class="d-flex align-items-center gap-3 mb-2">
                <strong class="text-nowrap small">{{ t('reports.mostBorrowed.investmentMethod') }} :</strong>
                <div class="btn-group btn-group-sm flex-grow-1" role="group">
                    <template v-for="m in investmentMethods" :key="m.value">
                        <input type="radio" class="btn-check" :id="'inv-' + m.value" v-model="investmentMethod" :value="m.value">
                        <label class="btn btn-outline-success" :for="'inv-' + m.value" :title="m.desc">{{ m.label }}</label>
                    </template>
                </div>
                <!-- Toggles groupés alignés à droite -->
                <div class="d-flex gap-1 flex-shrink-0 ms-auto">
                    <!-- Colonnes -->
                    <div class="position-relative">
                        <button class="btn btn-outline-secondary btn-sm" @click="showColDropdown = !showColDropdown"
                                :class="{ active: showColDropdown }" title="Colonnes du tableau">
                            <i class="bi bi-table"></i>
                        </button>
                        <div v-if="showColDropdown" class="dropdown-menu show shadow-sm"
                             style="position:absolute;right:0;top:calc(100% + 4px);min-width:200px;z-index:1050;" @click.stop>
                            <h6 class="dropdown-header py-1">Colonnes</h6>
                            <div class="dropdown-divider my-1"></div>
                            <div v-for="col in allColsMB" :key="col.key" class="form-check px-3 py-1">
                                <input type="checkbox" class="form-check-input" :id="'col-mb-' + col.key"
                                       :checked="isColVisible(col.key)" @change="toggleCol(col.key)">
                                <label class="form-check-label small" :for="'col-mb-' + col.key" style="cursor:pointer;">{{ col.label }}</label>
                            </div>
                            <div class="dropdown-divider my-1"></div>
                            <button class="dropdown-item small py-1" @click="resetCols">
                                <i class="bi bi-arrow-counterclockwise me-1"></i>Réinitialiser
                            </button>
                        </div>
                        <div v-if="showColDropdown" @click="showColDropdown = false" style="position:fixed;inset:0;z-index:1049;"></div>
                    </div>
                    <!-- Panneaux -->
                    <div class="position-relative">
                        <button class="btn btn-outline-secondary btn-sm" @click="showPanelDropdown = !showPanelDropdown"
                                :class="{ active: showPanelDropdown }" :title="t('reports.collectionReport.selectPanels')">
                            <i class="bi bi-layout-three-columns"></i>
                        </button>
                        <div v-if="showPanelDropdown" class="dropdown-menu show shadow-sm"
                             style="position:absolute;right:0;top:calc(100% + 4px);min-width:200px;z-index:1050;" @click.stop>
                            <h6 class="dropdown-header py-1">{{ t('reports.collectionReport.selectPanels') }}</h6>
                            <div class="dropdown-divider my-1"></div>
                            <div v-for="id in PANEL_IDS" :key="id" class="form-check px-3 py-1">
                                <input type="checkbox" class="form-check-input" :id="'panel-mb-' + id"
                                       :checked="isPanelVisible(id)" @change="togglePanel(id)">
                                <label class="form-check-label small" :for="'panel-mb-' + id" style="cursor:pointer;">{{ PANEL_LABELS[id] }}</label>
                            </div>
                            <div class="dropdown-divider my-1"></div>
                            <button class="dropdown-item small py-1" @click="resetPanels">
                                <i class="bi bi-arrow-counterclockwise me-1"></i>{{ t('reports.collectionReport.resetPanels') }}
                            </button>
                        </div>
                        <div v-if="showPanelDropdown" @click="showPanelDropdown = false" style="position:fixed;inset:0;z-index:1049;"></div>
                    </div>
                </div>
            </div>
            <div class="d-flex align-items-center gap-3">
                <strong class="text-nowrap small">{{ t('reports.period.label') }} :</strong>
                <div class="btn-group btn-group-sm" role="group">
                    <template v-for="opt in periodOptions" :key="opt.value">
                        <input type="radio" class="btn-check" :id="'period-' + opt.value" v-model="period" :value="opt.value">
                        <label class="btn btn-outline-secondary" :for="'period-' + opt.value">{{ opt.label }}</label>
                    </template>
                </div>
            </div>
        </div>
    </div>

    <!-- Active filter chips -->
    <filter-chips :chips="activeChips" @clear="clearFilter" @clear-all="clearAllFilters()" />

    <!-- Breakdown panels -->
    <div class="row g-2 mb-3" v-if="!loading && allData.length">
        <div class="col-6 col-md-4" v-if="isPanelVisible('medium_type') && mediumTypeBreakdown.length">
            <breakdown-panel
                :title="t('reports.mostBorrowed.bySupport')"
                :subtitle="t('reports.mostBorrowed.clickToFilter')"
                :rows="mediumTypeBreakdown"
                :active-value="crossFilters.medium_type"
                :colors="BREAKDOWN_COLORS"
                @toggle="toggleBreakdown('medium_type', $event)"
            />
        </div>
        <div class="col-6 col-md-4" v-if="isPanelVisible('taux_rotation') && tauxHistogramItems.length">
            <taux-rotation-panel
                :items="tauxHistogramItems"
                :model-min="crossFilters.taux_rotation_min"
                :model-max="crossFilters.taux_rotation_max"
                @update:model-min="crossFilters.taux_rotation_min = $event"
                @update:model-max="crossFilters.taux_rotation_max = $event"
            />
        </div>
        <div class="col-6 col-md-4" v-if="isPanelVisible('pub_year') && pubYearItems.length">
            <pub-year-panel
                :items="pubYearItems"
                :model-min="crossFilters.pub_year_min"
                :model-max="crossFilters.pub_year_max"
                @update:model-min="crossFilters.pub_year_min = $event"
                @update:model-max="crossFilters.pub_year_max = $event"
            />
        </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-5">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">{{ t('common.loading') }}</span>
        </div>
    </div>

    <!-- Results count -->
    <div v-if="!loading && totalItems > 0" class="mb-2 text-muted">
        {{ t('reports.mostBorrowed.showing', { count: paginatedData.length, total: totalItems }) }}
    </div>

    <!-- Table -->
    <div class="card" v-if="!loading && totalItems > 0">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-striped mb-0">
                    <thead>
                        <tr>
                            <th v-if="isColVisible('rank')" style="width:50px;">#</th>
                            <th v-if="isColVisible('title')" @click="handleSort('title')" style="cursor:pointer;">
                                {{ t('reports.mostBorrowed.bookTitle') }}
                                <i v-if="sortColumn==='title'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('checkout_count')" @click="handleSort('checkout_count')" style="width:220px;cursor:pointer;">
                                {{ t('reports.mostBorrowed.checkouts') }}
                                <i v-if="sortColumn==='checkout_count'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('total_copies')" @click="handleSort('total_copies')" style="width:60px;cursor:pointer;text-align:center;">
                                {{ t('reports.mostBorrowed.copies') }}
                                <i v-if="sortColumn==='total_copies'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('taux_rotation')" @click="handleSort('taux_rotation')" style="width:200px;cursor:pointer;"
                                :class="investmentMethod==='taux_rotation'||investmentMethod==='scarce' ? 'text-success fw-semibold' : ''">
                                {{ t('reports.tauxRotation.label') }}
                                <i v-if="sortColumn==='taux_rotation'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(item, idx) in paginatedData" :key="item.bibliographic_record_id">
                            <td v-if="isColVisible('rank')" class="text-center text-muted small">{{ (currentPage - 1) * pageSize + idx + 1 }}</td>
                            <td v-if="isColVisible('title')">
                                <a href="#" @click.prevent="openRecord(item.bibliographic_record_id)" class="link-entity fw-bold">
                                    {{ item.title }}
                                </a>
                                <div class="text-muted small">
                                    <span v-if="item.author || item.publisher">{{ item.author || item.publisher }}</span>
                                    <span v-if="item.medium_type" class="ms-1 badge bg-light text-secondary border" style="font-size:10px;">{{ item.medium_type }}</span>
                                </div>
                            </td>
                            <td v-if="isColVisible('checkout_count')">
                                <div class="d-flex align-items-center gap-2">
                                    <div class="progress flex-grow-1" style="height:18px;">
                                        <div class="progress-bar bg-primary" :style="{ width: (item.checkout_count / maxCheckouts * 100) + '%' }">
                                            {{ item.checkout_count }}
                                        </div>
                                    </div>
                                </div>
                            </td>
                            <td v-if="isColVisible('total_copies')" class="text-center">
                                <span :class="item.total_copies <= 1 ? 'text-danger fw-bold' : item.total_copies <= 2 ? 'text-warning fw-bold' : ''">
                                    {{ item.total_copies }}
                                </span>
                            </td>
                            <td v-if="isColVisible('taux_rotation')">
                                <div class="d-flex align-items-center gap-2">
                                    <div class="progress flex-grow-1" style="height:18px;">
                                        <div class="progress-bar"
                                             :class="item.taux_rotation >= 8 ? 'bg-danger' : item.taux_rotation >= 4 ? 'bg-warning' : 'bg-success'"
                                             :style="{ width: (item.taux_rotation / maxTauxRotation * 100) + '%' }">
                                            {{ item.taux_rotation.toFixed(1) }}
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && totalItems === 0" class="alert alert-info">
        <i class="bi bi-info-circle me-2"></i>{{ t('reports.mostBorrowed.noItems') }}
    </div>

    <!-- Pagination -->
    <pagination
        v-if="!loading && totalItems > 0"
        :current-page="currentPage" :page-size="pageSize"
        :total-items="totalItems" :total-pages="totalPages"
        @page-change="goToPage" @page-size-change="setPageSize"
        class="mt-3"
    />
</div>
    `
});
