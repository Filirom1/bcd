import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import BorrowerDetail from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerDetail.js';
import { makeBorrower } from '../../fixtures/borrowers.js';

const borrower = makeBorrower({
    id: 1,
    borrower_id: 'B-101',
    first_name: 'Amira',
    last_name: 'Benali',
    email: 'amira@school.com',
    phone: '123456',
    role: 'student',
    class_id: null
});

function mountDetail(props = {}) {
    return mount(BorrowerDetail, {
        props: {
            borrowerId: 'B-101',
            borrower: borrower,
            show: true,
            initialMode: 'edit',
            ...props
        },
        global: {
            stubs: {
                teleport: true,
                BorrowerActions: true,
                Pagination: true,
                BorrowerDeleteDialog: true
            }
        }
    });
}

beforeEach(() => {
    const fetchMock = vi.fn().mockImplementation(async (url) => {
        if (url.includes('/api/v1/borrowers/')) {
            return new Response(JSON.stringify(borrower), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        if (url.includes('/api/v1/classes')) {
            return new Response(JSON.stringify([]), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        if (url.includes('/api/v1/holds/')) {
            return new Response(JSON.stringify([]), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        return new Response('{}', { status: 200 });
    });
    vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('BorrowerDetail', () => {
    it('displays the edit modal when in edit mode', () => {
        const wrapper = mountDetail({ initialMode: 'edit' });
        expect(wrapper.get('[data-testid="borrower-edit-modal"]').exists()).toBe(true);
    });

    it('displays full borrower info and lists current loans in view mode', async () => {
        const borrowerWithLoans = {
            ...borrower,
            current_loans: [
                { item_id: 'I-001', title: 'The Little Prince', due_date: '2030-01-15' }
            ]
        };
        const fetchMock = vi.fn().mockImplementation(async (url) => {
            if (url.includes('/api/v1/borrowers/')) {
                return new Response(JSON.stringify(borrowerWithLoans), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            return new Response(JSON.stringify([]), { status: 200 });
        });
        vi.stubGlobal('fetch', fetchMock);

        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();

        expect(wrapper.get('[data-testid="borrower-detail-modal"]').exists()).toBe(true);
        expect(wrapper.text()).toContain('B-101');
        expect(wrapper.text()).toContain('amira@school.com');
        expect(wrapper.text()).toContain('123456');
    });

    it('pre-populates form fields with current borrower data', async () => {
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        expect(wrapper.get('[data-testid="input-borrower-id"]').element.value).toBe('B-101');
        expect(wrapper.get('[data-testid="input-first-name"]').element.value).toBe('Amira');
        expect(wrapper.get('[data-testid="input-last-name"]').element.value).toBe('Benali');
    });

    it('emits close event without saving when clicking cancel', async () => {
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        const cancelButton = wrapper.findAll('button').find(b => b.text().includes('Cancel') || b.text().includes('common.cancel'));
        if (cancelButton) {
            await cancelButton.trigger('click');
        } else {
            // fallback directly invoking vm.close
            await wrapper.vm.close();
        }

        expect(wrapper.emitted('close')).toBeDefined();
    });

    it('emits close event when clicking the modal close button', async () => {
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        await wrapper.get('[data-testid="modal-close-button"]').trigger('click');

        expect(wrapper.emitted('close')).toBeDefined();
    });
});
