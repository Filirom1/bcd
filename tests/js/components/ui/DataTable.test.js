import { describe, expect, it } from 'vitest';
import { h } from 'vue';
import { mount } from '@vue/test-utils';

import DataTable from '../../../../src/bcd_web_vue/js/components/ui/DataTable.js';

const columns = [
    { key: 'name', label: 'Name', width: '200px' },
    { key: 'count', label: 'Count' }
];

function mountTable(props = {}, slots = {}) {
    return mount(DataTable, {
        props: { columns, ...props },
        slots,
        global: { stubs: { LoadingSpinner: true } }
    });
}

describe('DataTable', () => {
    it('renders an empty state and a loading state', () => {
        const empty = mountTable({ emptyMessage: 'Nothing here' });
        expect(empty.find('.alert-info').text()).toContain('Nothing here');

        const loading = mountTable({ loading: true, rows: [{ id: 1, name: 'Hidden' }] });
        expect(loading.find('table').exists()).toBe(false);
        expect(loading.text()).toContain('common.loading');
    });

    it('renders headers, values, nulls, widths, and the default row shape', () => {
        const wrapper = mountTable({ rows: [{ id: 1, name: 'Book', count: null }] });

        expect(wrapper.findAll('th')).toHaveLength(2);
        expect(wrapper.find('th').attributes('style')).toContain('width: 200px');
        expect(wrapper.findAll('td')[0].text()).toBe('Book');
        expect(wrapper.findAll('td')[1].text()).toBe('');
    });

    it('supports row slots, custom row keys, bare mode, and card mode', () => {
        const row = { code: 'A-1', name: 'Book', count: 2 };
        const slot = {
            row: ({ row: value }) => h('td', { 'data-testid': 'custom-cell' }, value.code)
        };
        const bare = mountTable({ rows: [row], rowKey: 'code', bare: true }, slot);
        expect(bare.find('table').classes()).toContain('mb-0');
        expect(bare.get('[data-testid="custom-cell"]').text()).toBe('A-1');

        const card = mountTable({ rows: [row], card: true });
        expect(card.find('.card').exists()).toBe(true);
        expect(card.find('table').exists()).toBe(true);
    });

    it('emits a row click only when rows are clickable', async () => {
        const clickable = mountTable({ rows: [{ id: 7, name: 'Book', count: 1 }], clickable: true });
        await clickable.get('tbody tr').trigger('click');
        expect(clickable.emitted('row-click')).toEqual([[{ id: 7, name: 'Book', count: 1 }]]);
        expect(clickable.get('tbody tr').attributes('style')).toContain('cursor: pointer');

        const plain = mountTable({ rows: [{ id: 7, name: 'Book', count: 1 }] });
        await plain.get('tbody tr').trigger('click');
        expect(plain.emitted('row-click')).toBeUndefined();
    });
});
