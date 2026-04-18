/**
 * Sidebar Navigation Component
 * Contains logo, navigation menu, and language switcher
 */

const { defineComponent, computed } = Vue;
import NavigationMenu from './NavigationMenu.js';
import LanguageSwitcher from './LanguageSwitcher.js';
import { useAppState } from '../../composables/useAppState.js';

export default defineComponent({
    name: 'SidebarNav',

    components: {
        NavigationMenu,
        LanguageSwitcher
    },

    setup() {
        const { settings } = useAppState();
        const brandName = computed(() => settings.value?.library_code || '');
        return { brandName };
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
                <div class="text-muted small mt-2">v1.0.0</div>
                <div class="text-muted small mt-1" title="Libre d'usage et de modification">
                    <i class="bi bi-unlock me-1"></i>Logiciel libre
                </div>
            </div>
        </aside>
    `
});
