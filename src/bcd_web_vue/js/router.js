/**
 * Vue Router configuration
 * Defines all routes for the BCD web application
 */

const { createRouter, createWebHashHistory } = VueRouter;

// Import all page components
import { useAppState } from './composables/useAppState.js';
import CirculationPage from './pages/CirculationPage.js';
import CatalogPage from './pages/CatalogPage.js';
import CatalogingPage from './pages/CatalogingPage.js';
import BorrowersPage from './pages/BorrowersPage.js';
import ClassesPage from './pages/ClassesPage.js';
import ReportsPage from './pages/ReportsPage.js';
import CollectionsPage from './pages/CollectionsPage.js';
import SettingsPage from './pages/SettingsPage.js';
import PrintBorrowerReference from './pages/PrintBorrowerReference.js';
import PrintStudentCards from './pages/PrintStudentCards.js';
import PrintItemLabels from './pages/PrintItemLabels.js';
import InventoryPage from './pages/InventoryPage.js';
import OverdueNotices from './components/reports/OverdueNotices.js';

// Route definitions
const routes = [
    {
        path: '/',
        redirect: '/checkout'
    },
    {
        path: '/checkout',
        name: 'checkout',
        component: CirculationPage,
        meta: { titleKey: 'navigation.checkout' }
    },
    {
        path: '/return',
        name: 'return',
        component: CirculationPage,
        props: { mode: 'return' },
        meta: { titleKey: 'navigation.return' }
    },
    {
        path: '/catalog',
        name: 'catalog',
        component: CatalogPage,
        meta: { titleKey: 'navigation.catalog' }
    },
    {
        path: '/catalog/:id',
        name: 'catalog-detail',
        component: CatalogPage,
        meta: { titleKey: 'navigation.catalog_detail' }
    },
    {
        path: '/cataloging',
        name: 'cataloging',
        component: CatalogingPage,
        meta: { titleKey: 'navigation.cataloging' }
    },
    {
        path: '/borrowers',
        name: 'borrowers',
        component: BorrowersPage,
        meta: { titleKey: 'navigation.borrowers' }
    },
    {
        path: '/borrowers/:id',
        name: 'borrower-detail',
        component: BorrowersPage,
        meta: { titleKey: 'navigation.borrower_detail' }
    },
    {
        path: '/classes',
        name: 'classes',
        component: ClassesPage,
        meta: { titleKey: 'navigation.classes' }
    },
    {
        path: '/reports/overdue/notices',
        name: 'overdue-notices',
        component: OverdueNotices,
        meta: { titleKey: 'navigation.overdue_notices', layout: 'print' }
    },
    {
        path: '/reports/:type?',
        name: 'reports',
        component: ReportsPage,
        meta: { titleKey: 'navigation.reports' }
    },
    {
        path: '/collections',
        name: 'collections',
        component: CollectionsPage,
        meta: { titleKey: 'navigation.collections' }
    },
    {
        path: '/inventory',
        name: 'inventory',
        component: InventoryPage,
        meta: { titleKey: 'navigation.inventory' }
    },
    {
        path: '/settings',
        name: 'settings',
        component: SettingsPage,
        meta: { titleKey: 'navigation.settings' }
    },
    {
        path: '/print/borrowers/reference',
        name: 'print-borrower-reference',
        component: PrintBorrowerReference,
        meta: { titleKey: 'navigation.print_borrowers_reference', layout: 'print' }
    },
    {
        path: '/print/borrowers/cards',
        name: 'print-student-cards',
        component: PrintStudentCards,
        meta: { titleKey: 'navigation.print_student_cards', layout: 'print' }
    },
    {
        path: '/print/catalog/labels',
        name: 'print-item-labels',
        component: PrintItemLabels,
        meta: { titleKey: 'navigation.print_item_labels', layout: 'print' }
    }
];

/**
 * Create router instance
 * @param {Object} i18n - VueI18n instance
 * @returns {Router} Vue Router instance
 */
export function createAppRouter(i18n) {
    const router = createRouter({
        history: createWebHashHistory(),
        routes
    });

    const updateTitle = (to) => {
        if (to && to.meta && to.meta.titleKey) {
            const { settings } = useAppState();
            const prefix = settings.value?.library_code || settings.value?.library_name || '';
            const translatedTitle = i18n ? i18n.global.t(to.meta.titleKey) : to.meta.titleKey;
            document.title = prefix ? `${prefix} - ${translatedTitle}` : translatedTitle;
        }
    };

    // Update document title on route change
    router.afterEach((to) => {
        updateTitle(to);
    });

    // Update document title on language change
    if (i18n) {
        Vue.watch(i18n.global.locale, () => {
            updateTitle(router.currentRoute.value);
        });
    }

    return router;
}
