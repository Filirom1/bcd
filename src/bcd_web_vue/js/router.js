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
        meta: { title: 'Emprunter' }
    },
    {
        path: '/return',
        name: 'return',
        component: CirculationPage,
        props: { mode: 'return' },
        meta: { title: 'Retourner' }
    },
    {
        path: '/catalog',
        name: 'catalog',
        component: CatalogPage,
        meta: { title: 'Catalogue' }
    },
    {
        path: '/catalog/:id',
        name: 'catalog-detail',
        component: CatalogPage,
        meta: { title: 'Détail du catalogue' }
    },
    {
        path: '/cataloging',
        name: 'cataloging',
        component: CatalogingPage,
        meta: { title: 'Catalogage' }
    },
    {
        path: '/borrowers',
        name: 'borrowers',
        component: BorrowersPage,
        meta: { title: 'Emprunteurs' }
    },
    {
        path: '/borrowers/:id',
        name: 'borrower-detail',
        component: BorrowersPage,
        meta: { title: 'Détail emprunteur' }
    },
    {
        path: '/classes',
        name: 'classes',
        component: ClassesPage,
        meta: { title: 'Classes' }
    },
    {
        path: '/reports/overdue/notices',
        name: 'overdue-notices',
        component: OverdueNotices,
        meta: { title: 'Feuillets de retard', layout: 'print' }
    },
    {
        path: '/reports/:type?',
        name: 'reports',
        component: ReportsPage,
        meta: { title: 'Rapports' }
    },
    {
        path: '/collections',
        name: 'collections',
        component: CollectionsPage,
        meta: { title: 'Fonds' }
    },
    {
        path: '/inventory',
        name: 'inventory',
        component: InventoryPage,
        meta: { title: 'Inventaire' }
    },
    {
        path: '/settings',
        name: 'settings',
        component: SettingsPage,
        meta: { title: 'Paramètres' }
    },
    {
        path: '/print/borrowers/reference',
        name: 'print-borrower-reference',
        component: PrintBorrowerReference,
        meta: { title: 'Impression - Fiches de reference', layout: 'print' }
    },
    {
        path: '/print/borrowers/cards',
        name: 'print-student-cards',
        component: PrintStudentCards,
        meta: { title: 'Impression - Cartes bibliotheque', layout: 'print' }
    },
    {
        path: '/print/catalog/labels',
        name: 'print-item-labels',
        component: PrintItemLabels,
        meta: { title: 'Impression - Etiquettes articles', layout: 'print' }
    }
];

/**
 * Create router instance
 * @returns {Router} Vue Router instance
 */
export function createAppRouter() {
    const router = createRouter({
        history: createWebHashHistory(),
        routes
    });

    // Update document title on route change
    router.afterEach((to) => {
        if (to.meta.title) {
            const { settings } = useAppState();
            const prefix = settings.value?.library_code || settings.value?.library_name || '';
            document.title = prefix ? `${prefix} - ${to.meta.title}` : to.meta.title;
        }
    });

    return router;
}
