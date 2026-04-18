/**
 * Global application state composable
 * Manages locale, loading state, and settings with localStorage persistence
 */

const { ref, computed, watch } = Vue;

// Safe localStorage access helper
const safeGetItem = (key, defaultValue = null) => {
    try {
        return localStorage.getItem(key) || defaultValue;
    } catch (e) {
        console.warn(`localStorage.getItem('${key}') blocked by browser:`, e.message);
        return defaultValue;
    }
};

const safeSetItem = (key, value) => {
    try {
        localStorage.setItem(key, value);
    } catch (e) {
        console.warn(`localStorage.setItem('${key}') blocked by browser:`, e.message);
    }
};

const safeRemoveItem = (key) => {
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.warn(`localStorage.removeItem('${key}') blocked by browser:`, e.message);
    }
};

// Global reactive state (shared across all component instances)
const locale = ref(safeGetItem('bcd_locale', 'fr'));
const isLoading = ref(false);
const settings = ref(null);

/**
 * Application state composable
 * @returns {Object} App state and methods
 */
export function useAppState() {
    // Persist locale changes to localStorage
    watch(locale, (newLocale) => {
        safeSetItem('bcd_locale', newLocale);
        document.documentElement.lang = newLocale;
    }, { immediate: true });

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
        const stored = safeGetItem('bcd_settings');
        if (stored) {
            try {
                settings.value = JSON.parse(stored);
            } catch (e) {
                console.error('Failed to parse stored settings:', e);
                settings.value = null;
            }
        }
    };

    /**
     * Save settings to localStorage
     * @param {Object} newSettings - Settings object to save
     */
    const saveSettings = (newSettings) => {
        settings.value = newSettings;
        safeSetItem('bcd_settings', JSON.stringify(newSettings));
    };

    /**
     * Clear all stored data
     */
    const clearStorage = () => {
        safeRemoveItem('bcd_locale');
        safeRemoveItem('bcd_settings');
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
