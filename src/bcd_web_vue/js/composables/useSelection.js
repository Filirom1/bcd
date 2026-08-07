// @ts-check
/**
 * useSelection - Multi-select checkbox logic composable (DRY component)
 *
 * Provides reusable selection state management for tables with checkboxes.
 * Used by BorrowerList, SearchResults, and other list components.
 *
 * @returns {Object} Selection state and methods
 */

const { ref, computed } = Vue;

export function useSelection() {
    const selectedIds = ref(new Set());

    /**
     * Count of selected items
     */
    const selectedCount = computed(() => selectedIds.value.size);

    /**
     * Check if an item is selected
     * @param {string|number} id - Item ID
     * @returns {boolean}
     */
    const isSelected = (id) => {
        return selectedIds.value.has(id);
    };

    /**
     * Toggle selection for a single item
     * @param {string|number} id - Item ID
     */
    const toggleSelection = (id) => {
        if (selectedIds.value.has(id)) {
            selectedIds.value.delete(id);
        } else {
            selectedIds.value.add(id);
        }
        // Trigger reactivity
        selectedIds.value = new Set(selectedIds.value);
    };

    /**
     * Select all items from a list
     * @param {any[]} items - Array of items with id property
     */
    const selectAll = (items) => {
        selectedIds.value = new Set(items.map(item => item.id));
    };

    /**
     * Deselect all items
     */
    const clearSelection = () => {
        selectedIds.value = new Set();
    };

    /**
     * Toggle select all (select all if none selected, clear if any selected)
     * @param {any[]} items - Array of items with id property
     */
    const toggleSelectAll = (items) => {
        if (isAllSelected(items)) {
            clearSelection();
        } else {
            selectAll(items);
        }
    };

    /**
     * Get array of selected IDs
     * @returns {any[]}
     */
    const getSelectedIds = () => {
        return Array.from(selectedIds.value);
    };

    /**
     * Check if all items are selected
     * @param {any[]} items - Array of items
     * @returns {boolean}
     */
    const isAllSelected = (items) => {
        return items.length > 0 && items.every(item => selectedIds.value.has(item.id));
    };

    /**
     * Check if some (but not all) current items are selected.
     * Selections from a previous page or filter must not change this state.
     * @param {any[]} items - Array of items
     * @returns {boolean}
     */
    const isSomeSelected = (items) => {
        const selectedCurrentItems = items.filter(item => selectedIds.value.has(item.id));
        return selectedCurrentItems.length > 0 && selectedCurrentItems.length < items.length;
    };

    return {
        selectedIds,
        selectedCount,
        isSelected,
        toggleSelection,
        selectAll,
        clearSelection,
        toggleSelectAll,
        getSelectedIds,
        isAllSelected,
        isSomeSelected
    };
}
