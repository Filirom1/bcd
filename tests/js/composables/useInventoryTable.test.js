import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

import { useInventoryTable } from '../../../src/bcd_web_vue/js/composables/useInventoryTable.js';
import { apiClient } from '../../../src/bcd_web_vue/js/api/client.js';

beforeEach(() => {
    localStorage.clear();
});

afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
});

describe('useInventoryTable', () => {
    it('manages adding, deduplicating, and clearing items', () => {
        const table = useInventoryTable();

        table.addItem({ item_id: 'I-101', title: 'Book 1' });
        expect(table.items.value).toHaveLength(1);
        expect(table.getAllItemIds()).toEqual(['I-101']);

        // Adding duplicate moves it to top/deduplicates
        table.addItem({ item_id: 'I-102', title: 'Book 2' });
        table.addItem({ item_id: 'I-101', title: 'Book 1 (modified)' });

        expect(table.items.value).toHaveLength(2);
        expect(table.items.value[0].item_id).toBe('I-101'); // moved to top
        expect(table.items.value[0].title).toBe('Book 1 (modified)');

        table.clearAll();
        expect(table.items.value).toHaveLength(0);
        expect(table.getAllItemIds()).toHaveLength(0);
        expect(localStorage.getItem('bcd_inventory_table_ids')).toBeNull();
    });

    it('restores state from localStorage and fetches fresh item details from the API', async () => {
        localStorage.setItem('bcd_inventory_table_ids', JSON.stringify(['I-201', 'I-202']));
        const patchSpy = vi.spyOn(apiClient, 'patch').mockImplementation(async (url) => {
            const item_id = url.split('/').pop();
            return {
                item_id,
                title: `Fetched ${item_id}`,
                status: 'available'
            };
        });

        const table = useInventoryTable(); // automatically calls restore()
        await flushPromises();

        expect(table.loading.value).toBe(false);
        expect(table.items.value).toHaveLength(2);
        expect(table.items.value[0].title).toBe('Fetched I-201');
        expect(patchSpy).toHaveBeenCalledTimes(2);
    });
});
