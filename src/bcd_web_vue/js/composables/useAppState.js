// @ts-check
/**
 * Global application state composable
 * Manages locale, loading state, and settings with localStorage persistence
 */

const { ref, computed, watch } = Vue;
import { getItem, setItem, removeItem, getJSON, setJSON, clearStorage as apiClearStorage } from '../utils/storage.js';
import { apiClient } from '../api/client.js';

// Global reactive state (shared across all component instances)
const locale = ref(getItem('locale', 'fr'));
const isLoading = ref(false);
/** @type {import('vue').Ref<import('../api/client.js').SystemSettings | null>} */
const settings = ref(null);

/** @type {Promise<import('../api/client.js').SystemSettings | null> | null} */
let settingsPromise = null;

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
     * Load settings from API (with caching/deduplication)
     * @param {{ force?: boolean }} [options] - Options
     * @returns {Promise<import('../api/client.js').SystemSettings | null>}
     */
    const loadSettings = async ({ force = false } = {}) => {
        // Return existing settings if loaded and force is false
        if (settings.value && !force) {
            return settings.value;
        }

        // Return active promise if already loading and force is false
        if (settingsPromise && !force) {
            return settingsPromise;
        }

        settingsPromise = (async () => {
            try {
                // Pre-populate settings from localStorage if available
                if (!settings.value) {
                    const stored = getJSON('settings');
                    if (stored) {
                        settings.value = stored;
                    }
                }

                const settingsData = await apiClient.get('/admin/settings', {}, { skipGlobalLoading: true });
                if (settingsData) {
                    settings.value = settingsData;
                    setJSON('settings', settingsData);
                    return settingsData;
                }
            } catch (err) {
                console.error('Failed to load settings:', err);
                // Fallback to local storage if API fails
                const stored = getJSON('settings');
                if (stored) {
                    settings.value = stored;
                    return stored;
                }
            } finally {
                settingsPromise = null;
            }
            return null;
        })();

        return settingsPromise;
    };

    /**
     * Save settings to localStorage
     * @param {import('../api/client.js').SystemSettings} newSettings - Settings object to save
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
