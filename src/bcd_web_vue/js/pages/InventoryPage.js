/**
 * InventoryPage Component
 *
 * Main page for collection inventory operations (récolement/weeding).
 *
 * Features:
 * - 3-tab input panel (Scanner/File/Search)
 * - Working table with selection
 * - Bulk edit panel
 * - Admin dropdown for export/orphan cleanup
 */

const { defineComponent, ref, computed } = Vue;
const { useI18n } = VueI18n;

import { useAppState } from '../composables/useAppState.js';
import { useNotification } from '../composables/useNotification.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { useSelection } from '../composables/useSelection.js';
import { useInventoryTable } from '../composables/useInventoryTable.js';
import { useInventoryColumnSettings } from '../composables/useInventoryColumnSettings.js';
import { useGlobalModal } from '../composables/useGlobalModal.js';
import ScanTab from '../components/inventory/ScanTab.js';
import FileTab from '../components/inventory/FileTab.js';
import SearchTab from '../components/inventory/SearchTab.js';
import InventoryResults from '../components/inventory/InventoryResults.js';
import WorkingTableToolbar from '../components/inventory/WorkingTableToolbar.js';
import BulkEditPanel from '../components/inventory/BulkEditPanel.js';
import AdminDropdown from '../components/admin/AdminDropdown.js';
import HelpPanel from '../components/ui/HelpPanel.js';
import ConfirmDialog from '../components/admin/ConfirmDialog.js';
import ItemEditForm from '../components/catalog/ItemEditForm.js';
import RecordEditForm from '../components/catalog/RecordEditForm.js';

export default defineComponent({
    name: 'InventoryPage',

    components: {
        ScanTab,
        FileTab,
        SearchTab,
        InventoryResults,
        WorkingTableToolbar,
        BulkEditPanel,
        AdminDropdown,
        HelpPanel,
        ConfirmDialog,
        ItemEditForm,
        RecordEditForm
    },

    setup() {
        const { t } = useI18n();
        const { settings } = useAppState();
        const { success, error: showError } = useNotification();
        const { handleError } = useErrorHandler(t);
        // useGlobalModal kept for future use (openBorrower from record detail)

        // Active tab state
        const activeTab = ref('scan');

        // Working table state (localStorage persistence)
        const inventoryTable = useInventoryTable();

        // Column visibility settings (localStorage persistence)
        const {
            visibleColumns,
            toggleColumn,
            resetToDefaults: resetColumns
        } = useInventoryColumnSettings();

        // Selection state (matching catalog pattern)
        const {
            selectedIds,
            selectedCount,
            isSelected,
            toggleSelection,
            selectAll,
            clearSelection,
            toggleSelectAll,
            isAllSelected
        } = useSelection();

        // Modal states
        const showBulkEditConfirm = ref(false);
        const showBulkDeleteConfirm = ref(false);
        const showOrphanConfirm = ref(false);
        const showItemEditModal = ref(false);
        const pendingBulkEdit = ref(null);
        const orphanRecords = ref([]);
        const bulkEditPreview = ref(null);
        const bulkDeletePreview = ref(null);
        const editingItem = ref(null);

        /**
         * Switch to a different tab
         */
        const setActiveTab = (tab) => {
            activeTab.value = tab;
        };

        /**
         * Handle import file (US4) - switches to file tab
         */
        const handleImport = () => {
            setActiveTab('file');
        };

        /**
         * Handle export to CSV (US6)
         */
        const handleExport = async () => {
            const itemIds = inventoryTable.items.value.map(item => item.item_id);

            if (itemIds.length === 0) {
                showError(t('inventory.working_table.empty'));
                return;
            }

            try {
                const response = await fetch('/api/v1/inventory/export-csv', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ item_ids: itemIds })
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                // Download CSV file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `inventory_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                success(t('inventory.working_table.export_success'));
            } catch (error) {
                handleError(error, 'inventory.working_table.export_error');
            }
        };

        /**
         * Handle cleanup orphan records (US7)
         */
        const handleCleanupOrphans = async () => {
            try {
                const response = await fetch('/api/v1/admin/catalog/orphan-records');
                if (!response.ok) {
                    throw new Error(await response.text());
                }

                const data = await response.json();
                orphanRecords.value = data.records || [];

                if (data.count === 0) {
                    // No orphans - show info modal
                    showError(t('inventory.admin.no_orphans_body'));
                    return;
                }

                // Show confirmation modal
                showOrphanConfirm.value = true;
            } catch (error) {
                handleError(error, 'inventory.admin.error');
            }
        };

        /**
         * Confirm orphan cleanup
         */
        const confirmOrphanCleanup = async () => {
            showOrphanConfirm.value = false;

            try {
                const response = await fetch('/api/v1/admin/catalog/orphan-records', {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                const data = await response.json();
                success(t('inventory.admin.success', { count: data.records_deleted }));
            } catch (error) {
                handleError(error, 'inventory.admin.error');
            }
        };

        /**
         * Handle toggle select all
         * Maps inventory items (which use item_id) to work with useSelection composable (which expects id)
         */
        const handleToggleSelectAll = () => {
            // Create temporary objects with 'id' property for useSelection compatibility
            // Filter out items without valid item_id
            const itemsWithId = inventoryTable.items.value
                .filter(item => item.item_id != null && item.item_id !== '')
                .map(item => ({ id: item.item_id }));

            // Use the composable's toggleSelectAll
            toggleSelectAll(itemsWithId);
        };

        /**
         * Handle clear working table
         * Only clears selected items. To clear all, user must select all first.
         */
        const handleClear = () => {
            if (inventoryTable.items.value.length === 0) {
                return;
            }

            if (selectedCount.value === 0) {
                // Nothing selected - show message
                showError(t('inventory.search.no_selection'));
                return;
            }

            // Clear only selected items (filter out any null/undefined)
            const idsToRemove = Array.from(selectedIds.value).filter(id => id != null && id !== '');
            inventoryTable.removeItems(idsToRemove);
            clearSelection();

            success(t('inventory.working_table.cleared'));
        };

        /**
         * Handle bulk edit apply (US3)
         */
        const handleBulkApply = (payload) => {
            if (selectedCount.value === 0) {
                showError(t('inventory.search.no_selection'));
                return;
            }

            // Store payload and show confirmation
            pendingBulkEdit.value = payload;

            // Build preview info
            const itemCount = selectedCount.value;
            const hasItemUpdates = payload.item_updates && Object.keys(payload.item_updates).length > 0;
            const hasRecordUpdates = payload.record_updates && Object.keys(payload.record_updates).length > 0;

            bulkEditPreview.value = {
                itemCount,
                hasItemUpdates,
                hasRecordUpdates
            };

            showBulkEditConfirm.value = true;
        };

        /**
         * Confirm bulk edit
         */
        const confirmBulkEdit = async () => {
            showBulkEditConfirm.value = false;

            if (!pendingBulkEdit.value) return;

            // Filter out any null/undefined values from selectedIds
            const itemIds = Array.from(selectedIds.value).filter(id => id != null && id !== '');

            // Validation: ensure we have valid IDs
            if (itemIds.length === 0) {
                showError(t('inventory.search.no_selection'));
                return;
            }

            try {
                const response = await fetch('/api/v1/inventory/items/bulk-update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        item_ids: itemIds,
                        item_updates: pendingBulkEdit.value.item_updates || {},
                        record_updates: pendingBulkEdit.value.record_updates || {}
                    })
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                const data = await response.json();

                // Update the items in the working table with the changes we just applied
                const itemUpdates = pendingBulkEdit.value.item_updates || {};
                const recordUpdates = pendingBulkEdit.value.record_updates || {};
                const hasItemUpdates = Object.keys(itemUpdates).length > 0;
                const hasRecordUpdates = Object.keys(recordUpdates).length > 0;

                if (hasItemUpdates || hasRecordUpdates) {
                    // Collect bibliographic_record_ids from updated items (for record updates)
                    const affectedRecordIds = new Set();
                    if (hasRecordUpdates) {
                        itemIds.forEach(itemId => {
                            const item = inventoryTable.items.value.find(i => i.item_id === itemId);
                            if (item && item.bibliographic_record_id) {
                                affectedRecordIds.add(item.bibliographic_record_id);
                            }
                        });
                    }

                    // Collect all items that need updating (snapshot to avoid mutation during iteration)
                    const itemsSnapshot = [...inventoryTable.items.value];
                    const updatedItems = [];

                    itemsSnapshot.forEach(item => {
                        let needsUpdate = false;
                        const updatedItem = { ...item };

                        // Apply item updates only to selected items
                        if (hasItemUpdates && itemIds.includes(item.item_id)) {
                            Object.keys(itemUpdates).forEach(key => {
                                if (itemUpdates[key] !== null && itemUpdates[key] !== undefined) {
                                    updatedItem[key] = itemUpdates[key];
                                    needsUpdate = true;
                                }
                            });
                        }

                        // Apply record updates to ALL items with affected record_ids
                        if (hasRecordUpdates && affectedRecordIds.has(item.bibliographic_record_id)) {
                            Object.keys(recordUpdates).forEach(key => {
                                if (recordUpdates[key] !== null && recordUpdates[key] !== undefined) {
                                    updatedItem[key] = recordUpdates[key];
                                    needsUpdate = true;
                                }
                            });
                        }

                        if (needsUpdate) {
                            updatedItems.push(updatedItem);
                        }
                    });

                    // Apply all updates (addItem moves items to top, so do this after iteration)
                    updatedItems.forEach(item => {
                        inventoryTable.addItem(item);
                    });
                }

                success(t('inventory.bulk_edit.success', {
                    items: data.items_updated,
                    records: data.records_updated
                }));

                // Clear selection after successful edit
                clearSelection();
                pendingBulkEdit.value = null;
            } catch (error) {
                handleError(error, 'inventory.bulk_edit.error');
            }
        };

        /**
         * Handle bulk delete (US5)
         */
        const handleBulkDelete = () => {
            if (selectedCount.value === 0) {
                showError(t('inventory.search.no_selection'));
                return;
            }

            bulkDeletePreview.value = {
                itemCount: selectedCount.value
            };

            showBulkDeleteConfirm.value = true;
        };

        /**
         * Confirm bulk delete
         */
        const confirmBulkDelete = async () => {
            showBulkDeleteConfirm.value = false;

            // Filter out any null/undefined values from selectedIds
            const itemIds = Array.from(selectedIds.value).filter(id => id != null && id !== '');

            try {
                const response = await fetch('/api/v1/inventory/items/bulk', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        item_ids: itemIds
                    })
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                const data = await response.json();

                // Remove deleted items from working table
                inventoryTable.removeItems(itemIds);

                success(t('inventory.bulk_delete.success', {
                    count: data.items_deleted,
                    holds: data.holds_cancelled
                }));

                // Clear selection
                clearSelection();
            } catch (error) {
                handleError(error, 'inventory.bulk_delete.error');
            }
        };

        /**
         * Handle edit item click
         */
        const handleEditItem = (item) => {
            editingItem.value = item;
            showItemEditModal.value = true;
        };

        /**
         * Handle edit record click - fetch record and open edit modal
         */
        const showRecordEditModal = ref(false);
        const editingRecord = ref(null);

        const handleEditRecord = async (item) => {
            if (!item.bibliographic_record_id) return;
            try {
                const response = await fetch(`/api/v1/catalog/bibliographic/${item.bibliographic_record_id}`);
                if (!response.ok) throw new Error('Failed to load record');
                editingRecord.value = await response.json();
                showRecordEditModal.value = true;
            } catch (error) {
                handleError(error, 'catalog.fetch_error');
            }
        };

        const handleRecordSaved = () => {
            showRecordEditModal.value = false;
            editingRecord.value = null;
        };

        const handleRecordDeleted = () => {
            showRecordEditModal.value = false;
            editingRecord.value = null;
        };

        /**
         * Handle item saved - refresh the item in working table
         */
        const handleItemSaved = async (updatedItem) => {
            showItemEditModal.value = false;
            editingItem.value = null;

            // Refresh the item by fetching latest data from API
            try {
                const response = await fetch(`/api/v1/inventory/items/${updatedItem.item_id}`, {
                    method: 'PATCH'
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                const freshItem = await response.json();

                // Update item in working table
                inventoryTable.addItem({
                    // Item fields
                    item_id: freshItem.item_id,
                    bibliographic_record_id: freshItem.bibliographic_record_id,
                    status: freshItem.status,
                    condition: freshItem.condition,
                    loanable: freshItem.loanable,
                    shelf_location: freshItem.shelf_location,
                    call_number: freshItem.call_number,
                    last_inventoried_at: freshItem.last_inventoried_at,
                    // Record fields
                    title: freshItem.title,
                    level: freshItem.level,
                    target_audience: freshItem.target_audience,
                    language: freshItem.language,
                    medium_type: freshItem.medium_type
                });

                success(t('admin.item_updated'));
            } catch (error) {
                handleError(error, 'admin.update_error');
            }
        };

        // Computed for select all checkbox state
        const selectAllChecked = computed(() => {
            if (inventoryTable.items.value.length === 0) {
                return false;
            }
            // Map to objects with 'id' property for useSelection compatibility
            // Filter out items without valid item_id
            const itemsWithId = inventoryTable.items.value
                .filter(item => item.item_id != null && item.item_id !== '')
                .map(item => ({ id: item.item_id }));
            return isAllSelected(itemsWithId);
        });

        return {
            t,
            settings,
            activeTab,
            setActiveTab,
            inventoryTable,
            visibleColumns,
            toggleColumn,
            resetColumns,
            selectedIds,
            selectedCount,
            selectAllChecked,
            toggleSelection,
            handleImport,
            handleExport,
            handleCleanupOrphans,
            handleToggleSelectAll,
            handleClear,
            handleBulkApply,
            handleBulkDelete,
            handleEditItem,
            handleEditRecord,
            handleItemSaved,
            handleRecordSaved,
            handleRecordDeleted,
            // Modal states
            showBulkEditConfirm,
            showBulkDeleteConfirm,
            showOrphanConfirm,
            showItemEditModal,
            editingItem,
            showRecordEditModal,
            editingRecord,
            orphanRecords,
            bulkEditPreview,
            bulkDeletePreview,
            // Confirm handlers
            confirmBulkEdit,
            confirmBulkDelete,
            confirmOrphanCleanup
        };
    },

    template: `
        <div>
            <div class="page-header">
                <h1 class="page-title">
                    <i class="bi bi-box-seam me-2"></i>
                    {{ t('inventory.title') }}
                </h1>
                <div class="d-flex gap-2">
                    <admin-dropdown
                        :selected-count="selectedCount"
                        page="inventory"
                        @import="handleImport"
                        @export="handleExport"
                        @cleanup-orphans="handleCleanupOrphans"
                    />
                    <help-panel section="inventory" />
                </div>
            </div>

            <div class="inventory-page">
                <div class="inventory-workspace">
                    <!-- Left panel: Scanner + Bulk Edit -->
                    <div class="left-panel">
                        <!-- Scanner card -->
                        <div class="card shadow-sm mb-3">
                            <div class="card-header">
                                <h6 class="mb-0 text-uppercase small">
                                    {{ t('inventory.add_items.title') }}
                                </h6>
                            </div>
                            <div class="card-body">
                                <!-- Tab Navigation -->
                                <ul class="nav nav-pills mb-3" role="tablist">
                                    <li class="nav-item" role="presentation">
                                        <button
                                            class="nav-link"
                                            :class="{ active: activeTab === 'scan' }"
                                            @click="setActiveTab('scan')"
                                            type="button"
                                        >
                                            <i class="bi bi-upc-scan me-1"></i>
                                            {{ t('inventory.tabs.scan') }}
                                        </button>
                                    </li>
                                    <li class="nav-item" role="presentation">
                                        <button
                                            class="nav-link"
                                            :class="{ active: activeTab === 'file' }"
                                            @click="setActiveTab('file')"
                                            type="button"
                                        >
                                            <i class="bi bi-file-earmark me-1"></i>
                                            {{ t('inventory.tabs.file') }}
                                        </button>
                                    </li>
                                    <li class="nav-item" role="presentation">
                                        <button
                                            class="nav-link"
                                            :class="{ active: activeTab === 'search' }"
                                            @click="setActiveTab('search')"
                                            type="button"
                                        >
                                            <i class="bi bi-search me-1"></i>
                                            {{ t('inventory.tabs.search') }}
                                        </button>
                                    </li>
                                </ul>

                                <!-- Tab Content -->
                                <div class="tab-content">
                                    <div v-show="activeTab === 'scan'">
                                        <ScanTab :inventoryTable="inventoryTable" />
                                    </div>
                                    <div v-show="activeTab === 'file'">
                                        <FileTab
                                            :inventoryTable="inventoryTable"
                                            @switch-to-working-table="setActiveTab('scan')"
                                        />
                                    </div>
                                    <div v-show="activeTab === 'search'">
                                        <SearchTab
                                            :inventoryTable="inventoryTable"
                                            @switch-to-working-table="setActiveTab('scan')"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Bulk Edit card -->
                        <div class="card shadow-sm">
                            <div class="card-header">
                                <h6 class="mb-0 text-uppercase small">
                                    {{ t('inventory.bulk_edit.panel_title') }}
                                </h6>
                            </div>
                            <BulkEditPanel
                                :selected-count="selectedCount"
                                :settings="settings"
                                @apply="handleBulkApply"
                                @delete="handleBulkDelete"
                            />
                        </div>
                    </div>

                    <!-- Right panel: Working table -->
                    <div class="working-table-panel card shadow-sm">
                        <WorkingTableToolbar
                            :selected-count="selectedCount"
                            :total-count="inventoryTable.items.value.length"
                            :visible-columns="visibleColumns"
                            @clear="handleClear"
                            @toggle-column="toggleColumn"
                            @reset-columns="resetColumns"
                        />
                        <div class="card-body p-0">
                            <div v-if="inventoryTable.loading.value" class="text-center py-4">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">{{ t('common.loading') }}</span>
                                </div>
                                <p class="text-muted mt-2 mb-0 small">{{ t('inventory.working_table.loading') }}</p>
                            </div>
                            <InventoryResults
                                v-else
                                :items="inventoryTable.items.value"
                                :selected-ids="selectedIds"
                                :select-all-checked="selectAllChecked"
                                :visible-columns="visibleColumns"
                                @toggle-selection="toggleSelection"
                                @toggle-select-all="handleToggleSelectAll"
                                @edit-item="handleEditItem"
                                @edit-record="handleEditRecord"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <!-- Bulk Edit Confirmation Modal -->
            <confirm-dialog
                :show="showBulkEditConfirm"
                :title="t('inventory.bulk_edit.confirmation_title')"
                :message="t('inventory.bulk_edit.confirmation_body')"
                :count="bulkEditPreview?.itemCount || 0"
                :confirm-text="t('inventory.bulk_edit.confirm')"
                :cancel-text="t('inventory.bulk_edit.cancel')"
                confirm-class="btn-primary"
                @confirm="confirmBulkEdit"
                @cancel="showBulkEditConfirm = false"
            />

            <!-- Bulk Delete Confirmation Modal -->
            <confirm-dialog
                :show="showBulkDeleteConfirm"
                :title="t('inventory.bulk_delete.confirmation_title')"
                :message="t('inventory.bulk_delete.irreversible_warning')"
                :count="bulkDeletePreview?.itemCount || 0"
                :confirm-text="t('inventory.bulk_delete.confirm')"
                :cancel-text="t('inventory.bulk_delete.cancel')"
                confirm-class="btn-danger"
                @confirm="confirmBulkDelete"
                @cancel="showBulkDeleteConfirm = false"
            />

            <!-- Orphan Records Cleanup Confirmation Modal -->
            <confirm-dialog
                :show="showOrphanConfirm"
                :title="t('inventory.admin.orphan_count_title')"
                :message="t('inventory.admin.irreversible_warning')"
                :items="orphanRecords"
                :count="orphanRecords.length"
                :confirm-text="t('inventory.admin.confirm', { count: orphanRecords.length })"
                :cancel-text="t('inventory.admin.cancel')"
                confirm-class="btn-danger"
                @confirm="confirmOrphanCleanup"
                @cancel="showOrphanConfirm = false"
            />

            <!-- Item Edit Modal -->
            <item-edit-form
                v-if="editingItem"
                :show="showItemEditModal"
                :item="editingItem"
                @update:show="showItemEditModal = $event"
                @saved="handleItemSaved"
            />

            <!-- Record Edit Modal -->
            <record-edit-form
                v-if="editingRecord"
                :show="showRecordEditModal"
                :record="editingRecord"
                :settings="settings"
                @update:show="showRecordEditModal = $event"
                @saved="handleRecordSaved"
                @deleted="handleRecordDeleted"
            />
        </div>
    `
});
