import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import HoldsReport from '../../../../src/bcd_web_vue/js/components/reports/HoldsReport.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockResolvedValue([
        {
            hold_id: 1,
            borrower_id: 'B-101',
            borrower_name: 'Amira Benali',
            class_name: 'CM2',
            bibliographic_record_id: 9,
            title: 'Le Petit Prince',
            status: 'waiting',
            queue_position: 2,
            expiration_date: '2030-01-15',
            days_until_expiration: 5
        },
        {
            hold_id: 2,
            borrower_id: 'B-102',
            borrower_name: 'Louis Martin',
            class_name: null,
            bibliographic_record_id: 10,
            title: 'Matilda',
            status: 'expired',
            queue_position: null,
            expiration_date: null
        }
    ]);
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('HoldsReport', () => {
    it('loads holds, maps statuses, filters, and delegates printing', async () => {
        const print = vi.spyOn(window, 'print').mockImplementation(() => {});
        const wrapper = mount(HoldsReport, {
            global: {
                stubs: { ReportHeader: true, ReportFilters: true, DataTable: true }
            }
        });
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.data).toHaveLength(2);
        expect(wrapper.vm.columns.map(column => column.key)).toEqual([
            'borrower_name', 'class_name', 'title', 'status', 'queue_position', 'expiration_date'
        ]);
        expect(wrapper.vm.getStatusBadgeClass('waiting')).toBe('bg-primary');
        expect(wrapper.vm.getStatusBadgeClass('unknown')).toBe('bg-secondary');
        expect(wrapper.vm.getStatusLabel('expired')).toBe('reports.holds.status_expired');
        expect(wrapper.vm.getStatusLabel('unknown')).toBe('unknown');

        wrapper.vm.classFilter = 'CM2';
        await wrapper.vm.loadReport();
        expect(apiClient.get).toHaveBeenLastCalledWith('/reports/holds', {
            period: 'year', limit: 10, class_name: 'CM2'
        });

        wrapper.vm.printReport();
        expect(print).toHaveBeenCalledTimes(1);
    });
});
