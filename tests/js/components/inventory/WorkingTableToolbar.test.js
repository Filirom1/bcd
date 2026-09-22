import { describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import WorkingTableToolbar from '../../../../src/bcd_web_vue/js/components/inventory/WorkingTableToolbar.js';

const ColumnSelectorStub = {
    name: 'InventoryColumnSelector',
    props: ['visibleColumns'],
    template: '<div class="column-selector-stub" />'
};

function mountToolbar(props = {}) {
    return mount(WorkingTableToolbar, {
        props: { selectedCount: 0, totalCount: 10, visibleColumns: ['item_id', 'title'], ...props },
        global: {
            stubs: { InventoryColumnSelector: ColumnSelectorStub },
            mocks: { $t: key => key }
        }
    });
}

describe('WorkingTableToolbar', () => {
    it('renders a zero-selection counter and disables clear', () => {
        const wrapper = mountToolbar();
        expect(wrapper.text()).toContain('0/10');
        const clear = wrapper.find('button.btn-outline-danger');
        expect(clear.element.disabled).toBe(true);
    });

    it('enables clear for a selection and emits toolbar actions', async () => {
        const wrapper = mountToolbar({ selectedCount: 3, totalCount: 10 });
        const clear = wrapper.find('button.btn-outline-danger');
        expect(clear.element.disabled).toBe(false);
        await clear.trigger('click');
        expect(wrapper.emitted('clear')).toHaveLength(1);

        wrapper.vm.handleToggleColumn('condition');
        wrapper.vm.handleResetColumns();
        expect(wrapper.emitted('toggle-column')).toEqual([['condition']]);
        expect(wrapper.emitted('reset-columns')).toHaveLength(1);
    });

    it('passes visibleColumns to the column selector', () => {
        const columns = ['item_id', 'condition'];
        const wrapper = mountToolbar({ visibleColumns: columns });
        expect(wrapper.findComponent(ColumnSelectorStub).props('visibleColumns')).toEqual(columns);
    });
});
