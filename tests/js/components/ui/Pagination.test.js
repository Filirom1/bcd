import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import Pagination from '../../../../src/bcd_web_vue/js/components/ui/Pagination.js';

describe('Pagination', () => {
    it('calculates displayed item bounds and navigation state', () => {
        const wrapper = mount(Pagination, {
            props: { currentPage: 2, totalPages: 3, pageSize: 10, totalItems: 25 }
        });

        expect(wrapper.vm.firstItem).toBe(11);
        expect(wrapper.vm.lastItem).toBe(20);
        expect(wrapper.vm.hasPrevious).toBe(true);
        expect(wrapper.vm.hasNext).toBe(true);
    });

    it('emits only valid page and page-size changes', () => {
        const wrapper = mount(Pagination, {
            props: { currentPage: 2, totalPages: 3, pageSize: 10, totalItems: 25 }
        });

        wrapper.vm.goToPage(2);
        wrapper.vm.goToPage(3);
        wrapper.vm.goToPage(0);
        wrapper.vm.changePageSize({ target: { value: '25' } });

        expect(wrapper.emitted('page-change')).toEqual([[3]]);
        expect(wrapper.emitted('page-size-change')).toEqual([[25]]);
    });
});
