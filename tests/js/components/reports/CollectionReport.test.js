import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

vi.mock('chart.js', () => {
    class MockChart {
        static instances = [];
        static register = vi.fn();

        constructor(context, config) {
            this.context = context;
            this.config = config;
            this.destroyed = false;
            MockChart.instances.push(this);
        }

        destroy() {
            this.destroyed = true;
        }
    }

    return {
        Chart: MockChart,
        BarController: class {},
        BarElement: class {},
        CategoryScale: class {},
        Legend: class {},
        LinearScale: class {},
        Tooltip: class {}
    };
});

import { Chart } from 'chart.js';
import CollectionReport from '../../../../src/bcd_web_vue/js/components/reports/CollectionReport.js';
import Pagination from '../../../../src/bcd_web_vue/js/components/ui/Pagination.js';
import TauxRotationPanel from '../../../../src/bcd_web_vue/js/components/reports/TauxRotationPanel.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mockCollectionResponse = {
    total_records: 10,
    total_copies: 15,
    lost_copies: 1,
    weeded_copies: 0,
    distribution_by_medium: { 'Book': 14 },
    distribution_by_audience: { 'child': 12 },
    total_count: 15,
    breakdowns: {
        medium_type: [],
        condition: []
    },
    pub_year_histogram: [],
    acq_year_histogram: []
};

const mockWeedingItems = {
    items: [
        { item_id: 'I-101', title: 'Stuart Little', crew_score: 2, condition: 'good', age_days: 300, total_copies: 1, period_loan_count: 0 }
    ],
    total: 1
};

beforeEach(() => {
    Chart.instances.length = 0;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({});
    vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
        if (endpoint === '/reports/collection-stats') {
            return mockCollectionResponse;
        }
        if (endpoint === '/reports/weeding' || endpoint === '/inventory/items/search') {
            return mockWeedingItems;
        }
        return [];
    });
});

afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
});

describe('CollectionReport', () => {
    it('loads collection statistics and sets up visible panels', async () => {
        const wrapper = mount(CollectionReport, {
            global: {
                stubs: {
                    ReportHeader: true,
                    Pagination: true,
                    FilterChips: true,
                    TauxRotationPanel: true
                }
            }
        });
        await flushPromises();

        expect(wrapper.vm.statsLoading).toBe(false);
        expect(wrapper.vm.visiblePanels).toContain('crew_score');
        expect(wrapper.vm.visiblePanels).toContain('medium_type');
    });

    it('toggles panel visibility correctly and persists preference', async () => {
        const wrapper = mount(CollectionReport, {
            global: {
                stubs: {
                    ReportHeader: true,
                    Pagination: true,
                    FilterChips: true,
                    TauxRotationPanel: true
                }
            }
        });
        await flushPromises();

        expect(wrapper.vm.isPanelVisible('crew_score')).toBe(true);

        wrapper.vm.togglePanel('crew_score');
        expect(wrapper.vm.isPanelVisible('crew_score')).toBe(false);
        expect(JSON.parse(localStorage.getItem('bcd_collection_hidden_panels'))).toContain('crew_score');
    });

    it('rebuilds and destroys charts for discontinuous histogram data', async () => {
        const stats = {
            ...mockCollectionResponse,
            total_count: 2,
            breakdowns: { medium_type: [{ value: 'Book', count: 2 }], condition: [] },
            pub_year_histogram: [{ year: 2010, count: 1 }, { year: 2012, count: 1 }],
            acq_year_histogram: [{ year: 2020, count: 2 }]
        };
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') return stats;
            if (endpoint === '/inventory/items/search') return {
                items: [
                    { item_id: 'I-1', bibliographic_record_id: 1, crew_score: 1, circulation_count: 0 },
                    { item_id: 'I-2', bibliographic_record_id: 2, crew_score: 5, circulation_count: 3 }
                ]
            };
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        expect(wrapper.vm.pubYearRange).toEqual({ min: 2010, max: 2012 });
        expect(wrapper.vm.acqYearRange).toEqual({ min: 2020, max: 2020 });
        expect(Chart.instances).toHaveLength(2);

        const firstCharts = [...Chart.instances];
        wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await flushPromises();
        expect(firstCharts.every(chart => chart.destroyed)).toBe(true);
        expect(Chart.instances.length).toBeGreaterThan(2);
        wrapper.unmount();
        expect(Chart.instances.at(-1).destroyed).toBe(true);
    });

    it('reloads API filters but keeps local rotation filters client-side', async () => {
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        const initialCalls = apiClient.get.mock.calls.length;

        wrapper.vm.tauxRotationFilter = { min: 2, max: 4 };
        await wrapper.vm.$nextTick();
        expect(apiClient.get.mock.calls.length).toBe(initialCalls);

        wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await flushPromises();
        expect(apiClient.get).toHaveBeenCalledWith('/reports/collection-stats', expect.objectContaining({ medium_type: 'Book' }));
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining({ medium_type: 'Book' }));
    });

    it('changes CREW methods and sends the corresponding table parameters', async () => {
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        wrapper.vm.crewMethod = 'low_circulation';
        await flushPromises();
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining({
            no_limit: true,
            max_borrows: 2,
            since_date: expect.any(String)
        }));

        wrapper.vm.crewMethod = 'damaged_old';
        await flushPromises();
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining({
            no_limit: true,
            condition: 'damaged',
            acquired_before: expect.any(String)
        }));
    });

    it('sorts null values last, paginates filtered data, and resets every filter', async () => {
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        wrapper.vm.allItems = [
            { item_id: 'I-null', bibliographic_record_id: 1, title: null, crew_score: 1, taux_rotation: 0 },
            { item_id: 'I-book', bibliographic_record_id: 2, title: 'Book', crew_score: 2, taux_rotation: 3 }
        ];
        wrapper.vm.sortColumn = 'title';
        wrapper.vm.sortDirection = 'asc';
        wrapper.vm.tauxRotationFilter = { min: 1, max: null };
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.totalItems).toBe(1);
        expect(wrapper.vm.paginatedData[0].item_id).toBe('I-book');
        wrapper.vm.crossFilters.medium_type = 'Book';
        wrapper.vm.crewScoreFilter = { min: 2, max: 4 };
        wrapper.vm.clearAllFilters();
        expect(wrapper.vm.crossFilters).toEqual({
            medium_type: null, target_audience: null, condition: null,
            pub_year_min: null, pub_year_max: null, acq_year_min: null, acq_year_max: null
        });
        expect(wrapper.vm.tauxRotationFilter).toEqual({ min: null, max: null });
        expect(wrapper.vm.crewScoreFilter).toEqual({ min: null, max: null });
    });

    it.each([
        ['all', {}, []],
        ['never_inventoried', { never_inventoried: true, acquired_before: expect.any(String) }, []],
        ['high_score', {}, [
            { item_id: 'high', bibliographic_record_id: 1, age_days: 1200, condition: 'damaged', medium_type: 'Documentary', publication_year: 2000, period_loan_count: 0 },
            { item_id: 'low', bibliographic_record_id: 2, age_days: 10, condition: 'good', medium_type: 'Book', period_loan_count: 1 }
        ]],
        ['duplicate_low_demand', {}, [
            { item_id: 'single', bibliographic_record_id: 3, period_loan_count: 0 },
            { item_id: 'equal-1', bibliographic_record_id: 4, period_loan_count: 2 },
            { item_id: 'equal-2', bibliographic_record_id: 4, period_loan_count: 2 },
            { item_id: 'equal-3', bibliographic_record_id: 4, period_loan_count: 2 },
            { item_id: 'low-1', bibliographic_record_id: 5, period_loan_count: 1 },
            { item_id: 'low-2', bibliographic_record_id: 5, period_loan_count: 1 },
            { item_id: 'low-3', bibliographic_record_id: 5, period_loan_count: 1 }
        ]]
    ])('builds the %s CREW method query and applies its threshold', async (method, expectedParams, items) => {
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') return mockCollectionResponse;
            if (endpoint === '/inventory/items/search') return items;
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        wrapper.vm.crewMethod = method;
        await flushPromises();

        expect(apiClient.get).toHaveBeenCalledWith('/reports/collection-stats', expect.objectContaining({ crew_method: method }));
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining(expectedParams));
        if (method === 'high_score') {
            expect(wrapper.vm.allItems.map(item => item.item_id)).toEqual(['high']);
            expect(wrapper.vm.allItems[0].crew_score).toBeGreaterThanOrEqual(5);
        }
        if (method === 'duplicate_low_demand') {
            expect(wrapper.vm.allItems.map(item => item.item_id)).toEqual(['low-1', 'low-2', 'low-3']);
        }
    });

    it('uses the low-circulation and damaged-old CREW boundaries', async () => {
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        wrapper.vm.crewMethod = 'low_circulation';
        await flushPromises();
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining({ max_borrows: 2, since_date: expect.any(String) }));
        wrapper.vm.crewMethod = 'damaged_old';
        await flushPromises();
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining({ condition: 'damaged', acquired_before: expect.any(String) }));
    });

    it('combines API cross-filters with local rotation and score filters', async () => {
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        wrapper.vm.tauxRotationFilter = { min: 2, max: 4 };
        wrapper.vm.crewScoreFilter = { min: 4, max: 6 };
        wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await flushPromises();
        // The API reload replaces the collection; local filters are then applied
        // to the freshly loaded page.
        wrapper.vm.allItems = [
            { item_id: 'keep', bibliographic_record_id: 1, crew_score: 5, taux_rotation: 3 },
            { item_id: 'drop', bibliographic_record_id: 2, crew_score: 2, taux_rotation: 1 }
        ];
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.totalItems).toBe(1);
        expect(wrapper.vm.paginatedData[0].item_id).toBe('keep');
        expect(apiClient.get).toHaveBeenCalledWith('/reports/collection-stats', expect.objectContaining({ medium_type: 'Book' }));
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining({ medium_type: 'Book' }));
        expect(wrapper.vm.activeChips.map(chip => chip.key)).toEqual(expect.arrayContaining(['medium_type', 'taux_rotation', 'crew_score']));
    });

    it('resets filters when changing method and supports all API filter dimensions', async () => {
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        wrapper.vm.crossFilters = {
            medium_type: 'Book', target_audience: 'child', condition: 'good',
            pub_year_min: 2010, pub_year_max: 2020, acq_year_min: 2015, acq_year_max: 2022
        };
        await flushPromises();
        wrapper.vm.tauxRotationFilter = { min: 1, max: 2 };
        wrapper.vm.crewScoreFilter = { min: 2, max: 4 };
        wrapper.vm.crewMethod = 'all';
        await flushPromises();

        expect(wrapper.vm.hasActiveFilters).toBe(false);
        expect(wrapper.vm.tauxRotationFilter).toEqual({ min: null, max: null });
        expect(wrapper.vm.crewScoreFilter).toEqual({ min: null, max: null });
        expect(apiClient.get).toHaveBeenCalledWith('/reports/collection-stats', expect.objectContaining({ crew_method: 'all' }));
        wrapper.vm.crossFilters = {
            medium_type: 'DVD', target_audience: 'adult', condition: 'damaged',
            pub_year_min: 2001, pub_year_max: 2002, acq_year_min: 2011, acq_year_max: 2012
        };
        await flushPromises();
        expect(apiClient.get).toHaveBeenCalledWith('/inventory/items/search', expect.objectContaining({
            medium_type: 'DVD', target_audience: 'adult', condition: 'damaged',
            publication_year_min: 2001, publication_year_max: 2002,
            acquired_after: '2011-01-01', acquired_before: '2012-12-31'
        }));
    });

    it('handles empty, single-year and identical slider ranges', async () => {
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') {
                return { ...mockCollectionResponse, pub_year_histogram: [], acq_year_histogram: [] };
            }
            if (endpoint === '/inventory/items/search') return [];
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        expect(wrapper.vm.scoreHistogram).toEqual([]);
        expect(wrapper.vm.pubYearRange.max).toBe(new Date().getFullYear());
        expect(wrapper.vm.acqYearRange.max).toBe(new Date().getFullYear());
        expect(wrapper.vm.scoreFillStyle).toEqual(expect.any(Object));
        wrapper.vm.sliderScoreMin = wrapper.vm.sliderScoreMax;
        wrapper.vm.clampScoreMin();
        expect(wrapper.vm.sliderScoreMin).toBeLessThan(wrapper.vm.sliderScoreMax);
        wrapper.vm.sliderScoreMax = wrapper.vm.sliderScoreMin;
        wrapper.vm.clampScoreMax();
        expect(wrapper.vm.sliderScoreMax).toBeGreaterThan(wrapper.vm.sliderScoreMin);
        wrapper.vm.sliderPubMin = wrapper.vm.pubYearRange.min;
        wrapper.vm.sliderPubMax = wrapper.vm.pubYearRange.min;
        wrapper.vm.clampPubMax();
        expect(wrapper.vm.sliderPubMax).toBeGreaterThan(wrapper.vm.sliderPubMin);
        wrapper.vm.applyPubRange();
        expect(wrapper.vm.crossFilters.pub_year_max).not.toBe(null);
    });

    it('paginates after local filtering and sorts nulls in both directions', async () => {
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        wrapper.vm.allItems = Array.from({ length: 3 }, (_, i) => ({
            item_id: `I-${i}`, bibliographic_record_id: i, title: i === 1 ? null : `Title ${i}`, crew_score: i
        }));
        wrapper.vm.setPageSize(1);
        wrapper.vm.sortColumn = 'title';
        wrapper.vm.sortDirection = 'asc';
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.totalItems).toBe(3);
        expect(wrapper.vm.paginatedData[0].title).toBe('Title 0');
        wrapper.vm.goToPage(2);
        expect(wrapper.vm.paginatedData[0].title).toBe('Title 2');
        wrapper.vm.sortDirection = 'desc';
        await wrapper.vm.$nextTick();
        // Page 2 still contains the second non-null title after resorting.
        expect(wrapper.vm.paginatedData[0].title).toBe('Title 0');
        wrapper.vm.goToPage(1);
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.paginatedData[0].title).toBe('Title 2');
    });

    it('restores valid preferences and ignores invalid JSON preferences', async () => {
        localStorage.setItem('bcd_collection_hidden_panels', JSON.stringify(['condition']));
        localStorage.setItem('bcd_crew_cols', JSON.stringify(['title', 'not-a-column']));
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        expect(wrapper.vm.isPanelVisible('condition')).toBe(false);
        expect(wrapper.vm.visibleCols).toEqual(['title']);

        wrapper.unmount();
        localStorage.setItem('bcd_collection_hidden_panels', '{broken');
        localStorage.setItem('bcd_crew_cols', '{broken');
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const second = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        expect(second.vm.visiblePanels).toContain('condition');
        expect(second.vm.visibleCols).toContain('title');
        expect(consoleSpy).toHaveBeenCalled();
    });

    it('shows notification errors for statistics and table requests', async () => {
        const error = new Error('offline');
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') throw error;
            if (endpoint === '/inventory/items/search') throw error;
            return [];
        });
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        expect(wrapper.vm.statsLoading).toBe(false);
        expect(wrapper.vm.tableLoading).toBe(false);
        expect(wrapper.vm.stats).toBeNull();
        expect(consoleSpy).toHaveBeenCalled();
    });

    it('clicks audience and condition breakdowns, toggles them off, and combines filters', async () => {
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') {
                return {
                    ...mockCollectionResponse,
                    breakdowns: {
                        medium_type: [{ value: 'Book', count: 4 }],
                        target_audience: [{ value: 'child', count: 3 }, { value: 'adult', count: 1 }],
                        condition: [{ value: 'good', count: 3 }, { value: 'damaged', count: 1 }]
                    }
                };
            }
            if (endpoint === '/inventory/items/search') return { items: [] };
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        const rows = wrapper.findAll('.rounded');
        const audienceRow = rows.find(row => row.text().includes('bibliographic.audience_child'));
        const conditionRow = rows.find(row => row.text().includes('item.condition_good'));
        expect(audienceRow).toBeDefined();
        expect(conditionRow).toBeDefined();

        await audienceRow.trigger('click');
        await conditionRow.trigger('click');
        expect(wrapper.vm.crossFilters.target_audience).toBe('child');
        expect(wrapper.vm.crossFilters.condition).toBe('good');
        await flushPromises();
        expect(apiClient.get).toHaveBeenCalledWith('/reports/collection-stats', expect.objectContaining({ target_audience: 'child', condition: 'good' }));

        await audienceRow.trigger('click');
        await conditionRow.trigger('click');
        expect(wrapper.vm.crossFilters.target_audience).toBe(null);
        expect(wrapper.vm.crossFilters.condition).toBe(null);
    });

    it('applies publication, acquisition, score and rotation bounds independently', async () => {
        const stats = {
            ...mockCollectionResponse,
            pub_year_histogram: [{ year: 2010, count: 1 }, { year: 2012, count: 1 }],
            acq_year_histogram: [{ year: 2020, count: 1 }, { year: 2022, count: 1 }]
        };
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') return stats;
            if (endpoint === '/inventory/items/search') return { items: [] };
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        wrapper.vm.sliderPubMin = 2011;
        wrapper.vm.sliderPubMax = 2012;
        wrapper.vm.applyPubRange();
        await flushPromises();
        expect(wrapper.vm.crossFilters).toMatchObject({ pub_year_min: 2011, pub_year_max: null });
        expect(apiClient.get).toHaveBeenLastCalledWith('/inventory/items/search', expect.objectContaining({ publication_year_min: 2011 }));
        expect(apiClient.get.mock.calls.at(-1)[1]).not.toHaveProperty('publication_year_max');

        wrapper.vm.sliderPubMin = 2010;
        wrapper.vm.sliderPubMax = 2011;
        wrapper.vm.applyPubRange();
        wrapper.vm.sliderAcqMin = 2021;
        wrapper.vm.sliderAcqMax = 2022;
        wrapper.vm.applyAcqRange();
        wrapper.vm.sliderAcqMin = 2020;
        wrapper.vm.sliderAcqMax = 2021;
        wrapper.vm.applyAcqRange();
        wrapper.vm.crewScoreFilter = { min: 3, max: null };
        wrapper.vm.tauxRotationFilter = { min: null, max: 4 };
        await flushPromises();

        expect(wrapper.vm.crossFilters.pub_year_min).toBe(null);
        expect(wrapper.vm.crossFilters.pub_year_max).toBe(2011);
        expect(wrapper.vm.crossFilters.acq_year_min).toBe(null);
        expect(wrapper.vm.crossFilters.acq_year_max).toBe(2021);
        expect(wrapper.vm.activeChips.map(chip => chip.key)).toEqual(expect.arrayContaining([
            'pub_year', 'acq_year', 'crew_score', 'taux_rotation'
        ]));
        expect(wrapper.vm.hasActiveFilters).toBe(true);
    });

    it('resets panel and column dropdowns and sanitizes unknown saved values', async () => {
        localStorage.setItem('bcd_collection_hidden_panels', JSON.stringify(['condition', 'not-a-panel']));
        localStorage.setItem('bcd_crew_cols', JSON.stringify(['title', 'not-a-column']));
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        expect(wrapper.vm.hiddenPanels).toEqual(['condition']);
        expect(wrapper.vm.visibleCols).toEqual(['title']);
        wrapper.vm.showPanelDropdown = true;
        wrapper.vm.showColDropdown = true;
        wrapper.vm.resetPanels();
        wrapper.vm.resetCols();
        expect(wrapper.vm.showPanelDropdown).toBe(false);
        expect(wrapper.vm.showColDropdown).toBe(false);
        expect(wrapper.vm.hiddenPanels).toEqual([]);
        expect(wrapper.vm.visibleCols).toHaveLength(wrapper.vm.COL_IDS_CREW.length);
    });

    it('keeps rendering when statistics are null or omit optional arrays', async () => {
        let statsCalls = 0;
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') {
                statsCalls += 1;
                return statsCalls === 1 ? null : { total_records: 1, breakdowns: {} };
            }
            if (endpoint === '/inventory/items/search') return { items: [] };
            return [];
        });
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        expect(wrapper.vm.stats).toBe(null);

        await wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await flushPromises();
        expect(wrapper.vm.stats.breakdowns).toEqual({ medium_type: [], target_audience: [], condition: [] });
        expect(wrapper.vm.stats.pub_year_histogram).toEqual([]);
        expect(wrapper.vm.stats.acq_year_histogram).toEqual([]);
        expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('reports normalization failures from an invalid inventory response', async () => {
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') return mockCollectionResponse;
            if (endpoint === '/inventory/items/search') return { unexpected: true };
            return [];
        });
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        expect(wrapper.vm.tableLoading).toBe(false);
        expect(wrapper.vm.allItems).toEqual([]);
        expect(consoleSpy).toHaveBeenCalledWith('table load error', expect.any(Error));
    });

    it('filters more than one page and returns to a valid page after filtering or method changes', async () => {
        const items = Array.from({ length: 101 }, (_, index) => ({
            item_id: `I-${index}`,
            bibliographic_record_id: index,
            crew_score: index % 6,
            taux_rotation: index % 5
        }));
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') return mockCollectionResponse;
            if (endpoint === '/inventory/items/search') return { items };
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        expect(wrapper.vm.totalItems).toBe(101);
        expect(wrapper.vm.totalPages).toBe(3);
        wrapper.vm.goToPage(3);
        expect(wrapper.vm.paginatedData).toHaveLength(1);

        wrapper.vm.crewScoreFilter = { min: 5, max: 5 };
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.totalItems).toBeLessThan(50);
        expect(wrapper.vm.currentPage).toBe(1);

        wrapper.vm.goToPage(2);
        wrapper.vm.crewMethod = 'all';
        await flushPromises();
        expect(wrapper.vm.currentPage).toBe(1);
    });

    it('uses the real rotation panel and pagination controls in the rendered report', async () => {
        const items = Array.from({ length: 51 }, (_, index) => ({
            item_id: `I-${index}`,
            bibliographic_record_id: index,
            title: `Book ${index}`,
            circulation_count: index % 9,
            period_loan_count: index % 9
        }));
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') {
                return {
                    ...mockCollectionResponse,
                    total_count: items.length,
                    breakdowns: { medium_type: [], target_audience: [], condition: [] }
                };
            }
            if (endpoint === '/inventory/items/search') return { items };
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: {
                stubs: { ReportHeader: true, FilterChips: true }
            }
        });
        await flushPromises();

        const pagination = wrapper.findComponent(Pagination);
        expect(pagination.exists()).toBe(true);
        expect(wrapper.find('.pagination').exists()).toBe(true);
        const pageTwo = pagination.findAll('button').find(button => button.text() === '2');
        await pageTwo.trigger('click');
        expect(wrapper.vm.currentPage).toBe(2);
        expect(wrapper.find('.pagination .active').text()).toBe('2');

        const rotation = wrapper.findComponent(TauxRotationPanel);
        expect(rotation.exists()).toBe(true);
        const rotationSliders = rotation.findAll('input[type="range"]');
        await rotationSliders[0].setValue(2);
        await rotationSliders[0].trigger('change');
        expect(wrapper.vm.tauxRotationFilter.min).toBe(2);
    });

    it('covers filter, score, malformed-statistics and sorting boundaries', async () => {
        localStorage.setItem('bcd_collection_hidden_panels', JSON.stringify(42));
        const stats = {
            ...mockCollectionResponse,
            total_count: 5,
            breakdowns: { medium_type: [], target_audience: [], condition: [] },
            pub_year_histogram: [{ year: 2000, count: 1 }, { year: 2015, count: 2 }],
            acq_year_histogram: [{ year: 2010, count: 1 }, { year: 2020, count: 2 }]
        };
        let statsCalls = 0;
        const items = [
            { item_id: 'OLD', bibliographic_record_id: 1, age_days: 800, condition: 'good', publication_year: 2010, medium_type: 'Documentary', period_loan_count: 1 },
            { item_id: 'MID', bibliographic_record_id: 2, age_days: 400, condition: 'good', publication_year: 2018, medium_type: 'Documentary', period_loan_count: 2 },
            { item_id: 'DOC', bibliographic_record_id: 3, age_days: 10, condition: 'damaged', publication_year: 2000, medium_type: 'Documentary', period_loan_count: 0 },
            { item_id: 'NULL-A', bibliographic_record_id: 4, title: null, age_days: null, period_loan_count: null, circulation_count: 2 },
            { item_id: 'NULL-B', bibliographic_record_id: 5, title: null, age_days: null, period_loan_count: null, circulation_count: 3 }
        ];
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') {
                statsCalls += 1;
                return statsCalls === 1 ? stats : [];
            }
            if (endpoint === '/inventory/items/search') return { items };
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();

        expect(wrapper.vm.hiddenPanels).toEqual([]);
        wrapper.vm.togglePanel('crew_score');
        wrapper.vm.togglePanel('crew_score');
        expect(wrapper.vm.isPanelVisible('crew_score')).toBe(true);

        wrapper.vm.crewScoreFilter = { min: 3, max: 4 };
        expect(wrapper.vm.isScoreInRange(2)).toBe(false);
        expect(wrapper.vm.isScoreInRange(5)).toBe(false);
        expect(wrapper.vm.activeChips).toEqual(expect.arrayContaining([
            expect.objectContaining({ key: 'crew_score' })
        ]));
        wrapper.vm.crossFilters = {
            medium_type: 'Book', target_audience: 'child', condition: 'damaged',
            pub_year_min: 2001, pub_year_max: null, acq_year_min: null, acq_year_max: 2020
        };
        expect(wrapper.vm.activeChips.map(chip => chip.key)).toEqual(expect.arrayContaining([
            'medium_type', 'target_audience', 'condition', 'pub_year', 'acq_year'
        ]));
        wrapper.vm.clearFilter('acq_year');
        wrapper.vm.tauxRotationFilter = { min: 1, max: 2 };
        wrapper.vm.clearFilter('taux_rotation');
        wrapper.vm.clearFilter('medium_type');
        wrapper.vm.clearFilter('target_audience');
        wrapper.vm.clearFilter('condition');
        wrapper.vm.clearFilter('pub_year');
        wrapper.vm.clearFilter('crew_score');
        expect(wrapper.vm.hasActiveFilters).toBe(false);

        wrapper.vm.allItems = [
            { item_id: 'A', title: null, bibliographic_record_id: 1, crew_score: 1 },
            { item_id: 'B', title: null, bibliographic_record_id: 2, crew_score: 2 }
        ];
        wrapper.vm.sortColumn = 'title';
        wrapper.vm.paginatedData;
        wrapper.vm.toggleCol('title');
        wrapper.vm.toggleCol('title');
        expect(wrapper.vm.isColVisible('title')).toBe(true);
        wrapper.vm.sliderScoreMin = 1;
        wrapper.vm.sliderScoreMax = 4;
        wrapper.vm.clampScoreMin();
        wrapper.vm.clampScoreMax();
        wrapper.vm.sliderPubMin = 2000;
        wrapper.vm.sliderPubMax = 2015;
        wrapper.vm.clampPubMax();
        wrapper.vm.crewScoreFilter = { min: null, max: 2 };
        wrapper.vm.crossFilters = {
            ...wrapper.vm.crossFilters,
            acq_year_min: 2011,
            acq_year_max: null
        };
        expect(wrapper.vm.activeChips.map(chip => chip.key)).toEqual(expect.arrayContaining(['acq_year', 'crew_score']));
        wrapper.vm.handleSort('title');
        wrapper.vm.handleSort('title');
        wrapper.vm.handleSort('title');

        wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await flushPromises();
        expect(wrapper.vm.stats).toBe(null);
    });

    it('rebuilds charts after successive filter changes', async () => {
        const stats = {
            ...mockCollectionResponse,
            breakdowns: { medium_type: [{ value: 'Book', count: 1 }], target_audience: [], condition: [] },
            pub_year_histogram: [{ year: 2010, count: 1 }],
            acq_year_histogram: [{ year: 2020, count: 1 }]
        };
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') return stats;
            if (endpoint === '/inventory/items/search') return { items: [{ item_id: 'I-1', bibliographic_record_id: 1 }] };
            return [];
        });
        const wrapper = mount(CollectionReport, {
            global: { stubs: { ReportHeader: true, Pagination: true, FilterChips: true, TauxRotationPanel: true } }
        });
        await flushPromises();
        const firstCharts = [...Chart.instances];

        wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await flushPromises();
        const secondCharts = [...Chart.instances];
        wrapper.vm.toggleBreakdown('medium_type', null);
        await flushPromises();

        expect(firstCharts.every(chart => chart.destroyed)).toBe(true);
        expect(secondCharts.every(chart => chart.destroyed)).toBe(true);
        expect(Chart.instances.at(-1).destroyed).toBe(false);
    });

    it('calculates advanced statistics, filters the table and supports printing', async () => {
        const items = [
            {
                item_id: 'I-1', bibliographic_record_id: 1, title: 'Old documentary',
                age_days: 1200, condition: 'damaged', publication_year: new Date().getFullYear() - 12,
                medium_type: 'Documentary', period_loan_count: 0, circulation_count: 0
            },
            {
                item_id: 'I-2', bibliographic_record_id: 1, title: 'Old documentary',
                age_days: 100, condition: 'good', publication_year: new Date().getFullYear(),
                medium_type: 'Documentary', period_loan_count: 2, circulation_count: 2
            },
            {
                item_id: 'I-3', bibliographic_record_id: 2, title: 'Story book',
                age_days: 500, condition: 'good', publication_year: new Date().getFullYear() - 2,
                medium_type: 'Book', period_loan_count: 4, circulation_count: 4
            }
        ];
        vi.mocked(apiClient.get).mockImplementation(async endpoint => {
            if (endpoint === '/reports/collection-stats') return mockCollectionResponse;
            if (endpoint === '/inventory/items/search') return items;
            return [];
        });
        const print = vi.spyOn(window, 'print').mockImplementation(() => {});
        const wrapper = mount(CollectionReport, {
            global: {
                stubs: {
                    ReportHeader: true,
                    Pagination: true,
                    FilterChips: true,
                    TauxRotationPanel: true
                }
            }
        });
        await flushPromises();

        expect(wrapper.vm.allItems).toHaveLength(3);
        expect(wrapper.vm.scoreHistogram.length).toBeGreaterThanOrEqual(10);
        expect(wrapper.vm.scoreBarColor(2)).toBe('#33CC66');
        expect(wrapper.vm.scoreBarColor(4)).toBe('#F2BF33');
        expect(wrapper.vm.scoreBarColor(5)).toBe('#F24D66');
        expect(wrapper.vm.copiesPerTitle).toEqual({ 1: 2, 2: 1 });
        expect(wrapper.vm.tauxMax).toBe(4);
        expect(wrapper.vm.breakdownMax([{ count: 2 }, { count: 5 }])).toBe(5);
        expect(wrapper.vm.conditionLabel('damaged')).toBe('item.condition_damaged');
        expect(wrapper.vm.audienceLabel('child')).toBe('bibliographic.audience_child');

        wrapper.vm.tauxRotationFilter = { min: 3, max: null };
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.totalItems).toBe(1);
        wrapper.vm.tauxRotationFilter = { min: null, max: null };
        wrapper.vm.crewScoreFilter = { min: 5, max: null };
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.totalItems).toBe(1);
        wrapper.vm.clearFilter('crew_score');
        expect(wrapper.vm.crewScoreFilter).toEqual({ min: null, max: null });

        wrapper.vm.toggleBreakdown('medium_type', 'Book');
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.crossFilters.medium_type).toBe('Book');
        expect(wrapper.vm.activeChips).toContainEqual(expect.objectContaining({ key: 'medium_type', value: 'Book' }));
        wrapper.vm.clearAllFilters();
        expect(wrapper.vm.hasActiveFilters).toBe(false);

        wrapper.vm.handleSort('title');
        expect(wrapper.vm.sortColumn).toBe('title');
        wrapper.vm.handleSort('title');
        expect(wrapper.vm.sortDirection).toBe('asc');
        wrapper.vm.sliderPubMin = wrapper.vm.pubYearRange.min + 1;
        wrapper.vm.sliderPubMax = wrapper.vm.pubYearRange.max;
        wrapper.vm.applyPubRange();
        expect(wrapper.vm.crossFilters.pub_year_min).toBe(wrapper.vm.pubYearRange.min + 1);
        wrapper.vm.clearFilter('pub_year');
        expect(wrapper.vm.crossFilters.pub_year_min).toBe(null);

        wrapper.vm.toggleCol('title');
        expect(wrapper.vm.isColVisible('title')).toBe(false);
        wrapper.vm.resetCols();
        expect(wrapper.vm.isColVisible('title')).toBe(true);
        wrapper.vm.printReport();
        expect(print).toHaveBeenCalledTimes(1);
    });
});
