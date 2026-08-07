/**
 * Borrowers Page Component
 *
 * Main page for borrower management with list, filters, pagination, and detail modal.
 * Replaces Alpine.js borrowersPage() with Vue Composition API.
 *
 * COMPARISON WITH OLD SOLUTION:
 * - OLD: Alpine.js borrowersPage() function with manual state management
 * - NEW: Vue Composition API with reactive refs and computed
 * - OLD: HTMX for loading HTML into #borrower-list-container
 * - NEW: Vue components with reactive data binding
 * - OLD: Manual event listeners for htmx:afterSwap, page:navigate
 * - NEW: Vue event handling and watchers
 * - OLD: sessionStorage for cross-page navigation (bcd_view_borrower)
 * - NEW: Vue Router with dynamic routes
 */

import BorrowerFilters from '../components/borrowers/BorrowerFilters.js';
import BorrowerList from '../components/borrowers/BorrowerList.js';
import BorrowerImport from '../components/borrowers/BorrowerImport.js';
import BulkEditModal from '../components/borrowers/BulkEditModal.js';
import BorrowerDetail from '../components/borrowers/BorrowerDetail.js';
import BorrowerAddForm from '../components/borrowers/BorrowerAddForm.js';
import AdminDropdown from '../components/admin/AdminDropdown.js';
import Pagination from '../components/ui/Pagination.js';
import { usePagination } from '../composables/usePagination.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { useNotification } from '../composables/useNotification.js';
import { useAdminShortcuts, altHeld } from '../composables/useKeyboardShortcuts.js';
import { ApiError } from '../models/error.js';
import HelpPanel from '../components/ui/HelpPanel.js';
import { useGlobalModal } from '../composables/useGlobalModal.js';
import { apiClient } from '../api/client.js';
import { normalizeCollection } from '../models/pagination.js';
import { events } from '../utils/events.js';

const { defineComponent } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'BorrowersPage',

    components: {
        BorrowerFilters,
        BorrowerList,
        BorrowerImport,
        BulkEditModal,
        BorrowerDetail,
        BorrowerAddForm,
        AdminDropdown,
        Pagination,
        HelpPanel
    },

    template: `
        <div class="borrowers-page container-fluid">
            <!-- Page Header -->
            <div class="page-header">
                <div>
                    <h1 class="page-title">
                        <i class="bi bi-people me-2"></i>
                        {{ t('borrowers.title') }}
                    </h1>
                    <p class="text-muted mb-0">{{ t('borrowers.subtitle') }}</p>
                </div>
                <div class="d-flex gap-2 align-items-center">
                <!-- Add Borrower Button -->
                <button
                    class="btn btn-primary"
                    data-testid="add-borrower-button"
                    @click="showAddModal = true"
                >
                    <i class="bi bi-person-plus me-1"></i>
                    {{ t('admin.add_borrower') }}
                    <kbd v-if="altHeld" class="admin-shortcut ms-2">N</kbd>
                    <kbd v-else class="admin-shortcut ms-2" style="visibility: hidden;">N</kbd>
                </button>

                <!-- Admin Dropdown (replaces individual Import/Export buttons) -->
                <admin-dropdown
                    :selected-count="selectedCount"
                    page="borrowers"
                    @import="handleImportClick"
                    @export="handleExport"
                    @bulk-edit="handleBulkEdit"
                    @edit-selected="handleEditSelected"
                    @print-reference="handlePrintReference"
                    @print-cards="handlePrintCards"
                ></admin-dropdown>
                <help-panel section="borrowers" />
                </div>
            </div>

            <!-- Filters -->
            <borrower-filters
                @filter-change="handleFilterChange"
            ></borrower-filters>

            <!-- Results Summary -->
            <div v-if="!loading && paginationMeta" class="d-flex justify-content-between align-items-center mb-3">
                <div class="text-muted">
                    {{ t('pagination.showing') }}
                    <strong>{{ paginationMeta.offset + 1 }}</strong>
                    -
                    <strong>{{ Math.min(paginationMeta.offset + paginationMeta.limit, paginationMeta.total) }}</strong>
                    {{ t('pagination.of') }}
                    <strong>{{ paginationMeta.total }}</strong>
                    {{ t('borrowers.borrowers') }}
                </div>
            </div>

            <!-- Borrower List -->
            <borrower-list
                :borrowers="borrowers"
                :loading="loading"
                @view-borrower="openBorrowerDetail"
                @selection-changed="handleSelectionChanged"
            ></borrower-list>

            <!-- Pagination -->
            <pagination
                v-if="paginationMeta && paginationMeta.total > 0"
                :current-page="currentPage"
                :total-pages="totalPages"
                :page-size="pageSize"
                :total-items="paginationMeta.total"
                @page-change="handlePageChange"
                @page-size-change="handlePageSizeChange"
            ></pagination>

            <!-- Import CSV Modal -->
            <borrower-import
                :show="showBorrowerImport"
                @close="showBorrowerImport = false"
                @import-complete="handleImportComplete"
            ></borrower-import>

            <!-- Bulk Edit Modal -->
            <bulk-edit-modal
                :show="showBulkEditModal"
                :selected-borrowers="selectedBorrowers"
                @close="closeBulkEditModal"
                @execute="handleBulkOperation"
            ></bulk-edit-modal>

            <!-- Edit Single Borrower / Detail Modal -->
            <borrower-detail
                v-if="selectedBorrower && showEditModal"
                :borrower-id="selectedBorrower.borrower_id"
                :borrower="selectedBorrower"
                :show="showEditModal"
                initial-mode="edit"
                @update:show="showEditModal = $event"
                @saved="handleBorrowerSaved"
                @deleted="handleBorrowerDeleted"
                @close="showEditModal = false"
            />

            <!-- Add Borrower Modal -->
            <borrower-add-form
                :show="showAddModal"
                @update:show="showAddModal = $event"
                @created="handleBorrowerCreated"
            ></borrower-add-form>
        </div>
    `,

    setup() {
        const { t } = useI18n();
        const { handleError } = useErrorHandler(t);
        const { success } = useNotification();
        const { openBorrower, openRecord } = useGlobalModal();

        // State
        const borrowers = Vue.ref([]);
        const loading = Vue.ref(false);
        const filters = Vue.ref({});

        // Bulk edit state
        const selectedBorrowerIds = Vue.ref([]);
        const showBulkEditModal = Vue.ref(false);
        const bulkOperationInProgress = Vue.ref(false);

        // Edit single borrower state
        const showEditModal = Vue.ref(false);
        const selectedBorrower = Vue.ref(null);

        // Add borrower state
        const showAddModal = Vue.ref(false);

        // Pagination
        const {
            currentPage,
            pageSize,
            totalItems,
            totalPages,
            offset,
            firstItem,
            lastItem,
            goToPage,
            setPageSize,
            setTotalItems
        } = usePagination();

        // Create paginationMeta for template compatibility
        const paginationMeta = Vue.computed(() => ({
            total: totalItems.value,
            offset: offset.value,
            limit: pageSize.value,
            page: currentPage.value,
            page_size: pageSize.value
        }));

        // Load borrowers from API
        const loadBorrowers = async () => {
            loading.value = true;

            try {
                // Build query parameters
                const params = {
                    page: currentPage.value,
                    page_size: pageSize.value,
                    ...filters.value
                };

                const data = await apiClient.get('/borrowers', params);

                const normalized = normalizeCollection(data);
                borrowers.value = normalized.items;
                setTotalItems(normalized.pagination.total_items);

            } catch (error) {
                handleError(error);
                borrowers.value = [];
            } finally {
                loading.value = false;
            }
        };

        // Handle filter change
        const handleFilterChange = (newFilters) => {
            filters.value = newFilters;
            goToPage(1); // Reset to first page when filters change
            loadBorrowers();
        };

        // Handle page change
        const handlePageChange = (page) => {
            goToPage(page);
            loadBorrowers();
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };

        // Handle page size change
        const handlePageSizeChange = (size) => {
            setPageSize(size);
            goToPage(1); // Reset to first page
            loadBorrowers();
        };

        // Open borrower detail modal (global, no URL change)
        const openBorrowerDetail = (borrowerId) => {
            openBorrower(borrowerId);
        };

        // Handle borrower updated (after block/unblock/renew)
        const handleBorrowerUpdated = (action) => {
            // Reload borrower list to reflect changes
            loadBorrowers();
        };

        // Handle import complete
        const handleImportComplete = (result) => {
            // Reload borrower list to show newly imported borrowers
            loadBorrowers();
        };

        // Handle import button click (from admin dropdown)
        const showBorrowerImport = Vue.ref(false);
        const handleImportClick = () => { showBorrowerImport.value = true; };

        // Computed: Selected borrowers (full objects)
        const selectedBorrowers = Vue.computed(() => {
            return borrowers.value.filter(b => selectedBorrowerIds.value.includes(b.borrower_id));
        });

        // Computed: Selected count
        const selectedCount = Vue.computed(() => selectedBorrowerIds.value.length);

        // Handle selection changed from BorrowerList
        const handleSelectionChanged = (ids) => {
            selectedBorrowerIds.value = ids;
        };

        // Open bulk edit modal
        const openBulkEditModal = () => {
            showBulkEditModal.value = true;
        };

        // Close bulk edit modal
        const closeBulkEditModal = () => {
            showBulkEditModal.value = false;
        };

        // Handle bulk edit (from admin dropdown)
        const handleBulkEdit = () => {
            if (selectedCount.value >= 1) {
                openBulkEditModal();
            }
        };

        // Handle edit selected (from admin dropdown)
        const handleEditSelected = () => {
            if (selectedCount.value === 1) {
                // Get the selected borrower
                selectedBorrower.value = selectedBorrowers.value[0];
                showEditModal.value = true;
            }
        };

        // Handle borrower created from add modal
        const handleBorrowerCreated = (newBorrower) => {
            success(t('admin.borrower.add.success'));
            showAddModal.value = false;
            loadBorrowers();
        };

        // Handle borrower saved from edit modal
        const handleBorrowerSaved = (updatedBorrower) => {
            // Show success notification
            success(t('admin.borrower_updated'));

            // Clear selection
            selectedBorrowerIds.value = [];

            // Close modal
            showEditModal.value = false;

            // Reload borrowers to get updated data
            loadBorrowers();
        };

        // Handle borrower deleted from edit modal
        const handleBorrowerDeleted = (borrower_id) => {
            // Show success notification
            success(t('admin.borrower_deleted'));

            // Close detail modal if it was showing the deleted borrower
            if (selectedBorrowerId.value === borrower_id) {
                closeBorrowerDetail();
            }

            // Clear selection
            selectedBorrowerIds.value = [];

            // Close edit modal
            showEditModal.value = false;

            // Reload borrowers to reflect deletion
            loadBorrowers();
        };

        // Handle bulk operation execution
        const handleBulkOperation = async (payload) => {
            bulkOperationInProgress.value = true;

            try {
                const { operation, targetClassId } = payload;

                let endpoint = '';
                let requestBody = {
                    borrower_ids: selectedBorrowerIds.value
                };

                // Determine endpoint and request body
                if (operation === 'change_class') {
                    endpoint = '/api/v1/admin/borrowers/bulk-change-class';
                    requestBody.target_class_id = targetClassId;
                } else if (operation === 'delete') {
                    endpoint = '/api/v1/admin/borrowers/bulk-delete';
                }

                // Execute operation
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestBody)
                });

                if (!response.ok) {
                    const apiError = await ApiError.fromResponse(response);
                    throw apiError;
                }

                const result = await response.json();

                // Show success notification
                let operationName = '';
                if (operation === 'change_class') {
                    operationName = t('admin.change_class');
                } else if (operation === 'delete') {
                    operationName = t('admin.delete');
                }

                success(
                    t('admin.operation_success', {
                        operation: operationName.toLowerCase(),
                        count: result.successful_count,
                        type: t('borrowers.borrowers')
                    })
                );

                // Close modal
                closeBulkEditModal();

                // Clear selection
                selectedBorrowerIds.value = [];

                // Reload borrower list
                await loadBorrowers();
                events.emit('borrowers:refresh');

            } catch (error) {
                handleError(error);
            } finally {
                bulkOperationInProgress.value = false;
            }
        };

        // Export borrowers to CSV
        const exportLoading = Vue.ref(false);

        const handleExport = async () => {
            exportLoading.value = true;

            try {
                // Call export endpoint
                const blob = await apiClient.get('/borrowers/export', {}, { responseType: 'blob' });

                let filename = 'borrowers_export.csv';

                // Trigger download
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                // Show success message
                const { success } = useNotification();
                success(t('borrowers.export_success'));

            } catch (error) {
                handleError(error);
            } finally {
                exportLoading.value = false;
            }
        };

        // Handle print reference sheets (from admin dropdown)
        const handlePrintReference = () => {
            const params = new URLSearchParams();
            // Pass current class filter to print page if active
            if (filters.value.class_id) {
                params.set('class_ids', filters.value.class_id);
            }
            const query = params.toString();
            window.open(`#/print/borrowers/reference${query ? '?' + query : ''}`, '_blank');
        };

        // Handle print student cards (from admin dropdown)
        const handlePrintCards = () => {
            const params = new URLSearchParams();
            if (filters.value.class_id) {
                params.set('class_ids', filters.value.class_id);
            }
            const query = params.toString();
            window.open(`#/print/borrowers/cards${query ? '?' + query : ''}`, '_blank');
        };

        useAdminShortcuts({ N: () => { showAddModal.value = true; } });

        // Load borrowers on mount and subscribe to refresh events
        const unsubscribe = events.on('borrowers:refresh', () => {
            loadBorrowers();
        });
        Vue.onBeforeUnmount(unsubscribe);

        Vue.onMounted(() => {
            loadBorrowers();
        });

        return {
            t,
            borrowers,
            loading,
            filters,
            currentPage,
            pageSize,
            totalPages,
            paginationMeta,
            exportLoading,
            selectedBorrowerIds,
            selectedBorrowers,
            selectedCount,
            showBulkEditModal,
            bulkOperationInProgress,
            showEditModal,
            selectedBorrower,
            showAddModal,
            handleBorrowerCreated,
            handleFilterChange,
            handlePageChange,
            handlePageSizeChange,
            openBorrowerDetail,
            handleBorrowerUpdated,
            showBorrowerImport,
            handleImportComplete,
            handleImportClick,
            handleExport,
            handleSelectionChanged,
            handleBulkEdit,
            handleEditSelected,
            handleBorrowerSaved,
            handleBorrowerDeleted,
            openBulkEditModal,
            closeBulkEditModal,
            handleBulkOperation,
            handlePrintReference,
            handlePrintCards,
            altHeld
        };
    }
});
