import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import ReportFilters from '../../../../src/bcd_web_vue/js/components/reports/ReportFilters.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mountFilters = props => mount(ReportFilters, {
    props: {
        showPeriod: true,
        showLimit: true,
        showClass: true,
        showMediumType: true,
        period: 'month',
        limit: 25,
        classFilter: '',
        mediumTypeFilter: '',
        mediumTypeOptions: ['Book', 'Magazine'],
        ...props
    }
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('ReportFilters', () => {
    it('loads class names and emits every filter update', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue([
            { id: 1, name: 'CP' },
            { id: 2, name: 'CM2' }
        ]);
        const wrapper = mountFilters();
        await flushPromises();

        expect(apiClient.get).toHaveBeenCalledWith('/classes');
        expect(wrapper.vm.classes).toEqual(['CP', 'CM2']);
        expect(wrapper.findAll('select')).toHaveLength(4);

        const selects = wrapper.findAll('select');
        await selects[0].setValue('week');
        await selects[1].setValue('50');
        await selects[2].setValue('CM2');
        await selects[3].setValue('Magazine');

        expect(wrapper.emitted('update:period')).toEqual([['week']]);
        expect(wrapper.emitted('update:limit')).toEqual([[50]]);
        expect(wrapper.emitted('update:classFilter')).toEqual([['CM2']]);
        expect(wrapper.emitted('update:mediumTypeFilter')).toEqual([['Magazine']]);
        expect(wrapper.emitted('filter-change')).toHaveLength(4);
    });

    it('accepts the object-shaped classes response', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue({ classes: ['CE1', 'CE2'] });
        const wrapper = mountFilters();
        await flushPromises();

        expect(wrapper.vm.classes).toEqual(['CE1', 'CE2']);
    });

    it('keeps an empty class list when loading classes fails or returns an invalid shape', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ unexpected: true });
        const wrapper = mountFilters();
        await flushPromises();
        expect(wrapper.vm.classes).toEqual([]);
        wrapper.unmount();

        get.mockRejectedValueOnce(new Error('offline'));
        const failedWrapper = mountFilters();
        await flushPromises();
        expect(failedWrapper.vm.classes).toEqual([]);
    });
});
