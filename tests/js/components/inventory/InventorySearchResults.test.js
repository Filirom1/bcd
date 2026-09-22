import { afterEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '@vue/test-utils';

import InventorySearchResults from '../../../../src/bcd_web_vue/js/components/inventory/InventorySearchResults.js';

const mountedWrappers = [];

function makeItem(index, overrides = {}) {
    return {
        item_id: `I-${String(index).padStart(3, '0')}`,
        title: `Titre du livre ${index}`,
        condition: index % 2 ? 'good' : 'damaged',
        period_loan_count: index,
        ...overrides
    };
}

function mountResults(items, selectedIds = new Set(), showPeriodLoanCount = false) {
    const wrapper = mount(InventorySearchResults, {
        props: { items, selectedIds, showPeriodLoanCount }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
});

describe('InventorySearchResults', () => {
    it('renders at most 200 results even if the API returns more', () => {
        const items = Array.from({ length: 205 }, (_, index) => makeItem(index));
        const wrapper = mountResults(items);

        expect(wrapper.vm.MAX_RESULTS).toBe(200);
        expect(wrapper.vm.displayedItems).toHaveLength(200);
        expect(wrapper.findAll('.search-result-item')).toHaveLength(200);
        expect(wrapper.text()).toContain('I-199');
        expect(wrapper.text()).not.toContain('I-200');
    });

    it('computes global and partial selection from displayed results', async () => {
        const items = [makeItem(1), makeItem(2), makeItem(3)];
        const wrapper = mountResults(items, new Set(['I-001']));

        expect(wrapper.vm.allSelected).toBe(false);
        expect(wrapper.vm.someSelected).toBe(true);
        await nextTick();
        expect(wrapper.vm.headerCheckboxRef.indeterminate).toBe(true);

        wrapper.vm.handleHeaderCheckbox();
        wrapper.vm.handleRowCheckbox('I-002');
        expect(wrapper.emitted('toggle-select-all')).toHaveLength(1);
        expect(wrapper.emitted('toggle-selection')).toEqual([['I-002']]);
    });

    it('truncates titles and shows the rotation counter when requested', () => {
        const title = 'Un titre particulièrement long qui doit être tronqué dans la liste';
        const wrapper = mountResults([
            makeItem(1, { title, condition: 'damaged', period_loan_count: 4 })
        ], new Set(['I-001']), true);

        expect(wrapper.vm.truncateTitle(title, 35)).toBe(`${title.substring(0, 35)}…`);
        expect(wrapper.find('.search-result-item').classes()).toContain('selected');
        expect(wrapper.find('.search-result-item').text()).toContain(`${title.substring(0, 35)}…`);
        expect(wrapper.find('.search-result-item').text()).toContain('4 inventory.search.period_loans');
        expect(wrapper.find('.badge').classes()).toContain('bg-warning');
    });

    it('emits selection when clicking either the row or its checkbox', () => {
        const item = makeItem(1);
        const wrapper = mountResults([item]);

        wrapper.find('.search-result-item').trigger('click');
        wrapper.find('.search-result-item input').trigger('click');

        expect(wrapper.emitted('toggle-selection')).toEqual([['I-001'], ['I-001']]);
    });
});
