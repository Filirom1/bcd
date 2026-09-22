import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import RecordDetail from '../../../../src/bcd_web_vue/js/components/catalog/RecordDetail.js';
import RecordDeleteDialog from '../../../../src/bcd_web_vue/js/components/catalog/RecordDeleteDialog.js';
import ItemEditForm from '../../../../src/bcd_web_vue/js/components/catalog/ItemEditForm.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { events } from '../../../../src/bcd_web_vue/js/utils/events.js';

const mockRecord = {
    id: 42,
    title: 'Le Petit Prince',
    authors: ['Antoine de Saint-Exupéry'],
    illustrators: [],
    keywords: [],
    isbn_value: '9782070612758',
    total_items: 2,
    available_copies: 1
};

const mockItems = [
    { id: 1, item_id: 'COPY001', status: 'available', due_date: null },
    { id: 2, item_id: 'COPY002', status: 'on_loan', due_date: '2030-01-15' }
];

function mountDetail(props = {}, options = {}) {
    const stubs = {
        teleport: true,
        Modal: {
            props: ['show'],
            template: '<div v-if="show" class="test-modal"><slot name="header" /><slot /><slot name="footer" /></div>'
        },
        LoadingSpinner: true,
        AutocompleteInput: true,
        Pagination: true,
        RecordDeleteDialog: true,
        BibliographicFields: true
    };
    if (!options.realItemEditForm) stubs.ItemEditForm = true;
    if (options.realPagination) delete stubs.Pagination;

    return mount(RecordDetail, {
        props: {
            recordId: 42,
            record: mockRecord,
            show: true,
            initialMode: 'view',
            ...props
        },
        global: { stubs }
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
            if (url.includes('/catalog/bibliographic/42/items')) {
                return new Response(JSON.stringify(mockItems), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
            if (url.includes('/catalog/items/COPY001')) {
                return new Response(null, { status: 204 });
            }
            return new Response(JSON.stringify([]), { status: 200 });
        });
        vi.stubGlobal('fetch', fetchMock);

        await wrapper.vm.handleDeleteItem({ item_id: 'COPY001' });

        expect(emitSpy).toHaveBeenCalledWith('catalog:refresh');
    });

    it('shows the empty-copy state when the record has no physical items', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
            if (endpoint.endsWith('/items')) return [];
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });

        const wrapper = mountDetail();
        await flushPromises();

        expect(getSpy).toHaveBeenCalledWith('/catalog/bibliographic/42');
        expect(wrapper.vm.items).toEqual([]);
        expect(wrapper.text()).toContain('catalog.no_items');
    });

    it('keeps the modal in a safe empty state when loading the record fails', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('record unavailable'));

        const wrapper = mountDetail({ record: null });
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.record).toBeNull();
        expect(wrapper.vm.items).toEqual([]);
        expect(wrapper.text()).toContain('Failed to load record details');
    });

    it('maps available, loaned, lost, and withdrawn copies to their status badges', async () => {
        const statuses = [
            { item_id: 'AVAILABLE', status: 'available' },
            { item_id: 'LOANED', status: 'on_loan', current_loan: { borrower_id: 'B-1', borrower_name: 'A Student' } },
            { item_id: 'LOST', status: 'lost' },
            { item_id: 'WITHDRAWN', status: 'withdrawn' }
        ];
        vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
            if (endpoint.endsWith('/items')) return statuses;
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });

        const wrapper = mountDetail();
        await flushPromises();

        expect(wrapper.vm.items).toHaveLength(4);
        expect(wrapper.vm.getStatusBadge(statuses[0]).class).toBe('bg-success');
        expect(wrapper.vm.getStatusBadge(statuses[1]).class).toBe('bg-warning');
        expect(wrapper.vm.getStatusBadge(statuses[2]).class).toBe('bg-danger');
        expect(wrapper.vm.getStatusBadge(statuses[3]).class).toBe('bg-dark');
        expect(wrapper.text()).toContain('LOANED');
    });

    it('uses the fallback icon when a cover is missing or cannot be loaded', async () => {
        const recordWithCover = { ...mockRecord, cover_image: 'cover.jpg' };
        vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
            if (endpoint.endsWith('/items')) return [];
            if (endpoint.startsWith('/holds/')) return [];
            return recordWithCover;
        });

        const wrapper = mountDetail({ record: recordWithCover });
        await flushPromises();

        const image = wrapper.find('img');
        expect(image.exists()).toBe(true);
        await image.trigger('error');
        expect(wrapper.vm.coverLoadFailed).toBe(true);
        expect(wrapper.find('img').exists()).toBe(false);
        expect(wrapper.find('.bi-book.display-4').exists()).toBe(true);
    });

    it('navigates to add a copy and emits borrower navigation events', async () => {
        const push = vi.fn().mockResolvedValue(undefined);
        globalThis.__testRouter.push = push;
        const wrapper = mountDetail();
        await flushPromises();

        wrapper.vm.addItem();
        wrapper.vm.viewBorrower('B-101');
        await flushPromises();

        expect(push).toHaveBeenCalledWith({
            name: 'cataloging',
            query: { record_id: '42' }
        });
        expect(wrapper.emitted('view-borrower')).toEqual([['B-101']]);
    });

    it('opens, updates, and closes the item editor after an item is saved', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
            if (endpoint.endsWith('/items')) return mockItems;
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        wrapper.vm.handleEditItem(mockItems[0]);
        expect(wrapper.vm.editingItem).toEqual(mockItems[0]);
        expect(wrapper.vm.showItemEditModal).toBe(true);

        wrapper.vm.handleItemSaved({ ...mockItems[0], condition: 'damaged' });
        await flushPromises();

        expect(wrapper.vm.showItemEditModal).toBe(false);
        expect(wrapper.vm.editingItem).toBeNull();
        expect(getSpy).toHaveBeenCalledWith('/catalog/bibliographic/42/items');
    });

    it('patches the inline bibliographic edit and returns to view mode', async () => {
        const updated = { ...mockRecord, title: 'Updated title' };
        const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValue(updated);
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        wrapper.vm.isEditMode = true;

        wrapper.vm.formData.title = 'Updated title';
        wrapper.vm.formData.publication_year = 0;
        wrapper.vm.formData.page_count = 0;
        await wrapper.vm.handleSubmit();

        expect(patchSpy).toHaveBeenCalledWith('/catalog/records/42', expect.objectContaining({
            title: 'Updated title',
            publication_year: null,
            page_count: null
        }));
        expect(wrapper.vm.record).toEqual(updated);
        expect(wrapper.vm.isEditMode).toBe(false);
        expect(wrapper.emitted('saved')).toEqual([[updated]]);
    });

    it('exposes a validation error when saving the bibliographic edit fails', async () => {
        vi.spyOn(apiClient, 'patch').mockRejectedValue({ statusCode: 400, message: 'Invalid title' });
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        await wrapper.vm.handleSubmit();

        expect(wrapper.vm.errors.general).toBe('Invalid title');
        expect(wrapper.vm.isEditMode).toBe(true);
        expect(wrapper.vm.isSubmitting).toBe(false);
    });

    it('does not delete an item when confirmation is cancelled and handles a server refusal', async () => {
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockRejectedValue({ statusCode: 400, message: 'Item is on loan' });
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.stubGlobal('confirm', vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true));
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        await wrapper.vm.handleDeleteItem({ item_id: 'LOANED', status: 'on_loan' });
        expect(deleteSpy).not.toHaveBeenCalled();

        await wrapper.vm.handleDeleteItem({ item_id: 'LOANED', status: 'on_loan' });
        expect(deleteSpy).toHaveBeenCalledWith('/catalog/items/LOANED');
        expect(errorSpy).toHaveBeenCalled();
    });

    it('deletes a record after confirmation and emits the deleted identifier', async () => {
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        wrapper.vm.handleDeleteClick();
        expect(wrapper.vm.showDeleteDialog).toBe(true);
        await wrapper.vm.handleDeleteConfirm(42);

        expect(deleteSpy).toHaveBeenCalledWith('/catalog/records/42');
        expect(wrapper.vm.showDeleteDialog).toBe(false);
        expect(wrapper.emitted('deleted')).toEqual([[42]]);
        expect(wrapper.emitted('close')).toBeTruthy();
    });

    it('sorts periodical issues numerically and accepts object-wrapped item responses', async () => {
        const issues = [
            { id: 1, item_id: 'I-1', call_number: '2' },
            { id: 2, item_id: 'I-2', call_number: '10' },
            { id: 3, item_id: 'I-3', call_number: 'Special' }
        ];
        vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return { items: issues };
            if (endpoint.startsWith('/holds/')) throw new Error('optional endpoint unavailable');
            return { ...mockRecord, identifier_type: 'issn' };
        });
        const wrapper = mountDetail({ record: { ...mockRecord, identifier_type: 'issn' } });
        await flushPromises();

        expect(wrapper.vm.items.map(item => item.call_number)).toEqual(['10', '2', 'Special']);
    });

    it('handles item and hold loading failures without losing the record', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) throw new Error('items unavailable');
            if (endpoint.startsWith('/holds/')) throw new Error('holds unavailable');
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();

        expect(wrapper.vm.record).toEqual(mockRecord);
        expect(wrapper.vm.items).toEqual([]);
        expect(wrapper.vm.holds).toEqual([]);
        expect(consoleSpy).toHaveBeenCalledWith('Error loading record items:', expect.any(Error));
    });

    it('fetches borrowers, formats warning badges, and creates a hold', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/borrowers') return { data: [{ id: 7, borrower_id: 'B-7' }] };
            if (endpoint.startsWith('/holds/')) return [{ id: 1 }];
            if (endpoint.endsWith('/items')) return [];
            return mockRecord;
        });
        const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue({});
        const wrapper = mountDetail();
        await flushPromises();

        const signal = new AbortController().signal;
        await expect(wrapper.vm.fetchBorrowers('Amira', signal)).resolves.toEqual([{ id: 7, borrower_id: 'B-7' }]);
        const html = wrapper.vm.formatBorrowerResult({
            borrower_id: 'B-7', first_name: 'A', last_name: 'B', blocked: true, has_overdue: true, class_name: 'CM2'
        });
        expect(html).toContain('circulation.status_blocked');
        expect(html).toContain('circulation.overdue');

        await wrapper.vm.createHold({ id: 7, first_name: 'A', last_name: 'B' });
        expect(postSpy).toHaveBeenCalledWith('/holds', {
            borrower_id: 7, bibliographic_record_id: 42, created_by: 'web-ui'
        });
        expect(wrapper.vm.reserveMessage.type).toBe('success');
        expect(wrapper.vm.reserveBorrowerQuery).toBe('');
        expect(getSpy).toHaveBeenCalledWith('/holds/bibliographic/42');
    });

    it('reports hold limit and generic hold errors and ignores an empty borrower', async () => {
        const postSpy = vi.spyOn(apiClient, 'post');
        const wrapper = mountDetail();
        await flushPromises();

        await wrapper.vm.createHold(null);
        expect(postSpy).not.toHaveBeenCalled();

        postSpy.mockRejectedValueOnce({ code: 'hold_limit_exceeded', details: { limit: 1 } });
        await wrapper.vm.createHold({ id: 7, first_name: 'A', last_name: 'B' });
        expect(wrapper.vm.reserveMessage.text).toContain('holds.hold_limit_exceeded');

        postSpy.mockRejectedValueOnce({ message: 'Hold failed' });
        await wrapper.vm.createHold({ id: 7, first_name: 'A', last_name: 'B' });
        expect(wrapper.vm.reserveMessage).toEqual({ type: 'danger', text: 'Hold failed' });
        expect(wrapper.vm.reserveLoading).toBe(false);
    });

    it('loads item history with filters, pagination, current loan, and error fallback', async () => {
        const history = [{ borrower_id: 'B-1', borrower_name: 'A Student', checkout_date: '2024-01-01', status: 'returned_late' }];
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint, params) => {
            if (endpoint.includes('/history')) return {
                history, pagination: { page: params.page, total_pages: 2, page_size: params.page_size, total_items: 21 },
                current_loan: { borrower_name: 'Current Student', due_date: '2025-01-01' }
            };
            if (endpoint.endsWith('/items')) return mockItems;
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();

        expect(wrapper.vm.itemHistoryItems).toEqual(history);
        expect(wrapper.vm.itemCurrentLoan.borrower_name).toBe('Current Student');
        wrapper.vm.itemHistoryDateFrom = '2024-01-01';
        wrapper.vm.itemHistoryDateTo = '2024-12-31';
        wrapper.vm.applyItemHistoryFilter();
        await flushPromises();
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/item/COPY001/history', {
            page: 1, page_size: 20, date_from: '2024-01-01', date_to: '2024-12-31'
        });
        wrapper.vm.onItemHistoryPageChange(2);
        await flushPromises();
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/item/COPY001/history', expect.objectContaining({ page: 2 }));

        getSpy.mockRejectedValueOnce(new Error('history unavailable'));
        wrapper.vm.clearItemHistoryFilter();
        await flushPromises();
        expect(wrapper.vm.itemHistoryItems).toEqual([]);
        expect(wrapper.vm.itemHistoryLoading).toBe(false);
    });

    it('validates record fields, resets cancelled edits, and maps unknown statuses', async () => {
        const patchSpy = vi.spyOn(apiClient, 'patch');
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        wrapper.vm.isEditMode = true;
        wrapper.vm.formData.title = '';
        wrapper.vm.formData.publication_year = 999;
        wrapper.vm.formData.page_count = -1;
        await wrapper.vm.handleSubmit();

        expect(patchSpy).not.toHaveBeenCalled();
        expect(wrapper.vm.errors).toEqual(expect.objectContaining({
            title: 'errors.required_field',
            publication_year: 'errors.invalid_year_range',
            page_count: 'errors.must_be_positive'
        }));
        expect(wrapper.vm.getStatusBadge({ status: 'unknown' }).class).toBe('bg-secondary');
        expect(wrapper.vm.getConditionLabel('damaged')).toBe('item.condition_damaged');
        expect(wrapper.vm.getConditionLabel('unknown')).toBe('unknown');
        expect(wrapper.vm.getStatusLabel('withdrawn')).toBe('item.status_withdrawn');
        expect(wrapper.vm.getStatusLabel('unknown')).toBe('unknown');

        wrapper.vm.formData.title = 'Changed';
        wrapper.vm.handleCancelEdit();
        expect(wrapper.vm.formData.title).toBe(mockRecord.title);
    });

    it('maps record deletion failures to a network error and closes the dialog', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.spyOn(apiClient, 'delete').mockRejectedValue(new Error('offline'));
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        wrapper.vm.showDeleteDialog = true;
        await wrapper.vm.handleDeleteConfirm(42);
        expect(wrapper.vm.errors.general).toBe('errors.network_error');
        expect(wrapper.vm.showDeleteDialog).toBe(false);
        expect(consoleSpy).toHaveBeenCalledWith('Error deleting record:', expect.any(Error));
    });

    it('maps every item status, including holds, repairs, overdue and unknown values', () => {
        const wrapper = mountDetail();
        expect(wrapper.vm.getStatusBadge({ status: 'on_hold' }).class).toBe('bg-info');
        expect(wrapper.vm.getStatusBadge({ status: 'in_repair' }).class).toBe('bg-primary');
        expect(wrapper.vm.getStatusBadge({ status: 'overdue' }).class).toBe('bg-danger');
        expect(wrapper.vm.getStatusBadge({ status: 'mystery' }).class).toBe('bg-secondary');
        expect(wrapper.vm.getStatusLabel('on_hold')).toBe('item.status_on_hold');
        expect(wrapper.vm.getStatusLabel('in_repair')).toBe('item.status_in_repair');
        expect(wrapper.vm.getStatusLabel('mystery')).toBe('mystery');
    });

    it('keeps a loaded record when the item response is empty or malformed', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return { items: 'not-an-array' };
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();
        expect(getSpy).toHaveBeenCalledWith('/catalog/bibliographic/42/items');
        expect(wrapper.vm.record).toEqual(mockRecord);
        expect(wrapper.vm.items).toEqual([]);
    });

    it('keeps existing holds when reloading reservations fails after creation', async () => {
        let holdLoads = 0;
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.startsWith('/holds/')) {
                holdLoads += 1;
                if (holdLoads > 1) throw new Error('holds reload failed');
                return [{ id: 1, borrower_string_id: 'B-1' }];
            }
            if (endpoint.endsWith('/items')) return [];
            return mockRecord;
        });
        vi.spyOn(apiClient, 'post').mockResolvedValue({});
        const wrapper = mountDetail();
        await flushPromises();
        await wrapper.vm.createHold({ id: 9, first_name: 'A', last_name: 'B' });
        expect(wrapper.vm.reserveMessage.type).toBe('success');
        expect(wrapper.vm.holds).toEqual([{ id: 1, borrower_string_id: 'B-1' }]);
        expect(getSpy).toHaveBeenCalledWith('/holds/bibliographic/42');
    });

    it('handles a reservation creation failure without attempting a reload', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint.endsWith('/items')) return [];
            return mockRecord;
        });
        vi.spyOn(apiClient, 'post').mockRejectedValue({ code: 'hold_limit_exceeded', details: { limit: 2 } });
        const wrapper = mountDetail();
        await flushPromises();
        const holdCallsBefore = getSpy.mock.calls.filter(([url]) => url === '/holds/bibliographic/42').length;
        await wrapper.vm.createHold({ id: 9, first_name: 'A', last_name: 'B' });
        expect(wrapper.vm.reserveMessage).toEqual(expect.objectContaining({ type: 'danger' }));
        expect(getSpy.mock.calls.filter(([url]) => url === '/holds/bibliographic/42')).toHaveLength(holdCallsBefore);
    });

    it('handles an empty-item history request without making an API call', async () => {
        const historySpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return [];
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });
        const wrapper = mountDetail({ record: mockRecord });
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();
        expect(wrapper.vm.itemHistoryItems).toEqual([]);
        expect(historySpy.mock.calls.some(([url]) => url.includes('/history'))).toBe(false);
    });

    it('handles generic save errors and closes immediately from initial edit mode', async () => {
        vi.spyOn(apiClient, 'patch').mockRejectedValue(new Error('save offline'));
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('save offline');
        expect(wrapper.vm.isEditMode).toBe(true);
        wrapper.vm.handleCancelEdit();
        expect(wrapper.emitted('close')).toHaveLength(1);
        expect(wrapper.emitted('update:show')).toContainEqual([false]);
    });

    it('rejects a record deletion refused by the server', async () => {
        vi.spyOn(apiClient, 'delete').mockRejectedValue({ statusCode: 400, message: 'Record still in use' });
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();
        await wrapper.vm.handleDeleteConfirm(42);
        expect(wrapper.vm.errors.general).toBe('errors.network_error');
        expect(wrapper.vm.showDeleteDialog).toBe(false);
        expect(wrapper.emitted('deleted')).toBeUndefined();
    });

    it('reloads holds after saving an item and keeps the modal usable when that reload fails', async () => {
        let holdLoads = 0;
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return mockItems;
            if (endpoint.startsWith('/holds/')) {
                holdLoads += 1;
                if (holdLoads > 1) throw new Error('holds unavailable after save');
                return [{ id: 1 }];
            }
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();
        wrapper.vm.activeTab = 'holds';
        await wrapper.vm.$nextTick();
        wrapper.vm.handleItemSaved({ ...mockItems[0], condition: 'damaged' });
        await flushPromises();

        expect(wrapper.vm.showItemEditModal).toBe(false);
        expect(wrapper.vm.editingItem).toBe(null);
        expect(wrapper.vm.items).toEqual(mockItems);
        expect(getSpy.mock.calls.filter(([url]) => url === '/holds/bibliographic/42')).toHaveLength(2);
    });

    it('reloads item history after saving in the history tab and handles a history error', async () => {
        let historyLoads = 0;
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
            if (endpoint.endsWith('/items')) return mockItems;
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint.includes('/history')) {
                historyLoads += 1;
                if (historyLoads > 1) throw new Error('history unavailable after save');
                return {
                    history: [{ item_id: 'COPY001', title: 'Old loan' }],
                    pagination: { page: 1, total_pages: 2, total_items: 21 },
                    current_loan: null
                };
            }
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();
        expect(wrapper.vm.itemHistoryPagination.total_pages).toBe(2);
        wrapper.vm.handleItemSaved(mockItems[0]);
        await flushPromises();

        expect(wrapper.vm.itemHistoryItems).toEqual([]);
        expect(wrapper.vm.itemHistoryPagination).toBe(null);
        expect(getSpy.mock.calls.some(([url]) => url.includes('/history'))).toBe(true);
    });

    it('rejects null, malformed and normalization-error borrower responses', async () => {
        const responses = [null, { unexpected: true }];
        for (const response of responses) {
            const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(response);
            const wrapper = mountDetail();
            await flushPromises();
            await expect(wrapper.vm.fetchBorrowers('Am', new AbortController().signal)).rejects.toThrow();
            getSpy.mockRestore();
        }
    });

    it('keeps copies and emits refresh when deleting an item but reloading copies fails', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return mockItems;
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const emitSpy = vi.spyOn(events, 'emit');
        vi.stubGlobal('confirm', () => true);
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();
        getSpy.mockRejectedValueOnce(new Error('items unavailable after delete'));

        await expect(wrapper.vm.handleDeleteItem({ item_id: 'COPY001' })).resolves.toBeUndefined();
        await flushPromises();

        expect(deleteSpy).toHaveBeenCalledWith('/catalog/items/COPY001');
        expect(wrapper.vm.items).toEqual(mockItems);
        expect(emitSpy).toHaveBeenCalledWith('catalog:refresh');
    });

    it('maps a generic item deletion error without changing the current copies', async () => {
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockRejectedValue(new Error('delete offline'));
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.stubGlobal('confirm', () => true);
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        await wrapper.vm.handleDeleteItem({ item_id: 'COPY001' });
        expect(deleteSpy).toHaveBeenCalledWith('/catalog/items/COPY001');
        expect(wrapper.vm.items).toEqual(mockItems);
        expect(errorSpy).toHaveBeenCalledWith('Error deleting item:', expect.any(Error));
    });

    it('handles an empty current loan and a date filter with no history', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint, params) => {
            if (endpoint.endsWith('/items')) return [mockItems[0]];
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint.includes('/history')) {
                return {
                    history: [],
                    pagination: { page: params.page, total_pages: 1, total_items: 0 },
                    current_loan: null
                };
            }
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();
        wrapper.vm.itemHistoryDateFrom = '2024-01-01';
        wrapper.vm.itemHistoryDateTo = '2024-12-31';
        wrapper.vm.applyItemHistoryFilter();
        await flushPromises();

        expect(wrapper.vm.itemHistoryItems).toEqual([]);
        expect(wrapper.vm.itemCurrentLoan).toBe(null);
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/item/COPY001/history', {
            page: 1, page_size: 20, date_from: '2024-01-01', date_to: '2024-12-31'
        });
    });

    it('navigates to borrowers from a loan, a hold and a history entry', async () => {
        const loanItems = [{ item_id: 'COPY001', status: 'on_loan', current_loan: { borrower_id: 'LOAN-B' } }];
        const holds = [{ id: 1, borrower_string_id: 'HOLD-B', borrower_name: 'Holder', status: 'ready', queue_position: 1 }];
        vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return loanItems;
            if (endpoint.startsWith('/holds/')) return holds;
            if (endpoint.includes('/history')) return { history: [{ borrower_id: 'HIST-B', borrower_name: 'Historian', checkout_date: '2024-01-01' }] };
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();
        await wrapper.find('.link-entity').trigger('click');
        wrapper.vm.activeTab = 'holds';
        await wrapper.vm.$nextTick();
        await wrapper.find('.link-entity').trigger('click');
        wrapper.vm.activeTab = 'history';
        await flushPromises();
        await wrapper.find('.link-entity').trigger('click');
        expect(wrapper.emitted('view-borrower')).toEqual([['LOAN-B'], ['HOLD-B'], ['HIST-B']]);
    });

    it('saves successfully from initial edit mode and really removes the modal', async () => {
        const updated = { ...mockRecord, title: 'Updated while editing' };
        vi.spyOn(apiClient, 'patch').mockResolvedValue(updated);
        let wrapper;
        wrapper = mountDetail(
            { initialMode: 'edit', 'onUpdate:show': value => wrapper.setProps({ show: value }) }
        );
        await flushPromises();

        wrapper.vm.formData.title = updated.title;
        const saveButton = wrapper.findAll('button').find(button => button.text().includes('common.save'));
        await saveButton.trigger('click');
        await flushPromises();

        expect(wrapper.emitted('saved')).toEqual([[updated]]);
        expect(wrapper.emitted('update:show')).toContainEqual([false]);
        expect(wrapper.find('.test-modal').exists()).toBe(false);
    });

    it('emits quick-return from the rendered copy action', async () => {
        const items = [{ item_id: 'COPY-LOAN', status: 'on_loan', current_loan: { borrower_id: 'B-7' } }];
        vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return items;
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });
        const wrapper = mountDetail();
        await flushPromises();

        const quickReturn = wrapper.find('tbody button.btn-outline-primary');
        expect(quickReturn.exists()).toBe(true);
        await quickReturn.trigger('click');

        expect(wrapper.emitted('quick-return')).toEqual([['COPY-LOAN']]);
    });

    it('renders numeric, textual and missing issue numbers in periodical history', async () => {
        const issues = [
            { id: 1, item_id: 'ISSUE-2', call_number: '2', status: 'available' },
            { id: 2, item_id: 'ISSUE-S', call_number: 'Special', status: 'available' },
            { id: 3, item_id: 'ISSUE-EMPTY', call_number: null, status: 'available' }
        ];
        vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return issues;
            if (endpoint.startsWith('/holds/')) return [];
            return { ...mockRecord, identifier_type: 'issn' };
        });
        const wrapper = mountDetail({ record: { ...mockRecord, identifier_type: 'issn' } });
        await flushPromises();

        const issueCells = wrapper.findAll('tbody tr').map(row => row.findAll('td')[1].text());
        expect(issueCells).toEqual(['2', 'Special', '—']);
    });

    it('reacts to saved emitted by the real ItemEditForm', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return mockItems;
            if (endpoint.startsWith('/holds/')) return [];
            return mockRecord;
        });
        vi.spyOn(apiClient, 'patch').mockResolvedValue({ ...mockItems[0], condition: 'damaged' });
        const wrapper = mountDetail({ initialMode: 'edit' }, { realItemEditForm: true });
        await flushPromises();

        wrapper.vm.handleEditItem(mockItems[0]);
        await wrapper.vm.$nextTick();
        const itemForm = wrapper.findComponent(ItemEditForm);
        expect(itemForm.exists()).toBe(true);
        await itemForm.vm.handleSubmit();
        await flushPromises();

        expect(itemForm.emitted('saved')).toHaveLength(1);
        expect(wrapper.vm.showItemEditModal).toBe(false);
        expect(wrapper.vm.editingItem).toBe(null);
        expect(getSpy).toHaveBeenCalledWith('/catalog/bibliographic/42/items');
    });

    it('covers malformed bibliographic data, filter errors and edge validations', async () => {
        const periodicalItems = [
            { id: 1, item_id: 'TEXT', call_number: 'Special', status: 'available' },
            { id: 2, item_id: 'NUMBER', call_number: '2', status: 'available' },
            { id: 3, item_id: 'EMPTY', call_number: null, status: 'available' }
        ];
        const malformedRecord = {
            ...mockRecord,
            authors: 'not-an-array', illustrators: 'not-an-array', keywords: 'not-an-array',
            identifier_type: 'issn'
        };
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.endsWith('/items')) return periodicalItems;
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint.includes('/history')) return {};
            if (endpoint === '/borrowers') return { items: [] };
            return malformedRecord;
        });
        const post = vi.spyOn(apiClient, 'post').mockRejectedValue({});
        const patch = vi.spyOn(apiClient, 'patch')
            .mockRejectedValueOnce({ statusCode: 400 })
            .mockRejectedValueOnce({ statusCode: 500 })
            .mockResolvedValue({ ...malformedRecord, publication_year: 2020, page_count: 10 });
        const wrapper = mountDetail({ record: malformedRecord, initialMode: 'edit' });
        await flushPromises();

        expect(wrapper.vm.formData.authors).toEqual([]);
        expect(wrapper.vm.formData.illustrators).toEqual([]);
        expect(wrapper.vm.formData.keywords).toEqual([]);
        expect(wrapper.vm.items.map(item => item.item_id)).toEqual(['NUMBER', 'TEXT', 'EMPTY']);
        expect(wrapper.vm.formatBorrowerResult({ borrower_id: 'B-1', first_name: 'A', last_name: 'B' }))
            .toContain('<small class="text-muted"></small>');

        await wrapper.vm.createHold({ id: 1, first_name: 'A', last_name: 'B' });
        expect(wrapper.vm.reserveMessage.text).toBe('errors.generic');
        wrapper.vm.activeTab = 'history';
        await flushPromises();
        expect(wrapper.vm.itemHistoryItems).toEqual([]);

        wrapper.vm.isEditMode = true;
        wrapper.vm.formData.title = 'Valid';
        wrapper.vm.formData.publication_year = 2201;
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBeUndefined();
        expect(wrapper.vm.errors.publication_year).toBe('errors.invalid_year_range');

        wrapper.vm.formData.publication_year = 2020;
        wrapper.vm.formData.page_count = 10;
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('errors.validation_failed');
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('errors.unknown_error');
        await wrapper.vm.handleSubmit();
        expect(patch).toHaveBeenCalledWith('/catalog/records/42', expect.objectContaining({
            publication_year: 2020, page_count: 10
        }));
        expect(getSpy).toHaveBeenCalledWith('/circulation/item/NUMBER/history', expect.any(Object));

        wrapper.vm.record = null;
        const push = vi.fn();
        globalThis.__testRouter.push = push;
        wrapper.vm.addItem();
        expect(push).toHaveBeenCalledWith({
            name: 'cataloging', query: { record_id: '42' }
        });
    });
});


describe('RecordDeleteDialog', () => {
    const mountDeleteDialog = (items) => mount(RecordDeleteDialog, {
        props: {
            show: true,
            recordData: { id: 42, title: 'Le Petit Prince', authors: ['A. Author'], items }
        },
        global: { stubs: { teleport: true } }
    });

    it('blocks confirmation while a copy is on loan', async () => {
        const wrapper = mountDeleteDialog([{ item_id: 'I-1', status: 'on_loan' }]);
        const confirm = wrapper.findAll('button').find(button => button.classes('btn-danger'));

        expect(wrapper.vm.hasActiveLoans).toBe(true);
        expect(confirm.attributes('disabled')).toBeDefined();
        await confirm.trigger('click');
        expect(wrapper.emitted('confirm')).toBeUndefined();
    });

    it('emits confirmation when all copies can be deleted', async () => {
        const wrapper = mountDeleteDialog([{ item_id: 'I-1', status: 'available' }]);
        const confirm = wrapper.findAll('button').find(button => button.classes('btn-danger'));

        expect(wrapper.vm.hasActiveLoans).toBe(false);
        await confirm.trigger('click');
        expect(wrapper.emitted('confirm')).toEqual([[42]]);
    });
});
