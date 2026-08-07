/**
 * ClassRosterPanel Component
 *
 * Unified left panel for the checkout page.
 * Combines class selection, name/ID filter, and barcode scan into a single
 * scrollable student roster — replacing the disconnected BorrowerScanner.
 *
 * Status logic (mirrors the API):
 *   overdue_count > 0              → overdue  (orange)
 *   current_loans_count > 0        → borrowed (green)
 *   current_loans_count === 0      → none     (grey)
 *
 * API used (no new endpoints):
 *   GET /classes                           — populate class selector
 *   GET /borrowers?class_id=X&role=student&limit=500  — roster with counts
 *   GET /borrowers/{id}                    — when scanned ID not in current roster
 */

const { defineComponent, ref, computed, onMounted, watch } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { normalizeCollection } from '../../models/pagination.js';
import { useBarcodeUtils } from '../../composables/useBarcodeUtils.js';

export default defineComponent({
    name: 'ClassRosterPanel',

    props: {
        settings: {
            type: Object,
            default: null
        },
        selectedBorrowerId: {
            type: String,
            default: null
        },
        refreshTick: {
            type: Number,
            default: 0
        }
    },

    emits: ['borrower-selected'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { stripBarcodePrefix } = useBarcodeUtils();

        const classes = ref([]);
        const selectedClassId = ref(null);
        const roster = ref([]);
        const filterQuery = ref('');
        const rosterLoading = ref(false);
        const classesLoading = ref(true);
        const filterInputRef = ref(null);

        // ── Computed ──────────────────────────────────────────────────────────

        const filteredRoster = computed(() => {
            const prefix = props.settings?.borrower_barcode_prefix || '';
            let q = filterQuery.value.trim().toLowerCase();
            // Strip barcode prefix so "%101" matches borrower_id "101"
            if (prefix && q.startsWith(prefix.toLowerCase())) {
                q = q.substring(prefix.length);
            }
            if (!q) return roster.value;
            return roster.value.filter(b =>
                b.full_name.toLowerCase().includes(q) ||
                b.borrower_id.toLowerCase().startsWith(q)
            );
        });

        const stats = computed(() => {
            const all = roster.value;
            return {
                borrowed: all.filter(b => b.overdue_count === 0 && b.current_loans_count > 0).length,
                overdue:  all.filter(b => b.overdue_count > 0).length,
                notYet:   all.filter(b => b.current_loans_count === 0).length
            };
        });

        const selectedClass = computed(() =>
            classes.value.find(c => c.id === selectedClassId.value) || null
        );

        // ── Status helper ─────────────────────────────────────────────────────

        const studentStatus = (borrower) => {
            if (borrower.overdue_count > 0) return 'overdue';
            if (borrower.current_loans_count > 0) return 'borrowed';
            return 'none';
        };

        const bookCountLabel = (borrower) => {
            const n = borrower.current_loans_count;
            return n > 1
                ? t('circulation.books_plural', { count: n })
                : t('circulation.book_singular', { count: n });
        };

        // ── API calls ─────────────────────────────────────────────────────────

        const loadClasses = async () => {
            classesLoading.value = true;
            try {
                const data = await apiClient.get('/classes');
                classes.value = data;
                // Auto-select if only one class exists
                if (data.length === 1) {
                    await selectClass(data[0].id);
                }
            } catch (err) {
                console.error('Failed to load classes:', err);
            } finally {
                classesLoading.value = false;
            }
        };

        const loadRoster = async (classId) => {
            rosterLoading.value = true;
            try {
                const data = await apiClient.get('/borrowers', {
                    class_id: classId,
                    role: 'student',
                    limit: 500
                });
                const normalized = normalizeCollection(data);
                roster.value = normalized.items;
            } catch (err) {
                console.error('Failed to load roster:', err);
                roster.value = [];
            } finally {
                rosterLoading.value = false;
            }
        };

        const selectClass = async (classId) => {
            const id = Number(classId);
            if (!id) return;
            selectedClassId.value = id;
            filterQuery.value = '';
            await loadRoster(id);
        };

        // ── Input handler: filter by name OR resolve barcode scan ─────────────

        let lookupTimeout = null;

        const handleFilterInput = (value) => {
            filterQuery.value = value;
            clearTimeout(lookupTimeout);

            if (!value.trim()) return;

            // Strip borrower barcode prefix (e.g. "%421" → "421")
            const prefix = props.settings?.borrower_barcode_prefix || '';
            const stripped = prefix ? stripBarcodePrefix(value.trim(), prefix) : value.trim();

            // Need a non-empty stripped value and it must look like an ID
            if (!stripped) return;
            const couldBeId = stripped !== value.trim() || /^\d+$/.test(stripped);
            if (!couldBeId) return; // Pure text filter — filteredRoster handles it

            // Debounce: barcode scanners complete in ~50 ms, manual typing waits 300 ms.
            // This prevents partial barcode states (%4, %42…) from firing stale lookups.
            lookupTimeout = setTimeout(async () => {
                // Re-read the value at execution time — may have changed while waiting
                const currentRaw = filterQuery.value.trim();
                const currentStripped = prefix ? stripBarcodePrefix(currentRaw, prefix) : currentRaw;
                if (!currentStripped) return;

                // 1. Exact match in current roster
                const found = roster.value.find(b => b.borrower_id === currentStripped);
                if (found) {
                    filterQuery.value = '';
                    emit('borrower-selected', found.borrower_id);
                    return;
                }

                // 2. Not in roster — fetch borrower (may be in a different class)
                try {
                    const borrowerData = await apiClient.get(`/borrowers/${currentStripped}`);
                    if (borrowerData?.class_id && borrowerData.class_id !== selectedClassId.value) {
                        await selectClass(borrowerData.class_id);
                    }
                    filterQuery.value = '';
                    emit('borrower-selected', borrowerData.borrower_id);
                } catch {
                    // ID not found — leave filterQuery so empty-state message shows
                    console.warn('Borrower not found for ID:', currentStripped);
                }
            }, 300);
        };

        const selectStudent = (borrowerId) => {
            filterQuery.value = '';
            emit('borrower-selected', borrowerId);
        };

        // ── Init ──────────────────────────────────────────────────────────────

        // Reload roster when parent signals a checkout/return occurred
        watch(() => props.refreshTick, (newVal, oldVal) => {
            if (newVal !== oldVal && selectedClassId.value) {
                loadRoster(selectedClassId.value);
            }
        });

        onMounted(async () => {
            loadClasses();
            await Vue.nextTick();
            filterInputRef.value?.focus();
        });

        return {
            classes,
            selectedClassId,
            selectedClass,
            roster,
            filteredRoster,
            filterQuery,
            filterInputRef,
            rosterLoading,
            classesLoading,
            stats,
            studentStatus,
            bookCountLabel,
            selectClass,
            selectStudent,
            handleFilterInput,
            t
        };
    },

    template: `
        <div class="who-panel">

            <!-- ── Header: class selector + filter input ── -->
            <div class="who-panel-header">

                <div class="who-panel-title">{{ t('circulation.who_borrows') }}</div>

                <!-- Class selector -->
                <div v-if="classesLoading" class="text-muted small mb-2">
                    <i class="bi bi-hourglass-split me-1"></i>{{ t('common.loading') }}
                </div>
                <template v-else>
                    <select
                        v-if="classes.length > 0"
                        class="form-select form-select-sm mb-2"
                        :value="selectedClassId"
                        @change="selectClass($event.target.value)"
                    >
                        <option value="" disabled :selected="!selectedClassId">
                            {{ t('circulation.select_class') }}
                        </option>
                        <option v-for="cls in classes" :key="cls.id" :value="cls.id">
                            {{ cls.name }}
                        </option>
                    </select>
                    <div v-else class="text-muted small mb-2">
                        <i class="bi bi-info-circle me-1"></i>{{ t('circulation.no_class_selected') }}
                    </div>
                </template>

                <!-- Filter / scan input — single entry point -->
                <div class="filter-input-wrap mb-1">
                    <i class="bi bi-search filter-icon"></i>
                    <input
                        ref="filterInputRef"
                        type="text"
                        class="filter-input"
                        :placeholder="t('circulation.filter_or_scan_student')"
                        :value="filterQuery"
                        @input="handleFilterInput($event.target.value)"
                        autocomplete="off"
                    />
                </div>
                <div class="filter-hint">
                    <i class="bi bi-upc-scan me-1"></i>
                    {{ t('circulation.scan_auto_selects') }}
                </div>

                <!-- Stats chips (only when roster is loaded) -->
                <div v-if="roster.length > 0" class="roster-stats mt-2">
                    <span class="stat-chip stat-borrowed">
                        <i class="bi bi-check-circle-fill"></i>
                        {{ t('circulation.stat_borrowed', { count: stats.borrowed }) }}
                    </span>
                    <span v-if="stats.overdue > 0" class="stat-chip stat-overdue">
                        <i class="bi bi-clock-fill"></i>
                        {{ t('circulation.stat_overdue', { count: stats.overdue }) }}
                    </span>
                    <span class="stat-chip stat-none">
                        <i class="bi bi-dash-circle"></i>
                        {{ t('circulation.stat_not_yet', { count: stats.notYet }) }}
                    </span>
                </div>

            </div><!-- /who-panel-header -->

            <!-- ── Scrollable roster ── -->
            <div class="roster-scroll">

                <!-- Loading -->
                <div v-if="rosterLoading" class="roster-placeholder">
                    <i class="bi bi-hourglass-split fs-4 mb-2"></i>
                    {{ t('common.loading') }}
                </div>

                <!-- No class selected -->
                <div v-else-if="!selectedClassId" class="roster-placeholder">
                    <i class="bi bi-diagram-3 fs-4 mb-2"></i>
                    {{ t('circulation.no_class_selected') }}
                </div>

                <!-- Student rows -->
                <template v-else>
                    <div
                        v-for="borrower in filteredRoster"
                        :key="borrower.id"
                        class="student-row"
                        :class="{ selected: borrower.borrower_id === selectedBorrowerId }"
                        @click="selectStudent(borrower.borrower_id)"
                    >
                        <span
                            class="status-dot"
                            :class="{
                                'dot-orange': studentStatus(borrower) === 'overdue',
                                'dot-green':  studentStatus(borrower) === 'borrowed',
                                'dot-grey':   studentStatus(borrower) === 'none'
                            }"
                        ></span>
                        <span class="s-name">{{ borrower.full_name }}</span>
                        <span
                            class="s-badge"
                            :class="{
                                'badge-overdue':  studentStatus(borrower) === 'overdue',
                                'badge-borrowed': studentStatus(borrower) === 'borrowed',
                                'badge-none':     studentStatus(borrower) === 'none'
                            }"
                        >
                            <template v-if="studentStatus(borrower) === 'overdue'">
                                {{ t('circulation.overdue_label') }}
                            </template>
                            <template v-else-if="studentStatus(borrower) === 'borrowed'">
                                {{ bookCountLabel(borrower) }}
                            </template>
                            <template v-else>
                                {{ t('circulation.not_yet_borrowed') }}
                            </template>
                        </span>
                    </div>

                    <!-- Empty after filter -->
                    <div v-if="filteredRoster.length === 0 && filterQuery" class="roster-placeholder">
                        <i class="bi bi-search fs-4 mb-2"></i>
                        {{ t('circulation.no_students_found') }}
                    </div>
                </template>

            </div><!-- /roster-scroll -->

            <!-- ── Legend ── -->
            <div v-if="roster.length > 0" class="roster-legend">
                <span class="legend-item">
                    <span class="legend-dot dot-green"></span>
                    {{ t('circulation.has_borrowed') }}
                </span>
                <span class="legend-item">
                    <span class="legend-dot dot-orange"></span>
                    {{ t('circulation.overdue_label') }}
                </span>
                <span class="legend-item">
                    <span class="legend-dot dot-grey"></span>
                    {{ t('circulation.not_yet_borrowed') }}
                </span>
            </div>

        </div><!-- /who-panel -->
    `
});
