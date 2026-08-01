/**
 * Global application state composable
 * Manages locale, loading state, and settings with localStorage persistence
 */

const { ref, computed, watch } = Vue;
import { getItem, setItem, removeItem, getJSON, setJSON, clearStorage as apiClearStorage } from '../utils/storage.js';

// Global reactive state (shared across all component instances)
const locale = ref(getItem('locale', 'fr'));
const isLoading = ref(false);
const settings = ref(null);

// Persist locale changes to localStorage (declared once at module level to avoid duplicate watchers)
watch(locale, (newLocale) => {
    setItem('locale', newLocale);
    document.documentElement.lang = newLocale;
}, { immediate: true });

/**
 * Application state composable
 * @returns {Object} App state and methods
 */
export function useAppState() {
    /**
     * Set locale and persist to localStorage
     * @param {string} newLocale - Locale code ('fr' or 'en')
     */
    const setLocale = (newLocale) => {
        if (newLocale === 'fr' || newLocale === 'en') {
            locale.value = newLocale;
        }
    };

    /**
     * Toggle between FR and EN
     */
    const toggleLocale = () => {
        locale.value = locale.value === 'fr' ? 'en' : 'fr';
    };

    /**
     * Set loading state
     * @param {boolean} loading - Whether app is loading
     */
    const setLoading = (loading) => {
        isLoading.value = loading;
    };

    /**
     * Load settings from localStorage
     */
    const loadSettings = () => {
        const stored = getJSON('settings');
        if (stored) {
            settings.value = stored;
        } else {
            settings.value = null;
        }
    };

    /**
     * Save settings to localStorage
     * @param {Object} newSettings - Settings object to save
     */
    const saveSettings = (newSettings) => {
        settings.value = newSettings;
        setJSON('settings', newSettings);
    };

    /**
     * Clear all stored data
     */
    const clearStorage = () => {
        apiClearStorage();
        locale.value = 'fr';
        settings.value = null;
    };

    return {
        // State
        locale: computed(() => locale.value),
        isLoading: computed(() => isLoading.value),
        settings: computed(() => settings.value),

        // Methods
        setLocale,
        toggleLocale,
        setLoading,
        loadSettings,
        saveSettings,
        clearStorage
    };
}
