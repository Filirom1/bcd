/**
 * Filters composable with URL synchronization
 * Manages filter state and syncs with URL query parameters
 */

const { ref, computed, watch } = Vue;
const { useRouter, useRoute } = VueRouter;

/**
 * Filters composable
 * @param {Object} initialFilters - Initial filter values
 * @param {Object} [options] - Configuration options
 * @param {boolean} [options.syncWithURL=true] - Whether to sync with URL
 * @returns {Object} Filter state and methods
 */
export function useFilters(initialFilters = {}, options = {}) {
    const syncWithURL = options.syncWithURL !== false;
    const router = syncWithURL ? useRouter() : null;
    const route = syncWithURL ? useRoute() : null;

    // Initialize filters from URL query params if syncing, otherwise use defaults
    const filters = ref(
        syncWithURL
            ? { ...initialFilters, ...Object.fromEntries(Object.entries(route.query)) }
            : { ...initialFilters }
    );

    /**
     * Computed: Active filters count (non-empty values)
     */
    const activeFiltersCount = computed(() => {
        return Object.values(filters.value).filter(val => {
            return val !== null && val !== undefined && val !== '';
        }).length;
    });

    /**
     * Computed: Has active filters
     */
    const hasActiveFilters = computed(() => {
        return activeFiltersCount.value > 0;
    });

    /**
     * Update a filter value
     * @param {string} key - Filter key
     * @param {any} value - Filter value
     */
    const setFilter = (key, value) => {
        filters.value[key] = value;
    };

    /**
     * Update multiple filters at once
     * @param {Object} updates - Object with filter key-value pairs
     */
    const setFilters = (updates) => {
        Object.assign(filters.value, updates);
    };

    /**
     * Clear a specific filter
     * @param {string} key - Filter key to clear
     */
    const clearFilter = (key) => {
        filters.value[key] = Object.hasOwn(initialFilters, key)
            ? initialFilters[key]
            : null;
    };

    /**
     * Clear all filters (reset to initial values)
     */
    const clearAllFilters = () => {
        filters.value = { ...initialFilters };
    };

    /**
     * Get API params object (excludes null/undefined/empty values)
     */
    const getApiParams = () => {
        const params = {};
        Object.entries(filters.value).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                params[key] = value;
            }
        });
        return params;
    };

    // Watch filters and sync to URL
    if (syncWithURL && router) {
        watch(
            filters,
            (newFilters) => {
                const query = {};
                Object.entries(newFilters).forEach(([key, value]) => {
                    if (value !== null && value !== undefined && value !== '') {
                        query[key] = value.toString();
                    }
                });

                // Update URL without triggering navigation
                router.replace({ query });
            },
            { deep: true }
        );
    }

    return {
        // State
        filters: computed(() => filters.value),
        activeFiltersCount,
        hasActiveFilters,

        // Methods
        setFilter,
        setFilters,
        clearFilter,
        clearAllFilters,
        getApiParams
    };
}
