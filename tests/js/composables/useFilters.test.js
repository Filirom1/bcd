import { describe, expect, it } from 'vitest';

import { useFilters } from '../../../src/bcd_web_vue/js/composables/useFilters.js';

describe('useFilters', () => {
    it('counts only non-empty filters and creates API parameters', () => {
        const filters = useFilters(
            { query: '', available: false, page: 0, class_id: null },
            { syncWithURL: false }
        );

        expect(filters.activeFiltersCount.value).toBe(2);
        expect(filters.hasActiveFilters.value).toBe(true);
        expect(filters.getApiParams()).toEqual({ available: false, page: 0 });

        filters.setFilter('query', 'Verne');
        expect(filters.activeFiltersCount.value).toBe(3);
        expect(filters.getApiParams()).toEqual({ query: 'Verne', available: false, page: 0 });
    });

    it('updates individual and multiple filters', () => {
        const filters = useFilters({ query: '', status: '' }, { syncWithURL: false });

        filters.setFilter('query', 'Lupin');
        filters.setFilters({ status: 'available', audience: 'children' });

        expect(filters.filters.value).toEqual({
            query: 'Lupin',
            status: 'available',
            audience: 'children'
        });
    });

    it('restores falsy initial values when clearing an individual filter', () => {
        const filters = useFilters(
            { available: false, page: 0, query: '' },
            { syncWithURL: false }
        );

        filters.setFilters({ available: true, page: 3, query: 'Alice' });
        filters.clearFilter('available');
        filters.clearFilter('page');
        filters.clearFilter('query');

        expect(filters.filters.value).toEqual({ available: false, page: 0, query: '' });
    });

    it('resets all filters to their initial state', () => {
        const filters = useFilters({ query: '', status: 'available' }, { syncWithURL: false });

        filters.setFilters({ query: 'Dumas', status: 'lost', audience: 'adult' });
        filters.clearAllFilters();

        expect(filters.filters.value).toEqual({ query: '', status: 'available' });
    });
});
