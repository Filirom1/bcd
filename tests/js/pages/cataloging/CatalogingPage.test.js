import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import CatalogingPage from '../../../../src/bcd_web_vue/js/pages/CatalogingPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mountedWrappers = [];

function mountCatalogingPage(query = {}) {
    globalThis.__testRoute.query = query;
    const wrapper = shallowMount(CatalogingPage, {
        global: {
            stubs: { PageHeader: false },
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

        expect(wrapper.vm.state).toBe('find-notice');
        expect(wrapper.vm.showBackButton).toBe(false);
        expect(wrapper.vm.pageTitle).toBe('cataloging.find_notice_title');

        wrapper.vm.handleLookupSuccess({ isbn: '9782070612758', title: record.title });

        expect(wrapper.vm.state).toBe('bibliographic-form');
        expect(wrapper.vm.isbn).toBe('9782070612758');
        expect(wrapper.vm.bnfData).toEqual({ isbn: '9782070612758', title: record.title });
        expect(wrapper.vm.showBackButton).toBe(true);
        expect(wrapper.vm.pageTitle).toBe('cataloging.bibliographic_form_title');
    });

    it('keeps supported identifiers and opens the form for not-found and manual-entry workflows', () => {
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

    it('does not use a title search query as an ISBN', () => {
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleLookupNotFound({
            value: 'J-magazine',
            inputType: 'text',
            title: 'J-magazine'
        });

        expect(wrapper.vm.isbn).toBe('');
        expect(wrapper.vm.initialTitle).toBe('J-magazine');

        wrapper.vm.resetWorkflow();
        wrapper.vm.handleManualEntry({
            value: 'Jmagazine',
            inputType: 'text',
            title: 'Jmagazine'
        });

        expect(wrapper.vm.isbn).toBe('');
        expect(wrapper.vm.initialTitle).toBe('Jmagazine');
    });

    it('normalizes a newly created record and enters item creation', () => {
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleRecordCreated(record);

        expect(wrapper.vm.state).toBe('item-creation');
        expect(wrapper.vm.createdRecord).toEqual({
            id: 42,
            record_id: 42,
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

    it('keeps a selected remote cover visible through copy creation', () => {
        const wrapper = mountCatalogingPage();
        wrapper.vm.bnfData = {
            title: record.title,
            cover_url: 'https://books.example/cover.jpg'
        };
        wrapper.vm.handleRecordCreated(record);

        expect(wrapper.vm.createdRecord.cover_url).toBe('https://books.example/cover.jpg');
    });

    it('opens checkout for a newly cataloged copy with its barcode prefilled', async () => {
        const push = vi.fn().mockResolvedValue(undefined);
        globalThis.__testRouter.push = push;
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleCheckoutItem({ item_id: 'BCD-123' });
        await flushPromises();

        expect(push).toHaveBeenCalledWith({
            name: 'checkout',
            query: { item_id: 'BCD-123' }
        });
    });

    it('does not navigate to checkout when the copy has no barcode', () => {
        const push = vi.fn();
        globalThis.__testRouter.push = push;
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleCheckoutItem({});

        expect(push).not.toHaveBeenCalled();
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

    it('places the action to catalog another document in the page header', async () => {
        const wrapper = mountCatalogingPage();
        wrapper.vm.handleExistingRecordFound(record);
        await wrapper.vm.$nextTick();

        const header = wrapper.find('.page-header');
        expect(header.text()).toContain('cataloging.catalog_another');
        expect(header.find('button').exists()).toBe(true);
    });

    it('keeps the stepper near the header and resets the URL to a clean lookup', () => {
        const replace = vi.fn().mockResolvedValue(undefined);
        globalThis.__testRouter.replace = replace;
        const wrapper = mountCatalogingPage();
        wrapper.vm.handleExistingRecordFound(record);

        const workflowCard = wrapper.get('[data-testid="cataloging-workflow-card"]');
        const stepper = workflowCard.get('[data-testid="cataloging-stepper"]');
        expect(stepper.classes()).toContain('flex-grow-1');
        expect(stepper.get('[role="group"]').classes())
            .toEqual(expect.arrayContaining(['d-flex', 'w-100']));
        expect(stepper.findAll('[role="group"] > button')).toHaveLength(3);
        stepper.findAll('[role="group"] > button').forEach(button => {
            expect(button.classes()).toContain('flex-fill');
        });
        expect(workflowCard.get('.card-body').exists()).toBe(true);
        expect(wrapper.find('[data-testid="cataloging-stepper"]').exists()).toBe(true);
        wrapper.vm.resetWorkflow();

        expect(replace).toHaveBeenLastCalledWith({
            query: { step: 'lookup' }
        });
        expect(wrapper.vm.state).toBe('find-notice');
    });

    it('pushes the active text query into the bibliographic form route', () => {
        const push = vi.fn().mockResolvedValue(undefined);
        globalThis.__testRouter.push = push;
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleManualEntry({
            value: 'Le Petit Prince',
            inputType: 'text',
            title: 'Le Petit Prince'
        });

        expect(push).toHaveBeenCalledWith({
            query: { step: 'bibliographic-form', query: 'Le Petit Prince' }
        });
    });

    it('retains the active title query rather than an earlier scanned barcode', () => {
        const push = vi.fn().mockResolvedValue(undefined);
        globalThis.__testRouter.push = push;
        const wrapper = mountCatalogingPage();

        wrapper.vm.handleManualEntry({
            value: 'Le Petit Prince',
            originalInput: '3780237306003',
            inputType: 'text',
            title: 'Le Petit Prince'
        });

        expect(wrapper.vm.originalInput).toBe('3780237306003');
        expect(push).toHaveBeenCalledWith({
            query: { step: 'bibliographic-form', query: 'Le Petit Prince' }
        });
    });

    it('keeps selected remote data when the unsaved form route is synchronized', async () => {
        const wrapper = mountCatalogingPage();
        const candidate = {
            title: 'Le Petit Prince',
            cover_url: 'https://books.example/cover.jpg'
        };
        wrapper.vm.lookupQuery = 'Le Petit Prince';
        wrapper.vm.handleLookupSuccess(candidate);
        globalThis.__testRoute.query = {
            step: 'bibliographic-form',
            query: 'Le Petit Prince'
        };

        await wrapper.vm.syncFromRoute();

        expect(wrapper.vm.bnfData).toEqual(candidate);
        expect(wrapper.vm.initialTitle).toBe('Le Petit Prince');
    });

    it('loads a record from the route when launched from the catalog', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue(record);
        const wrapper = mountCatalogingPage({ record_id: '42' });
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/42');
        expect(wrapper.vm.state).toBe('item-creation');
        expect(wrapper.vm.createdRecord.id).toBe(42);
    });

    it('restores a saved step from the route and discards malformed item routes', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue(record);
        const wrapper = mountCatalogingPage({
            step: 'item-creation',
            record_id: '42'
        });
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/42');
        expect(wrapper.vm.state).toBe('item-creation');

        const replace = vi.fn().mockResolvedValue(undefined);
        globalThis.__testRouter.replace = replace;
        globalThis.__testRoute.query = { step: 'item-creation' };
        await wrapper.vm.syncFromRoute();

        expect(wrapper.vm.state).toBe('find-notice');
        expect(replace).toHaveBeenLastCalledWith({ query: { step: 'lookup' } });
    });

    it('restores saved bibliographic data when navigating back and forward', async () => {
        const wrapper = mountCatalogingPage();
        wrapper.vm.handleExistingRecordFound(record);

        globalThis.__testRoute.query = {
            step: 'bibliographic-form',
            record_id: '42'
        };
        await wrapper.vm.syncFromRoute();
        expect(wrapper.vm.state).toBe('bibliographic-form');
        expect(wrapper.vm.existingRecord.title).toBe(record.title);

        globalThis.__testRoute.query = {
            step: 'item-creation',
            record_id: '42'
        };
        await wrapper.vm.syncFromRoute();
        expect(wrapper.vm.state).toBe('item-creation');
        expect(wrapper.vm.createdRecord.title).toBe(record.title);
    });

    it('resets to a new lookup when Escape is pressed', () => {
        const wrapper = mountCatalogingPage();
        wrapper.vm.handleManualEntry({
            value: 'Le Petit Prince',
            inputType: 'text',
            title: 'Le Petit Prince'
        });
        const preventDefault = vi.fn();

        wrapper.vm.handleKeydown({ key: 'Escape', preventDefault });

        expect(preventDefault).toHaveBeenCalledOnce();
        expect(wrapper.vm.state).toBe('find-notice');
        expect(wrapper.vm.lookupQuery).toBe('');
    });

    it('runs the active primary action on Enter when focus is outside a control', () => {
        const wrapper = mountCatalogingPage();
        wrapper.vm.handleExistingRecordFound(record);
        const createItem = vi.fn();
        wrapper.vm.itemBarcodeInputRef = { createItem };
        const preventDefault = vi.fn();

        wrapper.vm.handleKeydown({
            key: 'Enter',
            repeat: false,
            target: document.body,
            preventDefault
        });

        expect(preventDefault).toHaveBeenCalledOnce();
        expect(createItem).toHaveBeenCalledOnce();

        const inputPreventDefault = vi.fn();
        wrapper.vm.handleKeydown({
            key: 'Enter',
            repeat: false,
            target: document.createElement('input'),
            preventDefault: inputPreventDefault
        });
        expect(createItem).toHaveBeenCalledOnce();
        expect(inputPreventDefault).not.toHaveBeenCalled();
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

        expect(wrapper.vm.state).toBe('find-notice');
        expect(wrapper.vm.isbn).toBe('');
        expect(wrapper.vm.bnfData).toBe(null);
        expect(wrapper.vm.createdRecord).toBe(null);

        wrapper.vm.handleExistingRecordFound(record);
        wrapper.vm.handleItemsDone();
        expect(wrapper.vm.state).toBe('find-notice');
        expect(wrapper.vm.createdRecord).toBe(null);
    });
});
