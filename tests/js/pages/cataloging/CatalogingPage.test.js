import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import CatalogingPage from '../../../../src/bcd_web_vue/js/pages/CatalogingPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mountedWrappers = [];

function mountCatalogingPage(query = {}) {
    globalThis.__testRoute.query = query;
    const wrapper = shallowMount(CatalogingPage, {
        global: {
            mocks: {
                $t: key => key
            }
        }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

const record = {
    record_id: 42,
    title: 'Le Petit Prince',
    subtitle: 'Édition scolaire',
    medium_type: 'Book',
    identifier_type: 'isbn',
    dewey_number: '843',
    authors: ['Antoine de Saint-Exupéry'],
    collection: 'Romans',
    illustrators: ['Antoine de Saint-Exupéry']
};

beforeEach(() => {
    globalThis.__testRoute.query = {};
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    globalThis.__testRoute.query = {};
    vi.restoreAllMocks();
});

describe('CatalogingPage', () => {
    it('starts at ISBN lookup and moves to the bibliographic form after a successful lookup', () => {
        const wrapper = mountCatalogingPage();

        expect(wrapper.vm.state).toBe('isbn-lookup');
        expect(wrapper.vm.showBackButton).toBe(false);
        expect(wrapper.vm.pageTitle).toBe('cataloging.page_title');

        wrapper.vm.handleLookupSuccess({ isbn: '9782070612758', title: record.title });

        expect(wrapper.vm.state).toBe('bibliographic-form');
        expect(wrapper.vm.isbn).toBe('9782070612758');
        expect(wrapper.vm.bnfData).toEqual({ isbn: '9782070612758', title: record.title });
        expect(wrapper.vm.showBackButton).toBe(true);
        expect(wrapper.vm.pageTitle).toBe('cataloging.bibliographic_form_title');
    });

    it('keeps the ISBN and opens the form for not-found and manual-entry workflows', () => {
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleLookupNotFound('9780000000000');
        expect(wrapper.vm.state).toBe('bibliographic-form');
        expect(wrapper.vm.bnfData).toBe(null);
        expect(wrapper.vm.isbn).toBe('9780000000000');

        wrapper.vm.resetWorkflow();
        wrapper.vm.handleManualEntry('123456789X');
        expect(wrapper.vm.state).toBe('bibliographic-form');
        expect(wrapper.vm.isbn).toBe('123456789X');
    });

    it('normalizes a newly created record and enters item creation', () => {
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleRecordCreated(record);

        expect(wrapper.vm.state).toBe('item-creation');
        expect(wrapper.vm.createdRecord).toEqual({
            id: 42,
            title: record.title,
            subtitle: record.subtitle,
            medium_type: record.medium_type,
            identifier_type: record.identifier_type,
            dewey_number: record.dewey_number,
            authors: record.authors,
            collection: record.collection,
            illustrators: record.illustrators
        });
        expect(wrapper.vm.existingRecord).toBe(null);
        expect(wrapper.vm.pageTitle).toBe('cataloging.item_creation_title');
    });

    it('opens an existing record directly in item creation with fallback fields', () => {
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleExistingRecordFound({
            id: 9,
            title: 'Documentaire',
            medium_type: 'Book',
            identifier_type: 'isbn'
        });

        expect(wrapper.vm.state).toBe('item-creation');
        expect(wrapper.vm.createdRecord).toMatchObject({
            id: 9,
            title: 'Documentaire',
            subtitle: null,
            dewey_number: null,
            authors: [],
            collection: null,
            illustrators: []
        });
    });

    it('loads a record from the route when launched from the catalog', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue(record);
        const wrapper = mountCatalogingPage({ record_id: '42' });
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/42');
        expect(wrapper.vm.state).toBe('item-creation');
        expect(wrapper.vm.createdRecord.id).toBe(42);
    });

    it('allows editing the created record and falls back to the current data if loading fails', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ ...record, title: 'Version à jour' });
        const wrapper = mountCatalogingPage();
        wrapper.vm.handleRecordCreated(record);

        await wrapper.vm.handleEditRecord();
        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/42');
        expect(wrapper.vm.state).toBe('bibliographic-form');
        expect(wrapper.vm.existingRecord.title).toBe('Version à jour');

        wrapper.vm.handleFormCancel();
        expect(wrapper.vm.state).toBe('item-creation');
        expect(wrapper.vm.existingRecord).toBe(null);

        get.mockRejectedValueOnce(new Error('offline'));
        await wrapper.vm.handleEditRecord();
        expect(wrapper.vm.state).toBe('bibliographic-form');
        expect(wrapper.vm.existingRecord).toEqual(wrapper.vm.createdRecord);
    });

    it('resets the whole workflow when cancelling a new bibliographic form or finishing items', () => {
        const wrapper = mountCatalogingPage();
        wrapper.vm.handleManualEntry('123456789X');
        wrapper.vm.handleFormCancel();

        expect(wrapper.vm.state).toBe('isbn-lookup');
        expect(wrapper.vm.isbn).toBe('');
        expect(wrapper.vm.bnfData).toBe(null);
        expect(wrapper.vm.createdRecord).toBe(null);

        wrapper.vm.handleExistingRecordFound(record);
        wrapper.vm.handleItemsDone();
        expect(wrapper.vm.state).toBe('isbn-lookup');
        expect(wrapper.vm.createdRecord).toBe(null);
    });
});
