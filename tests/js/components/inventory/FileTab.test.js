import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import FileTab from '../../../../src/bcd_web_vue/js/components/inventory/FileTab.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const mountedWrappers = [];

function mountFileTab(inventoryTable = { addItem: vi.fn() }) {
    const wrapper = mount(FileTab, {
        props: { inventoryTable },
        global: { mocks: { $t: key => key } }
    });
    mountedWrappers.push(wrapper);
    return { wrapper, inventoryTable };
}

function fileEvent(content, name = 'inventory.txt') {
    return {
        target: {
            files: [{ name, text: async () => content }]
        }
    };
}

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('FileTab', () => {
    it('parses comments, blank lines, prefixes, and duplicates before validation', async () => {
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            items_updated: 1,
            items_not_found: ['I-102'],
            timestamp: '2030-01-01T10:00:00Z'
        });
        const { wrapper } = mountFileTab();

        await wrapper.vm.handleFileChange(fileEvent('.I-101\n\n# scanned shelf\nI-102\n.I-101'));

        expect(post).toHaveBeenCalledWith('/inventory/items/bulk-mark', {
            item_ids: ['I-101', 'I-102']
        });
        expect(wrapper.vm.fileName).toBe('inventory.txt');
        expect(wrapper.vm.parseResult).toEqual({
            totalIds: ['I-101', 'I-102'],
            totalCount: 2,
            validCount: 1,
            unknownIds: ['I-102'],
            timestamp: '2030-01-01T10:00:00Z'
        });
    });

    it('imports only valid IDs, adds their details, and switches to the working table', async () => {
        vi.spyOn(apiClient, 'post').mockResolvedValue({
            items_updated: 2,
            items_not_found: ['I-102']
        });
        const patch = vi.spyOn(apiClient, 'patch').mockImplementation(async url => ({
            item_id: url.split('/').pop(),
            title: `Book ${url.split('/').pop()}`
        }));
        const { wrapper, inventoryTable } = mountFileTab();

        await wrapper.vm.handleFileChange(fileEvent('I-101\nI-102\nI-103'));
        await wrapper.vm.handleImport();

        expect(patch).toHaveBeenCalledTimes(2);
        expect(inventoryTable.addItem).toHaveBeenCalledTimes(2);
        expect(inventoryTable.addItem).toHaveBeenCalledWith(expect.objectContaining({ item_id: 'I-101' }));
        expect(inventoryTable.addItem).toHaveBeenCalledWith(expect.objectContaining({ item_id: 'I-103' }));
        expect(wrapper.emitted('switch-to-working-table')).toHaveLength(1);
        expect(wrapper.vm.parseResult).toBe(null);
        expect(wrapper.vm.fileName).toBe('');
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'inventory.file.import_success' })
        ]);
    });

    it('reports an empty file and does not start an import', async () => {
        const post = vi.spyOn(apiClient, 'post');
        const { wrapper } = mountFileTab();

        await wrapper.vm.handleFileChange(fileEvent('  \n# nothing here\n'));

        expect(post).not.toHaveBeenCalled();
        expect(wrapper.vm.parsing).toBe(false);
        expect(wrapper.vm.parseResult).toBe(null);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'inventory.file.no_valid_ids' })
        ]);
    });
});
