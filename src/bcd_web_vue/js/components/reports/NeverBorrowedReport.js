/**
 * CREW Weeding Report Component
 * Implements the CREW method (Continuous Review, Evaluation, and Weeding)
 * for systematic collection evaluation and weeding
 */

const { defineComponent, computed, ref, watch } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import { useAppState } from '../../composables/useAppState.js';
import { useNotification } from '../../composables/useNotification.js';
import { usePagination } from '../../composables/usePagination.js';
import ReportHeader from '../ui/ReportHeader.js';
import { getJSON, setJSON } from '../../utils/storage.js';
import DataTable from '../ui/DataTable.js';
import Pagination from '../ui/Pagination.js';
import TauxRotationPanel from './TauxRotationPanel.js';

export default defineComponent({
    name: 'NeverBorrowedReport',

    components: {
        ReportHeader,
        DataTable,
        Pagination,
        TauxRotationPanel,
    },

    setup() {
        const { t, d } = useI18n();
        const { settings } = useAppState();
        const { error: showError } = useNotification();
        const { openRecord } = useGlobalModal();

        const allItems = ref([]); // All filtered items
        const excludePeriodicals = ref(true);
        const tauxRotationFilter = ref({ min: null, max: null }); // Default: exclude periodicals from weeding report
        const loading = ref(false);
        const searchParams = ref(null); // For inventory search

        // Sorting
        const sortColumn = ref('crew_score'); // Default sort by CREW score
        const sortDirection = ref('desc'); // 'asc' or 'desc'

        // Pagination
        const {
            currentPage,
            pageSize,
            totalItems,
            totalPages,
            setTotalItems,
            goToPage,
            setPageSize
        } = usePagination({ pageSize: 50 }); // Default 50 per page

        // CREW Method Selection
        const crewMethod = ref('never_borrowed'); // 'never_borrowed', 'low_circulation', 'damaged_old'

        // Filters
        const filters = ref({
            level: '',
            target_audience: '',
            medium_type: '',
            min_age_years: 0 // Default: All ages (0 means no filter)
        });

        // Parse vocabulary lists from settings
        const parseCsv = (str) => {
            if (!str) return [];
            return str.split(',').map(s => s.trim()).filter(Boolean);
        };

        const levelOptions = computed(() => parseCsv(settings.value?.catalog_levels));
        const mediumTypeOptions = computed(() => parseCsv(settings.value?.catalog_medium_types));

        const audienceOptions = [
            { value: '', label: t('common.all') },
            { value: 'child', label: t('bibliographic.audience_child') },
            { value: 'youth', label: t('bibliographic.audience_youth') },
            { value: 'adult', label: t('bibliographic.audience_adult') }
        ];

        const ageOptions = [
            { value: 0, label: t('reports.crew.allAges') },
            { value: 0.5, label: t('reports.crew.moreThan6Months') },
            { value: 1, label: t('reports.crew.moreThan1Year') },
            { value: 2, label: t('reports.crew.moreThan2Years') },
            { value: 3, label: t('reports.crew.moreThan3Years') }
        ];

        const crewMethods = [
            { value: 'never_borrowed', label: t('reports.crew.neverBorrowed'), description: t('reports.crew.neverBorrowedDesc') },
            { value: 'low_circulation', label: t('reports.crew.lowCirculation'), description: t('reports.crew.lowCirculationDesc') },
            { value: 'damaged_old', label: t('reports.crew.damagedOld'), description: t('reports.crew.damagedOldDesc') },
            { value: 'high_score', label: t('reports.crew.highScore'), description: t('reports.crew.highScoreDesc') },
            { value: 'never_inventoried', label: t('reports.crew.neverInventoried'), description: t('reports.crew.neverInventoriedDesc') },
            { value: 'duplicate_low_demand', label: t('reports.crew.duplicateLowDemand'), description: t('reports.crew.duplicateLowDemandDesc') }
        ];

        // ── Column definitions + visibility ────────────────────────────────────
        const COL_IDS = ['crew_score', 'item_id', 'title', 'condition', 'shelf_location', 'age_days', 'publication_year', 'total_copies', 'period_loan_count'];
        const COL_STORAGE_KEY = 'never_borrowed_cols';
        const loadVisibleCols = () => {
            const s = getJSON(COL_STORAGE_KEY);
            if (s) return COL_IDS.filter(id => s.includes(id));
            return [...COL_IDS];
        };
        const visibleColumns = ref(loadVisibleCols());
        const showColDropdown = ref(false);
        watch(visibleColumns, v => setJSON(COL_STORAGE_KEY, v));
        const isColVisible = id => visibleColumns.value.includes(id);
        const toggleCol = id => {
            if (visibleColumns.value.includes(id)) visibleColumns.value = visibleColumns.value.filter(c => c !== id);
            else visibleColumns.value = [...visibleColumns.value, id];
        };
        const resetCols = () => { visibleColumns.value = [...COL_IDS]; showColDropdown.value = false; };

        const allColumns = computed(() => [
            { key: 'crew_score',      label: t('reports.crew.score'),              width: '80px'  },
            { key: 'item_id',         label: t('item.item_id'),                    width: '100px' },
            { key: 'title',           label: t('reports.neverBorrowed.bookTitle')                 },
            { key: 'condition',       label: t('item.condition'),                  width: '100px' },
            { key: 'shelf_location',  label: t('item.shelf_location'),             width: '120px' },
            { key: 'age_days',        label: t('reports.crew.ageInCollection'),    width: '100px' },
            { key: 'publication_year',label: t('reports.crew.pubYear'),            width: '90px'  },
            { key: 'total_copies',    label: t('reports.mostBorrowed.copies'),     width: '80px'  },
            { key: 'period_loan_count',label: t('reports.tauxRotation.label'),     width: '170px' },
        ]);
        const columns = computed(() => allColumns.value.filter(c => isColVisible(c.key)));

        // ── Per-title copies count (from loaded items) ─────────────────────────
        const copiesPerTitle = computed(() => {
            const map = {};
            allItems.value.forEach(i => {
                map[i.bibliographic_record_id] = (map[i.bibliographic_record_id] || 0) + 1;
            });
            return map;
        });

        // ── Max taux for progress bar scale ────────────────────────────────────
        const tauxMax = computed(() => Math.max(...allItems.value.map(i => i.taux_rotation ?? 0), 1));

        // Calculate CREW score based on item data
        const calculateCrewScore = (item) => {
            let score = 0;
            let reasons = [];

            // Age in collection (older = higher score)
            if (item.age_days) {
                if (item.age_days > 1095) { // 3+ years
                    score += 3;
                    reasons.push('3+ ans dans la collection');
                } else if (item.age_days > 730) { // 2+ years
                    score += 2;
                    reasons.push('2+ ans dans la collection');
                } else if (item.age_days > 365) { // 1+ year
                    score += 1;
                }
            }

            // Condition (damaged = higher score)
            if (item.condition === 'damaged') {
                score += 2;
                reasons.push('Abîmé');
            }

            // Old publication year for nonfiction (outdated info)
            const currentYear = new Date().getFullYear();
            if (item.publication_year && item.medium_type && item.medium_type.toLowerCase().includes('document')) {
                const age = currentYear - item.publication_year;
                if (age > 10) {
                    score += 2;
                    reasons.push(`Publication ancienne (${item.publication_year})`);
                } else if (age > 5) {
                    score += 1;
                }
            }

            // Low/zero circulation
            if (item.period_loan_count !== undefined) {
                if (item.period_loan_count === 0) {
                    score += 2;
                    reasons.push('Aucun emprunt');
                } else if (item.period_loan_count === 1) {
                    score += 1;
                    reasons.push('1 emprunt seulement');
                }
            }

            return { score, reasons };
        };

        // Helper: Convert min_age_years to acquired_before date
        const getAcquiredBeforeDate = (years) => {
            if (!years || years <= 0) return null;
            const date = new Date();
            // Use milliseconds for accurate date calculation
            const millisecondsInYear = 365.25 * 24 * 60 * 60 * 1000; // Account for leap years
            date.setTime(date.getTime() - (years * millisecondsInYear));
            return date.toISOString().split('T')[0];
        };

        // Load report data - use inventory search API which supports all filters
        const loadReport = async () => {
            loading.value = true;
            try {
                const endpoint = '/inventory/items/search';
                const params = {};

                // CREW method-specific filters
                if (crewMethod.value === 'never_borrowed') {
                    // Items never borrowed - no circulation at all
                    params.never_inventoried = false; // We want items that exist
                    // Use min_age_years if specified (0 means no filter, any positive value filters)
                    if (filters.value.min_age_years > 0) {
                        params.acquired_before = getAcquiredBeforeDate(filters.value.min_age_years);
                    }
                    // Add a note: we'll filter client-side for zero circulation
                } else if (crewMethod.value === 'low_circulation') {
                    // Low circulation: max 2 borrows in last 2 years
                    params.max_borrows = 2;
                    const monthsAgo = 24;
                    const sinceDate = new Date();
                    sinceDate.setMonth(sinceDate.getMonth() - monthsAgo);
                    params.since_date = sinceDate.toISOString().split('T')[0];
                } else if (crewMethod.value === 'damaged_old') {
                    // Damaged items + old items (3+ years in collection)
                    params.condition = 'damaged';
                    // Min 3 years old in collection (or use filter value if > 0)
                    const minAgeYears = filters.value.min_age_years > 0 ? filters.value.min_age_years : 3;
                    params.acquired_before = getAcquiredBeforeDate(minAgeYears);
                } else if (crewMethod.value === 'high_score') {
                    // High CREW score (≥5) - load all items, filter client-side by score
                    // No specific API filters, just get everything
                } else if (crewMethod.value === 'never_inventoried') {
                    // Never inventoried (missing) - items never physically verified
                    params.never_inventoried = true;
                    // Only show items older than 1 year (new acquisitions are normal, or use filter value if > 0)
                    const minAgeYears = filters.value.min_age_years > 0 ? filters.value.min_age_years : 1;
                    params.acquired_before = getAcquiredBeforeDate(minAgeYears);
                } else if (crewMethod.value === 'duplicate_low_demand') {
                    // Duplicate low demand - load all items, group client-side
                    // No specific API filters
                }

                // Common filters (only add if not empty)
                if (filters.value.level && filters.value.level !== '') {
                    params.level = filters.value.level;
                }
                if (filters.value.target_audience && filters.value.target_audience !== '') {
                    params.target_audience = filters.value.target_audience;
                }
                if (filters.value.medium_type && filters.value.medium_type !== '') {
                    params.medium_type = filters.value.medium_type;
                }

                // Skip result limit for CREW report (we need all items to calculate scores)
                params.no_limit = true;

                console.log('Loading CREW report with params:', params);

                const response = await apiClient.get(endpoint, params);

                // Filter and add CREW scores to items
                let items = response.items || [];

                // Calculate CREW scores for all items first
                items.forEach(item => {
                    const crew = calculateCrewScore(item);
                    item.crew_score = crew.score;
                    item.crew_reasons = crew.reasons;
                    item.taux_rotation = item.period_loan_count ?? item.circulation_count ?? 0;
                });

                // Method-specific post-processing filters
                if (crewMethod.value === 'never_borrowed') {
                    // Filter to only items with 0 circulation
                    items = items.filter(item => !item.last_borrowed_at);
                } else if (crewMethod.value === 'high_score') {
                    // Filter to only items with CREW score ≥ 5
                    items = items.filter(item => item.crew_score >= 5);
                } else if (crewMethod.value === 'duplicate_low_demand') {
                    // Group by bibliographic_record_id, find titles with 3+ copies and low avg circulation
                    const titleGroups = {};

                    // Group items by title
                    items.forEach(item => {
                        const titleId = item.bibliographic_record_id;
                        if (!titleGroups[titleId]) {
                            titleGroups[titleId] = [];
                        }
                        titleGroups[titleId].push(item);
                    });

                    // Calculate average circulation per copy for each title
                    const lowDemandTitles = new Set();
                    Object.entries(titleGroups).forEach(([titleId, copies]) => {
                        if (copies.length >= 3) {
                            // Calculate average period_loan_count
                            const totalLoans = copies.reduce((sum, item) => {
                                return sum + (item.period_loan_count || 0);
                            }, 0);
                            const avgLoansPerCopy = totalLoans / copies.length;

                            // Low demand = less than 1 loan per copy per year (in 2-year period = <2)
                            if (avgLoansPerCopy < 2) {
                                lowDemandTitles.add(parseInt(titleId));
                            }
                        }
                    });

                    // Filter to only items from low-demand duplicate titles
                    items = items.filter(item => lowDemandTitles.has(item.bibliographic_record_id));
                }

                // Sort by CREW score (highest first)
                items.sort((a, b) => b.crew_score - a.crew_score);

                // Store all items (pagination count updated reactively via watcher)
                allItems.value = items;
                searchParams.value = params;

                // Reset to page 1 when filters change
                if (currentPage.value !== 1) {
                    currentPage.value = 1;
                }
            } catch (err) {
                console.error('Failed to load CREW report:', err);
                showError(t('reports.loadError'));
            } finally {
                loading.value = false;
            }
        };

        // Sort items
        const sortItems = (items) => {
            if (!sortColumn.value) return items;

            return [...items].sort((a, b) => {
                let aVal = a[sortColumn.value];
                let bVal = b[sortColumn.value];

                // Handle null/undefined values
                if (aVal == null && bVal == null) return 0;
                if (aVal == null) return 1;
                if (bVal == null) return -1;

                // String comparison (case-insensitive)
                if (typeof aVal === 'string') {
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }

                // Compare
                let result = 0;
                if (aVal < bVal) result = -1;
                if (aVal > bVal) result = 1;

                // Apply direction
                return sortDirection.value === 'asc' ? result : -result;
            });
        };

        // Handle column header click for sorting
        const handleSort = (columnKey) => {
            if (sortColumn.value === columnKey) {
                // Toggle direction
                sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
            } else {
                // New column, default to descending
                sortColumn.value = columnKey;
                sortDirection.value = 'desc';
            }
        };

        // Filtered items (excludes periodicals when option is enabled)
        const filteredItems = computed(() => {
            let items = allItems.value;
            if (excludePeriodicals.value) {
                items = items.filter(item => item.medium_type !== 'Périodique');
            }
            const tr = tauxRotationFilter.value;
            if (tr.min !== null || tr.max !== null) {
                items = items.filter(item => {
                    const v = item.taux_rotation ?? 0;
                    if (tr.min !== null && v < tr.min) return false;
                    if (tr.max !== null && v > tr.max) return false;
                    return true;
                });
            }
            return items;
        });

        // Keep pagination total in sync with the filtered count
        watch(filteredItems, (items) => {
            setTotalItems(items.length);
        }, { immediate: true });

        // Computed paginated data (sorted, from filtered items)
        const paginatedData = computed(() => {
            const map = copiesPerTitle.value;
            const withCopies = filteredItems.value.map(i => ({ ...i, total_copies: map[i.bibliographic_record_id] ?? 1 }));
            const sorted = sortItems(withCopies);
            const start = (currentPage.value - 1) * pageSize.value;
            return sorted.slice(start, start + pageSize.value);
        });

        // Print report
        const printReport = () => {
            window.print();
        };

        // Handle page change
        const handlePageChange = (page) => {
            goToPage(page);
        };

        // Handle page size change
        const handlePageSizeChange = (size) => {
            setPageSize(size);
        };

        // Load on mount
        loadReport();

        return {
            t,
            d,
            settings,
            columns,
            paginatedData,
            loading,
            totalItems,
            totalPages,
            currentPage,
            pageSize,
            crewMethod,
            crewMethods,
            filters,
            excludePeriodicals,
            levelOptions,
            mediumTypeOptions,
            audienceOptions,
            ageOptions,
            sortColumn,
            sortDirection,
            loadReport,
            printReport,
            handlePageChange,
            handlePageSizeChange,
            handleSort,
            openRecord,
            allItems,
            tauxRotationFilter,
            COL_IDS, allColumns, visibleColumns, showColDropdown, isColVisible, toggleCol, resetCols,
            copiesPerTitle, tauxMax,
        };
    },

    template: `
        <div>
            <report-header
                :title="t('reports.crew.title')"
                @print="printReport"
            />

            <!-- CREW Method Selection - Compact -->
            <div class="card mb-3">
                <div class="card-body py-2">
                    <div class="d-flex align-items-center gap-3">
                        <strong class="text-nowrap small">{{ t('reports.crew.methodTitle') }}:</strong>
                        <div class="btn-group btn-group-sm flex-grow-1" role="group">
                            <template v-for="method in crewMethods" :key="method.value">
                                <input
                                    type="radio"
                                    class="btn-check"
                                    :id="'crew-' + method.value"
                                    v-model="crewMethod"
                                    :value="method.value"
                                    @change="loadReport"
                                >
                                <label class="btn btn-outline-primary" :for="'crew-' + method.value" :title="method.description">
                                    {{ method.label }}
                                </label>
                            </template>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Advanced Filters -->
            <div class="card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">{{ t('reports.crew.filters') }}</h6>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <!-- Medium Type -->
                        <div class="col-md-3">
                            <label class="form-label small">{{ t('bibliographic.medium_type') }}</label>
                            <input
                                type="text"
                                class="form-control form-control-sm"
                                v-model="filters.medium_type"
                                list="crew-medium-suggestions"
                                @input="loadReport"
                                :placeholder="t('common.all')"
                            />
                            <datalist id="crew-medium-suggestions">
                                <option v-for="medium in mediumTypeOptions" :key="medium" :value="medium" />
                            </datalist>
                        </div>

                        <!-- Level -->
                        <div class="col-md-3">
                            <label class="form-label small">{{ t('bibliographic.level') }}</label>
                            <input
                                type="text"
                                class="form-control form-control-sm"
                                v-model="filters.level"
                                list="crew-level-suggestions"
                                @input="loadReport"
                                :placeholder="t('common.all')"
                            />
                            <datalist id="crew-level-suggestions">
                                <option v-for="level in levelOptions" :key="level" :value="level" />
                            </datalist>
                        </div>

                        <!-- Target Audience -->
                        <div class="col-md-3">
                            <label class="form-label small">{{ t('bibliographic.target_audience') }}</label>
                            <select v-model="filters.target_audience" class="form-select" @change="loadReport">
                                <option v-for="opt in audienceOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                            </select>
                        </div>

                        <!-- Age Filter (custom values allowed) -->
                        <div class="col-md-3">
                            <label class="form-label small">{{ t('reports.neverBorrowed.minAge') }}</label>
                            <input
                                type="number"
                                class="form-control form-control-sm"
                                v-model.number="filters.min_age_years"
                                list="crew-age-suggestions"
                                @input="loadReport"
                                :placeholder="t('reports.crew.allAges')"
                                min="0"
                                max="10"
                                step="0.5"
                            />
                            <datalist id="crew-age-suggestions">
                                <option v-for="opt in ageOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
                            </datalist>
                        </div>

                        <!-- Exclude periodicals -->
                        <div class="col-md-3 d-flex align-items-end">
                            <div class="form-check mb-2">
                                <input
                                    class="form-check-input"
                                    type="checkbox"
                                    id="crew-exclude-periodicals"
                                    v-model="excludePeriodicals"
                                />
                                <label class="form-check-label small" for="crew-exclude-periodicals">
                                    {{ t('reports.crew.excludePeriodicals') }}
                                </label>
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <!-- Taux de rotation panel -->
            <div class="row g-2 mb-3" v-if="!loading && allItems.length">
                <div class="col-6 col-md-4">
                    <taux-rotation-panel
                        :items="allItems"
                        :model-min="tauxRotationFilter.min"
                        :model-max="tauxRotationFilter.max"
                        @update:model-min="tauxRotationFilter.min = $event"
                        @update:model-max="tauxRotationFilter.max = $event"
                    />
                </div>
            </div>

            <!-- Results Summary + column toggle -->
            <div v-if="!loading && totalItems > 0" class="d-flex align-items-center justify-content-between mb-2">
                <span class="text-muted">{{ t('reports.neverBorrowed.showing', { count: paginatedData.length, total: totalItems }) }}</span>
                <div class="position-relative">
                    <button class="btn btn-outline-secondary btn-sm" @click="showColDropdown = !showColDropdown" :title="t('reports.collectionReport.selectPanels')">
                        <i class="bi bi-layout-three-columns"></i>
                    </button>
                    <div v-if="showColDropdown" class="dropdown-menu show"
                         style="position:absolute;right:0;top:100%;margin-top:.25rem;min-width:190px;z-index:1050;" @click.stop>
                        <h6 class="dropdown-header">{{ t('reports.collectionReport.selectPanels') }}</h6>
                        <div class="dropdown-divider"></div>
                        <div v-for="col in allColumns" :key="col.key" class="form-check px-3 py-1">
                            <input type="checkbox" class="form-check-input" :id="'col-nb-' + col.key"
                                   :checked="isColVisible(col.key)" @change="toggleCol(col.key)">
                            <label class="form-check-label small" :for="'col-nb-' + col.key" style="cursor:pointer;">{{ col.label }}</label>
                        </div>
                        <div class="dropdown-divider"></div>
                        <button class="dropdown-item text-primary small" @click="resetCols">
                            <i class="bi bi-arrow-counterclockwise me-1"></i>{{ t('reports.collectionReport.resetPanels') }}
                        </button>
                    </div>
                    <div v-if="showColDropdown" @click="showColDropdown = false" style="position:fixed;inset:0;z-index:1049;"></div>
                </div>
            </div>

            <!-- Table -->
            <div class="card" v-if="!loading && totalItems > 0">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover table-striped mb-0">
                            <thead>
                                <tr>
                                    <th v-for="column in columns" :key="column.key"
                                        :style="column.width ? { width: column.width } : {}"
                                        @click="handleSort(column.key)"
                                        style="cursor:pointer;user-select:none;">
                                        {{ column.label }}
                                        <i v-if="sortColumn === column.key" class="bi ms-1"
                                           :class="sortDirection === 'asc' ? 'bi-arrow-up' : 'bi-arrow-down'"></i>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="item in paginatedData" :key="item.item_id">
                                    <td v-if="isColVisible('crew_score')" class="text-center">
                                        <span class="badge fs-6" :class="{
                                            'bg-success': item.crew_score < 3,
                                            'bg-warning text-dark': item.crew_score >= 3 && item.crew_score < 5,
                                            'bg-danger': item.crew_score >= 5
                                        }">{{ item.crew_score }}</span>
                                        <div v-if="item.crew_reasons && item.crew_reasons.length" class="mt-1">
                                            <small v-for="(r, i) in item.crew_reasons" :key="i" class="d-block text-muted">{{ r }}</small>
                                        </div>
                                    </td>
                                    <td v-if="isColVisible('item_id')" class="font-monospace small">{{ item.item_id }}</td>
                                    <td v-if="isColVisible('title')">
                                        <a href="#" @click.prevent="openRecord(item.bibliographic_record_id)" class="link-entity fw-bold">{{ item.title }}</a>
                                        <div v-if="item.authors && item.authors.length" class="text-muted small">
                                            {{ Array.isArray(item.authors) ? item.authors.join(', ') : item.authors }}
                                        </div>
                                    </td>
                                    <td v-if="isColVisible('condition')">
                                        <span v-if="item.condition" class="badge"
                                              :class="item.condition === 'good' ? 'bg-success' : 'bg-warning text-dark'">
                                            {{ t('item.condition_' + item.condition) }}
                                        </span>
                                    </td>
                                    <td v-if="isColVisible('shelf_location')"><small>{{ item.shelf_location || '—' }}</small></td>
                                    <td v-if="isColVisible('age_days')" class="text-end">
                                        <span v-if="item.age_days != null && !isNaN(item.age_days)"
                                              :class="item.age_days > 1095 ? 'text-danger' : item.age_days > 730 ? 'text-warning' : ''">
                                            {{ Math.floor(item.age_days / 365) }} {{ t('reports.crew.years') }}
                                        </span>
                                        <span v-else class="text-muted">—</span>
                                    </td>
                                    <td v-if="isColVisible('publication_year')" class="text-center">
                                        <span v-if="item.publication_year"
                                              :class="item.publication_year < new Date().getFullYear() - 10 ? 'text-danger' : item.publication_year < new Date().getFullYear() - 5 ? 'text-warning' : ''">
                                            {{ item.publication_year }}
                                        </span>
                                        <span v-else class="text-muted">—</span>
                                    </td>
                                    <td v-if="isColVisible('total_copies')" class="text-center">
                                        <span :class="(copiesPerTitle[item.bibliographic_record_id] ?? 1) <= 1 ? 'text-danger' : ''">
                                            {{ copiesPerTitle[item.bibliographic_record_id] ?? 1 }}
                                        </span>
                                    </td>
                                    <td v-if="isColVisible('period_loan_count')">
                                        <div class="d-flex align-items-center gap-2">
                                            <div class="progress flex-grow-1" style="height:16px;">
                                                <div class="progress-bar"
                                                     :class="(item.taux_rotation ?? 0) >= 8 ? 'bg-danger' : (item.taux_rotation ?? 0) >= 4 ? 'bg-warning' : (item.taux_rotation ?? 0) === 0 ? 'bg-secondary' : 'bg-success'"
                                                     :style="{ width: Math.max((item.taux_rotation ?? 0) / tauxMax * 100, 4) + '%' }">
                                                    {{ item.taux_rotation ?? 0 }}
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
                <i class="bi bi-info-circle me-2"></i>
                {{ t('reports.crew.noItems') }}
            </div>

            <!-- Loading state -->
            <div v-else-if="loading" class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">{{ t('common.loading') }}</span>
                </div>
            </div>

            <!-- Pagination -->
            <pagination
                v-if="!loading && totalItems > 0"
                :current-page="currentPage"
                :page-size="pageSize"
                :total-items="totalItems"
                :total-pages="totalPages"
                @page-change="handlePageChange"
                @page-size-change="handlePageSizeChange"
                class="mt-3"
            />
        </div>
    `
});
