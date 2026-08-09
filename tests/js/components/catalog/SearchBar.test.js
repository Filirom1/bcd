import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import SearchBar from '../../../../src/bcd_web_vue/js/components/catalog/SearchBar.js';

afterEach(() => vi.useRealTimers());

describe('SearchBar', () => {
    it('emits model and debounced search updates', async () => {
        vi.useFakeTimers();
        const wrapper = mount(SearchBar, { props: { debounce: 100 } });

        await wrapper.vm.$nextTick();
        wrapper.vm.searchQuery = 'prince';
        await wrapper.vm.$nextTick();
        vi.advanceTimersByTime(100);

        expect(wrapper.emitted('update:modelValue')).toEqual([['prince']]);
        expect(wrapper.emitted('search')).toEqual([['prince']]);
    });

    it('submits immediately and clears the query', async () => {
        vi.useFakeTimers();
        const wrapper = mount(SearchBar, { props: { modelValue: 'old', debounce: 500 } });

        wrapper.vm.searchQuery = 'new';
        await wrapper.vm.$nextTick();
        wrapper.vm.handleSubmit();
        wrapper.vm.clearSearch();

        expect(wrapper.emitted('search')).toEqual([['new'], ['']]);
        expect(wrapper.vm.searchQuery).toBe('');
    });
});
