/**
 * Navigation Menu Component
 * Main navigation with all routes
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import NavLink from './NavLink.js';
import { altHeld } from '../../composables/useKeyboardShortcuts.js';

export default defineComponent({
    name: 'NavigationMenu',

    components: {
        NavLink
    },

    setup() {
        const { t } = useI18n();

        const navItems = computed(() => [
            { to: '/checkout', icon: 'bi-book', label: t('navigation.checkout'), shortcut: 'A' },
            { to: '/return', icon: 'bi-arrow-return-left', label: t('navigation.return'), shortcut: 'R' },
            { to: '/catalog', icon: 'bi-search', label: t('navigation.catalog'), shortcut: 'C' },
            { to: '/borrowers', icon: 'bi-people', label: t('navigation.borrowers'), shortcut: 'L' },
            { to: '/classes', icon: 'bi-diagram-3', label: t('navigation.classes'), shortcut: 'S' },
            {
                to: '/reports/overdue',
                icon: 'bi-file-earmark-bar-graph',
                label: t('navigation.reports'),
                shortcut: 'B',
                submenu: [
                    { to: '/reports/overdue', icon: 'bi-exclamation-triangle', label: t('reports.tabs.overdue') },
                    { to: '/reports/active-loans', icon: 'bi-clock-history', label: t('reports.tabs.activeLoans') },
                    { to: '/reports/holds', icon: 'bi-bookmark', label: t('reports.tabs.holds') },
                    { to: '/reports/most-borrowed', icon: 'bi-trophy', label: t('reports.tabs.mostBorrowed') },
                    { to: '/reports/never-borrowed', icon: 'bi-recycle', label: t('reports.crew.title') }
                ]
            },
            { to: '/collections', icon: 'bi-diagram-3-fill', label: t('navigation.collections'), shortcut: 'F' },
            { to: '/inventory', icon: 'bi-box-seam', label: t('navigation.inventory'), shortcut: 'I' },
            { to: '/settings', icon: 'bi-gear', label: t('navigation.settings'), shortcut: 'O' }
        ]);

        return {
            navItems,
            altHeld
        };
    },

    template: `
        <nav class="nav flex-column">
            <nav-link
                v-for="item in navItems"
                :key="item.to"
                :to="item.to"
                :icon="item.icon"
                :label="item.label"
                :submenu="item.submenu || []"
                :shortcut="item.shortcut || ''"
                :show-shortcut="altHeld"
            />
        </nav>
    `
});
