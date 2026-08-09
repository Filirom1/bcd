// @ts-check
/**
 * useInventoryTable Composable
 *
 * Manages the working table state for inventory operations with localStorage persistence.
 * Survives page refresh and tab close (localStorage, not sessionStorage).
 *
 * Strategy: Only store item IDs in localStorage, fetch full details from API on restore.
 * This ensures fresh data and avoids stale localStorage issues.
 *
 * State:
 * - items: Array of inventory items with all fields
 * - itemIds: Array of item_id strings (persisted to localStorage)
 *
 * Operations:
 * - addItem(item): Add item to table (deduplicate by item_id, move to top if exists)
 * - addItems(items): Add multiple items (unselected by default, deduplicate)
 * - removeItems(item_ids): Remove items by item_id
 * - clearAll(): Clear entire table
 * - restore(): Restore IDs from localStorage and fetch details from API
 */

const { ref, watch } = Vue;
import { apiClient } from '../api/client.js';
import { getJSON, setJSON } from '../utils/storage.js';

const STORAGE_KEY = 'inventory_table_ids';

/**
 * Working table row — subset of Item fields plus denormalised record fields.
 * @typedef {Object} InventoryTableItem
 * @property {string} item_id
 * @property {number} bibliographic_record_id
 * @property {string} status
 * @property {string} condition
 * @property {boolean} loanable
 * @property {string|null} shelf_location
 * @property {string|null} call_number
 * @property {string|null} last_inventoried_at
 * @property {string} title
 * @property {string|null} level
 * @property {string|null} target_audience
 * @property {string|null} language
 * @property {string|null} medium_type
 */

export function useInventoryTable() {
    /** @type {import('vue').Ref<InventoryTableItem[]>} */
    const items = ref([]);
    /** @type {import('vue').Ref<string[]>} */
    const itemIds = ref([]);
    const loading = ref(false);

    /**
     * Persist only item IDs to localStorage
     */
    const persist = () => {
        setJSON(STORAGE_KEY, itemIds.value);
    };

    /**
     * Restore table from localStorage
     * 1. Load item IDs from localStorage
     * 2. Fetch full item details from API
     */
    const restore = async () => {
        try {
            const parsedIds = getJSON(STORAGE_KEY);
            if (!parsedIds) {
                items.value = [];
                itemIds.value = [];
                return;
            }
            if (!Array.isArray(parsedIds) || parsedIds.length === 0) {
                items.value = [];
                itemIds.value = [];
                return;
            }

            // Fetch full details from API
            loading.value = true;
            itemIds.value = parsedIds;

            try {
                // Fetch each item individually to get full details
                const fetchPromises = parsedIds.map(item_id =>
                    apiClient.patch(`/inventory/items/${item_id}`, {})
                        .catch(err => {
                            console.warn(`Failed to fetch item ${item_id}:`, err);
                            return null;
                        })
                );

                const results = await Promise.all(fetchPromises);

                // Filter out nulls (failed fetches) and build items array
                items.value = results
                    .filter(Boolean)
                    .map(item => ({
                        // Item fields
                        item_id: item.item_id,
                        bibliographic_record_id: item.bibliographic_record_id,
                        status: item.status,
                        condition: item.condition,
                        loanable: item.loanable,
                        shelf_location: item.shelf_location,
                        call_number: item.call_number,
                        last_inventoried_at: item.last_inventoried_at,
                        // Record fields
                        title: item.title,
                        level: item.level,
                        target_audience: item.target_audience,
                        language: item.language,
                        medium_type: item.medium_type
                    }));

                // Update itemIds to only include successfully fetched items
                itemIds.value = items.value.map(item => item.item_id);

            } catch (error) {
                console.error('Failed to fetch inventory item details from API:', error);
                // Keep IDs but clear items on error
                items.value = [];
            }
        } catch (error) {
            console.error('Failed to restore inventory table from localStorage:', error);
            items.value = [];
            itemIds.value = [];
        } finally {
            loading.value = false;
        }
    };

    /**
     * Add single item to table
     * - If item_id exists, move to top and update data
     * - Otherwise, prepend to array
     * - Updates both items and itemIds
     *
     * @param {InventoryTableItem} item - Item object with all fields
     */
    const addItem = (item) => {
        const existingIndex = items.value.findIndex(i => i.item_id === item.item_id);

        if (existingIndex !== -1) {
            // Item exists - remove from current position
            items.value.splice(existingIndex, 1);
            itemIds.value.splice(existingIndex, 1);
        }

        // Add/move to top
        items.value.unshift(item);
        itemIds.value.unshift(item.item_id);
    };

    /**
     * Add multiple items to table
     * - Deduplicates by item_id
     * - New items are appended (not selected by default)
     * - Updates both items and itemIds
     *
     * @param {InventoryTableItem[]} newItems - Array of item objects
     */
    const addItems = (newItems) => {
        const existingIds = new Set(itemIds.value);

        newItems.forEach(item => {
            if (!existingIds.has(item.item_id)) {
                items.value.push(item);
                itemIds.value.push(item.item_id);
                existingIds.add(item.item_id);
            }
        });
    };

    /**
     * Remove items by item_id
     * - Updates both items and itemIds
     *
     * @param {string[]} item_ids_to_remove - Array of item_ids to remove
     */
    const removeItems = (item_ids_to_remove) => {
        const idSet = new Set(item_ids_to_remove);
        items.value = items.value.filter(item => !idSet.has(item.item_id));
        itemIds.value = itemIds.value.filter(id => !idSet.has(id));
    };

    /**
     * Clear entire table
     * - Clears both items and itemIds
     */
    const clearAll = () => {
        items.value = [];
        itemIds.value = [];
    };

    /**
     * Get all item IDs in table
     *
     * @returns {string[]} Array of item_ids
     */
    const getAllItemIds = () => {
        return itemIds.value;
    };

    // Auto-persist on itemIds changes (not full items)
    watch(itemIds, persist, { deep: true });

    // Restore on mount (called by consumer)
    restore();

    return {
        items,
        loading,
        addItem,
        addItems,
        removeItems,
        clearAll,
        getAllItemIds,
        restore
    };
}
