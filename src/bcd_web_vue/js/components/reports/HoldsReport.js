/**
 * Holds Report Component
 * Shows active holds/reservations with status filtering
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import { useReport } from '../../composables/useReport.js';
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import ReportHeader from '../ui/ReportHeader.js';
import ReportFilters from './ReportFilters.js';
import DataTable from '../ui/DataTable.js';

export default defineComponent({
    name: 'HoldsReport',

    components: {
        ReportHeader,
        ReportFilters,
        DataTable
    },

    setup() {
        const { t, d } = useI18n();
        const { data, loading, classFilter, loadReport, printReport } = useReport('holds');
        const { openBorrower, openRecord } = useGlobalModal();

        // Define table columns
        const columns = computed(() => [
            { key: 'borrower_name', label: t('reports.holds.borrower') },
            { key: 'class_name', label: t('reports.holds.class') },
            { key: 'title', label: t('reports.holds.title_book') },
            { key: 'status', label: t('reports.holds.status') },
            { key: 'queue_position', label: t('reports.holds.queue') },
            { key: 'expiration_date', label: t('reports.holds.expiration') }
        ]);

        // Get badge class for status
        const getStatusBadgeClass = (status) => {
            const badgeMap = {
                'waiting': 'bg-primary',
                'ready': 'bg-success',
                'expired': 'bg-danger',
                'fulfilled': 'bg-secondary',
                'cancelled': 'bg-secondary'
            };
            return badgeMap[status] || 'bg-secondary';
        };

        // Get status label
        const getStatusLabel = (status) => {
            const labelMap = {
                'waiting': t('reports.holds.status_waiting'),
                'ready': t('reports.holds.status_ready'),
                'expired': t('reports.holds.status_expired'),
                'fulfilled': t('reports.holds.status_fulfilled'),
                'cancelled': t('reports.holds.status_cancelled')
            };
            return labelMap[status] || status;
        };

        loadReport();

        return {
            t,
            d,
            columns,
            data,
            loading,
            classFilter,
            loadReport,
            printReport,
            getStatusBadgeClass,
            getStatusLabel,
            openBorrower,
            openRecord
        };
    },

    template: `
        <div>
            <report-header
                :title="t('reports.holds.title')"
                @print="printReport"
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

            <div v-else-if="data.length === 0" class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                {{ t('reports.holds.noItems') }}
            </div>

            <div v-else class="card">
                <div class="card-body p-0">
                    <data-table
                        :columns="columns"
                        :rows="data"
                        row-key="hold_id"
                        bare
                    >
                        <template #row="{ row: item }">
                            <td>
                                <a href="#" @click.prevent="openBorrower(item.borrower_id)" class="link-entity fw-bold">
                                    {{ item.borrower_name }}
                                </a>
                            </td>
                            <td>{{ item.class_name || '-' }}</td>
                            <td>
                                <a href="#" @click.prevent="openRecord(item.bibliographic_record_id)" class="link-entity fw-bold">{{ item.title }}</a>
                                <div v-if="item.authors" class="text-muted small">{{ item.authors }}</div>
                            </td>
                            <td>
                                <span class="badge" :class="getStatusBadgeClass(item.status)">
                                    {{ getStatusLabel(item.status) }}
                                </span>
                            </td>
                            <td class="text-center">
                                <span v-if="item.status === 'waiting'" class="badge bg-light text-dark">
                                    #{{ item.queue_position }}
                                </span>
                                <span v-else>-</span>
                            </td>
                            <td>
                                <span v-if="item.expiration_date">
                                    {{ d(new Date(item.expiration_date), 'short') }}
                                    <small v-if="item.days_until_expiration !== undefined" class="ms-1"
                                        :class="item.days_until_expiration < 0 ? 'text-danger' : 'text-muted'">
                                        ({{ item.days_until_expiration < 0 ? 'expiré' : item.days_until_expiration + 'j' }})
                                    </small>
                                </span>
                                <span v-else>-</span>
                            </td>
                        </template>
                    </data-table>
                </div>
            </div>
        </div>
    `
});
