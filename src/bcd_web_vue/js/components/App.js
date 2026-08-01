/**
 * Main App Component
 * Root component with sidebar, notifications, and router view.
 * Also hosts global record and borrower detail modals so they can be opened
 * from any page without URL changes (see useGlobalModal).
 */

const { defineComponent, ref, onMounted } = Vue;
const { useRoute } = VueRouter;
const { useI18n } = VueI18n;
import SidebarNav from './layout/SidebarNav.js';
import NotificationContainer from './ui/NotificationContainer.js';
import RecordDetail from './catalog/RecordDetail.js';
import BorrowerDetail from './borrowers/BorrowerDetail.js';
import { useAppState } from '../composables/useAppState.js';
import { useKeyboardShortcuts } from '../composables/useKeyboardShortcuts.js';
import { useGlobalModal } from '../composables/useGlobalModal.js';
import { useNotification } from '../composables/useNotification.js';
import { apiClient } from '../api/client.js';

export default defineComponent({
    name: 'App',

    components: {
        SidebarNav,
        NotificationContainer,
        RecordDetail,
        BorrowerDetail,
    },

    setup() {
        const { t } = useI18n();
        const { isLoading } = useAppState();
        const { success, error: showError, warning } = useNotification();
        useKeyboardShortcuts();
        const appReady = ref(false);
        const route = useRoute();
        const isPrintLayout = Vue.computed(() => route.meta?.layout === 'print');

        const {
            globalRecordId,
            globalBorrowerId,
            catalogRefreshTick,
            openRecord,
            closeRecord,
            openBorrower,
            closeBorrower,
        } = useGlobalModal();

        // Quick-return an item from RecordDetail (opened from any page)
        const handleGlobalQuickReturn = async (itemId) => {
            const currentRecordId = globalRecordId.value;
            try {
                const result = await apiClient.post('/circulation/return', {
                    item_ids: [itemId],
                    returned_by: 'web-ui',
                });
                const returned = result.items?.[0];
                const titleDisplay = returned?.display_title || returned?.title || itemId;
                
                let locationParts = [];
                if (returned?.shelf_location) locationParts.push(returned.shelf_location);
                if (returned?.call_number) locationParts.push(returned.call_number);
                
                const locationText = locationParts.length > 0 ? locationParts.join(' / ') : '-';
                const shelfInfo = ` — ${t('circulation.ranger')} : ${locationText}`;
                success(`✓ ${titleDisplay}${shelfInfo}`);
                if (returned?.hold_ready) {
                    const hr = returned.hold_ready;
                    warning(t('circulation.hold_ready_message', {
                        name: hr.borrower_name,
                        class: hr.class_name || hr.borrower_id,
                    }));
                }
                // Reload RecordDetail by toggling the ID
                closeRecord();
                Vue.nextTick(() => openRecord(currentRecordId));
                // Signal CatalogPage to refresh its search results
                catalogRefreshTick.value++;
            } catch (err) {
                showError(err.message || t('common.error'));
            }
        };

        // View borrower from RecordDetail → close record, open borrower
        const handleGlobalViewBorrower = (borrowerId) => {
            closeRecord();
            openBorrower(borrowerId);
        };

        // View record from BorrowerDetail → close borrower, open record
        const handleGlobalViewItem = (recordId) => {
            closeBorrower();
            openRecord(recordId);
        };

        onMounted(() => {
            appReady.value = true;
        });

        return {
            isLoading,
            appReady,
            route,
            isPrintLayout,
            globalRecordId,
            globalBorrowerId,
            closeRecord,
            closeBorrower,
            handleGlobalQuickReturn,
            handleGlobalViewBorrower,
            handleGlobalViewItem,
            t,
        };
    },

    template: `
        <div class="d-flex w-100 min-vh-100">
            <!-- Loading overlay -->
            <div
                v-if="isLoading"
                class="loading-overlay"
            >
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">{{ t('common.loading') }}</span>
                </div>
            </div>

            <!-- Notification container (toasts) -->
            <notification-container />

            <!-- Sidebar -->
            <sidebar-nav v-if="!isPrintLayout" />

            <!-- Main content area -->
            <main class="main-content">
                <router-view v-if="appReady" :key="route.path" />
                <div v-else class="text-center p-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">{{ t('common.loading') }}</span>
                    </div>
                    <p class="mt-3 text-muted">{{ t('app.loading_app') }}</p>
                </div>
            </main>

            <!-- Global Record Detail Modal (opened from any page via useGlobalModal) -->
            <record-detail
                :record-id="globalRecordId"
                :show="globalRecordId !== null"
                @close="closeRecord"
                @quick-return="handleGlobalQuickReturn"
                @view-borrower="handleGlobalViewBorrower"
            />

            <!-- Global Borrower Detail Modal (opened from any page via useGlobalModal) -->
            <borrower-detail
                v-if="globalBorrowerId !== null"
                :borrower-id="String(globalBorrowerId)"
                :show="true"
                @close="closeBorrower"
                @updated="() => {}"
                @view-item="handleGlobalViewItem"
            />
        </div>
    `
});
