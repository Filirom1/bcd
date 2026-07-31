import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import BulkEditModal from '../../../../src/bcd_web_vue/js/components/borrowers/BulkEditModal.js';

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('BulkEditModal', () => {
    it('starts at step one and reports the selected borrower count', () => {
        const wrapper = mount(BulkEditModal, {
            props: { show: true, selectedBorrowers: [{ id: 1 }, { id: 2 }] }
        });

        expect(wrapper.vm.currentStep).toBe(1);
        expect(wrapper.vm.selectedCount).toBe(2);
        expect(wrapper.vm.canProceedStep1).toBe(false);
    });

    it('requires a target class before proceeding with a class change', () => {
        const wrapper = mount(BulkEditModal, { props: { show: true, selectedBorrowers: [{ id: 1 }] } });

        wrapper.vm.selectOperation(wrapper.vm.OPERATIONS.CHANGE_CLASS);
        expect(wrapper.vm.canProceedStep1).toBe(true);
        expect(wrapper.vm.canProceedStep2).toBe(false);

        wrapper.vm.targetClassId = 8;
        expect(wrapper.vm.canProceedStep2).toBe(true);
    });

    it('emits a change-class execution payload', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
            JSON.stringify([{ id: 8, name: 'CM2' }]),
            { status: 200, headers: { 'Content-Type': 'application/json' } }
        )));
        const wrapper = mount(BulkEditModal, { props: { show: false, selectedBorrowers: [{ id: 1 }, { id: 2 }] } });
        await wrapper.setProps({ show: true });
        await flushPromises();

        wrapper.vm.selectOperation(wrapper.vm.OPERATIONS.CHANGE_CLASS);
        wrapper.vm.targetClassId = 8;
        wrapper.vm.handleExecute();

        expect(wrapper.emitted('execute')).toEqual([[{ operation: 'change_class', targetClassId: 8 }]]);
        expect(wrapper.vm.currentStep).toBe(1);
    });

    it('can execute a delete operation without configuration', () => {
        const wrapper = mount(BulkEditModal, { props: { show: true, selectedBorrowers: [{ id: 1 }] } });

        wrapper.vm.selectOperation(wrapper.vm.OPERATIONS.DELETE);
        expect(wrapper.vm.canProceedStep2).toBe(true);
        wrapper.vm.handleExecute();

        expect(wrapper.emitted('execute')).toEqual([[{ operation: 'delete' }]]);
    });
});
