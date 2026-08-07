// @ts-check
/**
 * Global Modal Composable
 *
 * Provides a shared singleton state for opening record and borrower detail modals
 * from any page without changing the URL. Modals are rendered once in App.js.
 *
 * Usage:
 *   const { openRecord, openBorrower } = useGlobalModal();
 *   openRecord(42);      // opens RecordDetail modal from anywhere
 *   openBorrower('E01'); // opens BorrowerDetail modal from anywhere
 */

const { ref } = Vue;

// Module-level singletons — shared across all component instances
/** @type {import('vue').Ref<number|null>} */
const globalRecordId = ref(null);
/** @type {import('vue').Ref<string|null>} */
const globalBorrowerId = ref(null);

// Incremented after a quick-return so CatalogPage can refresh its search results
const catalogRefreshTick = ref(0);

export function useGlobalModal() {
    /**
     * @param {number|string|null|undefined} id
     */
    const openRecord = (id) => {
        globalRecordId.value = id !== null && id !== undefined ? parseInt(String(id)) : null;
    };

    const closeRecord = () => {
        globalRecordId.value = null;
    };

    /**
     * @param {string|number|null|undefined} id
     */
    const openBorrower = (id) => {
        globalBorrowerId.value = id !== null && id !== undefined ? String(id) : null;
    };

    const closeBorrower = () => {
        globalBorrowerId.value = null;
    };

    return {
        globalRecordId,
        globalBorrowerId,
        catalogRefreshTick,
        openRecord,
        closeRecord,
        openBorrower,
        closeBorrower,
    };
}
