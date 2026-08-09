import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import MostBorrowedReport from '../../../../src/bcd_web_vue/js/components/reports/MostBorrowedReport.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mockMostBorrowedResponse = {
    titles: [
        { record_id: 1, title: 'The Little Prince', checkout_count: 42, total_copies: 2, medium_type: 'Book' }
    ]
};

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
        if (endpoint === '/reports/most-borrowed') {
            return mockMostBorrowedResponse;
        }
        return [];
    });
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('MostBorrowedReport', () => {
    it('loads most-borrowed data and adapts to investment methods', async () => {
        const wrapper = mount(MostBorrowedReport, {
            global: {
                stubs: {
                    ReportHeader: true,
                    Pagination: true,
                    BreakdownPanel: true,
                    FilterChips: true,
                    TauxRotationPanel: true,
                    PubYearPanel: true
                }
            }
        });
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.allData).toHaveLength(1);
        expect(wrapper.vm.allData[0].title).toBe('The Little Prince');
        // Check computed adaptation: taux_rotation = 42 / 2 = 21
        expect(wrapper.vm.allData[0].taux_rotation).toBe(21);
    });
});
