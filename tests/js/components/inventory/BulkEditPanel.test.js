import { afterEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '@vue/test-utils';

import BulkEditPanel from '../../../../src/bcd_web_vue/js/components/inventory/BulkEditPanel.js';

const mountedWrappers = [];

function mountPanel(selectedCount = 2) {
    const wrapper = mount(BulkEditPanel, {
        props: {
            selectedCount,
            settings: {
                catalog_shelf_locations: JSON.stringify([
                    { label: 'Romans', color: '#4D99F2' },
                    { label: 'Documentaires', color: '#33CC66' }
                ]),
                catalog_languages: 'fr, en',
                catalog_medium_types: 'Livre, DVD',
                catalog_levels: 'CP, CM2'
            }
        },
        global: {
            stubs: {
                FilterSelect: true,
                ShelfLocationPicker: true
            }
        }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
});

describe('BulkEditPanel', () => {
    it('starts with every field unchanged and exposes configured suggestions', () => {
        const wrapper = mountPanel();

        expect(wrapper.vm.hasChanges).toBe(false);
        expect(wrapper.vm.itemCondition).toBe('unchanged');
        expect(wrapper.vm.itemStatus).toBe('unchanged');
        expect(wrapper.vm.loanable).toBe('unchanged');
        expect(wrapper.vm.targetAudience).toBe('unchanged');
        expect(wrapper.vm.shelfLocationOptions).toEqual([
            { label: 'Romans', color: '#4D99F2' },
            { label: 'Documentaires', color: '#33CC66' }
        ]);
        expect(wrapper.vm.languageSuggestions).toEqual(['fr', 'en']);
        expect(wrapper.vm.mediumTypeSuggestions).toEqual(['Livre', 'DVD']);
        expect(wrapper.vm.levelSuggestions).toEqual(['CP', 'CM2']);
    });

    it('builds item and record update payloads while leaving unchanged fields out', async () => {
        const wrapper = mountPanel();
        wrapper.vm.itemCondition = 'damaged';
        wrapper.vm.itemStatus = 'available';
        wrapper.vm.loanable = 'no';
        wrapper.vm.shelfLocation = 'Romans';
        wrapper.vm.callNumber = '800 DUP';
        wrapper.vm.level = 'CM2';
        wrapper.vm.targetAudience = 'child';
        wrapper.vm.language = 'fr';
        wrapper.vm.mediumType = 'Livre';
        await nextTick();
        // A shelf normally opts into generated call numbers; disable that
        // option here to cover the explicit manual call-number branch too.
        wrapper.vm.autoCallNumber = false;

        wrapper.vm.handleApply();

        expect(wrapper.emitted('apply')).toEqual([[
            {
                item_updates: {
                    condition: 'damaged',
                    status: 'available',
                    loanable: false,
                    shelf_location: 'Romans',
                    call_number: '800 DUP'
                },
                record_updates: {
                    level: 'CM2',
                    target_audience: 'child',
                    language: 'fr',
                    medium_type: 'Livre'
                }
            }
        ]]);
    });

    it('converts clear-value markers into explicit empty-string updates', () => {
        const wrapper = mountPanel();
        wrapper.vm.shelfLocation = '__clear__';
        wrapper.vm.callNumber = '__clear__';
        wrapper.vm.level = '__clear__';
        wrapper.vm.language = '__clear__';
        wrapper.vm.mediumType = '__clear__';
        wrapper.vm.targetAudience = 'adult';

        wrapper.vm.handleApply();

        expect(wrapper.emitted('apply')).toEqual([[
            {
                item_updates: {
                    shelf_location: '',
                    call_number: ''
                },
                record_updates: {
                    level: '',
                    target_audience: 'adult',
                    language: '',
                    medium_type: ''
                }
            }
        ]]);
    });

    it('automatically enables call-number generation when a shelf is chosen', async () => {
        const wrapper = mountPanel();
        wrapper.vm.shelfLocation = 'Documentaires';
        await nextTick();

        expect(wrapper.vm.autoCallNumber).toBe(true);
        expect(wrapper.vm.hasChanges).toBe(true);
        wrapper.vm.callNumber = '500 SCI';
        wrapper.vm.handleApply();

        const payload = wrapper.emitted('apply')[0][0];
        expect(payload.auto_call_number).toBe(true);
        expect(payload.item_updates.call_number).toBeUndefined();
    });

    it('does not apply or delete anything when no items are selected', () => {
        const wrapper = mountPanel(0);

        wrapper.vm.handleApply();
        wrapper.vm.handleDelete();

        expect(wrapper.emitted('apply')).toBeUndefined();
        expect(wrapper.emitted('delete')).toBeUndefined();
        expect(wrapper.find('button.btn-primary').attributes('disabled')).toBeDefined();
        expect(wrapper.find('button.btn-danger').attributes('disabled')).toBeDefined();
    });
});
