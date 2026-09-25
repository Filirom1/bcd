/**
 * Catalog Page Component
 * Search and browse bibliographic records
 */

const { defineComponent, ref, reactive, computed, onMounted, watch, onBeforeUnmount } = Vue;
const { useI18n } = VueI18n;
const { useRoute, useRouter } = VueRouter;
import { apiClient } from '../api/client.js';
import { events } from '../utils/events.js';
import { normalizeCollection } from '../models/pagination.js';
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
import MergeRecordsModal from '../components/catalog/MergeRecordsModal.js';
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
        MergeRecordsModal,
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
            mergeRecords,
            updateRecord
        } = useBulkOperations('catalog');

        // Column settings (with localStorage persistence)
        const { visibleColumns, isColumnVisible, toggleColumn, resetToDefaults } = useColumnSettings();

        // Filters (default to all items)
        const filters = reactive({
            availability: 'all',
            level: '',
            language: '',
            medium_type: '',
            shelf_location: '',
            status: '',
            condition: '',
            loanable: '',
            acquired_after: '',
            acquired_before: '',
            publication_year_min: '',
            publication_year_max: ''
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

        const { openRecord, openBorrower, closeRecord } = useGlobalModal();

        // Refresh search results when signaled by the event bus
        const unsubscribe = events.on('catalog:refresh', () => performSearch());
        onBeforeUnmount(unsubscribe);

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
            if (route.query.status) {
                filters.status = route.query.status;
            }
            if (route.query.condition) {
                filters.condition = route.query.condition;
            }
            if (route.query.loanable) {
                filters.loanable = route.query.loanable;
            }
            if (route.query.acquired_after) {
                filters.acquired_after = route.query.acquired_after;
            }
            if (route.query.acquired_before) {
                filters.acquired_before = route.query.acquired_before;
            }
            if (route.query.publication_year_min) {
                filters.publication_year_min = route.query.publication_year_min;
            }
            if (route.query.publication_year_max) {
                filters.publication_year_max = route.query.publication_year_max;
            }

            // Load shelf locations for the filter dropdown
            apiClient.get('/catalog/locations').then(data => {
                shelfLocations.value = data.locations || [];
            }).catch(() => {
                // Locations are an optional filter; keep the catalog usable without them.
            });

            // Always perform initial search to show all items by default
            performSearch();
        });

        // Update URL when search parameters change
        // This ensures filters persist when navigating to/from detail view
        const updateURL = () => {
            const query = {};
            if (searchQuery.value) query.q = searchQuery.value;
            if (currentPage.value > 1) query.page = currentPage.value;
            if (pageSize.value !== 10) query.limit = pageSize.value;

            // Persist filters to URL (skip 'all' as it's the default)
            if (filters.availability && filters.availability !== 'all') {
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
            if (filters.shelf_location) {
                query.shelf_location = filters.shelf_location;
            }
            if (filters.status) {
                query.status = filters.status;
            }
            if (filters.condition) {
                query.condition = filters.condition;
            }
            if (filters.loanable) {
                query.loanable = filters.loanable;
            }
            if (filters.acquired_after) {
                query.acquired_after = filters.acquired_after;
            }
            if (filters.acquired_before) {
                query.acquired_before = filters.acquired_before;
            }
            if (filters.publication_year_min) {
                query.publication_year_min = filters.publication_year_min;
            }
            if (filters.publication_year_max) {
                query.publication_year_max = filters.publication_year_max;
            }

            router.push({ query }).catch(() => {
                // Navigation may be cancelled by a newer filter update.
            });
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
                if (filters.status) {
                    params.status = filters.status;
                }
                if (filters.condition) {
                    params.condition = filters.condition;
                }
                if (filters.loanable) {
                    params.loanable = filters.loanable === 'true';
                }
                if (filters.acquired_after) {
                    params.acquired_after = filters.acquired_after;
                }
                if (filters.acquired_before) {
                    params.acquired_before = filters.acquired_before;
                }
                if (filters.publication_year_min) {
                    params.publication_year_min = Number(filters.publication_year_min);
                }
                if (filters.publication_year_max) {
                    params.publication_year_max = Number(filters.publication_year_max);
                }

                const data = await apiClient.get('/catalog/bibliographic/search', params);

                const normalized = normalizeCollection(data);
                results.value = normalized.items;
                totalItems.value = normalized.pagination.total_items;

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
            // Selection belongs to the current result page. Do not carry
            // selected records into another page, where they are no longer
            // visible and cannot be reviewed before a bulk operation.
            clearSelection();
            goToPage(page);
            performSearch();
        };

        /**
         * Handle page size change
         */
        const handlePageSizeChange = (size) => {
            // Changing the page size also changes the visible result set and
            // resets pagination to page 1, so discard the current selection.
            clearSelection();
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
        const showMergeRecordsModal = ref(false);
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

        const handleMergeRecords = () => {
            if (selectedCount.value < 2) {
                showError(t('admin.select_at_least_two'));
                return;
            }
            showMergeRecordsModal.value = true;
        };

        const executeMergeRecords = async ({ targetId, sourceIds, itemUpdates = [] }) => {
            try {
                await mergeRecords(
                    sourceIds,
                    targetId,
                    itemUpdates.map(({ itemId, shelfLocation, callNumber }) => ({
                        item_id: itemId,
                        shelf_location: shelfLocation,
                        call_number: callNumber
                    }))
                );
                showMergeRecordsModal.value = false;
                clearSelection();
                await performSearch();
                success(t('admin.merge_records_success', {
                    count: sourceIds.length
                }));
            } catch (err) {
                handleError(err);
            }
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
        const handleRecordDeleted = () => {
            success(t('admin.record_deleted'));

            // This page only owns the edit modal. Global record-detail modals
            // are hosted by App, so there is no local selectedRecordId to close.
            showRecordEditModal.value = false;
            editingRecord.value = null;

            // Refresh search results to reflect deletion.
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

                // Call export endpoint and download file
                await apiClient.download('/catalog/export', 'catalog_export.csv', {}, {
                    headers: {
                        'Accept': 'text/csv'
                    }
                });

                // Show success notification
                success(t('catalog.export_success'));

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
            handleMergeRecords,
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
            showMergeRecordsModal,
            executeMergeRecords,
            showRecordEditModal,
            editingRecord,
            handleExecuteBulkOperation,
            handleRecordSaved,
            handleRecordDeleted,
            bulkLoading,
            bulkProgress,
            bulkShowProgress,
            settings,
            openBorrower,
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
                        @merge-records="handleMergeRecords"
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

            <merge-records-modal
                :show="showMergeRecordsModal"
                :selected-records="selectedRecords"
                :settings="settings"
                :loading="bulkLoading"
                @close="showMergeRecordsModal = false"
                @confirm="executeMergeRecords"
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
                @view-borrower="openBorrower"
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
