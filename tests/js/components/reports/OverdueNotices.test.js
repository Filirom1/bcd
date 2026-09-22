import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import OverdueNotices from '../../../../src/bcd_web_vue/js/components/reports/OverdueNotices.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

beforeEach(() => {
    vi.spyOn(window, 'print').mockImplementation(() => {});
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('OverdueNotices', () => {
    it('groups notices by class and borrower and prints after loading', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue([
            {
                borrower_id: 'B-1', borrower_name: 'Amira', borrower_class: 'CM2',
                item_id: 'I-1', title: 'Book 1', checkout_date: '2030-01-01',
                due_date: '2030-01-10', days_overdue: 4
            },
            {
                borrower_id: 'B-1', borrower_name: 'Amira', borrower_class: 'CM2',
                item_id: 'I-2', title: 'Book 2', checkout_date: '2030-01-02',
                due_date: '2030-01-11', days_overdue: 3
            },
            {
                borrower_id: 'B-2', borrower_name: 'Louis', class_name: null,
                item_id: 'I-3', title: 'Book 3', checkout_date: '2030-01-03',
                due_date: '2030-01-12', days_overdue: 2
            }
        ]);
        const wrapper = mount(OverdueNotices);
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.error).toBe(null);
        expect(wrapper.vm.groupedData.CM2).toHaveLength(1);
        expect(wrapper.vm.groupedData.CM2[0].books).toHaveLength(2);
        expect(wrapper.vm.groupedData['reports.overdue.noClass'][0].name).toBe('Louis');
        expect(window.print).toHaveBeenCalledTimes(1);

        await wrapper.vm.doPrint();
        expect(window.print).toHaveBeenCalledTimes(2);
    });

    it('displays API failures without attempting to print', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('offline'));
        const wrapper = mount(OverdueNotices);
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.error).toBe('offline');
        expect(window.print).not.toHaveBeenCalled();
    });
});
