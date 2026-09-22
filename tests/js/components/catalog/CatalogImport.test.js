import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import CatalogImport from '../../../../src/bcd_web_vue/js/components/catalog/CatalogImport.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { events } from '../../../../src/bcd_web_vue/js/utils/events.js';

const mountedWrappers = [];

function mountImport() {
    const wrapper = mount(CatalogImport, {
        props: { show: true },
        global: {
            stubs: { Modal: true },
            mocks: { $t: key => key }
        }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

function fileEvent(name = 'catalog.csv', content = 'dc.title,dc.identifier\nLivre,isbn:1') {
    return {
        target: {
            files: [new File([content], name, { type: 'text/csv' })]
        }
    };
}

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
        importers: [
            { name: 'dublin_core', description: 'Dublin Core CSV' },
            { name: 'bcd', description: 'BCD CSV' }
        ]
    });
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
});

describe('CatalogImport', () => {
    it('loads available formats and selects the first format', async () => {
        const wrapper = mountImport();
        await flushPromises();

        expect(apiClient.get).toHaveBeenCalledWith('/catalog/importers');
        expect(wrapper.vm.importers).toHaveLength(2);
        expect(wrapper.vm.selectedFormat).toBe('dublin_core');
        expect(wrapper.vm.importersLoading).toBe(false);
    });

    it('accepts CSV files and rejects non-CSV files', () => {
        const alert = vi.spyOn(window, 'alert').mockImplementation(() => {});
        const wrapper = mountImport();

        wrapper.vm.onFileSelected(fileEvent('catalog.csv'));
        expect(wrapper.vm.selectedFile).toBeInstanceOf(File);
        expect(wrapper.vm.selectedFile.name).toBe('catalog.csv');

        wrapper.vm.onFileSelected(fileEvent('catalog.txt'));
        expect(wrapper.vm.selectedFile).toBe(null);
        expect(alert).toHaveBeenCalledWith('borrowers.import.invalid_file');
    });

    it('uploads a CSV with the selected format and preserves valid/invalid row results', async () => {
        const result = {
            records_created: 1,
            items_created: 1,
            records_skipped: 0,
            items_skipped: 0,
            errors: ['Ligne 2 : identifiant absent'],
            total_rows: 2
        };
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue(result);
        const wrapper = mountImport();
        await flushPromises();
        wrapper.vm.selectedFormat = 'bcd format';
        wrapper.vm.onFileSelected(fileEvent());

        await wrapper.vm.startImport();

        expect(post).toHaveBeenCalledTimes(1);
        const [endpoint, body] = post.mock.calls[0];
        expect(endpoint).toBe('/catalog/import?format=bcd%20format');
        expect(body).toBeInstanceOf(FormData);
        expect(body.get('file')).toBe(wrapper.vm.selectedFile);
        expect(wrapper.vm.importResult).toEqual(result);
        expect(wrapper.vm.importing).toBe(false);
    });

    it('turns an import failure into a result with an actionable detail', async () => {
        vi.spyOn(apiClient, 'post').mockRejectedValue(new Error('CSV malformed'));
        vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mountImport();
        wrapper.vm.onFileSelected(fileEvent());

        await wrapper.vm.startImport();

        expect(wrapper.vm.importResult).toMatchObject({
            records_created: 0,
            items_created: 0,
            total_rows: 0,
            errors: ['CSV malformed']
        });
        expect(wrapper.vm.importing).toBe(false);
    });

    it('emits refresh and completion only when the import creates data', async () => {
        const emit = vi.spyOn(events, 'emit');
        const wrapper = mountImport();
        wrapper.vm.importResult = {
            records_created: 2,
            items_created: 3,
            records_skipped: 1,
            items_skipped: 0,
            errors: [],
            total_rows: 3
        };

        wrapper.vm.onImportComplete();

        expect(emit).toHaveBeenCalledWith('catalog:refresh');
        expect(wrapper.emitted('import-complete')).toEqual([[expect.objectContaining({
            records_created: 2,
            items_created: 3
        })]]);
        expect(wrapper.emitted('close')).toHaveLength(1);
        expect(wrapper.vm.importResult).toBe(null);
    });

    it('does not refresh the catalog when every row is a duplicate', () => {
        const emit = vi.spyOn(events, 'emit');
        const wrapper = mountImport();
        wrapper.vm.importResult = {
            records_created: 0,
            items_created: 0,
            records_skipped: 2,
            items_skipped: 1,
            errors: [],
            total_rows: 3
        };

        wrapper.vm.onImportComplete();

        expect(emit).not.toHaveBeenCalledWith('catalog:refresh');
        expect(wrapper.emitted('import-complete')).toBeUndefined();
        expect(wrapper.emitted('close')).toHaveLength(1);
    });

    it('fails closed when the importer list cannot be loaded', async () => {
        apiClient.get.mockRejectedValueOnce(new Error('offline'));
        vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mountImport();
        await flushPromises();

        expect(wrapper.vm.importers).toEqual([]);
        expect(wrapper.vm.importersLoading).toBe(false);
    });
});
