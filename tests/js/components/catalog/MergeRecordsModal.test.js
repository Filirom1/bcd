import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import { setTestTranslator } from '../../helpers/i18n.js';
import MergeRecordsModal from '../../../../src/bcd_web_vue/js/components/catalog/MergeRecordsModal.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const records = [
    { id: 1717, title: 'Wakou', total_items: 121, isbn_value: '0998-2221' },
    { id: 3529, title: 'Wakou 396', total_items: 1 },
    { id: 3502, title: 'Wakou 188', total_items: 1 }
];

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockResolvedValue([]);
});

afterEach(() => {
    vi.restoreAllMocks();
});

function mountModal(props = {}) {
    setTestTranslator(key => key);
    return mount(MergeRecordsModal, {
        props: {
            show: true,
            selectedRecords: records,
            ...props
        },
        global: {
            stubs: {
                Modal: {
                    props: ['show'],
                    template: '<div v-if="show"><slot name="header" /><slot /><slot name="footer" /></div>'
                }
            }
        }
    });
}

describe('MergeRecordsModal', () => {
    it('selects the record with the most copies and emits the complete merge request', async () => {
        const wrapper = mountModal();
        await flushPromises();

        expect(wrapper.vm.targetRecord.id).toBe(1717);
        expect(wrapper.vm.sourceRecords.map(record => record.id)).toEqual([3529, 3502]);
        expect(wrapper.vm.totalCopies).toBe(123);

        await wrapper.get('button.btn-warning').trigger('click');

        expect(wrapper.emitted('confirm')).toEqual([[
            {
                targetId: 1717,
                sourceIds: [3529, 3502]
            }
        ]]);
    });

    it('emits location and call number values separately for every copy', async () => {
        apiClient.get.mockImplementation(async endpoint => {
            const recordId = Number(endpoint.match(/bibliographic\/(\d+)/)[1]);
            const itemsByRecord = {
                1717: [{ id: 1, item_id: '001', shelf_location: 'Old A', call_number: 'A 001' }],
                3529: [{ id: 2, item_id: '002', shelf_location: 'Old B', call_number: 'B 002' }],
                3502: [{ id: 3, item_id: '003', shelf_location: null, call_number: null }]
            };
            if (endpoint.endsWith('/items')) return itemsByRecord[recordId];
            return { id: recordId, title: records.find(record => record.id === recordId).title, authors: ['Auteur'] };
        });
        const wrapper = mountModal();
        await flushPromises();

        const rows = wrapper.findAll('tbody tr');
        expect(rows).toHaveLength(2);
        await rows[0].findAll('input')[0].setValue('Albums');
        await rows[0].findAll('input')[1].setValue('A 002');
        await rows[1].findAll('input')[0].setValue('BD');
        await rows[1].findAll('input')[1].setValue('BD 003');
        await wrapper.get('button.btn-warning').trigger('click');

        expect(wrapper.emitted('confirm')).toEqual([[
            {
                targetId: 1717,
                sourceIds: [3529, 3502],
                itemUpdates: [
                    { itemId: 2, shelfLocation: 'Albums', callNumber: 'A 002' },
                    { itemId: 3, shelfLocation: 'BD', callNumber: 'BD 003' }
                ]
            }
        ]]);
    });

    it('recalculates a migrated copy call number when its shelf changes', async () => {
        apiClient.get.mockImplementation(async endpoint => {
            const recordId = Number(endpoint.match(/bibliographic\/(\d+)/)[1]);
            if (endpoint.endsWith('/items')) {
                return [{ id: 2, item_id: '002', shelf_location: null, call_number: null }];
            }
            return {
                id: recordId,
                title: 'Wakou 396',
                authors: ['Auteur'],
                collection: 'La Bibliothèque Rose'
            };
        });
        const wrapper = mountModal({
            settings: {
                catalog_shelf_locations: [{ label: 'Romans', color: '#c0392b' }],
                catalog_call_number_rules: [{ shelf_location: 'Romans', pattern: 'R {SER3}' }]
            }
        });
        await flushPromises();

        const inputs = wrapper.findAll('tbody tr')[0].findAll('input');
        await inputs[0].setValue('Romans');
        await flushPromises();

        expect(inputs[1].element.value).toBe('R BIB');
    });

    it('uses the selected radio record as the merge target', async () => {
        const wrapper = mountModal();
        await flushPromises();

        const radios = wrapper.findAll('input[type="radio"]');
        await radios[1].setValue();
        await flushPromises();
        await wrapper.get('button.btn-warning').trigger('click');

        expect(wrapper.emitted('confirm')).toEqual([[
            {
                targetId: 3529,
                sourceIds: [1717, 3502]
            }
        ]]);
    });

    it('does not confirm while the merge request is loading', async () => {
        const wrapper = mountModal({ loading: true });
        await flushPromises();

        await wrapper.get('button.btn-warning').trigger('click');

        expect(wrapper.emitted('confirm')).toBeUndefined();
    });
});
