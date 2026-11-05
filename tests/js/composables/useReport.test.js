import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../../src/bcd_web_vue/js/api/client.js';
import { useReport } from '../../../src/bcd_web_vue/js/composables/useReport.js';

afterEach(() => {
    vi.restoreAllMocks();
});

describe('useReport', () => {
    it('loads every page for the all-classes report', async () => {
        const firstPage = Array.from({ length: 500 }, (_, index) => ({ id: index + 1 }));
        vi.spyOn(apiClient, 'get')
            .mockResolvedValueOnce({
                items: firstPage,
                total_active_loans: 501,
                limit: 500,
                offset: 0
            })
            .mockResolvedValueOnce({
                items: [{ id: 501 }],
                total_active_loans: 501,
                limit: 500,
                offset: 500
            });

        const report = useReport('active-loans');
        await report.loadReport();

        expect(apiClient.get).toHaveBeenNthCalledWith(1, '/reports/active-loans', {
            limit: 500,
            offset: 0
        });
        expect(apiClient.get).toHaveBeenNthCalledWith(2, '/reports/active-loans', {
            limit: 500,
            offset: 500
        });
        expect(report.data.value).toHaveLength(501);
        expect(report.totalItems.value).toBe(501);
        expect(report.pageSize.value).toBe(10);
        expect(report.paginatedData.value).toHaveLength(10);
        report.goToPage(2);
        expect(report.paginatedData.value[0].id).toBe(11);
        expect(report.paginatedData.value).toHaveLength(10);
        report.setPageSize(500);
        expect(report.currentPage.value).toBe(1);
        expect(report.paginatedData.value).toHaveLength(500);
        expect(report.loading.value).toBe(false);
    });

    it('applies a selected class and omits the class parameter again for all classes', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            items: [],
            total_active_loans: 0,
            limit: 500,
            offset: 0
        });
        const report = useReport('active-loans');

        report.classFilter.value = 'CM2';
        await report.loadReport();
        expect(get).toHaveBeenLastCalledWith('/reports/active-loans', {
            limit: 500,
            class_name: 'CM2',
            offset: 0
        });

        report.classFilter.value = '';
        await report.loadReport();
        expect(get).toHaveBeenLastCalledWith('/reports/active-loans', {
            limit: 500,
            offset: 0
        });
    });
});
