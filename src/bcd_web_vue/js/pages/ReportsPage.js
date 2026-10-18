/**
 * Reports Page Component
 * Container with tabs for three report types
 */

const { defineComponent, ref, watch } = Vue;
const { useRoute } = VueRouter;
import OverdueReport from '../components/reports/OverdueReport.js';
import MostBorrowedReport from '../components/reports/MostBorrowedReport.js';
import CollectionReport from '../components/reports/CollectionReport.js';
import HoldsReport from '../components/reports/HoldsReport.js';
import ActiveLoansReport from '../components/reports/ActiveLoansReport.js';

export default defineComponent({
    name: 'ReportsPage',

    components: {
        OverdueReport,
        MostBorrowedReport,
        CollectionReport,
        HoldsReport,
        ActiveLoansReport
    },

    setup() {
        const route = useRoute();
        const activeTab = ref(route.params.type || 'overdue');

        // Sync with route changes
        watch(() => route.params.type, (newType) => {
            if (newType && newType !== activeTab.value) {
                activeTab.value = newType;
            }
        });

        return {
            activeTab
        };
    },

    template: `
        <div>
            <!-- Report Content -->
            <overdue-report v-if="activeTab === 'overdue'" />
            <most-borrowed-report v-else-if="activeTab === 'most-borrowed'" />
            <collection-report v-else-if="activeTab === 'never-borrowed'" />
            <holds-report v-else-if="activeTab === 'holds'" />
            <active-loans-report v-else-if="activeTab === 'active-loans'" />
        </div>
    `
});
