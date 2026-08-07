import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import RecordDetail from '../../../../src/bcd_web_vue/js/components/catalog/RecordDetail.js';
import { events } from '../../../../src/bcd_web_vue/js/utils/events.js';

const mockRecord = {
    id: 42,
    title: 'Le Petit Prince',
    authors: ['Antoine de Saint-Exupéry'],
    isbn_value: '9782070612758',
    total_items: 2,
    available_copies: 1
};

const mockItems = [
    { id: 1, item_id: 'COPY001', status: 'available', due_date: null },
    { id: 2, item_id: 'COPY002', status: 'on_loan', due_date: '2030-01-15' }
];

function mountDetail(props = {}) {
    return mount(RecordDetail, {
        props: {
            recordId: 42,
            record: mockRecord,
            show: true,
            initialMode: 'view',
            ...props
        },
        global: {
            stubs: {
                teleport: true,
                Modal: true,
                LoadingSpinner: true,
                AutocompleteInput: true,
                Pagination: true,
                ItemEditForm: true,
                RecordDeleteDialog: true,
                BibliographicFields: true
            }
        }
    });
}

beforeEach(() => {
    const fetchMock = vi.fn().mockImplementation(async (url) => {
        if (url.includes('/api/v1/catalog/bibliographic/42/items')) {
            return new Response(JSON.stringify(mockItems), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        if (url.includes('/api/v1/holds/record/')) {
            return new Response(JSON.stringify([]), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        return new Response(JSON.stringify(mockRecord), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        });
    });
    vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('RecordDetail', () => {
    it('loads and displays multiple copies with status', async () => {
        const wrapper = mountDetail();
        await flushPromises();

        expect(wrapper.vm.record).toMatchObject(mockRecord);
        expect(wrapper.vm.items).toHaveLength(2);
        expect(wrapper.vm.items[0].item_id).toBe('COPY001');
        expect(wrapper.vm.items[0].status).toBe('available');
    });

    it('displays due dates for on-loan copies', async () => {
        const wrapper = mountDetail();
        await flushPromises();

        const onLoanCopy = wrapper.vm.items.find(item => item.status === 'on_loan');
        expect(onLoanCopy).toBeDefined();
        expect(onLoanCopy.due_date).toBe('2030-01-15');
    });

    it('populates fields for editing', async () => {
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        expect(wrapper.vm.isEditMode).toBe(true);
        expect(wrapper.vm.formData.title).toBe('Le Petit Prince');
        expect(wrapper.vm.formData.isbn).toBe('9782070612758');
    });

    it('emits catalog:refresh event when an item is deleted', async () => {
        const emitSpy = vi.spyOn(events, 'emit');
        vi.stubGlobal('confirm', () => true); // Mock window.confirm

        const wrapper = mountDetail();
        await flushPromises();

        // Stub fetch specifically for delete
        const fetchMock = vi.fn().mockImplementation(async (url) => {
            return new Response(null, { status: 204 });
        });
        vi.stubGlobal('fetch', fetchMock);

        await wrapper.vm.handleDeleteItem({ item_id: 'COPY001' });

        expect(emitSpy).toHaveBeenCalledWith('catalog:refresh');
    });
});
