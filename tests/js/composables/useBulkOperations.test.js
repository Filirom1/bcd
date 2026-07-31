import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useBulkOperations } from '../../../src/bcd_web_vue/js/composables/useBulkOperations.js';

describe('useBulkOperations', () => {
    beforeEach(() => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
            success: true,
            modified_count: 2
        }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
        })));
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('triggers progress visibility when count is 100 or more', async () => {
        const bulk = useBulkOperations('borrowers');
        const ids = Array.from({ length: 100 }, (_, i) => i + 1);

        const promise = bulk.bulkChangeClass(ids, 10);
        expect(bulk.showProgress.value).toBe(true);

        await promise;
        expect(bulk.progress.value).toBe(100);
    });

    it('submits change class payload to bulk-edit endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
            success: true,
            modified_count: 2
        }), { status: 200 }));
        vi.stubGlobal('fetch', fetchMock);

        const bulk = useBulkOperations('borrowers');
        await bulk.bulkChangeClass([1, 2], 8);

        expect(fetchMock).toHaveBeenCalledWith(
            '/api/v1/admin/borrowers/bulk-edit',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    operation: 'change_class',
                    borrower_ids: [1, 2],
                    target_class_id: 8
                })
            })
        );
    });

    it('submits delete payload to bulk-delete endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
            success: true,
            modified_count: 3
        }), { status: 200 }));
        vi.stubGlobal('fetch', fetchMock);

        const bulk = useBulkOperations('borrowers');
        await bulk.bulkDeleteBorrowers([1, 2, 3]);

        expect(fetchMock).toHaveBeenCalledWith(
            '/api/v1/admin/borrowers/bulk-delete',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    borrower_ids: [1, 2, 3]
                })
            })
        );
    });
});
