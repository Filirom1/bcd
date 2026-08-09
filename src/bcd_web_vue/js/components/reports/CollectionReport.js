/**
 * Collection Report Component
 * Unified view for "Jamais empruntés" and "À désherber (CREW)" reports.
 * Features clickable breakdown bars, interactive Chart.js histograms with
 * dual range sliders, cross-filtering, and configurable panel visibility.
 */

const { defineComponent, ref, computed, watch, onMounted, onBeforeUnmount, nextTick } = Vue;
const { useI18n } = VueI18n;
import { Chart, BarController, BarElement, CategoryScale, Legend, LinearScale, Tooltip } from 'chart.js';
import { apiClient } from '../../api/client.js';
import { normalizeCollection } from '../../models/pagination.js';
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import { useAppState } from '../../composables/useAppState.js';
import { useNotification } from '../../composables/useNotification.js';
import { usePagination } from '../../composables/usePagination.js';
import { formatAuthors } from '../../utils/domain.js';
import ReportHeader from '../ui/ReportHeader.js';
import { getJSON, setJSON } from '../../utils/storage.js';
import Pagination from '../ui/Pagination.js';
import FilterChips from './FilterChips.js';
import TauxRotationPanel from './TauxRotationPanel.js';

const PANEL_IDS = ['crew_score', 'medium_type', 'condition', 'pub_year', 'acq_year', 'taux_rotation'];
const HIDDEN_PANELS_KEY = 'collection_hidden_panels';

export default defineComponent({
    name: 'CollectionReport',

    components: { ReportHeader, Pagination, FilterChips, TauxRotationPanel },

    setup() {
        const { t } = useI18n();
        const { settings } = useAppState();
        const { error: showError } = useNotification();
        const { openRecord } = useGlobalModal();

        const pubChartRef = ref(null);
        const acqChartRef = ref(null);

        // ── Panel filters (structural — drive the API query) ──────────────────
        const crewMethod = ref('never_borrowed');

        // ── Cross-filters (set by clicking breakdowns or sliders) ─────────────
        const crossFilters = ref({
            medium_type: null,
            target_audience: null,
            condition: null,
            pub_year_min: null,
            pub_year_max: null,
            acq_year_min: null,
            acq_year_max: null,
        });

        // Client-side only — does NOT trigger API reload
        const tauxRotationFilter = ref({ min: null, max: null });
        const crewScoreFilter    = ref({ min: null, max: null });

        const hasActiveFilters = computed(() =>
            Object.values(crossFilters.value).some(v => v !== null)
        );

        // ── Panel visibility (localStorage) ───────────────────────────────────
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
            crew_score:     t('reports.crew.scoreHistogram'),
            medium_type:    t('reports.collectionReport.bySupport'),
            target_audience:t('reports.collectionReport.byAudience'),
            condition:      t('reports.collectionReport.byCondition'),
            pub_year:       t('reports.collectionReport.histoPubYear'),
            acq_year:       t('reports.collectionReport.histoAcqYear'),
            taux_rotation:  t('reports.tauxRotation.label'),
        }));

        // ── CREW method definitions ────────────────────────────────────────────
        const crewMethods = computed(() => [
            { value: 'all',                 label: t('reports.crew.all'),                desc: t('reports.crew.allDesc') },
            { value: 'never_borrowed',      label: t('reports.crew.neverBorrowed'),      desc: t('reports.crew.neverBorrowedDesc') },
            { value: 'low_circulation',     label: t('reports.crew.lowCirculation'),     desc: t('reports.crew.lowCirculationDesc') },
            { value: 'damaged_old',         label: t('reports.crew.damagedOld'),         desc: t('reports.crew.damagedOldDesc') },
            { value: 'high_score',          label: t('reports.crew.highScore'),          desc: t('reports.crew.highScoreDesc') },
            { value: 'never_inventoried',   label: t('reports.crew.neverInventoried'),   desc: t('reports.crew.neverInventoriedDesc') },
            { value: 'duplicate_low_demand',label: t('reports.crew.duplicateLowDemand'),desc: t('reports.crew.duplicateLowDemandDesc') },
        ]);

        // ── Aggregation data ───────────────────────────────────────────────────
        const stats = ref(null);
        const statsLoading = ref(false);

        // ── Table data ────────────────────────────────────────────────────────
        const allItems = ref([]);
        const tableLoading = ref(false);

        const sortColumn = ref('crew_score');
        const sortDirection = ref('desc');

        const { currentPage, pageSize, totalItems, totalPages, setTotalItems, goToPage, setPageSize }
            = usePagination({ pageSize: 50 });

        // ── Score histogram (client-side, computed from allItems) ──────────────
        const scoreHistogram = computed(() => {
            const counts = {};
            allItems.value.forEach(i => {
                const s = i.crew_score ?? 0;
                counts[s] = (counts[s] || 0) + 1;
            });
            if (!Object.keys(counts).length) return [];
            const maxS = Math.max(...Object.keys(counts).map(Number));
            const result = [];
            for (let i = 0; i <= Math.max(maxS, 5); i++) result.push({ score: i, count: counts[i] || 0 });
            return result;
        });
        const scoreHistMax  = computed(() => Math.max(...scoreHistogram.value.map(b => b.count), 1));
        const scoreRange    = computed(() => ({ min: 0, max: scoreHistogram.value.length ? scoreHistogram.value[scoreHistogram.value.length - 1].score : 8 }));
        const scoreBarColor = score => score >= 5 ? '#F24D66' : score >= 3 ? '#F2BF33' : '#33CC66';
        const isScoreInRange = score => {
            const sc = crewScoreFilter.value;
            if (sc.min === null && sc.max === null) return true;
            if (sc.min !== null && score < sc.min) return false;
            if (sc.max !== null && score > sc.max) return false;
            return true;
        };

        const sliderScoreMin = ref(0);
        const sliderScoreMax = ref(8);

        watch(scoreRange, r => {
            if (crewScoreFilter.value.min === null) sliderScoreMin.value = 0;
            if (crewScoreFilter.value.max === null) sliderScoreMax.value = r.max;
        });

        const clampScoreMin = () => { if (sliderScoreMin.value >= sliderScoreMax.value) sliderScoreMin.value = sliderScoreMax.value - 1; };
        const clampScoreMax = () => { if (sliderScoreMax.value <= sliderScoreMin.value) sliderScoreMax.value = sliderScoreMin.value + 1; };
        const applyScoreRange = () => {
            const atDefault = sliderScoreMin.value === 0 && sliderScoreMax.value === scoreRange.value.max;
            crewScoreFilter.value = { min: atDefault ? null : sliderScoreMin.value, max: atDefault ? null : sliderScoreMax.value };
        };
        const scoreFillStyle = computed(() => {
            const { min, max } = scoreRange.value;
            const total = max - min;
            if (total <= 0) return {};
            return { left: ((sliderScoreMin.value - min) / total * 100) + '%', right: ((max - sliderScoreMax.value) / total * 100) + '%' };
        });

        // ── Chart instances ────────────────────────────────────────────────────
        let pubChart = null;
        let acqChart = null;

        // ── Slider state ───────────────────────────────────────────────────────
        const curYear = new Date().getFullYear();
        const sliderPubMin = ref(curYear - 20);
        const sliderPubMax = ref(curYear);
        const sliderAcqMin = ref(curYear - 10);
        const sliderAcqMax = ref(curYear);

        const pubYearRange = computed(() => {
            if (!stats.value?.pub_year_histogram?.length) return { min: curYear - 20, max: curYear };
            const years = stats.value.pub_year_histogram.map(r => r.year);
            return { min: Math.min(...years), max: Math.max(...years) };
        });

        const acqYearRange = computed(() => {
            if (!stats.value?.acq_year_histogram?.length) return { min: curYear - 10, max: curYear };
            const years = stats.value.acq_year_histogram.map(r => r.year);
            return { min: Math.min(...years), max: Math.max(...years) };
        });

        // Initialize sliders from data when stats loads
        watch(() => stats.value, newStats => {
            if (!newStats) return;
            const ph = newStats.pub_year_histogram;
            if (ph.length) {
                if (crossFilters.value.pub_year_min === null) sliderPubMin.value = ph[0].year;
                if (crossFilters.value.pub_year_max === null) sliderPubMax.value = ph[ph.length - 1].year;
            }
            const ah = newStats.acq_year_histogram;
            if (ah.length) {
                if (crossFilters.value.acq_year_min === null) sliderAcqMin.value = ah[0].year;
                if (crossFilters.value.acq_year_max === null) sliderAcqMax.value = ah[ah.length - 1].year;
            }
        });

        const fillStyle = (sMin, sMax, range) => {
            const total = range.max - range.min;
            if (total <= 0) return {};
            const left = (sMin - range.min) / total * 100;
            const right = (range.max - sMax) / total * 100;
            return { left: left + '%', right: right + '%' };
        };

        const pubFillStyle = computed(() => fillStyle(sliderPubMin.value, sliderPubMax.value, pubYearRange.value));
        const acqFillStyle = computed(() => fillStyle(sliderAcqMin.value, sliderAcqMax.value, acqYearRange.value));

        // Clamp: ensure min < max
        const clampPubMin = () => { if (sliderPubMin.value >= sliderPubMax.value) sliderPubMin.value = sliderPubMax.value - 1; };
        const clampPubMax = () => { if (sliderPubMax.value <= sliderPubMin.value) sliderPubMax.value = sliderPubMin.value + 1; };
        const clampAcqMin = () => { if (sliderAcqMin.value >= sliderAcqMax.value) sliderAcqMin.value = sliderAcqMax.value - 1; };
        const clampAcqMax = () => { if (sliderAcqMax.value <= sliderAcqMin.value) sliderAcqMax.value = sliderAcqMin.value + 1; };

        // Apply slider values to crossFilters (triggers reload via watcher)
        const applyPubRange = () => {
            const r = pubYearRange.value;
            const atDefault = sliderPubMin.value === r.min && sliderPubMax.value === r.max;
            crossFilters.value = {
                ...crossFilters.value,
                pub_year_min: atDefault ? null : sliderPubMin.value,
                pub_year_max: atDefault ? null : sliderPubMax.value,
            };
        };
        const applyAcqRange = () => {
            const r = acqYearRange.value;
            const atDefault = sliderAcqMin.value === r.min && sliderAcqMax.value === r.max;
            crossFilters.value = {
                ...crossFilters.value,
                acq_year_min: atDefault ? null : sliderAcqMin.value,
                acq_year_max: atDefault ? null : sliderAcqMax.value,
            };
        };

        // ── Filter helpers ─────────────────────────────────────────────────────
        const toggleBreakdown = (key, value) => {
            crossFilters.value = {
                ...crossFilters.value,
                [key]: crossFilters.value[key] === value ? null : value,
            };
        };

        const clearFilter = key => {
            if (key === 'pub_year') {
                crossFilters.value = { ...crossFilters.value, pub_year_min: null, pub_year_max: null };
                sliderPubMin.value = pubYearRange.value.min;
                sliderPubMax.value = pubYearRange.value.max;
            } else if (key === 'acq_year') {
                crossFilters.value = { ...crossFilters.value, acq_year_min: null, acq_year_max: null };
                sliderAcqMin.value = acqYearRange.value.min;
                sliderAcqMax.value = acqYearRange.value.max;
            } else if (key === 'taux_rotation') {
                tauxRotationFilter.value = { min: null, max: null };
            } else if (key === 'crew_score') {
                crewScoreFilter.value = { min: null, max: null };
                sliderScoreMin.value = 0;
                sliderScoreMax.value = scoreRange.value.max;
            } else {
                crossFilters.value = { ...crossFilters.value, [key]: null };
            }
        };

        const clearAllFilters = () => {
            crossFilters.value = {
                medium_type: null, target_audience: null, condition: null,
                pub_year_min: null, pub_year_max: null, acq_year_min: null, acq_year_max: null,
            };
            tauxRotationFilter.value = { min: null, max: null };
            crewScoreFilter.value    = { min: null, max: null };
            sliderScoreMin.value = 0;
            sliderScoreMax.value = scoreRange.value.max;
            sliderPubMin.value = pubYearRange.value.min;
            sliderPubMax.value = pubYearRange.value.max;
            sliderAcqMin.value = acqYearRange.value.min;
            sliderAcqMax.value = acqYearRange.value.max;
        };

        // Active filter chips for display
        const activeChips = computed(() => {
            const chips = [];
            const cf = crossFilters.value;
            if (cf.medium_type)    chips.push({ key: 'medium_type',    label: t('bibliographic.medium_type'),    value: cf.medium_type });
            if (cf.target_audience)chips.push({ key: 'target_audience',label: t('bibliographic.target_audience'),value: audienceLabel(cf.target_audience) });
            if (cf.condition)      chips.push({ key: 'condition',      label: t('item.condition'),               value: conditionLabel(cf.condition) });
            if (cf.pub_year_min !== null || cf.pub_year_max !== null)
                chips.push({ key: 'pub_year', label: t('reports.collectionReport.histoPubYear'),
                    value: `${cf.pub_year_min ?? '…'} – ${cf.pub_year_max ?? '…'}` });
            if (cf.acq_year_min !== null || cf.acq_year_max !== null)
                chips.push({ key: 'acq_year', label: t('reports.collectionReport.histoAcqYear'),
                    value: `${cf.acq_year_min ?? '…'} – ${cf.acq_year_max ?? '…'}` });
            const tr = tauxRotationFilter.value;
            if (tr.min !== null || tr.max !== null)
                chips.push({ key: 'taux_rotation', label: t('reports.tauxRotation.label'),
                    value: `${tr.min ?? '…'} – ${tr.max ?? '…'}` });
            const sc = crewScoreFilter.value;
            if (sc.min !== null || sc.max !== null)
                chips.push({ key: 'crew_score', label: t('reports.crew.score'),
                    value: `${sc.min ?? '…'} – ${sc.max ?? '…'}` });
            return chips;
        });

        // ── API calls ──────────────────────────────────────────────────────────
        const buildBaseParams = () => {
            const cf = crossFilters.value;
            const p = {
                crew_method: crewMethod.value,
                min_age_years: 0,
                exclude_periodicals: false,
            };
            if (cf.medium_type)    p.medium_type = cf.medium_type;
            if (cf.target_audience)p.target_audience = cf.target_audience;
            if (cf.condition)      p.condition = cf.condition;
            if (cf.pub_year_min !== null) p.pub_year_min = cf.pub_year_min;
            if (cf.pub_year_max !== null) p.pub_year_max = cf.pub_year_max;
            if (cf.acq_year_min !== null) p.acq_year_min = cf.acq_year_min;
            if (cf.acq_year_max !== null) p.acq_year_max = cf.acq_year_max;
            return p;
        };

        const buildTableParams = () => {
            const cf = crossFilters.value;
            const p = { no_limit: true };

            if (crewMethod.value === 'never_borrowed') {
                p.never_borrowed = true;
            } else if (crewMethod.value === 'low_circulation') {
                p.max_borrows = 2;
                const since = new Date();
                since.setMonth(since.getMonth() - 24);
                p.since_date = since.toISOString().split('T')[0];
            } else if (crewMethod.value === 'damaged_old') {
                p.condition = 'damaged';
                const d2 = new Date();
                d2.setTime(d2.getTime() - 3 * 365.25 * 86400000);
                p.acquired_before = d2.toISOString().split('T')[0];
            } else if (crewMethod.value === 'never_inventoried') {
                p.never_inventoried = true;
                const d3 = new Date();
                d3.setTime(d3.getTime() - 365.25 * 86400000);
                p.acquired_before = d3.toISOString().split('T')[0];
            }

            if (cf.medium_type)    p.medium_type = cf.medium_type;
            if (cf.target_audience)p.target_audience = cf.target_audience;
            if (cf.condition && crewMethod.value !== 'damaged_old') p.condition = cf.condition;
            if (cf.pub_year_min !== null) p.publication_year_min = cf.pub_year_min;
            if (cf.pub_year_max !== null) p.publication_year_max = cf.pub_year_max;
            if (cf.acq_year_min !== null) p.acquired_after = `${cf.acq_year_min}-01-01`;
            if (cf.acq_year_max !== null) p.acquired_before = `${cf.acq_year_max}-12-31`;

            return p;
        };

        const printReport = () => window.print();

        const loadStats = async () => {
            statsLoading.value = true;
            try {
                stats.value = await apiClient.get('/reports/collection-stats', buildBaseParams());
                await nextTick();
                rebuildCharts();
            } catch (e) {
                console.error('collection-stats error', e);
                showError(t('reports.loadError'));
            } finally {
                statsLoading.value = false;
            }
        };

        const loadTable = async () => {
            tableLoading.value = true;
            try {
                const response = await apiClient.get('/inventory/items/search', buildTableParams());
                const normalized = normalizeCollection(response);
                let items = normalized.items;

                if (crewMethod.value === 'high_score') {
                    items.forEach(i => { const c = calculateCrewScore(i); i.crew_score = c.score; i.crew_reasons = c.reasons; i.taux_rotation = i.circulation_count || 0; });
                    items = items.filter(i => i.crew_score >= 5);
                } else if (crewMethod.value === 'duplicate_low_demand') {
                    items.forEach(i => { i.taux_rotation = i.circulation_count || 0; });
                    items = filterDuplicateLowDemand(items);
                } else {
                    items.forEach(i => { const c = calculateCrewScore(i); i.crew_score = c.score; i.crew_reasons = c.reasons; i.taux_rotation = i.circulation_count || 0; });
                }

                items.sort((a, b) => (b.crew_score || 0) - (a.crew_score || 0));
                allItems.value = items;
                if (currentPage.value !== 1) currentPage.value = 1;
            } catch (e) {
                console.error('table load error', e);
                showError(t('reports.loadError'));
            } finally {
                tableLoading.value = false;
            }
        };

        // ── CREW score ────────────────────────────────────────────────────────
        const calculateCrewScore = item => {
            let score = 0; const reasons = [];
            if (item.age_days) {
                if (item.age_days > 1095) { score += 3; reasons.push(t('reports.crew.moreThan3Years')); }
                else if (item.age_days > 730) { score += 2; }
                else if (item.age_days > 365) { score += 1; }
            }
            if (item.condition === 'damaged') { score += 2; reasons.push(t('item.condition_damaged')); }
            const yr = item.publication_year;
            const age = yr ? curYear - yr : 0;
            if (item.medium_type?.toLowerCase().includes('document')) {
                if (age > 10) { score += 2; reasons.push(`${yr}`); }
                else if (age > 5) { score += 1; }
            }
            if ((item.period_loan_count ?? item.circulation_count ?? null) === 0) { score += 2; reasons.push(t('reports.crew.neverBorrowed')); }
            else if ((item.period_loan_count ?? null) === 1) { score += 1; }
            return { score, reasons };
        };

        const filterDuplicateLowDemand = items => {
            const groups = {};
            items.forEach(i => {
                const id = i.bibliographic_record_id;
                if (!groups[id]) groups[id] = [];
                groups[id].push(i);
            });
            const lowDemand = new Set();
            Object.entries(groups).forEach(([id, copies]) => {
                if (copies.length >= 3) {
                    const avg = copies.reduce((s, c) => s + (c.period_loan_count || 0), 0) / copies.length;
                    if (avg < 2) lowDemand.add(parseInt(id));
                }
            });
            return items.filter(i => lowDemand.has(i.bibliographic_record_id));
        };

        // ── Pagination + sort ──────────────────────────────────────────────────
        const filteredItems = computed(() => {
            let items = allItems.value;
            const tr = tauxRotationFilter.value;
            if (tr.min !== null || tr.max !== null) {
                items = items.filter(i => {
                    const v = i.taux_rotation || 0;
                    if (tr.min !== null && v < tr.min) return false;
                    if (tr.max !== null && v > tr.max) return false;
                    return true;
                });
            }
            const sc = crewScoreFilter.value;
            if (sc.min !== null || sc.max !== null) {
                items = items.filter(i => {
                    const v = i.crew_score ?? 0;
                    if (sc.min !== null && v < sc.min) return false;
                    if (sc.max !== null && v > sc.max) return false;
                    return true;
                });
            }
            return items;
        });

        watch(filteredItems, items => setTotalItems(items.length), { immediate: true });

        const paginatedData = computed(() => {
            const map = copiesPerTitle.value;
            const items = filteredItems.value.map(i => ({ ...i, total_copies: map[i.bibliographic_record_id] ?? 1 }));
            const sorted = items.sort((a, b) => {
                let av = a[sortColumn.value], bv = b[sortColumn.value];
                if (av == null && bv == null) return 0;
                if (av == null) return 1;
                if (bv == null) return -1;
                if (typeof av === 'string') { av = av.toLowerCase(); bv = bv.toLowerCase(); }
                const r = av < bv ? -1 : av > bv ? 1 : 0;
                return sortDirection.value === 'asc' ? r : -r;
            });
            const start = (currentPage.value - 1) * pageSize.value;
            return sorted.slice(start, start + pageSize.value);
        });

        const handleSort = col => {
            if (sortColumn.value === col) sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
            else { sortColumn.value = col; sortDirection.value = 'desc'; }
        };

        // ── Chart.js integration ───────────────────────────────────────────────
        const COLORS = { primary: '#4D99F2', warning: '#F2BF33', danger: '#F24D66', muted: '#adb5bd' };

        const isInPubRange = year => {
            const min = crossFilters.value.pub_year_min;
            const max = crossFilters.value.pub_year_max;
            if (min === null && max === null) return true;
            if (min !== null && year < min) return false;
            if (max !== null && year > max) return false;
            return true;
        };

        const isInAcqRange = year => {
            const min = crossFilters.value.acq_year_min;
            const max = crossFilters.value.acq_year_max;
            if (min === null && max === null) return true;
            if (min !== null && year < min) return false;
            if (max !== null && year > max) return false;
            return true;
        };

        const pubBarColor = year => {
            const y = parseInt(year);
            const hasRange = crossFilters.value.pub_year_min !== null || crossFilters.value.pub_year_max !== null;
            let base = y <= curYear - 20 ? COLORS.danger : y <= curYear - 10 ? COLORS.warning : COLORS.primary;
            if (hasRange && !isInPubRange(y)) base += '44';
            return base;
        };

        const destroyCharts = () => {
            if (pubChart) { pubChart.destroy(); pubChart = null; }
            if (acqChart) { acqChart.destroy(); acqChart = null; }
        };

        const rebuildCharts = () => {
            if (!stats.value) return;
            Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);
            destroyCharts();

            const pubEl = pubChartRef.value;
            if (pubEl && stats.value.pub_year_histogram.length > 0) {
                const data = stats.value.pub_year_histogram;
                pubChart = new Chart(pubEl.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: data.map(r => r.year),
                        datasets: [{
                            label: t('reports.collectionReport.chartItems'),
                            data: data.map(r => r.count),
                            backgroundColor: data.map(r => pubBarColor(r.year)),
                            borderRadius: 3,
                        }],
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: { callbacks: {
                                title: i => `${t('reports.collectionReport.histoPubYear')} ${i[0].label}`,
                                label: i => `${i.raw} ${t('reports.collectionReport.chartItems')}`,
                            }},
                        },
                        scales: {
                            x: { ticks: { font: { size: 10 }, maxRotation: 45 }, grid: { display: false } },
                            y: { ticks: { font: { size: 10 } }, grid: { color: '#f0f0f0' } },
                        },
                    },
                });
            }

            const acqEl = acqChartRef.value;
            if (acqEl && stats.value.acq_year_histogram.length > 0) {
                const data = stats.value.acq_year_histogram;
                const hasRange = crossFilters.value.acq_year_min !== null || crossFilters.value.acq_year_max !== null;
                acqChart = new Chart(acqEl.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: data.map(r => r.year),
                        datasets: [{
                            label: t('reports.collectionReport.chartItems'),
                            data: data.map(r => r.count),
                            backgroundColor: data.map(r =>
                                hasRange && !isInAcqRange(r.year) ? COLORS.primary + '44' : COLORS.primary
                            ),
                            borderRadius: 4,
                        }],
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: { callbacks: {
                                title: i => `${t('reports.collectionReport.histoAcqYear')} ${i[0].label}`,
                                label: i => `${i.raw} ${t('reports.collectionReport.chartItems')}`,
                            }},
                        },
                        scales: {
                            x: { ticks: { font: { size: 11 } }, grid: { display: false } },
                            y: { ticks: { font: { size: 11 } }, grid: { color: '#f0f0f0' } },
                        },
                    },
                });
            }
        };

        // ── Breakdown bar helpers ──────────────────────────────────────────────
        const BREAKDOWN_COLORS = [COLORS.primary, '#1abc9c', '#e67e22', '#9b59b6', COLORS.warning, '#2ecc71', COLORS.muted];

        const breakdownMax = rows => Math.max(...rows.map(r => r.count), 1);

        const audienceLabel = val => {
            const map = { child: t('bibliographic.audience_child'), youth: t('bibliographic.audience_youth'), adult: t('bibliographic.audience_adult') };
            return map[val] || val;
        };
        const conditionLabel = val => {
            const map = { good: t('item.condition_good'), damaged: t('item.condition_damaged') };
            return map[val] || val;
        };

        // ── Watch: reload on any filter change ────────────────────────────────
        const reload = () => { loadStats(); loadTable(); };

        watch(crewMethod, () => { clearAllFilters(); });
        watch(crossFilters, reload, { deep: true });

        // ── Column visibility ──────────────────────────────────────────────────
        const COL_IDS_CREW = ['crew_score', 'item_id', 'title', 'condition', 'shelf_location', 'age_days', 'publication_year', 'total_copies', 'taux_rotation'];
        const COL_STORAGE_KEY_CREW = 'crew_cols';
        const loadVisibleColsCrew = () => {
            const s = getJSON(COL_STORAGE_KEY_CREW);
            if (s) return s.filter(id => COL_IDS_CREW.includes(id));
            return [...COL_IDS_CREW];
        };
        const visibleCols = ref(loadVisibleColsCrew());
        const showColDropdown = ref(false);
        const isColVisible = id => visibleCols.value.includes(id);
        const toggleCol = id => {
            visibleCols.value = visibleCols.value.includes(id)
                ? visibleCols.value.filter(c => c !== id)
                : [...visibleCols.value, id];
            setJSON(COL_STORAGE_KEY_CREW, visibleCols.value);
        };
        const resetCols = () => {
            visibleCols.value = [...COL_IDS_CREW];
            showColDropdown.value = false;
            setJSON(COL_STORAGE_KEY_CREW, visibleCols.value);
        };

        const allColsCrew = computed(() => [
            { key: 'crew_score',      label: t('reports.crew.score')              },
            { key: 'item_id',         label: t('item.item_id')                    },
            { key: 'title',           label: t('reports.neverBorrowed.bookTitle') },
            { key: 'condition',       label: t('item.condition')                  },
            { key: 'shelf_location',  label: t('item.shelf_location')             },
            { key: 'age_days',        label: t('reports.crew.ageInCollection')    },
            { key: 'publication_year',label: t('reports.crew.pubYear')            },
            { key: 'total_copies',    label: t('reports.mostBorrowed.copies')     },
            { key: 'taux_rotation',   label: t('reports.tauxRotation.label')      },
        ]);

        // ── Per-title copies + taux max ────────────────────────────────────────
        const copiesPerTitle = computed(() => {
            const map = {};
            allItems.value.forEach(i => {
                map[i.bibliographic_record_id] = (map[i.bibliographic_record_id] || 0) + 1;
            });
            return map;
        });
        const tauxMax = computed(() => Math.max(...allItems.value.map(i => i.taux_rotation ?? 0), 1));

        onMounted(reload);
        onBeforeUnmount(destroyCharts);

        return {
            pubChartRef, acqChartRef,
            t, settings, formatAuthors,
            crewMethod, crewMethods,
            crossFilters, tauxRotationFilter, hasActiveFilters, activeChips,
            toggleBreakdown, clearFilter, clearAllFilters,
            hiddenPanels, visiblePanels, showPanelDropdown, isPanelVisible, togglePanel, resetPanels, PANEL_IDS, PANEL_LABELS,
            sliderPubMin, sliderPubMax, sliderAcqMin, sliderAcqMax,
            pubYearRange, acqYearRange, pubFillStyle, acqFillStyle,
            clampPubMin, clampPubMax, clampAcqMin, clampAcqMax,
            applyPubRange, applyAcqRange,
            stats, statsLoading,
            BREAKDOWN_COLORS, breakdownMax, audienceLabel, conditionLabel,
            allItems, tableLoading, paginatedData, totalItems, totalPages,
            currentPage, pageSize, sortColumn, sortDirection,
            handleSort, goToPage, setPageSize,
            openRecord,
            COL_IDS_CREW, allColsCrew, visibleCols, showColDropdown, isColVisible, toggleCol, resetCols,
            copiesPerTitle, tauxMax,
            scoreHistogram, scoreHistMax, scoreRange, scoreBarColor, isScoreInRange,
            sliderScoreMin, sliderScoreMax, scoreFillStyle, clampScoreMin, clampScoreMax, applyScoreRange,
            crewScoreFilter,
            printReport,
        };
    },

    template: `
<div>
    <report-header :title="t('reports.crew.title')" @print="printReport" />

    <!-- CREW method selector -->
    <div class="card mb-3">
        <div class="card-body py-2">
            <div class="d-flex align-items-center gap-3">
                <strong class="text-nowrap small">{{ t('reports.crew.methodTitle') }} :</strong>
                <div class="btn-group btn-group-sm flex-grow-1" role="group">
                    <template v-for="m in crewMethods" :key="m.value">
                        <input type="radio" class="btn-check" :id="'crew-' + m.value" v-model="crewMethod" :value="m.value">
                        <label class="btn btn-outline-primary" :for="'crew-' + m.value" :title="m.desc">{{ m.label }}</label>
                    </template>
                </div>
                <!-- Toggles groupés : colonnes + panneaux -->
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
                            <div v-for="col in allColsCrew" :key="col.key" class="form-check px-3 py-1">
                                <input type="checkbox" class="form-check-input" :id="'col-crew-' + col.key"
                                       :checked="isColVisible(col.key)" @change="toggleCol(col.key)">
                                <label class="form-check-label small" :for="'col-crew-' + col.key" style="cursor:pointer;">{{ col.label }}</label>
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
                                <input type="checkbox" class="form-check-input" :id="'panel-' + id"
                                       :checked="isPanelVisible(id)" @change="togglePanel(id)">
                                <label class="form-check-label small" :for="'panel-' + id" style="cursor:pointer;">{{ PANEL_LABELS[id] }}</label>
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
        </div>
    </div>

    <!-- Active filter chips -->
    <filter-chips :chips="activeChips" @clear="clearFilter" @clear-all="clearAllFilters" />

    <!-- Breakdown panels + histograms — equal size, configurable visibility -->
    <div class="row g-2 mb-3" v-if="stats">

        <!-- Score CREW histogram + dual slider -->
        <div class="col-6 col-md-4" v-if="isPanelVisible('crew_score') && allItems.length">
            <div class="card h-100">
                <div class="card-body p-3">
                    <div class="text-uppercase fw-bold mb-2" style="font-size:11px;letter-spacing:.8px;color:#6c757d;">
                        {{ t('reports.crew.scoreHistogram') }}
                    </div>
                    <div v-if="!scoreHistogram.length" class="text-muted small">—</div>
                    <div v-if="scoreHistogram.length" class="d-flex mb-1" style="height:80px;align-items:flex-end;gap:2px;">
                        <div v-for="b in scoreHistogram" :key="b.score"
                             style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;">
                            <div :style="{
                                width:'100%', height: (b.count / scoreHistMax * 80) + 'px',
                                background: scoreBarColor(b.score),
                                borderRadius: '2px 2px 0 0',
                                opacity: isScoreInRange(b.score) ? 1 : 0.25,
                                transition: 'opacity 0.2s'
                            }" :title="b.score + ': ' + b.count + ' ' + t('reports.collectionReport.chartItems')"></div>
                        </div>
                    </div>
                    <div v-if="scoreHistogram.length" class="d-flex mb-1" style="gap:2px;">
                        <div v-for="b in scoreHistogram" :key="'lbl-' + b.score" style="flex:1;text-align:center;font-size:10px;color:#999;">{{ b.score }}</div>
                    </div>
                    <div class="range-slider-container" v-if="scoreHistogram.length">
                        <div class="range-slider-track"></div>
                        <div class="range-slider-fill" :style="scoreFillStyle"></div>
                        <input type="range" class="dual-range-input"
                               :min="scoreRange.min" :max="scoreRange.max" step="1"
                               v-model.number="sliderScoreMin"
                               @input="clampScoreMin" @change="applyScoreRange">
                        <input type="range" class="dual-range-input"
                               :min="scoreRange.min" :max="scoreRange.max" step="1"
                               v-model.number="sliderScoreMax"
                               @input="clampScoreMax" @change="applyScoreRange">
                    </div>
                    <div class="d-flex justify-content-between" style="font-size:11px;color:#888;margin-top:2px;">
                        <span>{{ sliderScoreMin }}</span>
                        <span>{{ sliderScoreMax }}</span>
                    </div>
                    <div class="mt-1" style="font-size:11px;color:#aaa;">
                        <i class="bi bi-square-fill me-1" style="color:#33CC66;"></i>0–2 &nbsp;
                        <i class="bi bi-square-fill text-warning me-1"></i>3–4 &nbsp;
                        <i class="bi bi-square-fill text-danger me-1"></i>≥5
                    </div>
                </div>
            </div>
        </div>

        <!-- Par support -->
        <div class="col-6 col-md-4" v-if="isPanelVisible('medium_type')">
            <div class="card h-100">
                <div class="card-body p-3">
                    <div class="text-uppercase fw-bold mb-2" style="font-size:11px;letter-spacing:.8px;color:#6c757d;">
                        {{ t('reports.collectionReport.bySupport') }}
                        <span class="fw-normal text-muted ms-1" style="text-transform:none;letter-spacing:0;">· {{ t('reports.collectionReport.clickToFilter') }}</span>
                    </div>
                    <div v-if="!stats.breakdowns.medium_type.length" class="text-muted small">—</div>
                    <div v-for="(row, i) in stats.breakdowns.medium_type" :key="row.value"
                         @click="toggleBreakdown('medium_type', row.value)"
                         class="d-flex align-items-center gap-2 mb-1 px-1 py-1 rounded"
                         style="cursor:pointer;"
                         :style="crossFilters.medium_type === row.value ? 'background:#ddeeff;outline:2px solid #4D99F2;' : ''">
                        <span style="min-width:90px;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="row.value">{{ row.value }}</span>
                        <div style="flex:1;background:#f0f0f0;border-radius:3px;height:7px;overflow:hidden;">
                            <div :style="{width: Math.round(row.count/breakdownMax(stats.breakdowns.medium_type)*100)+'%', background: BREAKDOWN_COLORS[i % BREAKDOWN_COLORS.length], height:'100%', borderRadius:'3px'}"></div>
                        </div>
                        <span style="min-width:28px;font-size:12px;font-weight:600;text-align:right;">{{ row.count }}</span>
                        <span style="min-width:34px;font-size:11px;color:#999;">{{ Math.round(row.count/stats.total_count*100) }}%</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Par état -->
        <div class="col-6 col-md-4" v-if="isPanelVisible('condition')">
            <div class="card h-100">
                <div class="card-body p-3">
                    <div class="text-uppercase fw-bold mb-2" style="font-size:11px;letter-spacing:.8px;color:#6c757d;">
                        {{ t('reports.collectionReport.byCondition') }}
                        <span class="fw-normal text-muted ms-1" style="text-transform:none;letter-spacing:0;">· {{ t('reports.collectionReport.clickToFilter') }}</span>
                    </div>
                    <div v-if="!stats.breakdowns.condition.length" class="text-muted small">—</div>
                    <div v-for="(row, i) in stats.breakdowns.condition" :key="row.value"
                         @click="toggleBreakdown('condition', row.value)"
                         class="d-flex align-items-center gap-2 mb-1 px-1 py-1 rounded"
                         style="cursor:pointer;"
                         :style="crossFilters.condition === row.value ? 'background:#ddeeff;outline:2px solid #4D99F2;' : ''">
                        <span style="min-width:70px;font-size:12px;">{{ conditionLabel(row.value) }}</span>
                        <div style="flex:1;background:#f0f0f0;border-radius:3px;height:7px;overflow:hidden;">
                            <div :style="{width: Math.round(row.count/breakdownMax(stats.breakdowns.condition)*100)+'%', background: row.value === 'damaged' ? '#F2BF33' : '#33CC66', height:'100%', borderRadius:'3px'}"></div>
                        </div>
                        <span style="min-width:28px;font-size:12px;font-weight:600;text-align:right;">{{ row.count }}</span>
                        <span style="min-width:34px;font-size:11px;color:#999;">{{ Math.round(row.count/stats.total_count*100) }}%</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Histogramme année publication + dual slider -->
        <div class="col-6 col-md-4" v-if="isPanelVisible('pub_year')">
            <div class="card h-100">
                <div class="card-body p-3">
                    <div class="text-uppercase fw-bold mb-1" style="font-size:11px;letter-spacing:.8px;color:#6c757d;">
                        {{ t('reports.collectionReport.histoPubYear') }}
                    </div>
                    <div style="position:relative;height:160px;">
                        <canvas ref="pubChartRef"></canvas>
                    </div>
                    <!-- Dual range slider -->
                    <div class="mt-2 px-1" v-if="stats.pub_year_histogram.length">
                        <div class="range-slider-container">
                            <div class="range-slider-track"></div>
                            <div class="range-slider-fill" :style="pubFillStyle"></div>
                            <input type="range" class="dual-range-input"
                                   :min="pubYearRange.min" :max="pubYearRange.max"
                                   v-model.number="sliderPubMin"
                                   @input="clampPubMin" @change="applyPubRange">
                            <input type="range" class="dual-range-input"
                                   :min="pubYearRange.min" :max="pubYearRange.max"
                                   v-model.number="sliderPubMax"
                                   @input="clampPubMax" @change="applyPubRange">
                        </div>
                        <div class="d-flex justify-content-between" style="font-size:11px;color:#888;margin-top:2px;">
                            <span>{{ sliderPubMin }}</span>
                            <span>{{ sliderPubMax }}</span>
                        </div>
                    </div>
                    <div class="mt-1" style="font-size:11px;color:#aaa;">
                        <i class="bi bi-square-fill text-danger me-1"></i>{{ t('reports.pubYear.ageOld') }} &nbsp;
                        <i class="bi bi-square-fill text-warning me-1"></i>{{ t('reports.pubYear.ageMid') }} &nbsp;
                        <i class="bi bi-square-fill me-1" style="color:#4D99F2;"></i>{{ t('reports.pubYear.ageNew') }}
                    </div>
                </div>
            </div>
        </div>

        <!-- Taux de rotation histogram + dual slider -->
        <div class="col-6 col-md-4" v-if="isPanelVisible('taux_rotation') && allItems.length">
            <taux-rotation-panel
                :items="allItems"
                :title="t('reports.tauxRotation.label')"
                :model-min="tauxRotationFilter.min"
                :model-max="tauxRotationFilter.max"
                @update:model-min="tauxRotationFilter.min = $event"
                @update:model-max="tauxRotationFilter.max = $event"
            />
        </div>

        <!-- Histogramme année acquisition + dual slider -->
        <div class="col-6 col-md-4" v-if="isPanelVisible('acq_year')">
            <div class="card h-100">
                <div class="card-body p-3">
                    <div class="text-uppercase fw-bold mb-1" style="font-size:11px;letter-spacing:.8px;color:#6c757d;">
                        {{ t('reports.collectionReport.histoAcqYear') }}
                    </div>
                    <div style="position:relative;height:160px;">
                        <canvas ref="acqChartRef"></canvas>
                    </div>
                    <!-- Dual range slider -->
                    <div class="mt-2 px-1" v-if="stats.acq_year_histogram.length">
                        <div class="range-slider-container">
                            <div class="range-slider-track"></div>
                            <div class="range-slider-fill" :style="acqFillStyle"></div>
                            <input type="range" class="dual-range-input"
                                   :min="acqYearRange.min" :max="acqYearRange.max"
                                   v-model.number="sliderAcqMin"
                                   @input="clampAcqMin" @change="applyAcqRange">
                            <input type="range" class="dual-range-input"
                                   :min="acqYearRange.min" :max="acqYearRange.max"
                                   v-model.number="sliderAcqMax"
                                   @input="clampAcqMax" @change="applyAcqRange">
                        </div>
                        <div class="d-flex justify-content-between" style="font-size:11px;color:#888;margin-top:2px;">
                            <span>{{ sliderAcqMin }}</span>
                            <span>{{ sliderAcqMax }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Loading skeleton for stats -->
    <div v-if="statsLoading && !stats" class="text-center py-4 text-muted">
        <div class="spinner-border spinner-border-sm me-2"></div>{{ t('common.loading') }}
    </div>

    <!-- Results summary -->
    <div v-if="!tableLoading" class="mb-2 text-muted">
        {{ t('reports.neverBorrowed.showing', { count: paginatedData.length, total: totalItems }) }}
    </div>

    <!-- Table -->
    <div class="card" v-if="!tableLoading && totalItems > 0">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-striped mb-0">
                    <thead>
                        <tr>
                            <th v-if="isColVisible('crew_score')" @click="handleSort('crew_score')" style="width:80px;cursor:pointer;">
                                {{ t('reports.crew.score') }}
                                <i v-if="sortColumn==='crew_score'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('item_id')" style="width:110px;">{{ t('item.item_id') }}</th>
                            <th v-if="isColVisible('title')" @click="handleSort('title')" style="cursor:pointer;">
                                {{ t('reports.neverBorrowed.bookTitle') }}
                                <i v-if="sortColumn==='title'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('condition')" style="width:95px;">{{ t('item.condition') }}</th>
                            <th v-if="isColVisible('shelf_location')" style="width:120px;">{{ t('item.shelf_location') }}</th>
                            <th v-if="isColVisible('age_days')" @click="handleSort('age_days')" style="width:100px;cursor:pointer;">
                                {{ t('reports.crew.ageInCollection') }}
                                <i v-if="sortColumn==='age_days'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('publication_year')" @click="handleSort('publication_year')" style="width:90px;cursor:pointer;">
                                {{ t('reports.crew.pubYear') }}
                                <i v-if="sortColumn==='publication_year'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('total_copies')" @click="handleSort('total_copies')" style="width:80px;cursor:pointer;">
                                {{ t('reports.mostBorrowed.copies') }}
                                <i v-if="sortColumn==='total_copies'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                            <th v-if="isColVisible('taux_rotation')" @click="handleSort('taux_rotation')" style="width:170px;cursor:pointer;">
                                {{ t('reports.tauxRotation.label') }}
                                <i v-if="sortColumn==='taux_rotation'" class="bi ms-1" :class="sortDirection==='asc'?'bi-arrow-up':'bi-arrow-down'"></i>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="item in paginatedData" :key="item.item_id">
                            <td v-if="isColVisible('crew_score')" class="text-center">
                                <span class="badge fs-6"
                                    :class="item.crew_score>=5?'bg-danger':item.crew_score>=3?'bg-warning text-dark':'bg-success'">
                                    {{ item.crew_score }}
                                </span>
                                <div v-if="item.crew_reasons && item.crew_reasons.length" class="mt-1">
                                    <small v-for="(r, i) in item.crew_reasons" :key="i" class="d-block text-muted">{{ r }}</small>
                                </div>
                            </td>
                            <td v-if="isColVisible('item_id')" class="font-monospace small">{{ item.item_id }}</td>
                            <td v-if="isColVisible('title')">
                                <a href="#" @click.prevent="openRecord(item.bibliographic_record_id)" class="link-entity fw-bold">{{ item.title }}</a>
                                <div v-if="item.authors && item.authors.length" class="text-muted small">
                                    {{ formatAuthors(item.authors) }}
                                </div>
                            </td>
                            <td v-if="isColVisible('condition')">
                                <span class="badge" :class="item.condition==='good'?'bg-success':'bg-warning text-dark'">
                                    {{ t('item.condition_' + item.condition) }}
                                </span>
                            </td>
                            <td v-if="isColVisible('shelf_location')"><small>{{ item.shelf_location || '—' }}</small></td>
                            <td v-if="isColVisible('age_days')" class="text-end">
                                <span v-if="item.age_days != null"
                                    :class="item.age_days>1095?'text-danger':item.age_days>730?'text-warning':''">
                                    {{ Math.floor(item.age_days/365) }} {{ t('reports.crew.years') }}
                                </span>
                                <span v-else class="text-muted">—</span>
                            </td>
                            <td v-if="isColVisible('publication_year')" class="text-center">
                                <span v-if="item.publication_year"
                                    :class="item.publication_year<new Date().getFullYear()-20?'text-danger':item.publication_year<new Date().getFullYear()-10?'text-warning':''">
                                    {{ item.publication_year }}
                                </span>
                                <span v-else class="text-muted">—</span>
                            </td>
                            <td v-if="isColVisible('total_copies')" class="text-center">
                                <span :class="(copiesPerTitle[item.bibliographic_record_id] ?? 1) <= 1 ? 'text-danger' : ''">
                                    {{ copiesPerTitle[item.bibliographic_record_id] ?? 1 }}
                                </span>
                            </td>
                            <td v-if="isColVisible('taux_rotation')">
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

    <div v-else-if="!tableLoading && totalItems === 0" class="alert alert-info">
        <i class="bi bi-info-circle me-2"></i>{{ t('reports.crew.noItems') }}
    </div>

    <div v-else-if="tableLoading" class="text-center py-5">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">{{ t('common.loading') }}</span>
        </div>
    </div>

    <pagination
        v-if="!tableLoading && totalItems > 0"
        :current-page="currentPage"
        :page-size="pageSize"
        :total-items="totalItems"
        :total-pages="totalPages"
        @page-change="goToPage"
        @page-size-change="setPageSize"
        class="mt-3"
    />
</div>
    `
});
