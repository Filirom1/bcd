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
    vi.useRealTimers();
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

    it('auto-checks out rapid scanner input in checkout without Enter', async () => {
        vi.useFakeTimers();
        const wrapper = mount(ItemScanner, {
            props: { mode: 'checkout', borrower: { id: 1 } }
        });
        const autocomplete = wrapper.findComponent({ name: 'AutocompleteInput' });

        autocomplete.vm.handleInput({ target: { value: '7' } });
        autocomplete.vm.handleInput({ target: { value: '78' } });
        autocomplete.vm.handleInput({ target: { value: '785' } });
        expect(wrapper.emitted('item-scanned')).toBeUndefined();

        await vi.advanceTimersByTimeAsync(120);
        expect(wrapper.emitted('item-scanned')).toEqual([['785']]);
        expect(wrapper.vm.itemBarcode).toBe('');
        wrapper.unmount();
    });

    it('auto-submits a prefilled copy only in checkout after a borrower is selected', async () => {
        const wrapper = mount(ItemScanner, {
            props: {
                mode: 'checkout',
                initialItemId: '.I-003'
            }
        });
        await flushPromises();

        expect(wrapper.vm.itemBarcode).toBe('.I-003');
        expect(wrapper.emitted('item-scanned')).toBeUndefined();
        expect(wrapper.findComponent({ name: 'AutocompleteInput' }).props('autoSubmitOnScanner')).toBe(false);

        await wrapper.setProps({ borrower: { id: 1 } });
        await flushPromises();

        expect(wrapper.emitted('item-scanned')).toEqual([['.I-003']]);
        expect(wrapper.vm.itemBarcode).toBe('');
        expect(wrapper.findComponent({ name: 'AutocompleteInput' }).props('autoSubmitOnScanner')).toBe(true);
    });

    it('does not auto-submit a prefilled copy outside checkout or while disabled', async () => {
        const returnScanner = mount(ItemScanner, {
            props: { mode: 'return', initialItemId: 'I-004' }
        });
        await flushPromises();
        expect(returnScanner.emitted('item-scanned')).toBeUndefined();
        expect(returnScanner.findComponent({ name: 'AutocompleteInput' }).props('autoSubmitOnScanner')).toBe(false);

        const disabledCheckout = mount(ItemScanner, {
            props: {
                mode: 'checkout',
                borrower: { id: 1 },
                disabled: true,
                initialItemId: 'I-005'
            }
        });
        await flushPromises();
        expect(disabledCheckout.emitted('item-scanned')).toBeUndefined();
        expect(disabledCheckout.findComponent({ name: 'AutocompleteInput' }).props('autoSubmitOnScanner')).toBe(false);

        await disabledCheckout.setProps({ disabled: false });
        await flushPromises();
        expect(disabledCheckout.emitted('item-scanned')).toEqual([['I-005']]);
    });

    it('filters return suggestions to copies that are currently on loan', async () => {
        const returnRecord = { id: 2, title: 'Returned candidate', physical_items: [{ item_id: 'I-2', status: 'available' }] };
        vi.mocked(apiClient.get).mockResolvedValueOnce({ items: [mockSearchResponse.items[0], returnRecord] });
        const wrapper = mount(ItemScanner, { props: { mode: 'return' } });

        const results = await wrapper.vm.fetchItems('book', new AbortController().signal);
        expect(results).toHaveLength(1);
        expect(results[0].physical_items[0].status).toBe('available');
    });

    it('selects the available copy for checkout and the loaned copy for return', async () => {
        vi.useFakeTimers();
        const checkout = mount(ItemScanner, { props: { mode: 'checkout', borrower: { id: 1 } } });
        const returned = mount(ItemScanner, { props: { mode: 'return' } });
        await checkout.vm.handleItemSelect(mockSearchResponse.items[0]);
        await returned.vm.handleItemSelect(mockSearchResponse.items[0]);

        expect(checkout.emitted('item-scanned')).toEqual([['I-001']]);
        expect(returned.emitted('item-scanned')).toEqual([['I-002']]);
        vi.advanceTimersByTime(50);
        expect(checkout.vm.scanning).toBe(false);
        vi.useRealTimers();
    });

    it('does not scan without a borrower, with a blank barcode, or during another scan', async () => {
        vi.useFakeTimers();
        const noBorrower = mount(ItemScanner, { props: { mode: 'checkout' } });
        await noBorrower.vm.scanItem('I-1');
        expect(noBorrower.emitted('item-scanned')).toBeUndefined();

        const wrapper = mount(ItemScanner, { props: { mode: 'checkout', borrower: { id: 1 } } });
        await wrapper.vm.scanItem('');
        await wrapper.vm.scanItem('I-1');
        await wrapper.vm.scanItem('I-2');
        expect(wrapper.emitted('item-scanned')).toEqual([['I-1']]);
        vi.advanceTimersByTime(50);
        vi.useRealTimers();
    });

    it('formats missing metadata and propagates autocomplete API failures', async () => {
        const wrapper = mount(ItemScanner, { props: { mode: 'checkout', borrower: { id: 1 } } });
        const html = wrapper.vm.formatItemResult({ physical_items: [], authors: [] });
        expect(html).toContain('N/A');
        expect(html).toContain('catalog.unknown_title');
        expect(html).toContain('catalog.unknown_author');

        const error = new Error('offline');
        vi.mocked(apiClient.get).mockRejectedValue(error);
        await expect(wrapper.vm.fetchItems('x', new AbortController().signal)).rejects.toBe(error);
    });
});
