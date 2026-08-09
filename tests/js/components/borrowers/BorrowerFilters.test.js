import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import BorrowerFilters from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerFilters.js';

const classesResponse = () => new Response(JSON.stringify([{ id: 3, name: 'CM1' }]), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('BorrowerFilters', () => {
    it('emits API filters for search, class, role, and status', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(classesResponse()));
        const wrapper = mount(BorrowerFilters);
        await wrapper.vm.$nextTick();

        wrapper.vm.searchQuery = 'Amira';
        wrapper.vm.classFilter = 3;
        wrapper.vm.roleFilter = 'student';
        wrapper.vm.statusFilter = 'overdue';
        wrapper.vm.applyFilters();

        expect(wrapper.emitted('filter-change').at(-1)).toEqual([{
            q: 'Amira', class_id: 3, role: 'student', has_overdue: true
        }]);
        expect(wrapper.vm.hasActiveFilters).toBe(true);
    });

    it('resets all filters and emits an empty filter set', () => {
        const wrapper = mount(BorrowerFilters);
        wrapper.vm.searchQuery = 'Amira';
        wrapper.vm.roleFilter = 'teacher';

        wrapper.vm.resetFilters();

        expect(wrapper.vm.searchQuery).toBe('');
        expect(wrapper.vm.roleFilter).toBe('');
        expect(wrapper.emitted('filter-change').at(-1)).toEqual([{}]);
        expect(wrapper.vm.hasActiveFilters).toBe(false);
    });
});
