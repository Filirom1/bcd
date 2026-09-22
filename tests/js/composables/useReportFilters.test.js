import { describe, expect, it, vi } from 'vitest';

import { useReportFilters } from '../../../src/bcd_web_vue/js/composables/useReportFilters.js';

describe('useReportFilters', () => {
    const t = key => key;
    const audienceLabel = audience => `audience:${audience}`;

    it('filters items, builds breakdowns, and clears a range filter', () => {
        const filters = useReportFilters(t, audienceLabel, { status: 'overdue' });
        filters.toggleBreakdown('medium_type', 'Book');
        filters.crossFilters.value.taux_rotation_min = 2;

        const items = [
            { medium_type: 'Book', taux_rotation: 3, target_audience: 'child' },
            { medium_type: 'Book', taux_rotation: 1, target_audience: 'child' },
            { medium_type: 'Magazine', taux_rotation: 4, target_audience: 'adult' }
        ];

        expect(filters.applyFilters(items)).toHaveLength(1);
        expect(filters.buildBreakdown(items, 'target_audience')).toEqual([
            { value: 'child', count: 1 }
        ]);
        expect(filters.hasActiveFilters.value).toBe(true);

        filters.clearFilter('taux_rotation');
        expect(filters.crossFilters.value.taux_rotation_min).toBeNull();
        expect(filters.crossFilters.value.medium_type).toBe('Book');
    });

    it('builds translated active chips and clears all filters', () => {
        const filters = useReportFilters(t, audienceLabel);
        filters.toggleBreakdown('target_audience', 'child');

        expect(filters.activeChips.value).toEqual([{
            key: 'target_audience',
            label: 'bibliographic.target_audience',
            value: 'audience:child'
        }]);

        filters.clearAllFilters();
        expect(filters.hasActiveFilters.value).toBe(false);
        expect(filters.activeChips.value).toEqual([]);
    });

    it('applies minimum and maximum rotation bounds, treating missing values as zero', () => {
        const filters = useReportFilters(t, audienceLabel, { taux_rotation_min: 1 });
        const items = [
            { id: 1, taux_rotation: undefined, publication_year: 2020 },
            { id: 2, taux_rotation: 1, publication_year: 2021 },
            { id: 3, taux_rotation: 3, publication_year: 2022 }
        ];
        expect(filters.applyFilters(items).map(item => item.id)).toEqual([2, 3]);

        filters.crossFilters.value.taux_rotation_min = null;
        filters.crossFilters.value.taux_rotation_max = 2;
        expect(filters.applyFilters(items).map(item => item.id)).toEqual([1, 2]);

        filters.crossFilters.value.taux_rotation_min = 1;
        expect(filters.applyFilters(items).map(item => item.id)).toEqual([2]);
    });

    it('excludes each active filter while building a breakdown', () => {
        const filters = useReportFilters(t, audienceLabel, {
            medium_type: 'Book',
            target_audience: 'child',
            taux_rotation_min: 2,
            pub_year_min: 2020
        });
        const items = [
            { medium_type: 'Book', target_audience: 'child', taux_rotation: 3, publication_year: 2021 },
            { medium_type: 'Magazine', target_audience: 'child', taux_rotation: 3, publication_year: 2021 },
            { medium_type: 'Book', target_audience: 'adult', taux_rotation: 1, publication_year: 2019 },
            { medium_type: 'Book', target_audience: 'adult', taux_rotation: 3, publication_year: null }
        ];

        expect(filters.buildBreakdown(items, 'medium_type')).toEqual([
            { value: 'Book', count: 1 },
            { value: 'Magazine', count: 1 }
        ]);
        expect(filters.buildBreakdown(items, 'target_audience')).toEqual([
            { value: 'child', count: 1 }
        ]);
        expect(filters.buildBreakdown(items, 'taux_rotation')).toEqual([
            { value: '3', count: 1 }
        ]);
        expect(filters.buildBreakdown([
            { medium_type: 'Book', target_audience: 'child', taux_rotation: 3, pub_year: 2010 },
            { medium_type: 'Book', target_audience: 'child', taux_rotation: 3, pub_year: 2020 }
        ], 'pub_year')).toEqual([
            { value: '2010', count: 1 },
            { value: '2020', count: 1 }
        ]);

        // Excluding an unknown key still applies the known filters.
        expect(filters.applyFilters(items, 'unknown').map(item => item.medium_type)).toEqual(['Book']);
    });

    it('clears publication and rotation ranges and invokes reset callbacks', () => {
        const filters = useReportFilters(t, audienceLabel, {
            pub_year_min: 2000,
            pub_year_max: 2020,
            taux_rotation_min: 1,
            taux_rotation_max: 4,
            medium_type: 'Book'
        });
        const reset = vi.fn();

        filters.clearFilter('pub_year', reset);
        expect(filters.crossFilters.value.pub_year_min).toBeNull();
        expect(filters.crossFilters.value.pub_year_max).toBeNull();
        expect(reset).toHaveBeenCalledWith('pub_year');

        filters.clearFilter('taux_rotation', reset);
        expect(filters.crossFilters.value.taux_rotation_min).toBeNull();
        expect(filters.crossFilters.value.taux_rotation_max).toBeNull();
        expect(reset).toHaveBeenLastCalledWith('taux_rotation');

        filters.clearAllFilters(reset);
        expect(filters.crossFilters.value).toEqual({
            medium_type: null,
            target_audience: null,
            taux_rotation_min: null,
            taux_rotation_max: null,
            pub_year_min: null,
            pub_year_max: null
        });
        expect(reset).toHaveBeenLastCalledWith();
    });

    it('keeps unknown audience values visible in active chips', () => {
        const filters = useReportFilters(t, audienceLabel);
        filters.toggleBreakdown('target_audience', 'unknown-audience');
        expect(filters.activeChips.value[0].value).toBe('audience:unknown-audience');
        filters.toggleBreakdown('target_audience', 'unknown-audience');
        expect(filters.activeChips.value).toEqual([]);
    });
});
