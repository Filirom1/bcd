import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, reactive } from 'vue';
import { shallowMount } from '@vue/test-utils';

import App from '../../../src/bcd_web_vue/js/components/App.js';
import { apiClient } from '../../../src/bcd_web_vue/js/api/client.js';
import { useGlobalModal } from '../../../src/bcd_web_vue/js/composables/useGlobalModal.js';
import { useNotification } from '../../../src/bcd_web_vue/js/composables/useNotification.js';
import { events } from '../../../src/bcd_web_vue/js/utils/events.js';

const mountedWrappers = [];

function mountApp() {
    const wrapper = shallowMount(App, {
        global: {
            stubs: {
                SidebarNav: true,
                NotificationContainer: true,
                RecordDetail: true,
                BorrowerDetail: true,
                'router-view': true
            }
        }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

beforeEach(() => {
    globalThis.__testRoute.meta = reactive({});
    useGlobalModal().closeRecord();
    useGlobalModal().closeBorrower();
    useNotification().clear();
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    globalThis.__testRoute.meta = {};
    useGlobalModal().closeRecord();
    useGlobalModal().closeBorrower();
    useNotification().clear();
});

describe('App', () => {
    it('marks the shell ready and hides the sidebar for print layouts', async () => {
        const wrapper = mountApp();
        await nextTick();

        expect(wrapper.vm.appReady).toBe(true);
        expect(wrapper.vm.isPrintLayout).toBe(false);

        globalThis.__testRoute.meta.layout = 'print';
        await nextTick();
        expect(wrapper.vm.isPrintLayout).toBe(true);
    });

    it('returns an item from the global record modal and refreshes the record', async () => {
        const { openRecord, globalRecordId } = useGlobalModal();
        openRecord(42);
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            items: [{
                item_id: 'I-101',
                title: 'Le Petit Prince',
                shelf_location: 'Romans',
                call_number: 'R SAI',
                hold_ready: null
            }]
        });
        const emit = vi.spyOn(events, 'emit');
        const wrapper = mountApp();

        await wrapper.vm.handleGlobalQuickReturn('I-101');
        await nextTick();

        expect(post).toHaveBeenCalledWith('/circulation/return', {
            item_ids: ['I-101'],
            returned_by: 'web-ui'
        });
        expect(emit).toHaveBeenCalledWith('catalog:refresh');
        expect(globalRecordId.value).toBe(42);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success' })
        ]);
    });

    it('cross-navigates between global record and borrower modals', () => {
        const wrapper = mountApp();
        const modal = useGlobalModal();
        modal.openRecord(7);

        wrapper.vm.handleGlobalViewBorrower('B-204');
        expect(modal.globalRecordId.value).toBe(null);
        expect(modal.globalBorrowerId.value).toBe('B-204');

        wrapper.vm.handleGlobalViewItem(12);
        expect(modal.globalBorrowerId.value).toBe(null);
        expect(modal.globalRecordId.value).toBe(12);
    });

    it('shows a useful notification when a global quick return fails', async () => {
        vi.spyOn(apiClient, 'post').mockRejectedValue(new Error('Return failed'));
        const wrapper = mountApp();

        await wrapper.vm.handleGlobalQuickReturn('I-404');

        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'Return failed' })
        ]);
    });
});
