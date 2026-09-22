import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { nextTick, reactive } from 'vue';
import { shallowMount } from '@vue/test-utils';

import ReportsPage from '../../../../src/bcd_web_vue/js/pages/ReportsPage.js';

const mountedWrappers = [];

beforeEach(() => {
    globalThis.__testRoute.params = reactive({});
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    globalThis.__testRoute.params = {};
});

function mountReportsPage(type) {
    globalThis.__testRoute.params = reactive(type ? { type } : {});
    const wrapper = shallowMount(ReportsPage, {
        global: {
            stubs: {
                OverdueReport: true,
                MostBorrowedReport: true,
                CollectionReport: true,
                HoldsReport: true,
                ActiveLoansReport: true,
                HelpPanel: true
            }
        }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

describe('ReportsPage', () => {
    it('defaults to the overdue report and selects the route-specific report', () => {
        const wrapper = mountReportsPage();
        expect(wrapper.vm.activeTab).toBe('overdue');
        expect(wrapper.find('overdue-report-stub').exists()).toBe(true);
    });

    it('renders the report requested by the route and reacts to later route changes', async () => {
        const wrapper = mountReportsPage('most-borrowed');
        expect(wrapper.vm.activeTab).toBe('most-borrowed');
        expect(wrapper.findComponent({ name: 'MostBorrowedReport' }).exists()).toBe(true);

        globalThis.__testRoute.params.type = 'holds';
        await nextTick();

        expect(wrapper.vm.activeTab).toBe('holds');
        expect(wrapper.findComponent({ name: 'HoldsReport' }).exists()).toBe(true);
    });
});
