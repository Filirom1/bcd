// @ts-check
/**
 * Column Settings Composable
 * Manages visible columns with localStorage persistence
 */

const { ref, watch } = Vue;
import { getJSON, setJSON } from '../utils/storage.js';

const STORAGE_KEY = 'catalog_columns';

/**
 * @typedef {Object} ColumnDefinition
 * @property {string} id
 * @property {string} label_en
 * @property {string} label_fr
 * @property {boolean} default
 */

// Available columns (18 total - matches SearchResults.js table columns)
/** @type {ColumnDefinition[]} */
export const AVAILABLE_COLUMNS = [
    // Basic information (default visible)
    { id: 'title', label_en: 'Title', label_fr: 'Titre', default: true },
    { id: 'author', label_en: 'Author', label_fr: 'Auteur', default: true },
    { id: 'isbn', label_en: 'ISBN', label_fr: 'ISBN', default: false },

    // Publication information
    { id: 'publisher', label_en: 'Publisher', label_fr: 'Éditeur', default: true },
    { id: 'year', label_en: 'Year', label_fr: 'Année', default: true },
    { id: 'collection', label_en: 'Collection/Series', label_fr: 'Collection/Série', default: false },
    { id: 'series_number', label_en: 'Volume', label_fr: 'Volume', default: false },

    // Classification
    { id: 'medium_type', label_en: 'Medium Type', label_fr: 'Type de support', default: false },
    { id: 'target_audience', label_en: 'Audience', label_fr: 'Public', default: false },
    { id: 'level', label_en: 'Level', label_fr: 'Niveau', default: false },
    { id: 'language', label_en: 'Language', label_fr: 'Langue', default: false },

    // Physical description
    { id: 'binding_type', label_en: 'Binding', label_fr: 'Reliure', default: false },
    { id: 'page_count', label_en: 'Pages', label_fr: 'Pages', default: false },
    { id: 'has_illustrations', label_en: 'Illustrations', label_fr: 'Illustrations', default: false },

    // Availability (default visible)
    { id: 'copies', label_en: 'Copies', label_fr: 'Exemplaires', default: true },
    { id: 'availability', label_en: 'Availability', label_fr: 'Disponibilité', default: true }
];

export function useColumnSettings() {
    // Load from localStorage or use defaults
    const loadSettings = () => {
        const stored = getJSON(STORAGE_KEY);
        if (stored) {
            return stored;
        }
        // Return default columns (matching mockup)
        return AVAILABLE_COLUMNS.filter(col => col.default).map(col => col.id);
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
        visibleColumns.value = AVAILABLE_COLUMNS.filter(col => col.default).map(col => col.id);
    };

    return {
        visibleColumns,
        isColumnVisible,
        toggleColumn,
        resetToDefaults
    };
}
