import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import ItemScanner from '../../../../src/bcd_web_vue/js/components/circulation/ItemScanner.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mockItemsResponse = [
    { item_id: 'I-001', status: 'available' },
    { item_id: 'I-002', status: 'on_loan' }
];

const mockSearchResponse = {
    items: [
        {
            id: 1,
            title: 'Le Petit Prince',
            authors: ['Antoine de Saint-Exupéry'],
            medium_type: 'Book',
            total_items: 2,
            physical_items: mockItemsResponse
        }
    ]
};

beforeEach(() => {
    globalThis.__testTranslate = (key) => {
        if (key === 'item.status_available') return 'Available';
        if (key === 'catalog.status_en_cours') return 'En cours';
        return key;
    };

    vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint, params = {}) => {
        if (endpoint === '/catalog/bibliographic/search') {
            if (params && params.include_items) {
                return mockSearchResponse;
            }
            // Return copy without physical_items if include_items is false
            return {
                items: mockSearchResponse.items.map(({ physical_items, ...rest }) => rest)
            };
        }
        if (endpoint.includes('/items')) {
            return mockItemsResponse;
        }
        return [];
    });
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('ItemScanner', () => {
    it('fetches items for autocomplete query and formats result', async () => {
        const wrapper = mount(ItemScanner, {
            props: {
                mode: 'checkout',
                borrower: { id: 1 }
            }
        });
        await flushPromises();

        const results = await wrapper.vm.fetchItems('Petit');
        expect(results).toHaveLength(1);
        expect(results[0].title).toBe('Le Petit Prince');
        expect(results[0].physical_items).toEqual(mockItemsResponse);

        const html = wrapper.vm.formatItemResult(results[0]);
        expect(html).toContain('Le Petit Prince');
        expect(html).toContain('Available');
    });

    it('formats result in return mode differently showing on loan items', async () => {
        const wrapper = mount(ItemScanner, {
            props: {
                mode: 'return'
            }
        });
        await flushPromises();

        const results = await wrapper.vm.fetchItems('Petit');
        const html = wrapper.vm.formatItemResult(results[0]);
        expect(html).toContain('I-002 - Le Petit Prince');
        expect(html).toContain('En cours');
    });

    it('emits item-scanned event when a value is submitted', async () => {
        const wrapper = mount(ItemScanner, {
            props: {
                mode: 'checkout',
                borrower: { id: 1 }
            }
        });
        await flushPromises();

        wrapper.vm.itemBarcode = '.I-001';
        await wrapper.get('form').trigger('submit');

        expect(wrapper.emitted('item-scanned')).toEqual([['.I-001']]);
        expect(wrapper.vm.itemBarcode).toBe('');
    });
});
