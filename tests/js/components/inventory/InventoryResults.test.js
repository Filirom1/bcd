import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '@vue/test-utils';

import InventoryResults from '../../../../src/bcd_web_vue/js/components/inventory/InventoryResults.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';

const mountedWrappers = [];

const visibleColumns = [
    'item_id', 'title', 'condition', 'status', 'call_number', 'loanable',
    'shelf_location', 'level', 'target_audience', 'language', 'medium_type',
    'last_inventoried'
];

function makeItem(overrides = {}) {
    return {
        item_id: 'I-101',
        title: 'Le Petit Prince',
        condition: 'good',
        status: 'available',
        call_number: '843 SAI',
        loanable: true,
        shelf_location: 'Romans',
        level: 'CM2',
        target_audience: 'child',
        language: 'fr',
        medium_type: 'Livre',
        last_inventoried_at: '2030-01-02',
        ...overrides
    };
}

function mountResults(items = [makeItem()], selectedIds = new Set(), columns = visibleColumns) {
    const wrapper = mount(InventoryResults, {
        props: { items, selectedIds, visibleColumns: columns }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

beforeEach(() => {
    useAppState().saveSettings({
        catalog_shelf_locations: JSON.stringify([{ label: 'Romans', color: '#4D99F2' }]),
        dewey_colors: JSON.stringify(['#000000', '#111111', '#222222', '#333333', '#444444', '#555555', '#666666', '#777777', '#888888', '#999999'])
    });
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
});

describe('InventoryResults', () => {
    it('keeps the selection column and only exposes configured data columns', () => {
        const wrapper = mountResults([makeItem()], new Set(), ['item_id', 'title', 'status']);

        expect(wrapper.vm.tableColumns.map(column => column.key)).toEqual([
            'select', 'item_id', 'title', 'status'
        ]);
        expect(wrapper.findAll('thead th')).toHaveLength(4);
    });

    it('emits individual and global selection changes and exposes partial selection', async () => {
        const item = makeItem();
        const second = makeItem({ item_id: 'I-102', title: 'Autre titre' });
        const wrapper = mountResults([item, second], new Set(['I-101']));

        expect(wrapper.vm.isSelected('I-101')).toBe(true);
        expect(wrapper.vm.isSelected('I-102')).toBe(false);
        wrapper.vm.toggleItemSelection('I-102');
        wrapper.vm.toggleSelectAll();

        expect(wrapper.emitted('toggle-selection')).toEqual([['I-102']]);
        expect(wrapper.emitted('toggle-select-all')).toHaveLength(1);

        await nextTick();
        expect(wrapper.vm.headerCheckboxRef.indeterminate).toBe(true);
    });

    it('renders condition/status badges and supports editing an item or its notice', () => {
        const item = makeItem({ condition: 'damaged', status: 'lost' });
        const wrapper = mountResults([item]);

        const badges = wrapper.findAll('tbody span.badge');
        expect(badges[0].classes()).toContain('bg-warning');
        expect(badges[1].classes()).toContain('bg-danger');
        expect(badges[0].text()).toBe('item.condition_damaged');
        expect(badges[1].text()).toBe('item.status_lost');

        wrapper.vm.handleEditItem(item);
        wrapper.vm.handleEditRecord(item);
        expect(wrapper.emitted('edit-item')).toEqual([[item]]);
        expect(wrapper.emitted('edit-record')).toEqual([[item]]);
    });

    it('truncates long titles, formats inventory dates, and renders configured badges', () => {
        const longTitle = 'A'.repeat(45);
        const wrapper = mountResults([makeItem({ title: longTitle })]);

        expect(wrapper.vm.truncateTitle(longTitle)).toBe(`${'A'.repeat(40)}…`);
        expect(wrapper.vm.formatDate('2030-01-02')).not.toBe('');
        expect(wrapper.find('tbody').text()).toContain(`${'A'.repeat(40)}…`);
        expect(wrapper.find('tbody').text()).toContain('Romans');
        expect(wrapper.find('tbody').text()).toContain('843 SAI');
    });
});
