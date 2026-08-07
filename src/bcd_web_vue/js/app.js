/**
 * Main Vue 3 application initialization
 * Sets up Vue app, i18n, router, and global plugins
 */

const { createApp } = Vue;
const { createI18n } = VueI18n;

import { createAppRouter } from './router.js';
import { useAppState } from './composables/useAppState.js';
import { apiClient } from './api/client.js';
import App from './components/App.js';

/**
 * Initialize and mount the Vue app
 */
async function initApp() {
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
        // Priority: an explicit browser preference wins; otherwise the server
        // language is the library-wide default for this browser profile.

        // Fetch settings early so components (e.g. sidebar) can read library_code
        // We use apiClient with skipGlobalLoading to avoid triggering global loading indicator during bootstrap
        try {
            const settingsData = await loadSettings();
            if (settingsData) {
                if (typeof localStorage !== 'undefined' && !localStorage.getItem('locale')) {
                    setLocale(settingsData.language);
                }
            }
        } catch (e) {
            // Non-fatal: sidebar will show empty until settings load
        }

        // Load translation messages (direct fetch is justified as these are local static JSON resources)
        const [frMessages, enMessages] = await Promise.all([
            fetch('/locales/fr.json').then(async r => {
                const text = await r.text();
                if (!r.ok) throw new Error(`Failed to load fr.json: ${r.status}`);
                try {
                    return JSON.parse(text);
                } catch (e) {
                    throw new Error(`Invalid JSON in fr.json: ${text.substring(0, 100)}`);
                }
            }),
            fetch('/locales/en.json').then(async r => {
                const text = await r.text();
                if (!r.ok) throw new Error(`Failed to load en.json: ${r.status}`);
                try {
                    return JSON.parse(text);
                } catch (e) {
                    throw new Error(`Invalid JSON in en.json: ${text.substring(0, 100)}`);
                }
            })
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

        document.getElementById('app').innerHTML = `
            <div class="alert alert-danger m-5">
                <h4>Failed to load application</h4>
                <p>${error.message}</p>
                <button class="btn btn-primary" onclick="location.reload()">Reload</button>
            </div>
        `;
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
