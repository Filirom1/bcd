import { describe, expect, it } from 'vitest';

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
});
