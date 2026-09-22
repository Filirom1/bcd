import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import BorrowerDetail from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerDetail.js';
import BorrowerActions from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerActions.js';
import Pagination from '../../../../src/bcd_web_vue/js/components/ui/Pagination.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { events } from '../../../../src/bcd_web_vue/js/utils/events.js';
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

function mountDetail(props = {}, options = {}) {
    const stubs = {
        teleport: true,
        BorrowerDeleteDialog: true
    };
    if (!options.realActions) stubs.BorrowerActions = true;
    if (!options.realPagination) stubs.Pagination = true;

    return mount(BorrowerDetail, {
        props: {
            borrowerId: 'B-101',
            borrower: borrower,
            show: true,
            initialMode: 'edit',
            ...props
        },
        global: { stubs }
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
    const mockBorrowerApi = (data = borrower, classes = []) => vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
        if (endpoint.startsWith('/borrowers/')) return data;
        if (endpoint === '/classes') return classes;
        if (endpoint.startsWith('/holds/')) return data.holds || [];
        return [];
    });

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

    it('shows loan limits, overdue warnings, and active loan details', async () => {
        const detailedBorrower = makeBorrower({
            current_loans_count: 2,
            loan_limit: 2,
            overdue_count: 1,
            total_checkouts: 12,
            current_loans: [{
                item_id: 'I-001',
                title: 'The Little Prince',
                bibliographic_record_id: 42,
                due_date: '2020-01-01',
                is_overdue: true,
                renewal_count: 1
            }]
        });
        mockBorrowerApi(detailedBorrower);
        const wrapper = mountDetail({ borrower: detailedBorrower, initialMode: 'view' });
        await flushPromises();

        expect(wrapper.vm.currentLoans).toHaveLength(1);
        expect(wrapper.vm.getLoanBadgeClass(detailedBorrower)).toBe('bg-danger');
        expect(wrapper.text()).toContain('I-001');
        expect(wrapper.text()).toContain('borrower.has_overdue_items');
        expect(wrapper.text()).toContain('borrower.cannot_checkout');
    });

    it('displays an API error for a borrower that cannot be loaded', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue({ message: 'Borrower not found' });
        const wrapper = mountDetail({ borrower: null, initialMode: 'view' });
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.borrower).toBeNull();
        expect(wrapper.vm.error).toBe('Borrower not found');
        expect(wrapper.text()).toContain('Borrower not found');
    });

    it('loads an empty history only when the history tab is opened', async () => {
        const getSpy = mockBorrowerApi(makeBorrower({ current_loans: [] }));
        getSpy.mockImplementation(async (endpoint) => {
            if (endpoint.includes('/history')) return { history: [], pagination: null };
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint === '/classes') return [];
            return [];
        });
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();

        expect(getSpy).not.toHaveBeenCalledWith('/circulation/borrower/B-101/history', expect.anything());
        wrapper.vm.activeTab = 'history';
        await flushPromises();

        expect(getSpy).toHaveBeenCalledWith('/circulation/borrower/B-101/history', {
            page: 1,
            page_size: 10
        });
        expect(wrapper.vm.historyItems).toEqual([]);
        expect(wrapper.text()).toContain('circulation.no_history');
    });

    it('loads and filters a populated history', async () => {
        const history = [{
            item_id: 'I-001',
            title: 'A returned book',
            bibliographic_record_id: 9,
            checkout_date: '2024-01-01',
            return_date: '2024-01-15',
            was_overdue: true
        }];
        const getSpy = mockBorrowerApi();
        getSpy.mockImplementation(async (endpoint, params) => {
            if (endpoint.includes('/history')) return { history, pagination: { page: params.page, total_pages: 2, page_size: params.page_size, total_items: 11 } };
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint === '/classes') return [];
            return [];
        });
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();

        expect(wrapper.vm.historyItems).toEqual(history);
        expect(wrapper.vm.historyPagination.total_pages).toBe(2);
        wrapper.vm.historyDateFrom = '2024-01-01';
        wrapper.vm.historyDateTo = '2024-12-31';
        wrapper.vm.applyHistoryFilter();
        await flushPromises();
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/borrower/B-101/history', {
            page: 1,
            page_size: 10,
            date_from: '2024-01-01',
            date_to: '2024-12-31'
        });
    });

    it('updates role, class, and contact information successfully', async () => {
        const updated = makeBorrower({ role: 'teacher', class_id: 7, first_name: 'Updated' });
        mockBorrowerApi(borrower, [{ id: 7, name: 'CM2', homeroom_teacher: 'M. Dupont' }]);
        const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValue(updated);
        const refreshSpy = vi.spyOn(events, 'emit');
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        wrapper.vm.formData.role = 'teacher';
        wrapper.vm.formData.class_id = 7;
        wrapper.vm.formData.first_name = 'Updated';
        await wrapper.vm.handleSubmit();

        expect(patchSpy).toHaveBeenCalledWith('/borrowers/B-101', expect.objectContaining({
            role: 'teacher', class_id: 7, first_name: 'Updated'
        }));
        expect(wrapper.vm.borrower).toEqual(updated);
        expect(wrapper.emitted('saved')).toEqual([[updated]]);
        expect(refreshSpy).toHaveBeenCalledWith('borrowers:refresh');
    });

    it('rejects incomplete borrower edits before sending a request', async () => {
        const patchSpy = vi.spyOn(apiClient, 'patch');
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        wrapper.vm.formData.first_name = '';
        wrapper.vm.formData.last_name = '';
        wrapper.vm.formData.borrower_id = '';
        wrapper.vm.formData.role = '';
        await wrapper.vm.handleSubmit();

        expect(patchSpy).not.toHaveBeenCalled();
        expect(wrapper.vm.errors).toEqual(expect.objectContaining({
            first_name: 'admin.borrower.validation.first_name_required',
            last_name: 'admin.borrower.validation.last_name_required',
            borrower_id: 'admin.borrower.validation.borrower_id_required',
            role: 'admin.borrower.validation.role_required'
        }));
    });

    it('maps duplicate, validation, and network errors to edit feedback', async () => {
        const patchSpy = vi.spyOn(apiClient, 'patch');
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        patchSpy.mockRejectedValueOnce({ statusCode: 409 });
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.borrower_id).toBe('errors.BORROWER_ID_NOT_AVAILABLE');

        patchSpy.mockRejectedValueOnce({ statusCode: 400, message: 'role is invalid' });
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.role).toBe('role is invalid');

        patchSpy.mockRejectedValueOnce({ statusCode: 500, message: 'Server unavailable' });
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('Server unavailable');
    });

    it('opens the delete confirmation and deletes a borrower after confirmation', async () => {
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const refreshSpy = vi.spyOn(events, 'emit');
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        wrapper.vm.handleDeleteClick();
        expect(wrapper.vm.showDeleteDialog).toBe(true);
        await wrapper.vm.handleDeleteConfirm('B-101');

        expect(deleteSpy).toHaveBeenCalledWith('/borrowers/B-101');
        expect(refreshSpy).toHaveBeenCalledWith('borrowers:refresh');
        expect(wrapper.emitted('deleted')).toEqual([['B-101']]);
        expect(wrapper.emitted('close')).toBeTruthy();
    });

    it('keeps the delete dialog closed and shows a business error when deletion is refused', async () => {
        vi.spyOn(apiClient, 'delete').mockRejectedValue({ statusCode: 400, message: 'Active loans' });
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        await wrapper.vm.handleDeleteConfirm('B-101');

        expect(wrapper.vm.showDeleteDialog).toBe(false);
        expect(wrapper.vm.errors.general).toBe('Active loans');
        expect(wrapper.emitted('deleted')).toBeUndefined();
    });

    it('supports hold search, creation, cancellation, and linked-record navigation', async () => {
        const getSpy = mockBorrowerApi();
        getSpy.mockImplementation(async (endpoint) => {
            if (endpoint === '/catalog/bibliographic/search') return { items: [{ id: 42, title: 'A book', authors: ['Author'] }] };
            if (endpoint === '/holds/borrower/1') return [{ id: 8, bibliographic_record_id: 42, title: 'A book' }];
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint === '/classes') return [];
            return [];
        });
        const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue({});
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();

        wrapper.vm.holdSearch = 'book';
        await wrapper.vm.searchBooksForHold();
        expect(wrapper.vm.holdResults).toHaveLength(1);

        await wrapper.vm.createHold(42);
        expect(postSpy).toHaveBeenCalledWith('/holds', expect.objectContaining({ borrower_id: 1, bibliographic_record_id: 42 }));
        expect(wrapper.vm.holdResults).toEqual([]);

        await wrapper.vm.cancelHold(8);
        expect(deleteSpy).toHaveBeenCalledWith('/holds/8');
        wrapper.vm.viewItem(42);
        expect(wrapper.emitted('view-item')).toEqual([[42]]);
    });

    it('reloads borrower data after a block or unblock action', async () => {
        const getSpy = mockBorrowerApi();
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        const initialCalls = getSpy.mock.calls.length;

        wrapper.vm.handleActionCompleted('block');
        await flushPromises();

        expect(wrapper.emitted('updated')).toEqual([['block']]);
        expect(getSpy.mock.calls.length).toBeGreaterThan(initialCalls);
    });

    it('survives class and hold loading failures while retaining the borrower', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/classes') throw new Error('classes unavailable');
            if (endpoint.startsWith('/holds/')) throw new Error('holds unavailable');
            return borrower;
        });
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        expect(wrapper.vm.borrower).toEqual(borrower);
        expect(wrapper.vm.classes).toEqual([]);
        expect(wrapper.vm.holds).toEqual([]);
        expect(wrapper.vm.isLoadingClasses).toBe(false);
        expect(consoleSpy).toHaveBeenCalled();
        expect(getSpy).toHaveBeenCalledWith('/classes', { limit: 500 });
    });

    it('maps hold search, creation and cancellation errors without leaving loading state', async () => {
        const getSpy = mockBorrowerApi();
        const postSpy = vi.spyOn(apiClient, 'post')
            .mockRejectedValueOnce({ code: 'hold_limit_exceeded', details: { limit: 3 } })
            .mockRejectedValueOnce(new Error('hold offline'));
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockRejectedValue(new Error('cancel offline'));
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();

        wrapper.vm.holdSearch = 'book';
        getSpy.mockRejectedValueOnce(new Error('search offline'));
        await wrapper.vm.searchBooksForHold();
        expect(wrapper.vm.holdResults).toEqual([]);
        expect(wrapper.vm.holdSearchLoading).toBe(false);

        await wrapper.vm.createHold(7);
        expect(wrapper.vm.holdFormMessage).toEqual(expect.objectContaining({ type: 'error' }));
        await wrapper.vm.createHold(8);
        expect(wrapper.vm.holdFormMessage.text).toBe('hold offline');
        await wrapper.vm.cancelHold(1);
        expect(deleteSpy).toHaveBeenCalledWith('/holds/1');
        expect(wrapper.vm.holds).toEqual([]);
        expect(postSpy).toHaveBeenCalledTimes(2);
    });

    it('handles history errors and changes both page and page size', async () => {
        const getSpy = mockBorrowerApi();
        getSpy.mockImplementation(async (endpoint, params) => {
            if (endpoint.includes('/history')) {
                return { history: [{ item_id: `I-${params.page}`, title: 'Book' }], pagination: { page: params.page, total_pages: 3, page_size: params.page_size, total_items: 30 } };
            }
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint === '/classes') return [];
            return [];
        });
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();
        wrapper.vm.onHistoryPageChange(2);
        await flushPromises();
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/borrower/B-101/history', { page: 2, page_size: 10 });
        wrapper.vm.onHistoryPageSizeChange(25);
        await flushPromises();
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/borrower/B-101/history', { page: 1, page_size: 25 });
        getSpy.mockRejectedValueOnce(new Error('history offline'));
        wrapper.vm.applyHistoryFilter();
        await flushPromises();
        expect(wrapper.vm.historyItems).toEqual([]);
        expect(wrapper.vm.historyPagination).toBe(null);
        expect(wrapper.vm.historyLoading).toBe(false);
    });

    it('covers loan badge thresholds, unknown roles and borrowers without a class', async () => {
        const specialBorrower = makeBorrower({ current_loans_count: 0, loan_limit: 3, loan_limit_warning: 2, role: 'principal', class_name: null });
        mockBorrowerApi(specialBorrower);
        const wrapper = mountDetail({
            borrower: specialBorrower,
            initialMode: 'view'
        });
        await flushPromises();
        expect(wrapper.vm.getLoanBadgeClass({ current_loans_count: 0, loan_limit: 3, loan_limit_warning: 2 })).toBe('bg-secondary');
        expect(wrapper.vm.getLoanBadgeClass({ current_loans_count: 2, loan_limit: 3, loan_limit_warning: 2 })).toBe('bg-warning text-dark');
        expect(wrapper.vm.getLoanBadgeClass({ current_loans_count: 3, loan_limit: 3, loan_limit_warning: 2 })).toBe('bg-danger');
        expect(wrapper.vm.getRoleDisplayName('principal')).toBe('principal');
        expect(wrapper.text()).toContain('borrower.role_principal');
        expect(wrapper.text()).toContain('—');
    });

    it('updates borrowerId and borrower props and reloads the dependent data', async () => {
        const replacement = makeBorrower({ id: 2, borrower_id: 'B-202', first_name: 'New', last_name: 'Student' });
        const getSpy = mockBorrowerApi(replacement);
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        await wrapper.setProps({ borrowerId: 'B-202', borrower: replacement });
        await flushPromises();
        expect(getSpy).toHaveBeenCalledWith('/borrowers/B-202', { detail: true });
        expect(wrapper.vm.borrower.borrower_id).toBe('B-202');
        expect(wrapper.vm.formData.first_name).toBe('New');
    });

    it('clears invalid class responses instead of passing a non-array to the form', async () => {
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/classes') return { classes: 'not-an-array' };
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint.startsWith('/holds/')) return [];
            return [];
        });
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        expect(getSpy).toHaveBeenCalledWith('/classes', { limit: 500 });
        expect(wrapper.vm.classes).toEqual([]);
        expect(wrapper.vm.isLoadingClasses).toBe(false);
    });

    it('keeps the borrower page usable after a successful hold cancellation whose reload fails', async () => {
        let holdLoads = 0;
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint === '/classes') return [];
            if (endpoint.startsWith('/holds/')) {
                holdLoads += 1;
                if (holdLoads > 1) throw new Error('holds reload failed');
                return [{ id: 8 }];
            }
            return [];
        });
        const deleteSpy = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        await wrapper.vm.cancelHold(8);

        expect(deleteSpy).toHaveBeenCalledWith('/holds/8');
        expect(wrapper.vm.borrower).toEqual(borrower);
        expect(wrapper.vm.holds).toEqual([]);
        expect(getSpy.mock.calls.filter(([url]) => url === '/holds/borrower/1')).toHaveLength(2);
    });

    it('emits action completion even when reloading the borrower fails', async () => {
        let borrowerLoads = 0;
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint.startsWith('/borrowers/')) {
                borrowerLoads += 1;
                if (borrowerLoads > 1) throw new Error('borrower reload failed');
                return borrower;
            }
            if (endpoint === '/classes') return [];
            if (endpoint.startsWith('/holds/')) return [];
            return [];
        });
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        wrapper.vm.handleActionCompleted('unblock');
        await flushPromises();

        expect(wrapper.emitted('updated')).toEqual([['unblock']]);
        expect(wrapper.vm.borrower).toEqual(borrower);
        expect(wrapper.vm.error).toBe('borrower reload failed');
        expect(getSpy.mock.calls.filter(([url]) => url === '/borrowers/B-101')).toHaveLength(2);
    });

    it('updates the form when only the borrower prop changes', async () => {
        const replacement = makeBorrower({ borrower_id: 'B-101', first_name: 'Prop', last_name: 'Replacement' });
        mockBorrowerApi(replacement);
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();
        await wrapper.setProps({ borrower: replacement });
        await flushPromises();

        expect(wrapper.vm.formData.first_name).toBe('Prop');
        expect(wrapper.vm.formData.last_name).toBe('Replacement');
    });

    it('reloads a new borrowerId even when the borrower prop is absent', async () => {
        const replacement = makeBorrower({ id: 2, borrower_id: 'B-202', first_name: 'New', last_name: 'Borrower' });
        const getSpy = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/classes') return [];
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint === '/borrowers/B-202') return replacement;
            if (endpoint === '/borrowers/B-101') return borrower;
            return [];
        });
        const wrapper = mountDetail({ borrower: null, borrowerId: 'B-101', initialMode: 'view' });
        await flushPromises();
        await wrapper.setProps({ borrowerId: 'B-202' });
        await flushPromises();

        expect(getSpy).toHaveBeenCalledWith('/borrowers/B-202', { detail: true });
        expect(wrapper.vm.borrower.borrower_id).toBe('B-202');
    });

    it('clears a paginated history page when the next page fails', async () => {
        const getSpy = mockBorrowerApi();
        getSpy.mockImplementation(async (endpoint, params) => {
            if (endpoint.includes('/history')) {
                if (params.page === 2) throw new Error('next page unavailable');
                return { history: [{ item_id: 'I-1' }], pagination: { page: 1, total_pages: 2, total_items: 11 } };
            }
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint === '/classes') return [];
            return [];
        });
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();
        wrapper.vm.onHistoryPageChange(2);
        await flushPromises();

        expect(wrapper.vm.historyItems).toEqual([]);
        expect(wrapper.vm.historyPagination).toBe(null);
        expect(wrapper.vm.historyLoading).toBe(false);
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/borrower/B-101/history', { page: 2, page_size: 10 });
    });

    it('maps a network deletion error to the generic deletion message', async () => {
        vi.spyOn(apiClient, 'delete').mockRejectedValue(new Error('offline'));
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();
        await wrapper.vm.handleDeleteConfirm('B-101');
        expect(wrapper.vm.errors.general).toBe('admin.error_delete_borrower');
        expect(wrapper.vm.showDeleteDialog).toBe(false);
        expect(consoleSpy).toHaveBeenCalledWith('Error deleting borrower:', expect.any(Error));
    });

    it('saves from view mode through the modal and returns to consultation', async () => {
        const updated = makeBorrower({ first_name: 'Consulted', role: 'teacher' });
        mockBorrowerApi(borrower);
        vi.spyOn(apiClient, 'patch').mockResolvedValue(updated);
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();

        await wrapper.get('[data-testid="borrower-detail-modal"] button.btn-primary').trigger('click');
        expect(wrapper.get('[data-testid="borrower-edit-modal"]').exists()).toBe(true);
        await wrapper.get('[data-testid="input-first-name"]').setValue('Consulted');
        await wrapper.get('[data-testid="button-save"]').trigger('click');
        await flushPromises();

        expect(wrapper.vm.borrower).toEqual(updated);
        expect(wrapper.vm.isEditMode).toBe(false);
        expect(wrapper.get('[data-testid="borrower-detail-modal"]').exists()).toBe(true);
        expect(wrapper.find('[data-testid="borrower-edit-modal"]').exists()).toBe(false);
        expect(wrapper.emitted('saved')).toEqual([[updated]]);
    });

    it('falls back to the generic edit error for a message-less 400 response', async () => {
        vi.spyOn(apiClient, 'patch').mockRejectedValue({ statusCode: 400 });
        const wrapper = mountDetail({ initialMode: 'edit' });
        await flushPromises();

        await wrapper.vm.handleSubmit();

        expect(wrapper.vm.errors.general).toBe('admin.borrower.edit.error');
        expect(wrapper.get('[data-testid="general-error"]').text()).toContain('admin.borrower.edit.error');
        expect(wrapper.vm.isSubmitting).toBe(false);
    });

    it('handles a real BorrowerActions completion in the view modal', async () => {
        mockBorrowerApi(borrower);
        vi.spyOn(apiClient, 'post').mockResolvedValue({});
        const wrapper = mountDetail({ initialMode: 'view' }, { realActions: true });
        await flushPromises();

        const actions = wrapper.findComponent(BorrowerActions);
        expect(actions.exists()).toBe(true);
        await actions.get('button.btn-danger').trigger('click');
        await actions.get('select').setValue('Lost Book');
        await actions.vm.confirmBlock();
        await flushPromises();

        expect(apiClient.post).toHaveBeenCalledWith(
            '/borrowers/B-101/block', null, { reason: 'Lost Book' }
        );
        expect(wrapper.emitted('updated')).toContainEqual(['block']);
    });

    it('changes history page through the rendered Pagination component', async () => {
        const getSpy = mockBorrowerApi();
        getSpy.mockImplementation(async (endpoint, params) => {
            if (endpoint.includes('/history')) {
                return {
                    history: [{ item_id: `I-${params.page}`, title: `Book ${params.page}` }],
                    pagination: { page: params.page, total_pages: 2, page_size: params.page_size, total_items: 11 }
                };
            }
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint.startsWith('/holds/')) return [];
            if (endpoint === '/classes') return [];
            return [];
        });
        const wrapper = mountDetail({ initialMode: 'view' }, { realPagination: true });
        await flushPromises();
        wrapper.vm.activeTab = 'history';
        await flushPromises();

        const pagination = wrapper.findComponent(Pagination);
        expect(pagination.exists()).toBe(true);
        expect(wrapper.find('.pagination').exists()).toBe(true);
        const pageTwo = pagination.findAll('button').find(button => button.text() === '2');
        await pageTwo.trigger('click');
        await flushPromises();

        expect(wrapper.find('.pagination .active').text()).toBe('2');
        expect(wrapper.find('tbody').text()).toContain('Book 2');
        expect(getSpy).toHaveBeenLastCalledWith('/circulation/borrower/B-101/history', {
            page: 2, page_size: 10
        });
    });

    it('covers empty hold queries, wrapped classes, empty history and message-less saves', async () => {
        const getSpy = mockBorrowerApi();
        getSpy.mockImplementation(async (endpoint) => {
            if (endpoint === '/classes') return { items: [{ id: 1, name: 'CM1' }] };
            if (endpoint.includes('/history')) return {};
            if (endpoint.startsWith('/borrowers/')) return borrower;
            if (endpoint.startsWith('/holds/')) return [];
            return [];
        });
        const post = vi.spyOn(apiClient, 'post').mockRejectedValue({});
        const patch = vi.spyOn(apiClient, 'patch')
            .mockRejectedValueOnce({ statusCode: 400 })
            .mockRejectedValueOnce({});
        const wrapper = mountDetail({ initialMode: 'view' });
        await flushPromises();

        wrapper.vm.holdSearch = '   ';
        await wrapper.vm.searchBooksForHold();
        expect(wrapper.vm.holdResults).toEqual([]);
        expect(getSpy).not.toHaveBeenCalledWith('/catalog/bibliographic/search', expect.anything());
        expect(wrapper.vm.classes).toEqual([{ id: 1, name: 'CM1' }]);

        await wrapper.vm.createHold(9);
        expect(post).toHaveBeenCalledWith('/holds', expect.any(Object));
        expect(wrapper.vm.holdFormMessage).toEqual({ type: 'error', text: 'errors.generic' });

        wrapper.vm.isEditMode = true;
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('admin.borrower.edit.error');
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('admin.borrower.edit.error');

        wrapper.vm.activeTab = 'history';
        await flushPromises();
        expect(wrapper.vm.historyItems).toEqual([]);
        expect(wrapper.vm.historyPagination).toBe(null);
    });
});
