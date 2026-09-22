import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import InventoryPage from '../../../../src/bcd_web_vue/js/pages/InventoryPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const mountedWrappers = [];

function makeItem(overrides = {}) {
    return {
        item_id: 'I-101',
        bibliographic_record_id: 10,
        title: 'Le Petit Prince',
        condition: 'good',
        status: 'available',
        loanable: true,
        shelf_location: 'Romans',
        call_number: '843 SAI',
        level: 'CM2',
        language: 'fr',
        medium_type: 'Book',
        ...overrides
    };
}

function mountInventoryPage() {
    const wrapper = shallowMount(InventoryPage, {
        global: {
            stubs: {
                ScanTab: true,
                FileTab: true,
                SearchTab: true,
                InventoryResults: true,
                WorkingTableToolbar: true,
                BulkEditPanel: true,
                AdminDropdown: true,
                HelpPanel: true,
                ConfirmDialog: true,
                ItemEditForm: true,
                RecordDetail: true
            }
        }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

beforeEach(() => {
    localStorage.clear();
    useNotification().clear();
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    localStorage.clear();
    useNotification().clear();
});

describe('InventoryPage', () => {
    it('switches to the file tab when an import is requested', () => {
        const wrapper = mountInventoryPage();

        expect(wrapper.vm.activeTab).toBe('scan');
        wrapper.vm.handleImport();
        expect(wrapper.vm.activeTab).toBe('file');

        wrapper.vm.setActiveTab('search');
        expect(wrapper.vm.activeTab).toBe('search');
    });

    it('rejects an empty export and exports the working table as a dated CSV', async () => {
        const wrapper = mountInventoryPage();
        const downloadPost = vi.spyOn(apiClient, 'downloadPost').mockResolvedValue();

        await wrapper.vm.handleExport();
        expect(downloadPost).not.toHaveBeenCalled();
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'inventory.working_table.empty' })
        ]);

        wrapper.vm.inventoryTable.addItems([makeItem(), makeItem({ item_id: 'I-102' })]);
        await wrapper.vm.handleExport();

        expect(downloadPost).toHaveBeenCalledWith(
            '/inventory/export-csv',
            { item_ids: ['I-101', 'I-102'] },
            expect.stringMatching(/^inventory_\d{4}-\d{2}-\d{2}\.csv$/)
        );
        expect(useNotification().notifications.value.at(-1)).toEqual(
            expect.objectContaining({ type: 'success', message: 'inventory.working_table.export_success' })
        );
    });

    it('handles orphan cleanup with and without records', async () => {
        const wrapper = mountInventoryPage();
        const get = vi.spyOn(apiClient, 'get');

        get.mockResolvedValueOnce({ count: 0, records: [] });
        await wrapper.vm.handleCleanupOrphans();
        expect(wrapper.vm.showOrphanConfirm).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'inventory.admin.no_orphans_body' })
        ]);

        get.mockResolvedValueOnce({ count: 1, records: [{ id: 7, title: 'Notice orpheline' }] });
        await wrapper.vm.handleCleanupOrphans();
        expect(wrapper.vm.orphanRecords).toEqual([{ id: 7, title: 'Notice orpheline' }]);
        expect(wrapper.vm.showOrphanConfirm).toBe(true);

        const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue({ records_deleted: 1 });
        await wrapper.vm.confirmOrphanCleanup();
        expect(remove).toHaveBeenCalledWith('/admin/catalog/orphan-records');
        expect(wrapper.vm.showOrphanConfirm).toBe(false);
        expect(useNotification().notifications.value.at(-1)).toEqual(
            expect.objectContaining({ type: 'success', message: 'inventory.admin.success' })
        );
    });

    it('clears only selected rows and prevents a clear with no selection', () => {
        const wrapper = mountInventoryPage();
        wrapper.vm.inventoryTable.addItems([
            makeItem({ item_id: 'I-101' }),
            makeItem({ item_id: 'I-102' })
        ]);

        wrapper.vm.handleClear();
        expect(wrapper.vm.inventoryTable.getAllItemIds()).toEqual(['I-101', 'I-102']);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'inventory.search.no_selection' })
        ]);

        wrapper.vm.toggleSelection('I-101');
        wrapper.vm.handleClear();
        expect(wrapper.vm.inventoryTable.getAllItemIds()).toEqual(['I-102']);
        expect(wrapper.vm.selectedCount).toBe(0);
        expect(useNotification().notifications.value.at(-1)).toEqual(
            expect.objectContaining({ type: 'success', message: 'inventory.working_table.cleared' })
        );
    });

    it('previews and applies a bulk edit to the selected items', async () => {
        const wrapper = mountInventoryPage();
        wrapper.vm.inventoryTable.addItems([makeItem()]);
        wrapper.vm.toggleSelection('I-101');
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            items_updated: 1,
            records_updated: 0
        });

        wrapper.vm.handleBulkApply({
            item_updates: { condition: 'damaged' },
            record_updates: {},
            auto_call_number: false
        });

        expect(wrapper.vm.bulkEditPreview).toEqual({
            itemCount: 1,
            hasItemUpdates: true,
            hasRecordUpdates: false
        });
        expect(wrapper.vm.showBulkEditConfirm).toBe(true);

        await wrapper.vm.confirmBulkEdit();
        expect(post).toHaveBeenCalledWith('/inventory/items/bulk-update', {
            item_ids: ['I-101'],
            item_updates: { condition: 'damaged' },
            record_updates: {},
            auto_call_number: false
        });
        expect(wrapper.vm.inventoryTable.items.value[0].condition).toBe('damaged');
        expect(wrapper.vm.selectedCount).toBe(0);
    });

    it('applies record updates to every selected item sharing the record', async () => {
        const wrapper = mountInventoryPage();
        wrapper.vm.inventoryTable.addItems([
            makeItem({ item_id: 'I-101', title: 'Old title' }),
            makeItem({ item_id: 'I-102', title: 'Old title' })
        ]);
        wrapper.vm.toggleSelection('I-101');
        vi.spyOn(apiClient, 'post').mockResolvedValue({ items_updated: 1, records_updated: 1 });

        wrapper.vm.handleBulkApply({
            item_updates: {},
            record_updates: { title: 'Nouveau titre' },
            auto_call_number: false
        });
        await wrapper.vm.confirmBulkEdit();

        expect(wrapper.vm.inventoryTable.items.value).toEqual(expect.arrayContaining([
            expect.objectContaining({ item_id: 'I-101', title: 'Nouveau titre' }),
            expect.objectContaining({ item_id: 'I-102', title: 'Nouveau titre' })
        ]));
    });

    it('confirms bulk deletion and removes the selected rows', async () => {
        const wrapper = mountInventoryPage();
        wrapper.vm.inventoryTable.addItems([makeItem(), makeItem({ item_id: 'I-102' })]);
        wrapper.vm.toggleSelection('I-102');
        wrapper.vm.handleBulkDelete();

        expect(wrapper.vm.bulkDeletePreview).toEqual({ itemCount: 1 });
        expect(wrapper.vm.showBulkDeleteConfirm).toBe(true);

        const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue({
            items_deleted: 1,
            holds_cancelled: 0
        });
        await wrapper.vm.confirmBulkDelete();

        expect(remove).toHaveBeenCalledWith('/inventory/items/bulk', { item_ids: ['I-102'] });
        expect(wrapper.vm.inventoryTable.getAllItemIds()).toEqual(['I-101']);
        expect(wrapper.vm.selectedCount).toBe(0);
    });

    it('loads and saves an item edit while handling record lookup', async () => {
        const wrapper = mountInventoryPage();
        const record = { id: 10, title: 'Notice' };
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue(record);
        wrapper.vm.handleEditItem(makeItem());
        expect(wrapper.vm.editingItem.item_id).toBe('I-101');
        expect(wrapper.vm.showItemEditModal).toBe(true);

        await wrapper.vm.handleEditRecord(makeItem());
        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/10');
        expect(wrapper.vm.editingRecord).toEqual(record);
        expect(wrapper.vm.showRecordEditModal).toBe(true);

        const freshItem = makeItem({ condition: 'damaged', title: 'Updated title' });
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue(freshItem);
        await wrapper.vm.handleItemSaved({ item_id: 'I-101' });

        expect(patch).toHaveBeenCalledWith('/inventory/items/I-101', {});
        expect(wrapper.vm.inventoryTable.items.value[0]).toMatchObject({
            item_id: 'I-101',
            condition: 'damaged',
            title: 'Updated title'
        });
        expect(wrapper.vm.showItemEditModal).toBe(false);
        expect(useNotification().notifications.value.at(-1)).toEqual(
            expect.objectContaining({ type: 'success', message: 'admin.item_updated' })
        );
    });

    it('does not open a record editor for an item without a bibliographic record', async () => {
        const wrapper = mountInventoryPage();
        const get = vi.spyOn(apiClient, 'get');

        await wrapper.vm.handleEditRecord({ item_id: 'I-without-record' });

        expect(get).not.toHaveBeenCalled();
        expect(wrapper.vm.showRecordEditModal).toBe(false);
    });
});
