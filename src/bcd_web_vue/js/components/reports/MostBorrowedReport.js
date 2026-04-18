/**
 * Most Borrowed Report Component
 * Shows ranking of most borrowed items with visual bars
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import { useReport } from '../../composables/useReport.js';
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import { useAppState } from '../../composables/useAppState.js';
import ReportHeader from '../ui/ReportHeader.js';
import ReportFilters from './ReportFilters.js';
import DataTable from '../ui/DataTable.js';

export default defineComponent({
    name: 'MostBorrowedReport',

    components: {
        ReportHeader,
        ReportFilters,
        DataTable
    },

    setup() {
        const { t } = useI18n();
        const { settings } = useAppState();
        const { data, loading, period, limit, mediumTypeFilter, loadReport, printReport } = useReport('most-borrowed');
        const { openRecord } = useGlobalModal();

        const mediumTypeOptions = computed(() => {
            const types = (settings.value?.catalog_medium_types || '')
                .split(',').map(s => s.trim()).filter(Boolean);
            return types;
        });

        // Define table columns
        const columns = computed(() => [
            { key: 'rank', label: t('reports.mostBorrowed.rank'), width: '60px' },
            { key: 'title', label: t('reports.mostBorrowed.bookTitle') },
            { key: 'author', label: t('catalog.author_publisher') },
            { key: 'checkout_count', label: t('reports.mostBorrowed.checkouts'), width: '300px' }
        ]);

        // Calculate max for visual bars
        const maxCheckouts = computed(() => {
            return data.value.length > 0 ? Math.max(...data.value.map(item => item.checkout_count)) : 1;
        });

        const getBarWidth = (count) => {
            return (count / maxCheckouts.value) * 100 + '%';
        };

        loadReport();

        return {
            t,
            columns,
            data,
            loading,
            period,
            limit,
            mediumTypeFilter,
            mediumTypeOptions,
            maxCheckouts,
            getBarWidth,
            loadReport,
            printReport,
            openRecord
        };
    },

    template: `
        <div>
            <report-header
                :title="t('reports.mostBorrowed.title')"
                @print="printReport"
            />

            <report-filters
                show-period
                show-limit
                show-medium-type
                v-model:period="period"
                v-model:limit="limit"
                v-model:medium-type-filter="mediumTypeFilter"
                :medium-type-options="mediumTypeOptions"
                @filter-change="loadReport"
            />

            <data-table
                :columns="columns"
                :rows="data"
                :loading="loading"
                :empty-message="t('reports.mostBorrowed.noItems')"
                row-key="bibliographic_record_id"
                card
            >
                <template #row="{ row: item }">
                    <td class="text-center">
                        <span v-if="data.indexOf(item) < 3" class="badge" :class="{
                            'bg-warning': data.indexOf(item) === 0,
                            'bg-secondary': data.indexOf(item) === 1,
                            'bg-info': data.indexOf(item) === 2
                        }">
                            {{ data.indexOf(item) + 1 }}
                        </span>
                        <span v-else class="text-muted">{{ data.indexOf(item) + 1 }}</span>
                    </td>
                    <td>
                        <a href="#" @click.prevent="openRecord(item.bibliographic_record_id)" class="link-entity fw-bold">
                            {{ item.title }}
                        </a>
                    </td>
                    <td>{{ item.author || item.publisher || '\u2014' }}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="progress flex-grow-1 me-3" style="height: 20px">
                                <div
                                    class="progress-bar bg-primary"
                                    :style="{ width: getBarWidth(item.checkout_count) }"
                                >
                                    {{ item.checkout_count }}
                                </div>
                            </div>
                        </div>
                    </td>
                </template>
            </data-table>
        </div>
    `
});
