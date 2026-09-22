import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import ItemBarcodeInput from '../../../../src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

function mountInput(props = {}) {
    return mount(ItemBarcodeInput, {
        props: {
            recordId: 42,
            recordTitle: 'Le Petit Prince',
            recordAuthors: ['Antoine de Saint-Exupéry'],
            ...props
        },
        global: {
            mocks: { $t: key => key },
            stubs: {
                DeweyPicker: true,
                ShelfLocationPicker: true
            }
        }
    });
}

beforeEach(() => {
    vi.spyOn(apiClient, 'post').mockImplementation(async (endpoint, data) => {
        if (endpoint === '/catalog/items') {
            return { id: 1, item_id: data.item_id, status: 'available' };
        }
        return {};
    });
    const { saveSettings } = useAppState();
    saveSettings({
        catalog_call_number_rules: JSON.stringify([
            { medium_type: 'Book', pattern: '{AUT3}' }
        ])
    });
});

afterEach(() => {
    vi.restoreAllMocks();
    const { clearStorage } = useAppState();
    clearStorage();
    useNotification().clear();
});

describe('ItemBarcodeInput', () => {
    it('creates physical item for a record when barcode is submitted', async () => {
        const postSpy = vi.spyOn(apiClient, 'post');
        const wrapper = mountInput();
        await flushPromises();

        wrapper.vm.barcode = 'BCD000123';
        await wrapper.vm.createItem();

        expect(postSpy).toHaveBeenCalledWith('/catalog/items', expect.objectContaining({
            bibliographic_record_id: 42,
            item_id: 'BCD000123'
        }));
        expect(wrapper.emitted('item-created')).toHaveLength(1);
    });

    it('computes suggested call number based on authors correctly (AUT3)', async () => {
        const wrapper = mountInput();
        await flushPromises();

        // "Saint-Exupéry" -> "SAINTEXUPERY" -> first 3 letters "SAI"
        expect(wrapper.vm.callNumber).toBe('SAI');
    });

    it('handles accented characters and names with commas correctly', async () => {
        const wrapper = mountInput({
            recordAuthors: ['Hébert, Jean-Marc']
        });
        await flushPromises();

        // "Hébert" -> "HEBERT" -> first 3 letters "HEB"
        expect(wrapper.vm.callNumber).toBe('HEB');
    });

    it('processes custom call number rule patterns correctly', async () => {
        const { saveSettings } = useAppState();
        saveSettings({
            catalog_call_number_rules: JSON.stringify([
                { medium_type: 'Book', pattern: '{DEWEY} {SER3} {TIT1}' }
            ])
        });

        const wrapper = mountInput({
            recordTitle: 'La gloire de mon père',
            recordAuthors: ['Marcel Pagnol'],
            recordCollection: 'La Bibliothèque Rose',
            recordDeweyNumber: '840',
            recordMediumType: 'Book'
        });
        await flushPromises();

        // DEWEY -> "840"
        // SER3 -> "BIB" (strips "La " from "La Bibliothèque Rose")
        // TIT1 -> "G" (strips "La " from "La gloire de mon père" -> "gloire..." -> first letter "G")
        expect(wrapper.vm.callNumber).toBe('840 BIB G');
    });

    it('recalculates the call number when the shelf location changes', async () => {
        const { saveSettings } = useAppState();
        saveSettings({
            catalog_shelf_locations: [
                { label: 'Romans', color: null },
                { label: 'Documentaires', color: null }
            ],
            catalog_call_number_rules: [
                { medium_type: null, shelf_location: 'Romans', pattern: 'R {AUT3}' },
                { medium_type: null, shelf_location: 'Documentaires', pattern: '{DEWEY} {AUT3}' }
            ]
        });

        const wrapper = mountInput({ recordDeweyNumber: '500' });
        await flushPromises();

        expect(wrapper.vm.callNumber).toBe('SAI');
        wrapper.vm.shelfLocation = 'Romans';
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.callNumber).toBe('R SAI');
    });

    it('recalculates after the suggested shelf location is prefilled', async () => {
        const { saveSettings } = useAppState();
        saveSettings({
            catalog_shelf_locations: [{ label: 'Romans', color: null }],
            catalog_call_number_rules: [
                { medium_type: null, shelf_location: 'Romans', pattern: 'R {AUT3}' }
            ]
        });

        const wrapper = mountInput({ recordMediumType: 'Roman' });
        await flushPromises();

        expect(wrapper.vm.shelfLocation).toBe('Romans');
        expect(wrapper.vm.callNumber).toBe('R SAI');
    });

    it('rejects an empty barcode and keeps the form available for cancellation', async () => {
        const wrapper = mountInput();
        await flushPromises();
        await wrapper.vm.createItem();

        expect(apiClient.post).not.toHaveBeenCalledWith('/catalog/items', expect.anything());
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ type: 'error', message: 'cataloging.error_no_barcode' })
        );
        wrapper.vm.finish();
        expect(wrapper.emitted('done')).toHaveLength(1);
    });

    it('sends optional fields and loanability when creating an item', async () => {
        const postSpy = vi.mocked(apiClient.post);
        const wrapper = mountInput();
        await flushPromises();
        wrapper.vm.barcode = 'I-002';
        wrapper.vm.shelfLocation = 'Romans';
        wrapper.vm.callNumber = 'R SAI';
        wrapper.vm.fundingSource = 'Donation';
        wrapper.vm.condition = 'damaged';
        wrapper.vm.loanable = false;
        await wrapper.vm.createItem();

        expect(postSpy).toHaveBeenCalledWith('/catalog/items', expect.objectContaining({
            item_id: 'I-002', bibliographic_record_id: 42,
            shelf_location: 'Romans', call_number: 'R SAI',
            funding_source: 'Donation', condition: 'damaged', loanable: false
        }));
        expect(wrapper.vm.itemCount).toBe(1);
        expect(wrapper.vm.barcode).toBe('');
    });

    it('reports duplicate barcode and generic server errors', async () => {
        const postSpy = vi.mocked(apiClient.post);
        const wrapper = mountInput();
        await flushPromises();
        postSpy.mockRejectedValueOnce({ code: 'duplicate_item_id' });
        wrapper.vm.barcode = 'DUPLICATE';
        await wrapper.vm.createItem();
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ type: 'error', message: 'cataloging.error_barcode_exists' })
        );

        postSpy.mockRejectedValueOnce(new Error('server error'));
        wrapper.vm.barcode = 'ERROR';
        await wrapper.vm.createItem();
        expect(wrapper.vm.loading).toBe(false);
    });

    it('requires an issue number for periodicals and clears it after creation', async () => {
        const postSpy = vi.mocked(apiClient.post);
        const wrapper = mountInput({ recordIdentifierType: 'issn' });
        await flushPromises();
        wrapper.vm.callNumber = '';
        wrapper.vm.barcode = 'ISSUE-1';
        await wrapper.vm.createItem();
        expect(postSpy.mock.calls.filter(([endpoint]) => endpoint === '/catalog/items')).toHaveLength(0);
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ type: 'error', message: 'periodical.required' })
        );

        wrapper.vm.callNumber = '42';
        await wrapper.vm.createItem();
        expect(postSpy).toHaveBeenCalledWith('/catalog/items', expect.objectContaining({ item_id: 'ISSUE-1', call_number: '42' }));
        expect(wrapper.vm.callNumber).toBe('');
    });

    it('updates and deletes created items with confirmation', async () => {
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const wrapper = mountInput();
        await flushPromises();
        wrapper.vm.createdItems = [{ item_id: 'I-1', status: 'available' }];
        wrapper.vm.editItem(wrapper.vm.createdItems[0]);
        expect(wrapper.vm.showItemEditModal).toBe(true);
        wrapper.vm.handleItemSaved({ item_id: 'I-1', status: 'on_loan' });
        expect(wrapper.vm.createdItems[0].status).toBe('on_loan');

        vi.stubGlobal('confirm', vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true));
        await wrapper.vm.deleteItem(wrapper.vm.createdItems[0]);
        expect(deleteSpy).not.toHaveBeenCalled();
        await wrapper.vm.deleteItem(wrapper.vm.createdItems[0]);
        expect(deleteSpy).toHaveBeenCalledWith('/catalog/items/I-1');
        expect(wrapper.vm.createdItems).toEqual([]);
    });

    it('emits edit-record and handles scanner Enter events', async () => {
        const wrapper = mountInput();
        await flushPromises();
        await wrapper.get('button').trigger('click');
        expect(wrapper.emitted('edit-record')).toHaveLength(1);
        const createSpy = vi.spyOn(wrapper.vm, 'createItem');
        wrapper.vm.handleKeypress({ key: 'Escape', preventDefault: vi.fn() });
        expect(createSpy).not.toHaveBeenCalled();
    });
});
