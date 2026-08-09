import { describe, expect, it } from 'vitest';

import { usePagination } from '../../../src/bcd_web_vue/js/composables/usePagination.js';

describe('usePagination', () => {
    it('calculates page bounds and API offset', () => {
        const pagination = usePagination({ initialPage: 2, pageSize: 10, totalItems: 25 });

        expect(pagination.totalPages.value).toBe(3);
        expect(pagination.offset.value).toBe(10);
        expect(pagination.limit.value).toBe(10);
        expect(pagination.firstItem.value).toBe(11);
        expect(pagination.lastItem.value).toBe(20);
        expect(pagination.hasPreviousPage.value).toBe(true);
        expect(pagination.hasNextPage.value).toBe(true);
    });

    it('does not navigate beyond the first or last page', () => {
        const pagination = usePagination({ pageSize: 10, totalItems: 11 });

        pagination.previousPage();
        expect(pagination.currentPage.value).toBe(1);

        pagination.nextPage();
        pagination.nextPage();
        expect(pagination.currentPage.value).toBe(2);
        expect(pagination.hasNextPage.value).toBe(false);
    });

    it('clamps an invalid current page when the result set shrinks', () => {
        const pagination = usePagination({ initialPage: 4, pageSize: 10, totalItems: 40 });

        pagination.setTotalItems(13);

        expect(pagination.currentPage.value).toBe(2);
        expect(pagination.totalPages.value).toBe(2);
        expect(pagination.lastItem.value).toBe(13);
    });

    it('resets to the first page when the page size changes or state is reset', () => {
        const pagination = usePagination({ initialPage: 3, pageSize: 20, totalItems: 100 });

        pagination.setPageSize(50);
        expect(pagination.currentPage.value).toBe(1);
        expect(pagination.pageSize.value).toBe(50);

        pagination.reset();
        expect(pagination.currentPage.value).toBe(1);
        expect(pagination.pageSize.value).toBe(20);
        expect(pagination.totalItems.value).toBe(0);
        expect(pagination.firstItem.value).toBe(0);
    });
});
