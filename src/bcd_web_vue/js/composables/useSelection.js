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
     * @param {Array} items - Array of items with id property
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
     * @param {Array} items - Array of items with id property
     */
    const toggleSelectAll = (items) => {
        if (selectedIds.value.size === items.length) {
            clearSelection();
        } else {
            selectAll(items);
        }
    };

    /**
     * Get array of selected IDs
     * @returns {Array}
     */
    const getSelectedIds = () => {
        return Array.from(selectedIds.value);
    };

    /**
     * Check if all items are selected
     * @param {Array} items - Array of items
     * @returns {boolean}
     */
    const isAllSelected = (items) => {
        return items.length > 0 && selectedIds.value.size === items.length;
    };

    /**
     * Check if some (but not all) items are selected
     * @param {Array} items - Array of items
     * @returns {boolean}
     */
    const isSomeSelected = (items) => {
        return selectedIds.value.size > 0 && selectedIds.value.size < items.length;
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
