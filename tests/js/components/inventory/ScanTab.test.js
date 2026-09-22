import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import ScanTab from '../../../../src/bcd_web_vue/js/components/inventory/ScanTab.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const mountedWrappers = [];

function mountScanTab(inventoryTable = { addItem: vi.fn() }) {
    const wrapper = mount(ScanTab, {
        props: { inventoryTable },
        global: { mocks: { $t: key => key } }
    });
    mountedWrappers.push(wrapper);
    return { wrapper, inventoryTable };
}

beforeEach(() => {
    useNotification().clear();
    useAppState().saveSettings({ item_barcode_prefix: '.' });
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('ScanTab', () => {
    it('strips the configured prefix, marks the item, and adds its full details', async () => {
        const item = {
            item_id: 'I-101',
            bibliographic_record_id: 10,
            title: 'Le Petit Prince',
            status: 'available',
            condition: 'good',
            loanable: true,
            last_inventoried_at: '2030-01-01T00:00:00Z'
        };
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue(item);
        const { wrapper, inventoryTable } = mountScanTab();

        wrapper.vm.barcodeInput = '  .I-101  ';
        await wrapper.vm.handleScan();
        await flushPromises();

        expect(patch).toHaveBeenCalledWith('/inventory/items/I-101');
        expect(inventoryTable.addItem).toHaveBeenCalledWith(expect.objectContaining(item));
        expect(wrapper.vm.barcodeInput).toBe('');
        expect(wrapper.vm.scanning).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'inventory.scan.item_scanned' })
        ]);
    });

    it('leaves the working table unchanged for an unknown barcode', async () => {
        const addItem = vi.fn();
        vi.spyOn(apiClient, 'patch').mockRejectedValue({ statusCode: 404 });
        const { wrapper } = mountScanTab({ addItem });

        wrapper.vm.barcodeInput = '.UNKNOWN';
        await wrapper.vm.handleScan();

        expect(addItem).not.toHaveBeenCalled();
        expect(wrapper.vm.barcodeInput).toBe('');
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'inventory.scan.item_not_found' })
        ]);
    });

    it('does not call the API for a blank submission', async () => {
        const patch = vi.spyOn(apiClient, 'patch');
        const { wrapper } = mountScanTab();

        wrapper.vm.barcodeInput = '   ';
        await wrapper.vm.handleScan();

        expect(patch).not.toHaveBeenCalled();
        expect(useNotification().notifications.value).toEqual([]);
    });
});
