import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import SearchTab from '../../../../src/bcd_web_vue/js/components/inventory/SearchTab.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const mountedWrappers = [];

function mountSearchTab(inventoryTable = { addItem: vi.fn() }) {
    const wrapper = shallowMount(SearchTab, {
        props: { inventoryTable },
        global: { mocks: { $t: key => key } }
    });
    mountedWrappers.push(wrapper);
    return { wrapper, inventoryTable };
}

const searchItem = {
    item_id: 'I-201',
    bibliographic_record_id: 20,
    title: 'Documentaire sciences',
    status: 'available',
    condition: 'good',
    loanable: true,
    shelf_location: 'Documentaires',
    call_number: '500 SCI',
    level: 'CM2',
    language: 'fr',
    medium_type: 'Book'
};

beforeEach(() => {
    useNotification().clear();
    useAppState().saveSettings({
        catalog_levels: 'CP, CM2',
        catalog_medium_types: 'Book, Magazine',
        catalog_languages: 'fr, en'
    });
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('SearchTab', () => {
    it('sends only active filters and warns when rotation history predates the archive', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            items: [searchItem],
            total: 250,
            displayed_count: 200,
            capped: true,
            archive_cutoff_date: '2024-01-01'
        });
        const { wrapper } = mountSearchTab();

        wrapper.vm.filters.q = 'sciences';
        wrapper.vm.filters.status = 'available';
        wrapper.vm.filters.never_inventoried = true;
        wrapper.vm.filters.max_borrows = 2;
        wrapper.vm.filters.since_date = '2023-01-01';
        await wrapper.vm.performSearch();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/inventory/items/search', {
            q: 'sciences',
            status: 'available',
            never_inventoried: true,
            max_borrows: 2,
            since_date: '2023-01-01'
        });
        expect(wrapper.vm.searchResults).toEqual([searchItem]);
        expect(wrapper.vm.totalCount).toBe(250);
        expect(wrapper.vm.displayedCount).toBe(200);
        expect(wrapper.vm.capped).toBe(true);
        expect(wrapper.vm.rotationFilterActive).toBe(true);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'warning', message: 'inventory.search.archive_warning' })
        ]);
    });

    it('adds selected search results to the working table and avoids an empty selection request', async () => {
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ items_updated: 1 });
        const { wrapper, inventoryTable } = mountSearchTab();

        await wrapper.vm.addSelectedToWorkingTable();
        expect(post).not.toHaveBeenCalled();
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'warning', message: 'inventory.search.no_selection' })
        ]);

        wrapper.vm.searchResults = [searchItem, { ...searchItem, item_id: 'I-202', title: 'Autre livre' }];
        wrapper.vm.toggleSelection('I-201');
        await wrapper.vm.addSelectedToWorkingTable();

        expect(post).toHaveBeenCalledWith('/inventory/items/bulk-mark', { item_ids: ['I-201'] });
        expect(inventoryTable.addItem).toHaveBeenCalledWith(expect.objectContaining({
            item_id: 'I-201',
            title: 'Documentaire sciences',
            last_inventoried_at: expect.any(String)
        }));
        expect(wrapper.emitted('switch-to-working-table')).toHaveLength(1);
    });

    it('selects all results, exposes settings suggestions, and clears the search state', async () => {
        const { wrapper } = mountSearchTab();
        wrapper.vm.searchResults = [searchItem, { ...searchItem, item_id: 'I-202' }];

        expect(wrapper.vm.levelOptions).toEqual(['CP', 'CM2']);
        expect(wrapper.vm.mediumTypeOptions).toEqual(['Book', 'Magazine']);
        expect(wrapper.vm.languageOptions).toEqual(['fr', 'en']);

        wrapper.vm.toggleSelectAll();
        expect(wrapper.vm.selectedCount).toBe(2);
        wrapper.vm.toggleSelectAll();
        expect(wrapper.vm.selectedCount).toBe(0);

        wrapper.vm.hasSearched = true;
        wrapper.vm.filters.q = 'old query';
        wrapper.vm.clearFilters();
        expect(wrapper.vm.hasSearched).toBe(false);
        expect(wrapper.vm.filters.q).toBe('');
        expect(wrapper.vm.searchResults).toEqual([]);
    });

    it('reports a failed search without leaving the loading state active', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('offline'));
        const { wrapper } = mountSearchTab();

        await wrapper.vm.performSearch();

        expect(wrapper.vm.searching).toBe(false);
        expect(wrapper.vm.hasSearched).toBe(true);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'inventory.search.error' })
        ]);
    });
});
