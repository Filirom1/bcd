/**
 * Overdue Report Component
 * Shows overdue items grouped by class
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import { useReport } from '../../composables/useReport.js';
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import ReportHeader from '../ui/ReportHeader.js';
import ReportFilters from './ReportFilters.js';
import DataTable from '../ui/DataTable.js';

export default defineComponent({
    name: 'OverdueReport',

    components: {
        ReportHeader,
        ReportFilters,
        DataTable
    },

    setup() {
        const { t, d } = useI18n();
        const { data, loading, classFilter, loadReport, printReport } = useReport('overdue');
        const { openRecord, openBorrower } = useGlobalModal();

        // Define table columns
        const columns = computed(() => [
            { key: 'borrower_name', label: t('reports.overdue.borrower') },
            { key: 'title', label: t('reports.overdue.item') },
            { key: 'due_date', label: t('reports.overdue.dueDate') },
            { key: 'days_overdue', label: t('reports.overdue.daysOverdue') }
        ]);

        // Group items by class
        const groupedData = computed(() => {
            const groups = {};
            data.value.forEach(item => {
                const className = item.borrower_class || item.class_name || t('reports.overdue.noClass');
                if (!groups[className]) groups[className] = [];
                groups[className].push(item);
            });
            return groups;
        });

        const printNotices = () => window.open('/#/reports/overdue/notices', '_blank');

        loadReport();

        return {
            t,
            d,
            columns,
            loading,
            classFilter,
            groupedData,
            loadReport,
            printReport,
            printNotices,
            openRecord,
            openBorrower
        };
    },

    template: `
        <div>
            <report-header
                :title="t('reports.overdue.title')"
                :show-notices="true"
                @print="printReport"
                @print-notices="printNotices"
            />

            <report-filters
                show-class
                v-model:class-filter="classFilter"
                @filter-change="loadReport"
            />

            <div v-if="loading" class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">{{ t('common.loading') }}</span>
                </div>
            </div>

            <div v-else-if="Object.keys(groupedData).length === 0" class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                {{ t('reports.overdue.noItems') }}
            </div>

            <div v-else>
                <div v-for="(items, className) in groupedData" :key="className" class="card mb-3 print-page-break">
                    <div class="card-header bg-light">
                        <h5 class="mb-0">
                            {{ className }}
                            <span class="badge bg-danger ms-2">{{ items.length }}</span>
                        </h5>
                    </div>
                    <div class="card-body p-0">
                        <data-table
                            :columns="columns"
                            :rows="items"
                            row-key="item_id"
                            bare
                        >
                            <template #row="{ row: item }">
                                <td>
                                    <a href="#" @click.prevent="openBorrower(item.borrower_id)" class="link-entity fw-bold">
                                        {{ item.borrower_name }}
                                    </a>
                                </td>
                                <td>
                                    <a href="#" @click.prevent="openRecord(item.record_id)" class="link-entity fw-bold">
                                        {{ item.title }}
                                    </a>
                                </td>
                                <td>{{ d(new Date(item.due_date), 'short') }}</td>
                                <td>
                                    <span class="badge bg-danger">
                                        {{ item.days_overdue }} {{ t('reports.overdue.days') }}
                                    </span>
                                </td>
                            </template>
                        </data-table>
                    </div>
                </div>
            </div>
        </div>
    `
});
