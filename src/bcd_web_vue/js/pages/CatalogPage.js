/**
 * Catalog Page Component
 * Search and browse bibliographic records
 */

const { defineComponent, ref, reactive, computed, onMounted, watch } = Vue;
const { useI18n } = VueI18n;
const { useRoute, useRouter } = VueRouter;
import { apiClient } from '../api/client.js';
import { useAppState } from '../composables/useAppState.js';
import { useNotification } from '../composables/useNotification.js';
import { useAdminShortcuts, altHeld } from '../composables/useKeyboardShortcuts.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { usePagination } from '../composables/usePagination.js';
import { useColumnSettings } from '../composables/useColumnSettings.js';
import { useSelection } from '../composables/useSelection.js';
import { useBulkOperations } from '../composables/useBulkOperations.js';
import SearchBar from '../components/catalog/SearchBar.js';
import AdvancedFilters from '../components/catalog/AdvancedFilters.js';
import SearchResults from '../components/catalog/SearchResults.js';
import CatalogImport from '../components/catalog/CatalogImport.js';
import { useGlobalModal } from '../composables/useGlobalModal.js';
import AdminDropdown from '../components/admin/AdminDropdown.js';
import Pagination from '../components/ui/Pagination.js';
import BulkEditModal from '../components/catalog/BulkEditModal.js';
import RecordDetail from '../components/catalog/RecordDetail.js';
import ProgressIndicator from '../components/admin/ProgressIndicator.js';
import HelpPanel from '../components/ui/HelpPanel.js';

export default defineComponent({
    name: 'CatalogPage',

    components: {
        SearchBar,
        AdvancedFilters,
        SearchResults,
        CatalogImport,
        AdminDropdown,
        Pagination,
        BulkEditModal,
        RecordDetail,
        ProgressIndicator,
        HelpPanel
    },

    setup() {
        const { t } = useI18n();
        const { settings } = useAppState();
        const route = useRoute();
        const router = useRouter();
        const { success, error: showError, warning } = useNotification();
        const { handleError } = useErrorHandler(t);

        // Search state
        const searchQuery = ref('');
        const results = ref([]);
        const loading = ref(false);

        // View mode (table or cards)
        const viewMode = ref('table'); // Default to table view like mockup

        // Selection state (useSelection composable)
        const {
            selectedIds,
            selectedCount,
            isSelected,
            toggleSelection,
            selectAll,
            clearSelection,
            toggleSelectAll,
            getSelectedIds,
            isAllSelected
        } = useSelection();

        // Bulk operations (useBulkOperations composable)
        const {
            loading: bulkLoading,
            error: bulkError,
            progress: bulkProgress,
            showProgress: bulkShowProgress,
            bulkEditRecords,
            bulkDeleteRecords,
            updateRecord
        } = useBulkOperations('catalog');

        // Column settings (with localStorage persistence)
        const { visibleColumns, isColumnVisible, toggleColumn, resetToDefaults } = useColumnSettings();

        // Filters (default to borrowed/on loan)
        const filters = reactive({
            availability: 'borrowed',
            level: '',
            language: '',
            medium_type: '',
            shelf_location: ''
        });

        // Shelf locations loaded from API for the filter dropdown
        const shelfLocations = ref([]);

        // Pagination
        const {
            currentPage,
            pageSize,
            totalItems,
            totalPages,
            offset,
            limit,
            hasNextPage,
            hasPreviousPage,
            goToPage,
            nextPage,
            previousPage,
            setPageSize
        } = usePagination();

        /**
         * Normalize ISBN (remove dashes and spaces)
         * This helps search for ISBNs with different formatting
         */
        const normalizeISBN = (query) => {
            // Check if query looks like an ISBN (10-13 digits with optional dashes/spaces)
            if (/^[\d\s-]{10,17}$/.test(query)) {
                return query.replace(/[-\s]/g, '');
            }
            return query;
        };

        const { openRecord, openBorrower, closeRecord, catalogRefreshTick } = useGlobalModal();

        // Refresh search results when a quick-return was performed from the global modal
        Vue.watch(catalogRefreshTick, () => performSearch());

        // Initialize from URL params
        onMounted(() => {
            if (route.query.q) {
                searchQuery.value = route.query.q;
            }
            if (route.query.page) {
                currentPage.value = parseInt(route.query.page);
            }
            if (route.query.limit) {
                pageSize.value = parseInt(route.query.limit);
            }

            // Restore filters from URL query params
            if (route.query.availability) {
                filters.availability = route.query.availability;
            }
            if (route.query.level) {
                filters.level = route.query.level;
            }
            if (route.query.language) {
                filters.language = route.query.language;
            }
            if (route.query.medium_type) {
                filters.medium_type = route.query.medium_type;
            }
            if (route.query.shelf_location) {
                filters.shelf_location = route.query.shelf_location;
            }

            // Load shelf locations for the filter dropdown
            apiClient.get('/catalog/locations').then(data => {
                shelfLocations.value = data.locations || [];
            }).catch(() => {});

            // Always perform initial search to show borrowed items by default
            performSearch();
        });

        // Update URL when search parameters change
        // This ensures filters persist when navigating to/from detail view
        const updateURL = () => {
            const query = {};
            if (searchQuery.value) query.q = searchQuery.value;
            if (currentPage.value > 1) query.page = currentPage.value;
            if (pageSize.value !== 10) query.limit = pageSize.value;

            // Persist filters to URL (skip 'borrowed' as it's the default)
            if (filters.availability && filters.availability !== 'borrowed') {
                query.availability = filters.availability;
            }
            if (filters.level) {
                query.level = filters.level;
            }
            if (filters.language) {
                query.language = filters.language;
            }
            if (filters.medium_type) {
                query.medium_type = filters.medium_type;
            }

            router.push({ query }).catch(() => {});
        };

        /**
         * Perform catalog search
         */
        const performSearch = async (resetPage = false) => {
            if (resetPage) {
                currentPage.value = 1;
            }

            try {
                loading.value = true;

                const params = {
                    limit: limit.value,
                    offset: offset.value
                };

                // Add search query (normalize ISBNs)
                if (searchQuery.value.trim()) {
                    params.q = normalizeISBN(searchQuery.value.trim());
                }

                // Add availability filter
                if (filters.availability === 'available') {
                    params.available_only = true;
                } else if (filters.availability === 'borrowed') {
                    params.borrowed_only = true;
                } else if (filters.availability === 'reserved') {
                    params.has_holds = true;
                }

                // Add advanced filters
                if (filters.level) {
                    params.level = filters.level;
                }
                if (filters.language) {
                    params.language = filters.language;
                }
                if (filters.medium_type) {
                    params.medium_type = filters.medium_type;
                }
                if (filters.shelf_location) {
                    params.shelf_location = filters.shelf_location;
                }

                const data = await apiClient.get('/catalog/bibliographic/search', params);

                results.value = data.items || [];
                totalItems.value = data.total || 0;

                // Update URL
                updateURL();

            } catch (err) {
                handleError(err);
                results.value = [];
                totalItems.value = 0;
            } finally {
                loading.value = false;
            }
        };

        /**
         * Handle search input
         */
        const handleSearch = (query) => {
            searchQuery.value = query;
            performSearch(true); // Reset to page 1
        };

        /**
         * Handle filter changes
         */
        const handleFilter = (newFilters) => {
            // Update filters if provided
            if (newFilters) {
                Object.assign(filters, newFilters);
            }
            performSearch(true); // Reset to page 1
        };

        /**
         * Handle record click - navigate to detail route
         */
        const handleRecordClick = (record) => {
            openRecord(record.id);
        };

        /**
         * Handle page change
         */
        const handlePageChange = (page) => {
            goToPage(page);
            performSearch();
        };

        /**
         * Handle page size change
         */
        const handlePageSizeChange = (size) => {
            setPageSize(size);
            performSearch(true); // Reset to page 1
        };

        /**
         * Toggle view mode between table and cards
         */
        const toggleViewMode = () => {
            viewMode.value = viewMode.value === 'table' ? 'cards' : 'table';
        };



        /**
         * Handle catalog import complete
         */
        const handleCatalogImportComplete = (result) => {
            // Refresh search results to show newly imported records
            performSearch();
        };

        /**
         * Handle import button click (from admin dropdown)
         */
        const showCatalogImport = ref(false);
        const handleImportClick = () => { showCatalogImport.value = true; };

        // Bulk edit modal state
        const showBulkEditModal = ref(false);
        const selectedRecords = computed(() => {
            return results.value.filter(r => selectedIds.value.has(r.id));
        });

        // Record edit modal state
        const showRecordEditModal = ref(false);
        const editingRecord = ref(null);

        /**
         * Handle bulk edit (from admin dropdown)
         */
        const handleBulkEdit = () => {
            if (selectedCount.value === 0) {
                showError(t('admin.select_at_least_one'));
                return;
            }
            showBulkEditModal.value = true;
        };

        /**
         * Handle edit selected (from admin dropdown)
         */
        const handleEditSelected = () => {
            if (selectedCount.value === 0) {
                showError(t('admin.select_at_least_one'));
                return;
            }
            if (selectedCount.value > 1) {
                showError(t('admin.select_exactly_one'));
                return;
            }

            // Get the single selected record
            const recordId = getSelectedIds()[0];
            const record = results.value.find(r => r.id === recordId);
            if (record) {
                editingRecord.value = record;
                showRecordEditModal.value = true;
            }
        };

        /**
         * Execute bulk operation from BulkEditModal
         */
        const handleExecuteBulkOperation = async (payload) => {
            showBulkEditModal.value = false;

            try {
                if (payload.operation === 'bulk_edit') {
                    // Bulk edit metadata
                    await bulkEditRecords(getSelectedIds(), payload.fields);
                    success(t('admin.operation_success', {
                        operation: t('admin.updated'),
                        count: selectedCount.value,
                        type: t('admin.records')
                    }));
                } else if (payload.operation === 'delete') {
                    // Bulk delete records
                    await bulkDeleteRecords(getSelectedIds());
                    success(t('admin.operation_success', {
                        operation: t('admin.deleted'),
                        count: selectedCount.value,
                        type: t('admin.records')
                    }));
                }

                // Clear selection and refresh results
                clearSelection();
                performSearch();
            } catch (err) {
                handleError(err);
            }
        };

        /**
         * Handle record edit save
         */
        const handleRecordSaved = (updatedRecord) => {
            success(t('admin.record_updated'));
            // Refresh the results to show updated data
            performSearch();
        };

        /**
         * Handle record deleted from edit modal
         */
        const handleRecordDeleted = (record_id) => {
            success(t('admin.record_deleted'));

            // Close detail modal if it was showing the deleted record
            if (selectedRecordId.value === record_id) {
                showRecordDetail.value = false;
                selectedRecordId.value = null;
            }

            // Close edit modal
            showRecordEditModal.value = false;

            // Refresh search results to reflect deletion
            performSearch();
        };

        /**
         * Handle selection toggle
         */
        const handleToggleSelection = (recordId) => {
            toggleSelection(recordId);
        };

        /**
         * Handle select all toggle
         */
        const handleToggleSelectAll = () => {
            toggleSelectAll(results.value);
        };

        // Computed: check if all visible records are selected
        const selectAllChecked = computed(() => {
            return isAllSelected(results.value);
        });

        // Export state
        const exportLoading = ref(false);

        /**
         * Export catalog to CSV
         */
        const handleExportCatalog = async () => {
            try {
                exportLoading.value = true;

                // Call export endpoint
                const response = await fetch('/api/v1/catalog/export', {
                    method: 'GET',
                    headers: {
                        'Accept': 'text/csv'
                    }
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Export failed');
                }

                // Get filename from Content-Disposition header or generate default
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'catalog_export.csv';
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename=([^;]+)/);
                    if (match) {
                        filename = match[1].replace(/"/g, '');
                    }
                }

                // Download file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                // Show success notification
                const recordCount = response.headers.get('X-Record-Count') || '?';
                const itemCount = response.headers.get('X-Item-Count') || '?';
                success(t('catalog.export_success') + ` (${recordCount} records, ${itemCount} items)`);

            } catch (err) {
                console.error('Export failed:', err);
                showError(t('catalog.export_failed') + ': ' + err.message);
            } finally {
                exportLoading.value = false;
            }
        };

        // Handle print item labels (from admin dropdown)
        const handlePrintLabels = () => {
            window.open('#/print/catalog/labels', '_blank');
        };

        useAdminShortcuts({ N: () => { window.location.hash = '/cataloging'; } });

        return {
            searchQuery,
            results,
            loading,
            exportLoading,
            selectedCount,
            viewMode,
            visibleColumns,
            toggleColumn,
            resetToDefaults,
            filters,
            shelfLocations,
            currentPage,
            pageSize,
            totalItems,
            totalPages,
            hasNextPage,
            hasPreviousPage,
            handleSearch,
            handleExportCatalog,
            handlePrintLabels,
            showCatalogImport,
            handleImportClick,
            handleBulkEdit,
            handleEditSelected,
            handleFilter,
            handleRecordClick,
            handlePageChange,
            handlePageSizeChange,
            toggleViewMode,
            handleCatalogImportComplete,
            // Selection & Bulk Operations
            selectedIds,
            selectedRecords,
            selectAllChecked,
            handleToggleSelection,
            handleToggleSelectAll,
            showBulkEditModal,
            showRecordEditModal,
            editingRecord,
            handleExecuteBulkOperation,
            handleRecordSaved,
            handleRecordDeleted,
            bulkLoading,
            bulkProgress,
            bulkShowProgress,
            settings,
            t,
            altHeld
        };
    },

    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">
                    <i class="bi bi-book me-2"></i>
                    {{ t('navigation.catalog') }}
                </h1>
                <div class="d-flex gap-2">
                    <!-- Add Book button (remains separate) -->
                    <a href="#/cataloging" class="btn btn-primary">
                        <i class="bi bi-plus-circle me-1"></i>
                        {{ t('catalog.add_record') || 'Add Book' }}
                        <kbd v-if="altHeld" class="admin-shortcut ms-2">N</kbd>
                        <kbd v-else class="admin-shortcut ms-2" style="visibility: hidden;">N</kbd>
                    </a>

                    <!-- Admin Dropdown (replaces individual Import/Export buttons) -->
                    <admin-dropdown
                        :selected-count="selectedCount"
                        page="catalog"
                        @import="handleImportClick"
                        @export="handleExportCatalog"
                        @bulk-edit="handleBulkEdit"
                        @edit-selected="handleEditSelected"
                        @print-labels="handlePrintLabels"
                    ></admin-dropdown>
                    <help-panel section="catalog" />
                </div>
            </div>

            <!-- Search Bar -->
            <search-bar
                v-model="searchQuery"
                @search="handleSearch"
            />

            <!-- Advanced Filters -->
            <advanced-filters
                :filters="filters"
                :settings="settings"
                :shelf-locations="shelfLocations"
                :view-mode="viewMode"
                :visible-columns="visibleColumns"
                @filter="handleFilter"
                @update:view-mode="viewMode = $event"
                @toggle-column="toggleColumn"
                @reset-columns="resetToDefaults"
            />

            <!-- Search Results -->
            <search-results
                :results="results"
                :loading="loading"
                :query="searchQuery"
                :view-mode="viewMode"
                :visible-columns="visibleColumns"
                :selected-ids="selectedIds"
                :select-all-checked="selectAllChecked"
                @record-click="handleRecordClick"
                @toggle-selection="handleToggleSelection"
                @toggle-select-all="handleToggleSelectAll"
            />

            <!-- Pagination -->
            <pagination
                v-if="!loading && totalItems > 0"
                :current-page="currentPage"
                :total-pages="totalPages"
                :page-size="pageSize"
                :total-items="totalItems"
                @page-change="handlePageChange"
                @page-size-change="handlePageSizeChange"
                class="mt-4"
            />

            <!-- Catalog Import Modal -->
            <catalog-import
                :show="showCatalogImport"
                @close="showCatalogImport = false"
                @import-complete="handleCatalogImportComplete"
            />

            <!-- Bulk Edit Modal -->
            <bulk-edit-modal
                :show="showBulkEditModal"
                :selected-records="selectedRecords"
                :settings="settings"
                @close="showBulkEditModal = false"
                @execute="handleExecuteBulkOperation"
            />

            <!-- Record Detail / Edit Modal -->
            <record-detail
                v-if="editingRecord"
                :record-id="editingRecord.id"
                :record="editingRecord"
                :show="showRecordEditModal"
                :settings="settings"
                initial-mode="edit"
                @update:show="showRecordEditModal = $event"
                @saved="handleRecordSaved"
                @deleted="handleRecordDeleted"
            />

            <!-- Progress Indicator (for bulk operations with 100+ records) -->
            <div v-if="bulkShowProgress" class="position-fixed top-50 start-50 translate-middle" style="z-index: 9999;">
                <div class="card shadow-lg" style="min-width: 400px;">
                    <div class="card-body">
                        <progress-indicator
                            :progress="bulkProgress"
                            :total="selectedCount"
                            :processed="Math.floor(selectedCount * bulkProgress / 100)"
                            :show-percentage="true"
                            operation="Updating catalog records..."
                            variant="primary"
                        />
                    </div>
                </div>
            </div>
        </div>
    `
});
