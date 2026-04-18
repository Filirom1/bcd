/**
 * Reusable Report Composable
 * Handles data fetching, filtering, and state for all reports
 */

const { ref, computed } = Vue;
import { apiClient } from '../api/client.js';

export function useReport(reportType) {
    const data = ref([]);
    const loading = ref(false);
    const period = ref('year');
    const limit = ref(10);
    const classFilter = ref('');
    const mediumTypeFilter = ref('');

    const loadReport = async () => {
        loading.value = true;
        try {
                const params = {};
            // Only add non-empty filter values
            if (period.value) params.period = period.value;
            if (limit.value) params.limit = limit.value;
            if (classFilter.value && classFilter.value !== '') params.class_name = classFilter.value;
            if (mediumTypeFilter.value && mediumTypeFilter.value !== '') params.medium_type = mediumTypeFilter.value;

            const response = await apiClient.get(`/reports/${reportType}`, params);
            // Different report types return data in different fields
            data.value = response.data || response.items || response.titles || [];
        } catch (error) {
            console.error(`Error loading ${reportType} report:`, error);
            data.value = [];
        } finally {
            loading.value = false;
        }
    };

    const printReport = () => window.print();

    return {
        data,
        loading,
        period,
        limit,
        classFilter,
        mediumTypeFilter,
        loadReport,
        printReport
    };
}
