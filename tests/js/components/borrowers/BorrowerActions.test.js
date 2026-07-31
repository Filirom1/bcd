import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import { makeBorrower } from '../../fixtures/borrowers.js';
import BorrowerActions from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerActions.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const borrower = makeBorrower({ borrower_id: 'B-201' });

function mountActions(value = borrower) {
    return mount(BorrowerActions, {
        props: { borrower: value },
        global: {
            stubs: { teleport: true }
        }
    });
}

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    useNotification().clear();
});

describe('BorrowerActions', () => {
    it('opens the block modal and requires a blocking reason', async () => {
        const wrapper = mountActions();

        await wrapper.get('button.btn-danger').trigger('click');
        expect(wrapper.vm.showBlockModal).toBe(true);

        await wrapper.get('.modal-footer .btn-danger').trigger('click');

        expect(wrapper.vm.blockReasonError).toBe('borrowers.error_select_reason');
        expect(wrapper.emitted('action-completed')).toBeUndefined();
    });

    it('submits a block request with the selected reason and notes', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
        vi.stubGlobal('fetch', fetchMock);
        const wrapper = mountActions();

        await wrapper.get('button.btn-danger').trigger('click');
        await wrapper.get('select').setValue('Lost Book');
        await wrapper.get('textarea').setValue('Not returned');
        await wrapper.get('.modal-footer .btn-danger').trigger('click');
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith(
            '/api/v1/borrowers/B-201/block?reason=Lost%20Book%20-%20Not%20returned',
            expect.objectContaining({ method: 'POST' })
        );
        expect(wrapper.emitted('action-completed')).toEqual([['block']]);
    });

    it('shows the unblock action for inactive borrowers', async () => {
        const wrapper = mountActions({ ...borrower, active: false });

        expect(wrapper.get('button.btn-success').exists()).toBe(true);
        await wrapper.get('button.btn-success').trigger('click');

        expect(wrapper.vm.showUnblockModal).toBe(true);
    });

    it('summarizes mixed renewal results with success and warning notifications', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
            renewed_count: 1,
            failed_count: 1
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
        vi.stubGlobal('fetch', fetchMock);
        const wrapper = mountActions({ ...borrower, current_loans_count: 2 });

        await wrapper.get('button.btn-primary').trigger('click');
        await flushPromises();

        expect(useNotification().notifications.value).toEqual(expect.arrayContaining([
            expect.objectContaining({
                type: 'warning',
                message: 'circulation.renewed_successfully, circulation.renewal_failed'
            })
        ]));
    });

    it('renews all current loans and emits completion', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
            renewed_count: 2,
            failed_count: 0
        }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
        vi.stubGlobal('fetch', fetchMock);
        const wrapper = mountActions({ ...borrower, current_loans_count: 2 });

        await wrapper.get('button.btn-primary').trigger('click');
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith('/api/v1/circulation/renew', expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ borrower_id: 'B-201', item_ids: null })
        }));
        expect(wrapper.emitted('action-completed')).toEqual([['renew']]);
    });
});
