/**
 * Inventory Column Settings Composable
 * Manages visible columns for inventory working table with localStorage persistence
 */

const { ref, watch } = Vue;

const STORAGE_KEY = 'bcd_inventory_columns';

// Available columns for inventory working table
// Includes all fields that can be modified via bulk edit
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
    { id: 'genre', label_en: 'Genre', label_fr: 'Genre', default: false, group: 'record' },
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
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                return JSON.parse(stored);
            }
        } catch (e) {
            console.warn('Failed to load inventory column settings from localStorage', e);
        }
        // Return default columns
        return INVENTORY_AVAILABLE_COLUMNS.filter(col => col.default).map(col => col.id);
    };

    const visibleColumns = ref(loadSettings());

    // Save to localStorage when changed
    watch(visibleColumns, (newValue) => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(newValue));
        } catch (e) {
            console.warn('Failed to save inventory column settings to localStorage', e);
        }
    }, { deep: true });

    const isColumnVisible = (columnId) => {
        return visibleColumns.value.includes(columnId);
    };

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
