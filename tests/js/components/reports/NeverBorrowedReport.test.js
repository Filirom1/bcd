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

    it('covers all CREW methods, filters, sorting and column preferences', async () => {
        const now = new Date().getFullYear();
        const items = [
            { item_id: 'I-1', bibliographic_record_id: 1, title: 'Old damaged', age_days: 1200, condition: 'damaged', publication_year: now - 12, medium_type: 'Documentaire', period_loan_count: 0 },
            { item_id: 'I-2', bibliographic_record_id: 1, title: 'Old damaged', age_days: 1200, condition: 'damaged', publication_year: now - 12, medium_type: 'Documentaire', period_loan_count: 0 },
            { item_id: 'I-3', bibliographic_record_id: 1, title: 'Old damaged', age_days: 1200, condition: 'damaged', publication_year: now - 12, medium_type: 'Documentaire', period_loan_count: 1 },
            { item_id: 'I-4', bibliographic_record_id: 2, title: 'Borrowed', age_days: 10, condition: 'good', period_loan_count: 5, last_borrowed_at: '2030-01-01' },
            { item_id: 'I-5', bibliographic_record_id: 3, title: 'Magazine', age_days: 10, condition: 'good', period_loan_count: 0, identifier_type: 'issn' }
        ];
        vi.mocked(apiClient.get).mockImplementation(async () => ({ items }));
        const print = vi.spyOn(window, 'print').mockImplementation(() => {});
        const wrapper = mount(NeverBorrowedReport, {
            global: { stubs: { ReportHeader: true, DataTable: true, Pagination: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        expect(wrapper.vm.allItems).toHaveLength(4); // never borrowed excludes I-4
        expect(wrapper.vm.allItems[0].crew_score).toBeGreaterThanOrEqual(5);
        expect(wrapper.vm.copiesPerTitle[1]).toBe(3);
        expect(wrapper.vm.tauxMax).toBe(1);

        for (const method of ['low_circulation', 'damaged_old', 'high_score', 'never_inventoried', 'duplicate_low_demand']) {
            wrapper.vm.crewMethod = method;
            if (method === 'duplicate_low_demand') {
                await wrapper.vm.loadReport();
                expect(wrapper.vm.allItems.every(item => item.bibliographic_record_id === 1)).toBe(true);
            } else {
                await wrapper.vm.loadReport();
            }
            expect(wrapper.vm.loading).toBe(false);
        }
        wrapper.vm.filters.level = 'CM2';
        wrapper.vm.filters.target_audience = 'child';
        wrapper.vm.filters.medium_type = 'Livre';
        wrapper.vm.filters.min_age_years = 2;
        wrapper.vm.crewMethod = 'never_borrowed';
        await wrapper.vm.loadReport();
        const lastParams = apiClient.get.mock.calls.at(-1)[1];
        expect(lastParams).toMatchObject({ level: 'CM2', target_audience: 'child', medium_type: 'Livre', no_limit: true });

        wrapper.vm.excludePeriodicals = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.paginatedData.every(item => item.identifier_type !== 'issn')).toBe(true);
        wrapper.vm.excludePeriodicals = false;
        wrapper.vm.tauxRotationFilter = { min: 1, max: 2 };
        await wrapper.vm.$nextTick();
        wrapper.vm.handleSort('title');
        wrapper.vm.handleSort('title');
        expect(wrapper.vm.sortDirection).toBe('asc');
        wrapper.vm.toggleCol('title');
        expect(wrapper.vm.isColVisible('title')).toBe(false);
        wrapper.vm.resetCols();
        expect(wrapper.vm.isColVisible('title')).toBe(true);
        wrapper.vm.printReport();
        expect(print).toHaveBeenCalledTimes(1);
    });
});
