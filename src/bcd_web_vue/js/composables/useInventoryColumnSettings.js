// @ts-check
/**
 * Inventory Column Settings Composable
 * Manages visible columns for inventory working table with localStorage persistence
 */

const { ref, watch } = Vue;
import { getJSON, setJSON } from '../utils/storage.js';

const STORAGE_KEY = 'inventory_columns';

/**
 * @typedef {Object} InventoryColumnDefinition
 * @property {string} id
 * @property {string} label_en
 * @property {string} label_fr
 * @property {boolean} default
 * @property {string} group
 */

// Available columns for inventory working table
// Includes all fields that can be modified via bulk edit
/** @type {InventoryColumnDefinition[]} */
export const INVENTORY_AVAILABLE_COLUMNS = [
    // Item identification
    { id: 'item_id', label_en: 'Barcode', label_fr: 'Code-barre', default: true, group: 'item' },
    { id: 'title', label_en: 'Title', label_fr: 'Titre', default: true, group: 'record' },

    // Item fields (modifiable)
    { id: 'condition', label_en: 'Condition', label_fr: 'État', default: true, group: 'item' },
    { id: 'status', label_en: 'Status', label_fr: 'Statut', default: true, group: 'item' },
    { id: 'call_number', label_en: 'Call Number', label_fr: 'Cote', default: false, group: 'item' },
    { id: 'loanable', label_en: 'Loanable', label_fr: 'Empruntable', default: false, group: 'item' },
    { id: 'shelf_location', label_en: 'Location', label_fr: 'Emplacement', default: false, group: 'item' },

    // Record fields (modifiable via bulk edit)
    { id: 'level', label_en: 'Level', label_fr: 'Niveau', default: false, group: 'record' },
    { id: 'target_audience', label_en: 'Audience', label_fr: 'Public', default: false, group: 'record' },
    { id: 'language', label_en: 'Language', label_fr: 'Langue', default: false, group: 'record' },
    { id: 'medium_type', label_en: 'Medium Type', label_fr: 'Type de support', default: false, group: 'record' },

    // Inventory tracking
    { id: 'last_inventoried', label_en: 'Last Inventoried', label_fr: 'Dernier inventaire', default: false, group: 'item' }
];

export function useInventoryColumnSettings() {
    // Load from localStorage or use defaults
    const loadSettings = () => {
        const stored = getJSON(STORAGE_KEY);
        if (stored) {
            return stored;
        }
        // Return default columns
        return INVENTORY_AVAILABLE_COLUMNS.filter(col => col.default).map(col => col.id);
    };

    const visibleColumns = ref(loadSettings());

    // Save to localStorage when changed
    watch(visibleColumns, (newValue) => {
        setJSON(STORAGE_KEY, newValue);
    }, { deep: true });

    /**
     * @param {string} columnId
     */
    const isColumnVisible = (columnId) => {
        return visibleColumns.value.includes(columnId);
    };

    /**
     * @param {string} columnId
     */
    const toggleColumn = (columnId) => {
        const index = visibleColumns.value.indexOf(columnId);
        if (index > -1) {
            visibleColumns.value.splice(index, 1);
        } else {
            visibleColumns.value.push(columnId);
        }
    };

    const resetToDefaults = () => {
        visibleColumns.value = INVENTORY_AVAILABLE_COLUMNS.filter(col => col.default).map(col => col.id);
    };

    return {
        visibleColumns,
        isColumnVisible,
        toggleColumn,
        resetToDefaults
    };
}
