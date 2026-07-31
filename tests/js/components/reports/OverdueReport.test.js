import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import OverdueReport from '../../../../src/bcd_web_vue/js/components/reports/OverdueReport.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mockOverdueResponse = {
    data: [
        { borrower_id: 'B-101', borrower_name: 'Amira Benali', borrower_class: 'CP', title: 'Stuart Little', due_date: '2030-01-10', days_overdue: 10, record_id: 1, item_id: 'I-001' }
    ]
};

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
        if (endpoint === '/reports/overdue') {
            return mockOverdueResponse;
        }
        return [];
    });
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('OverdueReport', () => {
    it('loads overdue data and groups it by class', async () => {
        const wrapper = mount(OverdueReport, {
            global: {
                stubs: {
                    ReportHeader: true,
                    ReportFilters: true,
                    DataTable: true
                }
            }
        });
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.groupedData).toEqual({
            'CP': [expect.objectContaining({ borrower_name: 'Amira Benali', title: 'Stuart Little' })]
        });
    });
});
