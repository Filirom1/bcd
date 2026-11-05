// @ts-check
/**
 * Reusable Report Composable
 * Handles data fetching and class filtering for the loan reports.
 */

const { ref, computed } = Vue;
import { apiClient } from '../api/client.js';
import { normalizeCollection } from '../models/pagination.js';
import { usePagination } from './usePagination.js';

const REPORT_PAGE_SIZE = 500;

/**
 * @param {string} reportType - API report endpoint segment (e.g. 'active-loans')
 */
export function useReport(reportType) {
    /** @type {import('vue').Ref<any[]>} */
    const data = ref([]);
    const loading = ref(false);
    const classFilter = ref('');
    const {
        currentPage,
        pageSize,
        totalItems,
        totalPages,
        offset,
        setTotalItems,
        goToPage,
        setPageSize
    } = usePagination({ pageSize: 10 });
    const paginatedData = computed(() => data.value.slice(offset.value, offset.value + pageSize.value));
    let latestRequestId = 0;

    const loadReport = async () => {
        const requestId = ++latestRequestId;
        currentPage.value = 1;
        loading.value = true;
        try {
            const baseParams = {
                limit: REPORT_PAGE_SIZE,
                ...(classFilter.value ? { class_name: classFilter.value } : {})
            };

            const items = [];
            let offset = 0;
            let totalItems = Infinity;

            do {
                const response = await apiClient.get(`/reports/${reportType}`, {
                    ...baseParams,
                    offset
                });
                const normalized = normalizeCollection(response);
                items.push(...normalized.items);
                totalItems = normalized.pagination.total_items;

                // Avoid an infinite loop if an API response has inconsistent pagination metadata.
                if (normalized.items.length === 0) break;
                offset += normalized.items.length;
            } while (offset < totalItems);

            if (requestId === latestRequestId) {
                data.value = items;
                setTotalItems(items.length);
            }
        } catch (error) {
            console.error(`Error loading ${reportType} report:`, error);
            if (requestId === latestRequestId) {
                data.value = [];
                setTotalItems(0);
            }
        } finally {
            if (requestId === latestRequestId) loading.value = false;
        }
    };

    const printReport = () => window.print();

    return {
        data,
        loading,
        classFilter,
        paginatedData,
        currentPage,
        pageSize,
        totalItems,
        totalPages,
        loadReport,
        printReport,
        goToPage,
        setPageSize
    };
}
