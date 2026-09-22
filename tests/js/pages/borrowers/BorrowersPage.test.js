import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import BorrowersPage from '../../../../src/bcd_web_vue/js/pages/BorrowersPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';
import { ApiError } from '../../../../src/bcd_web_vue/js/models/error.js';
import { makeBorrower } from '../../fixtures/borrowers.js';

const borrower = makeBorrower({ borrower_id: 'B-101' });
const listResponse = {
    items: [borrower],
    total: 26,
    page: 1,
    page_size: 10,
    limit: 10,
    offset: 0
};
const mountedWrappers = [];

function mountBorrowersPage() {
    const wrapper = shallowMount(BorrowersPage);
    mountedWrappers.push(wrapper);
    return wrapper;
}

function mockBorrowerListApi() {
    return vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
        if (endpoint === '/borrowers') return listResponse;
        throw new Error(`Unexpected GET request: ${endpoint}`);
    });
}

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('BorrowersPage', () => {
    it('loads a paginated collection and exposes its pagination metadata', async () => {
        const get = mockBorrowerListApi();
        const wrapper = mountBorrowersPage();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/borrowers', {
            page: 1,
            page_size: 10
        });
        expect(wrapper.vm.borrowers).toEqual([borrower]);
        expect(wrapper.vm.paginationMeta).toMatchObject({
            total: 26,
            offset: 0,
            limit: 10
        });
        expect(wrapper.vm.totalPages).toBe(3);
    });

    it('resets pagination and reloads when filters change', async () => {
        const get = mockBorrowerListApi();
        const wrapper = mountBorrowersPage();
        await flushPromises();

        wrapper.vm.currentPage = 2;
        wrapper.vm.handleFilterChange({ class_id: 4, active: true });
        await flushPromises();

        expect(get).toHaveBeenLastCalledWith('/borrowers', {
            page: 1,
            page_size: 10,
            class_id: 4,
            active: true
        });
        expect(wrapper.vm.currentPage).toBe(1);
    });

    it('opens edit mode only for the single selected borrower', async () => {
        mockBorrowerListApi();
        const wrapper = mountBorrowersPage();
        await flushPromises();

        wrapper.vm.handleSelectionChanged(['B-101']);
        wrapper.vm.handleEditSelected();

        expect(wrapper.vm.selectedBorrower).toEqual(borrower);
        expect(wrapper.vm.showEditModal).toBe(true);
    });

    it('uses the API client for bulk class changes and refreshes once', async () => {
        const get = mockBorrowerListApi();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ successful_count: 1 });
        const wrapper = mountBorrowersPage();
        await flushPromises();

        wrapper.vm.handleSelectionChanged(['B-101']);
        await wrapper.vm.handleBulkOperation({ operation: 'change_class', targetClassId: 4 });
        await flushPromises();

        expect(post).toHaveBeenCalledWith('/admin/borrowers/bulk-change-class', {
            borrower_ids: ['B-101'],
            target_class_id: 4
        });
        expect(get).toHaveBeenCalledTimes(2);
        expect(wrapper.vm.selectedBorrowerIds).toEqual([]);
        expect(wrapper.vm.showBulkEditModal).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'admin.operation_success' })
        ]);
    });

    it('normalizes an API error without leaving the bulk operation busy', async () => {
        mockBorrowerListApi();
        vi.spyOn(apiClient, 'post').mockRejectedValue(
            ApiError.networkError(new Error('offline'))
        );
        const wrapper = mountBorrowersPage();
        await flushPromises();

        wrapper.vm.handleSelectionChanged(['B-101']);
        await wrapper.vm.handleBulkOperation({ operation: 'delete' });

        expect(wrapper.vm.bulkOperationInProgress).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.network_error' })
        ]);
    });

    it('handles pagination, import/edit callbacks, and opens borrower print views', async () => {
        const get = mockBorrowerListApi();
        const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
        const open = vi.spyOn(window, 'open').mockImplementation(() => null);
        const wrapper = mountBorrowersPage();
        await flushPromises();

        wrapper.vm.handlePageChange(2);
        await flushPromises();
        expect(wrapper.vm.currentPage).toBe(2);
        expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' });

        wrapper.vm.handlePageSizeChange(25);
        await flushPromises();
        expect(wrapper.vm.pageSize).toBe(25);
        expect(wrapper.vm.currentPage).toBe(1);

        wrapper.vm.filters.class_id = 4;
        wrapper.vm.handlePrintReference();
        wrapper.vm.handlePrintCards();
        expect(open).toHaveBeenNthCalledWith(1, '#/print/borrowers/reference?class_ids=4', '_blank');
        expect(open).toHaveBeenNthCalledWith(2, '#/print/borrowers/cards?class_ids=4', '_blank');

        wrapper.vm.showAddModal = true;
        wrapper.vm.handleBorrowerCreated(borrower);
        await flushPromises();
        expect(wrapper.vm.showAddModal).toBe(false);

        wrapper.vm.selectedBorrowerIds = ['B-101'];
        wrapper.vm.showEditModal = true;
        wrapper.vm.handleBorrowerSaved({ ...borrower, first_name: 'Updated' });
        await flushPromises();
        expect(wrapper.vm.showEditModal).toBe(false);
        expect(wrapper.vm.selectedBorrowerIds).toEqual([]);

        wrapper.vm.handleImportClick();
        expect(wrapper.vm.showBorrowerImport).toBe(true);
        wrapper.vm.handleImportComplete({ imported: 1 });
        await flushPromises();
        expect(get).toHaveBeenCalled();
    });
});
