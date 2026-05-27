/**
 * Reports Page Component
 * Container with tabs for three report types
 */

const { defineComponent, ref, watch } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;
import OverdueReport from '../components/reports/OverdueReport.js';
import MostBorrowedReport from '../components/reports/MostBorrowedReport.js';
import CollectionReport from '../components/reports/CollectionReport.js';
import HoldsReport from '../components/reports/HoldsReport.js';
import ActiveLoansReport from '../components/reports/ActiveLoansReport.js';
import HelpPanel from '../components/ui/HelpPanel.js';

export default defineComponent({
    name: 'ReportsPage',

    components: {
        OverdueReport,
        MostBorrowedReport,
        CollectionReport,
        HoldsReport,
        ActiveLoansReport,
        HelpPanel
    },

    setup() {
        const { t } = useI18n();
        const route = useRoute();
        const activeTab = ref(route.params.type || 'overdue');

        // Sync with route changes
        watch(() => route.params.type, (newType) => {
            if (newType && newType !== activeTab.value) {
                activeTab.value = newType;
            }
        });

        return {
            t,
            activeTab
        };
    },

    template: `
        <div class="container-fluid">
            <div class="page-header">
                <h1 class="page-title">
                    <i class="bi bi-bar-chart me-2"></i>
                    {{ t('navigation.reports') }}
                </h1>
                <div class="d-flex gap-2">
                    <help-panel section="reports" />
                </div>
            </div>
            <!-- Report Content -->
            <overdue-report v-if="activeTab === 'overdue'" />
            <most-borrowed-report v-else-if="activeTab === 'most-borrowed'" />
            <collection-report v-else-if="activeTab === 'never-borrowed'" />
            <holds-report v-else-if="activeTab === 'holds'" />
            <active-loans-report v-else-if="activeTab === 'active-loans'" />
        </div>
    `
});
