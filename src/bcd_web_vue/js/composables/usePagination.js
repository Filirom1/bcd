// @ts-check
/**
 * Pagination composable
 * Manages pagination state and calculations
 */

const { ref, computed, watch } = Vue;

/**
 * @typedef {Object} PaginationState
 * @property {import('vue').Ref<number>} currentPage
 * @property {import('vue').Ref<number>} pageSize
 * @property {import('vue').Ref<number>} totalItems
 * @property {import('vue').ComputedRef<number>} totalPages
 * @property {import('vue').ComputedRef<number>} offset
 * @property {import('vue').Ref<number>} limit
 * @property {import('vue').ComputedRef<boolean>} hasNextPage
 * @property {import('vue').ComputedRef<boolean>} hasPreviousPage
 * @property {import('vue').ComputedRef<number>} firstItem
 * @property {import('vue').ComputedRef<number>} lastItem
 * @property {(page: number) => void} goToPage
 * @property {() => void} nextPage
 * @property {() => void} previousPage
 * @property {(size: number) => void} setPageSize
 * @property {(total: number) => void} setTotalItems
 * @property {() => void} reset
 */

/**
 * Pagination composable
 * @param {Object} [options] - Configuration options
 * @param {number} [options.initialPage=1] - Initial page number
 * @param {number} [options.pageSize=50] - Items per page
 * @param {number} [options.totalItems=0] - Total number of items
 * @returns {PaginationState} Pagination state and methods
 */
export function usePagination(options = {}) {
    const currentPage = ref(options.initialPage || 1);
    const pageSize = ref(options.pageSize || 10);
    const totalItems = ref(options.totalItems || 0);

    /**
     * Computed: Total pages
     */
    const totalPages = computed(() => {
        return Math.ceil(totalItems.value / pageSize.value) || 1;
    });

    /**
     * Computed: Offset for database query
     */
    const offset = computed(() => {
        return (currentPage.value - 1) * pageSize.value;
    });

    /**
     * Computed: Has next page
     */
    const hasNext = computed(() => {
        return currentPage.value < totalPages.value;
    });

    /**
     * Computed: Has previous page
     */
    const hasPrevious = computed(() => {
        return currentPage.value > 1;
    });

    /**
     * Computed: First item number on current page
     */
    const firstItem = computed(() => {
        if (totalItems.value === 0) return 0;
        return offset.value + 1;
    });

    /**
     * Computed: Last item number on current page
     */
    const lastItem = computed(() => {
        const last = offset.value + pageSize.value;
        return Math.min(last, totalItems.value);
    });

    /**
     * Go to next page
     */
    const nextPage = () => {
        if (hasNext.value) {
            currentPage.value++;
        }
    };

    /**
     * Go to previous page
     */
    const previousPage = () => {
        if (hasPrevious.value) {
            currentPage.value--;
        }
    };

    /**
     * Go to specific page
     * @param {number} page - Page number
     */
    const goToPage = (page) => {
        if (page >= 1 && page <= totalPages.value) {
            currentPage.value = page;
        }
    };

    /**
     * Set page size
     * @param {number} size - New page size
     */
    const setPageSize = (size) => {
        pageSize.value = size;
        // Reset to page 1 when changing page size
        currentPage.value = 1;
    };

    /**
     * Set total items
     * @param {number} total - Total number of items
     */
    const setTotalItems = (total) => {
        totalItems.value = total;
        // Ensure current page is valid
        if (currentPage.value > totalPages.value) {
            currentPage.value = totalPages.value || 1;
        }
    };

    /**
     * Reset pagination to initial state
     */
    const reset = () => {
        currentPage.value = 1;
        pageSize.value = options.pageSize || 10;
        totalItems.value = 0;
    };

    return {
        // State (return refs directly so they're writable)
        currentPage,
        pageSize,
        totalItems,
        totalPages,
        offset,
        limit: pageSize, // Alias for clarity
        hasNextPage: hasNext,
        hasPreviousPage: hasPrevious,
        firstItem,
        lastItem,

        // Methods
        nextPage,
        previousPage,
        goToPage,
        setPageSize,
        setTotalItems,
        reset
    };
}
