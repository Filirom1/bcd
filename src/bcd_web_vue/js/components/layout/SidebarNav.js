/**
 * Sidebar Navigation Component
 * Contains logo, navigation menu, and language switcher
 */

const { defineComponent, computed, ref, onMounted } = Vue;
import NavigationMenu from './NavigationMenu.js';
import LanguageSwitcher from './LanguageSwitcher.js';
import { useAppState } from '../../composables/useAppState.js';
import { apiClient } from '../../api/client.js';

export default defineComponent({
    name: 'SidebarNav',

    components: {
        NavigationMenu,
        LanguageSwitcher
    },

    setup() {
        const { settings } = useAppState();
        const brandName = computed(() => settings.value?.library_code || '');
        const appVersion = ref('');

        onMounted(async () => {
            try {
                appVersion.value = (await apiClient.get('/health')).version || '';
            } catch (e) {
                // Non-fatal: hide version if API is unavailable
            }
        });

        return { brandName, appVersion };
    },

    template: `
        <aside class="sidebar d-flex flex-column">
            <!-- Logo/Brand -->
            <div class="p-3 border-bottom">
                <div class="d-flex align-items-center">
                    <i class="bi bi-book text-primary fs-3 me-2"></i>
                    <h1 class="h4 mb-0 fw-bold text-primary">{{ brandName }}</h1>
                </div>
            </div>

            <!-- Navigation Menu -->
            <div class="flex-grow-1 py-3">
                <navigation-menu />
            </div>

            <!-- Footer: Language Switcher + Version -->
            <div class="p-3 border-top">
                <language-switcher />
                <div v-if="appVersion" class="text-muted small mt-2">v{{ appVersion }}</div>
                <div class="text-muted small mt-1" title="Libre d'usage et de modification">
                    <a class="text-muted text-decoration-none" href="https://github.com/Filirom1/bcd" target="_blank" rel="noopener">
                        <i class="bi bi-unlock me-1"></i>Logiciel libre
                    </a>
                </div>
            </div>
        </aside>
    `
});
