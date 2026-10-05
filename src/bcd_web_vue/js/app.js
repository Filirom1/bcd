/**
 * Main Vue 3 application initialization
 * Sets up Vue app, i18n, router, and global plugins
 */

const { createApp } = Vue;
const { createI18n } = VueI18n;

import { createAppRouter } from './router.js';
import { useAppState } from './composables/useAppState.js';
import { getItem } from './utils/storage.js';
import { apiClient } from './api/client.js';
import App from './components/App.js';

/**
 * Initialize and mount the Vue app
 */
export async function initApp() {
    let bootstrapMessages = {};
    let activeLocale = 'fr';

    // Initialize global test state BEFORE async operations
    if (typeof window !== 'undefined') {
        window.__BCD_APP__ = {
            ready: false,
            error: null,
            router: null,
            i18n: null,
            version: '1.0.0'
        };
    }

    try {
        // Get initial locale from app state
        const { locale, setLocale, loadSettings } = useAppState();
        activeLocale = locale.value;
        // Priority: an explicit browser preference wins; otherwise the server
        // language is the library-wide default for this browser profile.

        // Fetch settings early so components (e.g. sidebar) can read library_code
        // We use apiClient with skipGlobalLoading to avoid triggering global loading indicator during bootstrap
        try {
            const settingsData = await loadSettings();
            if (settingsData) {
                // Check through the BCD storage adapter. The adapter prefixes
                // keys, so reading raw localStorage('locale') would always
                // miss the user's persisted language choice.
                if (getItem('locale') === null) {
                    setLocale(settingsData.language);
                }
            }
        } catch (e) {
            // Non-fatal: sidebar will show empty until settings load
        }
        activeLocale = locale.value;

        // Load translation messages (direct fetch is justified as these are local static JSON resources).
        // Store each language as soon as it loads so the startup error can use
        // whichever bundle remains available if the other one is malformed.
        const loadMessages = async (language) => {
            const response = await fetch(`/locales/${language}.json`);
            const text = await response.text();
            if (!response.ok) throw new Error(`Failed to load ${language}.json: ${response.status}`);
            try {
                const messages = JSON.parse(text);
                bootstrapMessages[language] = messages;
                return messages;
            } catch (error) {
                throw new Error(`Invalid JSON in ${language}.json: ${text.substring(0, 100)}`);
            }
        };
        const [frMessages, enMessages] = await Promise.all([
            loadMessages('fr'),
            loadMessages('en')
        ]);

        // Create i18n instance
        const i18n = createI18n({
            legacy: false, // Use Composition API mode
            locale: locale.value,
            fallbackLocale: 'fr',
            messages: {
                fr: frMessages,
                en: enMessages
            },
            datetimeFormats: {
                en: {
                    short: {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                    },
                    long: {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        weekday: 'long'
                    }
                },
                fr: {
                    short: {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                    },
                    long: {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        weekday: 'long'
                    }
                }
            }
        });

        // Create router
        const router = createAppRouter(i18n);

        // Create Vue app
        const app = createApp(App);

        // Configure API client to use app state and i18n
        apiClient.getLocale = () => i18n.global.locale.value;
        const { setLoading } = useAppState();
        apiClient.onLoadingChange = setLoading;

        // Install plugins
        app.use(i18n);
        app.use(router);

        // Enable Vue devtools
        app.config.devtools = true;

        // Global error handler
        app.config.errorHandler = (err, instance, info) => {
            console.error('Vue error:', err, info);
        };

        // Mount app
        app.mount('#app');

        // Fade out beautiful loading screen
        const loadingScreen = document.querySelector('.bcd-loading');
        if (loadingScreen) {
            loadingScreen.style.transition = 'opacity 0.5s ease-out';
            loadingScreen.style.opacity = '0';
            setTimeout(() => {
                loadingScreen.remove();
            }, 500);
        }

        // ✅ Mark app as ready for E2E tests
        if (typeof window !== 'undefined') {
            window.__BCD_APP__.ready = true;
            window.__BCD_APP__.router = router;
            window.__BCD_APP__.i18n = i18n;

            // Expose useful test helpers
            window.__BCD_APP__.navigate = (path) => router.push(path);
            window.__BCD_APP__.setLocale = (locale) => { i18n.global.locale.value = locale; };
        }

        // Initialization is intentionally silent in production.

    } catch (error) {
        console.error('❌ Failed to initialize app:', error);

        // ✅ Expose error to E2E tests
        if (typeof window !== 'undefined') {
            window.__BCD_APP__.error = {
                message: error.message,
                stack: error.stack
            };
        }

        // Remove loading screen on error
        const loadingScreen = document.querySelector('.bcd-loading');
        if (loadingScreen) {
            loadingScreen.remove();
        }

        const messages = bootstrapMessages[activeLocale]
            || bootstrapMessages.fr
            || bootstrapMessages.en
            || {};
        const emergencyText = activeLocale === 'fr'
            ? { title: "Impossible de charger l'application", reload: 'Recharger' }
            : { title: 'Unable to load the application', reload: 'Reload' };
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger m-5';

        const heading = document.createElement('h4');
        heading.textContent = messages.app?.startup_error_title || emergencyText.title;
        alert.appendChild(heading);

        // Preserve the diagnostic detail for the user, but add it as text so
        // an error response can never be interpreted as HTML.
        const detail = document.createElement('p');
        detail.textContent = error?.message || '';
        alert.appendChild(detail);

        const reload = document.createElement('button');
        reload.className = 'btn btn-primary';
        reload.textContent = messages.common?.reload || emergencyText.reload;
        reload.addEventListener('click', () => window.location.reload());
        alert.appendChild(reload);

        const appContainer = document.getElementById('app');
        if (appContainer) appContainer.replaceChildren(alert);
    }
}

// Initialize app when DOM is ready. Tests can import initApp without starting a
// second application instance by setting this opt-out before module evaluation.
if (typeof window !== 'undefined' && !window.__BCD_DISABLE_AUTO_INIT__) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApp);
    } else {
        initApp();
    }
}
