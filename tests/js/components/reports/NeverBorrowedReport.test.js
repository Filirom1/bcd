import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import NeverBorrowedReport from '../../../../src/bcd_web_vue/js/components/reports/NeverBorrowedReport.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mockItems = [
    { item_id: 'I-101', title: 'Never Borrowed Book', acquisition_date: '2020-01-01', checkout_count: 0, publication_year: 2018 }
];

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
        if (endpoint === '/inventory/items/search') {
            return { items: mockItems, total: 1 };
        }
        return [];
    });
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('NeverBorrowedReport', () => {
    it('loads weeding data and displays items', async () => {
        const wrapper = mount(NeverBorrowedReport, {
            global: {
                stubs: {
                    ReportHeader: true,
                    DataTable: true,
                    Pagination: true,
                    TauxRotationPanel: true
                }
            }
        });
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.allItems).toHaveLength(1);
        expect(wrapper.vm.allItems[0].title).toBe('Never Borrowed Book');
    });
});
