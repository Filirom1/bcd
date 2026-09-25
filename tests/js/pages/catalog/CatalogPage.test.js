import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import CatalogPage from '../../../../src/bcd_web_vue/js/pages/CatalogPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';
import { setTestTranslator } from '../../helpers/i18n.js';

const records = [
    { id: 10, title: 'Le Petit Prince', author: 'Antoine de Saint-Exupéry' }
];
const searchResponse = {
    items: records,
    total: 1,
    limit: 10,
    offset: 0
};
const mountedWrappers = [];

function mountCatalogPage() {
    const wrapper = shallowMount(CatalogPage);
    mountedWrappers.push(wrapper);
    return wrapper;
}

function mockCatalogApi() {
    return vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
        if (endpoint === '/catalog/locations') return { locations: ['Romans'] };
        if (endpoint === '/catalog/bibliographic/search') return searchResponse;
        throw new Error(`Unexpected GET request: ${endpoint}`);
    });
}

beforeEach(() => {
    useNotification().clear();
    setTestTranslator(key => key);
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('CatalogPage', () => {
    it('loads locations and searches the catalog on mount', async () => {
        const get = mockCatalogApi();
        const wrapper = mountCatalogPage();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/locations');
        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/search', {
            limit: 10,
            offset: 0
        });
        expect(wrapper.vm.results).toEqual(records);
        expect(wrapper.vm.totalItems).toBe(1);
        expect(wrapper.vm.shelfLocations).toEqual(['Romans']);
    });

    it('normalizes ISBN input and resets pagination when searching', async () => {
        const get = mockCatalogApi();
        const wrapper = mountCatalogPage();
        await flushPromises();

        await wrapper.vm.handleSearch('978-2-07-061275-8');
        await flushPromises();

        expect(get).toHaveBeenLastCalledWith('/catalog/bibliographic/search', {
            limit: 10,
            offset: 0,
            q: '9782070612758'
        });
        expect(wrapper.vm.currentPage).toBe(1);
    });

    it('translates filters into API parameters', async () => {
        const get = mockCatalogApi();
        const wrapper = mountCatalogPage();
        await flushPromises();

        await wrapper.vm.handleFilter({
            availability: 'available',
            level: 'CM2',
            language: 'fr',
            medium_type: 'Book',
            shelf_location: 'Romans'
        });
        await flushPromises();

        expect(get).toHaveBeenLastCalledWith('/catalog/bibliographic/search', {
            limit: 10,
            offset: 0,
            available_only: true,
            level: 'CM2',
            language: 'fr',
            medium_type: 'Book',
            shelf_location: 'Romans'
        });
    });

    it('opens the selected record for editing and rejects invalid selection counts', async () => {
        mockCatalogApi();
        const wrapper = mountCatalogPage();
        await flushPromises();

        wrapper.vm.handleEditSelected();
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'admin.select_at_least_one' })
        ]);

        wrapper.vm.handleToggleSelection(10);
        wrapper.vm.handleEditSelected();

        expect(wrapper.vm.editingRecord).toEqual(records[0]);
        expect(wrapper.vm.showRecordEditModal).toBe(true);
    });

    it('clears stale results and reports a failed search', async () => {
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/catalog/locations') return { locations: [] };
            throw new Error('server unavailable');
        });
        const wrapper = mountCatalogPage();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/search', {
            limit: 10,
            offset: 0
        });
        expect(wrapper.vm.results).toEqual([]);
        expect(wrapper.vm.totalItems).toBe(0);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.unknown_error' })
        ]);
    });

    it('maps borrowed and reserved availability filters to their API flags', async () => {
        const get = mockCatalogApi();
        const wrapper = mountCatalogPage();
        await flushPromises();

        await wrapper.vm.handleFilter({ availability: 'borrowed' });
        await flushPromises();
        expect(get).toHaveBeenLastCalledWith('/catalog/bibliographic/search', {
            limit: 10,
            offset: 0,
            borrowed_only: true
        });

        await wrapper.vm.handleFilter({ availability: 'reserved' });
        await flushPromises();
        expect(get).toHaveBeenLastCalledWith('/catalog/bibliographic/search', {
            limit: 10,
            offset: 0,
            has_holds: true
        });
    });

    it('clears the catalog selection when changing page or page size', async () => {
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/catalog/locations') return { locations: [] };
            if (endpoint === '/catalog/bibliographic/search') {
                return { ...searchResponse, total: 30 };
            }
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const wrapper = mountCatalogPage();
        await flushPromises();

        wrapper.vm.handleToggleSelection(10);
        expect(wrapper.vm.selectedCount).toBe(1);

        await wrapper.vm.handlePageChange(2);
        await flushPromises();
        expect(wrapper.vm.currentPage).toBe(2);
        expect(wrapper.vm.selectedCount).toBe(0);
        expect(get).toHaveBeenLastCalledWith('/catalog/bibliographic/search', {
            limit: 10,
            offset: 10
        });

        wrapper.vm.handleToggleSelection(10);
        await wrapper.vm.handlePageSizeChange(25);
        await flushPromises();
        expect(wrapper.vm.currentPage).toBe(1);
        expect(wrapper.vm.selectedCount).toBe(0);
        expect(get).toHaveBeenLastCalledWith('/catalog/bibliographic/search', {
            limit: 25,
            offset: 0
        });
    });

    it('executes catalog bulk edits, clears selection, and refreshes the results', async () => {
        const get = mockCatalogApi();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ modified_count: 1 });
        const wrapper = mountCatalogPage();
        await flushPromises();
        wrapper.vm.handleToggleSelection(10);

        await wrapper.vm.handleExecuteBulkOperation({
            operation: 'bulk_edit',
            fields: { language: 'fr' }
        });
        await flushPromises();

        expect(post).toHaveBeenCalledWith('/admin/catalog/bulk-edit', {
            record_ids: [10],
            language: 'fr'
        });
        expect(wrapper.vm.selectedCount).toBe(0);
        expect(get).toHaveBeenCalledTimes(3);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'admin.operation_success' })
        ]);
    });

    it('merges selected records through the catalog API and clears selection', async () => {
        const get = mockCatalogApi();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            operation: 'merge_bibliographic_records',
            successful_count: 1
        });
        const wrapper = mountCatalogPage();
        await flushPromises();

        wrapper.vm.results = [
            ...records,
            { id: 11, title: 'Duplicate record', total_items: 1 }
        ];
        wrapper.vm.handleToggleSelection(10);
        wrapper.vm.handleToggleSelection(11);
        wrapper.vm.handleMergeRecords();
        expect(wrapper.vm.showMergeRecordsModal).toBe(true);

        await wrapper.vm.executeMergeRecords({ targetId: 10, sourceIds: [11] });
        await flushPromises();

        expect(post).toHaveBeenCalledWith('/admin/catalog/merge', {
            source_ids: [11],
            target_id: 10
        });
        expect(wrapper.vm.showMergeRecordsModal).toBe(false);
        expect(wrapper.vm.selectedCount).toBe(0);
        expect(get).toHaveBeenCalledTimes(3);
    });

    it('closes the edit modal safely after a record is deleted', async () => {
        const get = mockCatalogApi();
        const wrapper = mountCatalogPage();
        await flushPromises();
        wrapper.vm.editingRecord = records[0];
        wrapper.vm.showRecordEditModal = true;

        wrapper.vm.handleRecordDeleted(10);
        await flushPromises();

        expect(wrapper.vm.editingRecord).toBe(null);
        expect(wrapper.vm.showRecordEditModal).toBe(false);
        expect(get).toHaveBeenCalledTimes(3);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'admin.record_deleted' })
        ]);
    });

    it('exports the catalog, reports export failures, and builds the print route', async () => {
        mockCatalogApi();
        const download = vi.spyOn(apiClient, 'download').mockResolvedValue();
        const open = vi.spyOn(window, 'open').mockImplementation(() => null);
        const wrapper = mountCatalogPage();
        await flushPromises();

        await wrapper.vm.handleExportCatalog();
        expect(download).toHaveBeenCalledWith('/catalog/export', 'catalog_export.csv', {}, {
            headers: { Accept: 'text/csv' }
        });
        expect(wrapper.vm.exportLoading).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'catalog.export_success' })
        ]);

        download.mockRejectedValueOnce(new Error('disk full'));
        await wrapper.vm.handleExportCatalog();
        expect(wrapper.vm.exportLoading).toBe(false);
        expect(useNotification().notifications.value.at(-1)).toEqual(
            expect.objectContaining({ type: 'error', message: 'catalog.export_failed: disk full' })
        );

        wrapper.vm.handlePrintLabels();
        expect(open).toHaveBeenCalledWith('#/print/catalog/labels', '_blank');
    });
});
