import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import CollectionReport from '../../../../src/bcd_web_vue/js/components/reports/CollectionReport.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mockCollectionResponse = {
    total_records: 10,
    total_copies: 15,
    lost_copies: 1,
    weeded_copies: 0,
    distribution_by_medium: { 'Book': 14 },
    distribution_by_audience: { 'child': 12 }
};

const mockWeedingItems = {
    items: [
        { item_id: 'I-101', title: 'Stuart Little', crew_score: 2, condition: 'good', age_days: 300, total_copies: 1, period_loan_count: 0 }
    ],
    total: 1
};

beforeEach(() => {
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
});
