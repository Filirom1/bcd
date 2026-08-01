import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import BorrowerAddForm from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerAddForm.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';

function mountAddForm(props = {}) {
    return mount(BorrowerAddForm, {
        props: {
            show: true,
            ...props
        },
        global: {
            mocks: { $t: key => key },
            stubs: {
                teleport: true,
                BorrowerFields: true
            }
        }
    });
}

beforeEach(() => {
    const fetchMock = vi.fn().mockImplementation(async (url) => {
        if (url.includes('/api/v1/classes')) {
            return new Response(JSON.stringify([{ id: 8, name: 'CM2' }]), { status: 200 });
        }
        if (url.includes('/api/v1/borrowers/next-available-id')) {
            return new Response(JSON.stringify({ next_id: 'B-105' }), { status: 200 });
        }
        return new Response(JSON.stringify({ id: 10, borrower_id: 'B-105' }), { status: 201 });
    });
    vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('BorrowerAddForm', () => {
    it('initializes and pre-fills next available ID when shown', async () => {
        const wrapper = mountAddForm({ show: false });
        await flushPromises();

        expect(wrapper.vm.formData.borrower_id).toBe('');

        // Switch show to true to trigger load next available ID
        await wrapper.setProps({ show: true });
        await flushPromises();

        expect(wrapper.vm.formData.borrower_id).toBe('B-105');
        expect(wrapper.vm.classes).toEqual([{ id: 8, name: 'CM2' }]);
    });

    it('triggers client-side required field validations', async () => {
        const wrapper = mountAddForm({ show: true });
        await flushPromises();

        wrapper.vm.formData.first_name = '';
        wrapper.vm.formData.last_name = '';

        await wrapper.vm.handleSubmit();

        expect(wrapper.vm.errors.first_name).toBe('admin.borrower.validation.first_name_required');
        expect(wrapper.vm.errors.last_name).toBe('admin.borrower.validation.last_name_required');
        expect(wrapper.emitted('created')).toBeUndefined();
    });

    it('submits a POST request on successful submit and emits created', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 10, borrower_id: 'B-105' }), { status: 201 }));
        vi.stubGlobal('fetch', fetchMock);

        const wrapper = mountAddForm({ show: true });
        await flushPromises();

        wrapper.vm.formData.borrower_id = 'B-105';
        wrapper.vm.formData.first_name = 'Lucas';
        wrapper.vm.formData.last_name = 'Martin';

        await wrapper.vm.handleSubmit();
        await flushPromises();

        expect(fetchMock).toHaveBeenLastCalledWith(
            expect.stringContaining('/api/v1/borrowers'),
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    borrower_id: 'B-105',
                    first_name: 'Lucas',
                    last_name: 'Martin',
                    role: 'student',
                    class_id: null,
                    email: '',
                    phone: '',
                    notes: ''
                })
            })
        );
        expect(wrapper.emitted('created')).toEqual([[{ id: 10, borrower_id: 'B-105' }]]);
    });
});
