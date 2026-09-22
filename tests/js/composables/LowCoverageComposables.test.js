import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, nextTick } from 'vue';
import { mount } from '@vue/test-utils';

import { useBorrowerData } from '../../../src/bcd_web_vue/js/composables/useBorrowerData.js';
import { useBulkOperations } from '../../../src/bcd_web_vue/js/composables/useBulkOperations.js';
import { useInventoryColumnSettings } from '../../../src/bcd_web_vue/js/composables/useInventoryColumnSettings.js';
import { useKeyboardShortcuts, useAdminShortcuts, altHeld } from '../../../src/bcd_web_vue/js/composables/useKeyboardShortcuts.js';
import { apiClient } from '../../../src/bcd_web_vue/js/api/client.js';

beforeEach(() => {
    localStorage.clear();
    altHeld.value = false;
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    localStorage.clear();
    altHeld.value = false;
});

describe('useBorrowerData', () => {
    it('normalizes borrower collections and adds optional class filters', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ items: [{ borrower_id: 'B-1' }] });
        const { fetchBorrowers } = useBorrowerData();
        expect(await fetchBorrowers('class-1', 20)).toEqual([{ borrower_id: 'B-1' }]);
        expect(get).toHaveBeenCalledWith('/borrowers', { page: 1, page_size: 20, class_id: 'class-1' });
        await fetchBorrowers();
        expect(get).toHaveBeenLastCalledWith('/borrowers', { page: 1, page_size: 500 });
    });

    it('converts API failures into a stable domain error', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('offline'));
        await expect(useBorrowerData().fetchBorrowers()).rejects.toThrow('Failed to load borrowers');
    });
});

describe('useBulkOperations', () => {
    it('executes borrower and catalog bulk operations with progress state', async () => {
        vi.useFakeTimers();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ updated: 2 });
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ id: 1 });
        const ops = useBulkOperations('all');

        expect(await ops.bulkChangeClass([1, 2], 3)).toEqual({ updated: 2 });
        expect(await ops.bulkChangeRole([1], 'teacher')).toEqual({ updated: 2 });
        expect(await ops.bulkDeleteBorrowers([1, 2])).toEqual({ updated: 2 });
        expect(await ops.bulkEditRecords([4], { language: 'fr' })).toEqual({ updated: 2 });
        expect(await ops.bulkDeleteRecords([4])).toEqual({ updated: 2 });
        expect(await ops.updateRecord(4, { title: 'Updated' })).toEqual({ id: 1 });
        expect(await ops.updateItem(8, { condition: 'damaged' })).toEqual({ id: 1 });
        expect(post).toHaveBeenCalledTimes(5);
        expect(patch).toHaveBeenNthCalledWith(1, '/catalog/records/4', { title: 'Updated' });
        expect(patch).toHaveBeenNthCalledWith(2, '/catalog/items/8', { condition: 'damaged' });
        vi.runAllTimers();
        expect(ops.showProgress.value).toBe(false);
        expect(ops.progress.value).toBe(0);
    });

    it('tracks errors and shows progress for large operations', async () => {
        const error = new Error('failed');
        vi.spyOn(apiClient, 'post').mockRejectedValue(error);
        const ops = useBulkOperations('borrowers');
        const promise = ops.bulkChangeClass(Array.from({ length: 100 }, (_, i) => i), 4);
        await expect(promise).rejects.toThrow('failed');
        expect(ops.error.value).toBe('failed');
        expect(ops.loading.value).toBe(false);
        expect(ops.showProgress.value).toBe(true);
    });
});

describe('useInventoryColumnSettings', () => {
    it('loads defaults, persists toggles and resets them', async () => {
        const settings = useInventoryColumnSettings();
        expect(settings.visibleColumns.value).toEqual(['item_id', 'title', 'condition', 'status']);
        expect(settings.isColumnVisible('title')).toBe(true);
        settings.toggleColumn('title');
        settings.toggleColumn('loanable');
        await nextTick();
        expect(settings.visibleColumns.value).toContain('loanable');
        expect(JSON.parse(localStorage.getItem('bcd_inventory_columns'))).toContain('loanable');
        settings.resetToDefaults();
        expect(settings.visibleColumns.value).toEqual(['item_id', 'title', 'condition', 'status']);
    });

    it('uses a stored column list', () => {
        localStorage.setItem('bcd_inventory_columns', JSON.stringify(['item_id', 'shelf_location']));
        const settings = useInventoryColumnSettings();
        expect(settings.visibleColumns.value).toEqual(['item_id', 'shelf_location']);
    });
});

describe('keyboard shortcuts', () => {
    const Harness = defineComponent({
        setup() {
            const calls = { admin: 0 };
            useKeyboardShortcuts();
            useAdminShortcuts({ I: () => { calls.admin++; } });
            return { calls };
        },
        render() { return h('div'); }
    });

    it('handles navigation, admin, modifier and blur events', async () => {
        const wrapper = mount(Harness);
        const preventDefault = vi.fn();
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Alt', altKey: false }));
        expect(altHeld.value).toBe(true);
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'c', altKey: true, preventDefault }));
        expect(window.location.hash).toBe('#/catalog');
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'i', altKey: true }));
        expect(wrapper.vm.calls.admin).toBe(1);
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'x', altKey: true, ctrlKey: true }));
        expect(wrapper.vm.calls.admin).toBe(1);
        window.dispatchEvent(new Event('blur'));
        expect(altHeld.value).toBe(false);
        document.dispatchEvent(new KeyboardEvent('keyup', { key: 'Alt' }));
        wrapper.unmount();
    });
});
