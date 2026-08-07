// @ts-check
/**
 * Shared composable for cross-filter state used by collection reports.
 * Handles: medium_type, target_audience, taux_rotation min/max.
 *
 * Each report may extend crossFilters with additional keys (e.g. condition,
 * pub_year_min/max in CollectionReport).
 */

const { ref, computed } = Vue;

/**
 * @typedef {Object} CrossFilters
 * @property {string|null} [medium_type]
 * @property {string|null} [target_audience]
 * @property {number|null} [taux_rotation_min]
 * @property {number|null} [taux_rotation_max]
 * @property {number|null} [pub_year_min]
 * @property {number|null} [pub_year_max]
 */

/**
 * @param {Function} t - vue-i18n translation function
 * @param {Function} audienceLabel - label resolver for audience values
 * @param {Partial<CrossFilters>} [extraFilters]
 */
export function useReportFilters(t, audienceLabel, extraFilters = {}) {
    /** @type {import('vue').Ref<any>} */
    const crossFilters = ref({
        medium_type: null,
        target_audience: null,
        taux_rotation_min: null,
        taux_rotation_max: null,
        ...extraFilters,
    });

    const hasActiveFilters = computed(() =>
        Object.values(crossFilters.value).some(v => v !== null)
    );

    /**
     * @param {string} key
     * @param {any} value
     */
    const toggleBreakdown = (key, value) => {
        const cf = /** @type {Record<string, any>} */ (crossFilters.value);
        crossFilters.value = {
            ...crossFilters.value,
            [key]: cf[key] === value ? null : value,
        };
    };

    /**
     * @param {string} key
     * @param {Function|null} [resetFn]
     */
    const clearFilter = (key, resetFn = null) => {
        if (key === 'taux_rotation') {
            crossFilters.value = { ...crossFilters.value, taux_rotation_min: null, taux_rotation_max: null };
        } else if (key === 'pub_year') {
            crossFilters.value = { ...crossFilters.value, pub_year_min: null, pub_year_max: null };
        } else {
            crossFilters.value = { ...crossFilters.value, [key]: null };
        }
        if (resetFn) resetFn(key);
    };

    /**
     * @param {Function|null} [resetFn]
     */
    const clearAllFilters = (resetFn = null) => {
        const cleared = /** @type {Record<string, any>} */ ({});
        for (const k of Object.keys(crossFilters.value)) cleared[k] = null;
        crossFilters.value = cleared;
        if (resetFn) resetFn();
    };

    /**
     * Filter an item list applying all active cross-filters.
     * excludeKey: skip that filter (for breakdown distribution queries).
     * tauxField: which field to compare against taux_rotation min/max.
     * @param {any[]} items
     * @param {string|null} [excludeKey]
     * @param {string} [tauxField]
     * @returns {any[]}
     */
    const applyFilters = (items, excludeKey = null, tauxField = 'taux_rotation') => {
        const cf = crossFilters.value;
        return items.filter(item => {
            if (excludeKey !== 'medium_type'     && cf.medium_type     && item.medium_type     !== cf.medium_type)     return false;
            if (excludeKey !== 'target_audience' && cf.target_audience && item.target_audience !== cf.target_audience) return false;
            if (excludeKey !== 'taux_rotation') {
                if (cf.taux_rotation_min !== null && (item[tauxField] ?? 0) < cf.taux_rotation_min) return false;
                if (cf.taux_rotation_max !== null && (item[tauxField] ?? 0) > cf.taux_rotation_max) return false;
            }
            if (excludeKey !== 'pub_year') {
                if (cf.pub_year_min != null && (!item.publication_year || item.publication_year < cf.pub_year_min)) return false;
                if (cf.pub_year_max != null && (!item.publication_year || item.publication_year > cf.pub_year_max)) return false;
            }
            return true;
        });
    };

    /** 
     * Build a sorted [{ value, count }] breakdown for a given key.
     * @param {any[]} allItems
     * @param {string} key
     * @param {string} [tauxField]
     * @returns {Array<{value: string, count: number}>}
     */
    const buildBreakdown = (allItems, key, tauxField = 'taux_rotation') => {
        /** @type {Record<string, number>} */
        const counts = {};
        applyFilters(allItems, key, tauxField).forEach(item => {
            const val = item[key];
            if (val) counts[val] = (counts[val] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([value, count]) => ({ value, count }))
            .sort((a, b) => b.count - a.count);
    };

    const activeChips = computed(() => {
        const cf = crossFilters.value;
        const chips = [];
        if (cf.medium_type)     chips.push({ key: 'medium_type',     label: t('bibliographic.medium_type'),     value: cf.medium_type });
        if (cf.target_audience) chips.push({ key: 'target_audience', label: t('bibliographic.target_audience'), value: audienceLabel(cf.target_audience) });
        if (cf.taux_rotation_min !== null || cf.taux_rotation_max !== null) {
            const min = cf.taux_rotation_min ?? '…';
            const max = cf.taux_rotation_max ?? '…';
            chips.push({ key: 'taux_rotation', label: t('reports.tauxRotation.label'), value: `${min} – ${max}` });
        }
        if (cf.pub_year_min != null || cf.pub_year_max != null) {
            chips.push({ key: 'pub_year', label: t('reports.pubYear.label'),
                value: `${cf.pub_year_min ?? '…'} – ${cf.pub_year_max ?? '…'}` });
        }
        return chips;
    });

    return {
        crossFilters,
        hasActiveFilters,
        activeChips,
        toggleBreakdown,
        clearFilter,
        clearAllFilters,
        applyFilters,
        buildBreakdown,
    };
}
