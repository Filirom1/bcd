import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import ActiveLoansReport from '../../../../src/bcd_web_vue/js/components/reports/ActiveLoansReport.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockResolvedValue([
        {
            circulation_id: 1,
            borrower_id: 'B-101',
            borrower_name: 'Amira Benali',
            bibliographic_record_id: 9,
            title: 'Le Petit Prince',
            class_name: 'CM2',
            checkout_date: '2030-01-01',
            due_date: '2030-01-10',
            days_until_due: 3,
            is_overdue: false
        },
        {
            circulation_id: 2,
            borrower_id: 'B-102',
            borrower_name: 'Louis Martin',
            bibliographic_record_id: 10,
            title: 'Matilda',
            class_name: null,
            checkout_date: '2030-01-01',
            due_date: '2029-12-20',
            days_until_due: -12,
            is_overdue: true
        }
    ]);
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('ActiveLoansReport', () => {
    it('groups active loans by class and maps due-date badges', async () => {
        const print = vi.spyOn(window, 'print').mockImplementation(() => {});
        const wrapper = mount(ActiveLoansReport, {
            global: {
                stubs: { ReportHeader: true, ReportFilters: true, DataTable: true }
            }
        });
        await flushPromises();

        expect(wrapper.vm.groupedData).toEqual({
            CM2: [expect.objectContaining({ borrower_name: 'Amira Benali' })],
            'reports.activeLoans.noClass': [expect.objectContaining({ borrower_name: 'Louis Martin' })]
        });
        expect(wrapper.vm.getDaysUntilDueBadge(-1, true)).toBe('bg-danger');
        expect(wrapper.vm.getDaysUntilDueBadge(2, false)).toBe('bg-warning text-dark');
        expect(wrapper.vm.getDaysUntilDueBadge(8, false)).toBe('bg-success');

        wrapper.vm.printReport();
        expect(print).toHaveBeenCalledTimes(1);
    });
});
