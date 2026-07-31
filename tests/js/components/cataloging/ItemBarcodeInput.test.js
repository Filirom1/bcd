import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import ItemBarcodeInput from '../../../../src/bcd_web_vue/js/components/cataloging/ItemBarcodeInput.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';

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
});
