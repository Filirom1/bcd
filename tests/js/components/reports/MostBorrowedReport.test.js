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

    it('covers investment methods, cross-filters, sorting and persisted columns', async () => {
        const response = {
            titles: [
                { record_id: 1, title: 'Popular book', checkout_count: 40, total_copies: 2, medium_type: 'Book', target_audience: 'child', publication_year: 2020 },
                { record_id: 2, title: 'Rare DVD', checkout_count: 8, total_copies: 1, medium_type: 'DVD', target_audience: 'adult', publication_year: 2010 },
                { record_id: 3, title: 'Many copies', checkout_count: 3, total_copies: 4, medium_type: 'Book', target_audience: 'child', publication_year: 2022 }
            ]
        };
        vi.mocked(apiClient.get).mockResolvedValue(response);
        const print = vi.spyOn(window, 'print').mockImplementation(() => {});
        const wrapper = mount(MostBorrowedReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, BreakdownPanel: true, FilterChips: true, TauxRotationPanel: true, PubYearPanel: true } }
        });
        await flushPromises();

        expect(wrapper.vm.mediumTypeBreakdown).toEqual([
            { value: 'Book', count: 2 }, { value: 'DVD', count: 1 }
        ]);
        expect(wrapper.vm.maxCheckouts).toBe(40);
        expect(wrapper.vm.maxTauxRotation).toBe(20);
        wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.processedData).toHaveLength(2);
        expect(wrapper.vm.activeChips).toContainEqual(expect.objectContaining({ key: 'medium_type' }));
        wrapper.vm.clearFilter('medium_type');
        expect(wrapper.vm.hasActiveFilters).toBe(false);

        for (const method of ['all', 'most_borrowed', 'taux_rotation', 'scarce']) {
            wrapper.vm.investmentMethod = method;
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.processedData.length).toBeGreaterThanOrEqual(1);
        }
        wrapper.vm.investmentMethod = 'taux_rotation';
        wrapper.vm.handleSort('checkout_count');
        expect(wrapper.vm.sortColumn).toBe('checkout_count');
        wrapper.vm.handleSort('title');
        expect(wrapper.vm.sortColumn).toBe('title');
        wrapper.vm.togglePanel('pub_year');
        expect(wrapper.vm.isPanelVisible('pub_year')).toBe(false);
        wrapper.vm.resetPanels();
        expect(wrapper.vm.isPanelVisible('pub_year')).toBe(true);
        wrapper.vm.toggleCol('title');
        expect(wrapper.vm.isColVisible('title')).toBe(false);
        wrapper.vm.resetCols();
        expect(wrapper.vm.isColVisible('title')).toBe(true);
        wrapper.vm.printReport();
        expect(print).toHaveBeenCalledTimes(1);
    });
});
