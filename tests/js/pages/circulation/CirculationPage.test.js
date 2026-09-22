import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount, shallowMount } from '@vue/test-utils';

import { makeBorrower } from '../../fixtures/borrowers.js';
import { jsonResponse } from '../../helpers/http.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';
import { useGlobalModal } from '../../../../src/bcd_web_vue/js/composables/useGlobalModal.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';
import { ApiError, ERROR_CODES } from '../../../../src/bcd_web_vue/js/models/error.js';
import CirculationPage from '../../../../src/bcd_web_vue/js/pages/CirculationPage.js';
import { events } from '../../../../src/bcd_web_vue/js/utils/events.js';

const borrower = makeBorrower();

function mockBorrowerRequests() {
    return vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
        if (endpoint === '/borrowers/B-101') {
            return { ...borrower };
        }
        if (endpoint === '/circulation/borrower/B-101/items') {
            return { loans: [] };
        }
        if (endpoint === '/holds/borrower/1') {
            return [];
        }
        if (endpoint === '/admin/settings') {
            return {
                borrower_barcode_prefix: '%',
                item_barcode_prefix: '.'
            };
        }
        throw new Error(`Unexpected GET request: ${endpoint}`);
    });
}

function mountCirculationPage(mode = 'checkout') {
    return shallowMount(CirculationPage, {
        props: { mode },
        global: {
            stubs: {
                BorrowerCard: true,
                ItemScanner: true,
                ClassRosterPanel: true,
                HelpPanel: true
            }
        }
    });
}

// Keep the scanner and borrower card real for the boundary tests below.  The
// roster/help panel are unrelated to circulation actions and remain stubbed so
// these tests exercise the actual DOM contract of both action components.
function mountRealCirculationPage(mode = 'checkout') {
    return mount(CirculationPage, {
        props: { mode },
        global: {
            stubs: {
                ClassRosterPanel: true,
                HelpPanel: true
            }
        }
    });
}

beforeEach(() => {
    useNotification().clear();
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse({
        borrower_barcode_prefix: '%',
        item_barcode_prefix: '.'
    }))));
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    useNotification().clear();
});

describe('CirculationPage', () => {
    it('keeps checkout scanning disabled until a borrower is loaded', async () => {
        mockBorrowerRequests();
        const wrapper = mountCirculationPage();
        await flushPromises();

        expect(wrapper.vm.scannerDisabled).toBe(true);

        await wrapper.vm.loadBorrower('B-101');

        expect(wrapper.vm.scannerDisabled).toBe(false);
    });

    it('checks out a scanned item for the loaded borrower and updates the session list', async () => {
        mockBorrowerRequests();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            transactions: [{
                item_id: 'I-001',
                title: 'The Little Prince',
                author: 'Antoine de Saint-Exupéry',
                due_date: '2030-01-15'
            }]
        });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.handleItemScanned('.I-001');

        expect(post).toHaveBeenCalledWith('/circulation/checkout', {
            borrower_id: 'B-101',
            item_ids: ['I-001'],
            checked_out_by: 'web-ui'
        });
        expect(wrapper.vm.scannedItems).toEqual([expect.objectContaining({
            item_id: 'I-001',
            barcode: '.I-001',
            title: 'The Little Prince',
            checked_out: true
        })]);
    });

    it('checks out multiple scanned items in sequence', async () => {
        mockBorrowerRequests();
        const transactions = [
            { item_id: 'I-010', title: 'Book one', due_date: '2030-01-15' },
            { item_id: 'I-011', title: 'Book two', due_date: '2030-01-15' }
        ];
        const post = vi.spyOn(apiClient, 'post')
            .mockResolvedValueOnce({ transactions: [transactions[0]] })
            .mockResolvedValueOnce({ transactions: [transactions[1]] });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.handleItemScanned('.I-010');
        await wrapper.vm.handleItemScanned('.I-011');

        expect(post).toHaveBeenNthCalledWith(1, '/circulation/checkout', {
            borrower_id: 'B-101', item_ids: ['I-010'], checked_out_by: 'web-ui'
        });
        expect(post).toHaveBeenNthCalledWith(2, '/circulation/checkout', {
            borrower_id: 'B-101', item_ids: ['I-011'], checked_out_by: 'web-ui'
        });
        expect(wrapper.vm.scannedItems).toHaveLength(2);
    });

    it('shows the loan-limit error without adding an item', async () => {
        mockBorrowerRequests();
        vi.spyOn(apiClient, 'post').mockRejectedValue(new ApiError(
            ERROR_CODES.LOAN_LIMIT_EXCEEDED,
            'Loan limit reached',
            { current: 3, limit: 3, additional: 1 },
            400
        ));
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.handleItemScanned('.I-012');

        expect(wrapper.vm.scannedItems).toEqual([]);
        expect(useNotification().notifications.value).toEqual([expect.objectContaining({
            type: 'error',
            message: 'errors.loan_limit_exceeded'
        })]);
    });

    it('shows renewal results for renewed and failed items', async () => {
        mockBorrowerRequests();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            renewed: [{ item_id: 'I-013' }],
            failed: [{ item_id: 'I-014' }]
        });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.renewAll();

        expect(post).toHaveBeenCalledWith('/circulation/renew', {
            borrower_id: 'B-101', item_ids: null
        });
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'circulation.renewed_successfully' }),
            expect.objectContaining({ type: 'warning', message: 'circulation.renewal_failed' })
        ]);
    });

    it('returns a scanned item and records its return information', async () => {
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            items: [{
                item_id: 'I-002',
                title: 'Matilda',
                author: 'Roald Dahl',
                call_number: '823.9 DAH',
                shelf_location: 'Romans',
                return_date: '2030-01-02T10:15:00Z',
                was_overdue: false,
                days_overdue: 0,
                hold_ready: null
            }]
        });
        const wrapper = mountCirculationPage('return');
        await flushPromises();

        await wrapper.vm.handleItemScanned('.I-002');

        expect(post).toHaveBeenCalledWith('/circulation/return', {
            item_ids: ['I-002'],
            returned_by: 'web-ui'
        });
        expect(wrapper.vm.scannedItems).toEqual([expect.objectContaining({
            item_id: 'I-002',
            barcode: '.I-002',
            title: 'Matilda',
            returned: true,
            returned_date: '2030-01-02T10:15:00Z'
        })]);
    });

    it('shows a translated checkout error without adding a failed item to the session', async () => {
        mockBorrowerRequests();
        vi.spyOn(apiClient, 'post').mockRejectedValue(new ApiError(
            ERROR_CODES.ITEM_NOT_AVAILABLE,
            'Item unavailable',
            { item_id: 'I-003', status: 'on_loan' },
            400
        ));
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.handleItemScanned('.I-003');

        expect(wrapper.vm.scannedItems).toEqual([]);
        expect(useNotification().notifications.value).toEqual([expect.objectContaining({
            type: 'error',
            message: 'errors.item_not_available'
        })]);
    });

    it('shows the already-on-loan error without recording a checkout', async () => {
        mockBorrowerRequests();
        vi.spyOn(apiClient, 'post').mockRejectedValue(new ApiError(
            ERROR_CODES.ITEM_ALREADY_ON_LOAN,
            'Item is already on loan',
            {
                item_id: 'I-004',
                borrower_name: 'Samira Martin',
                due_date: '2030-01-10'
            },
            409
        ));
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.handleItemScanned('.I-004');

        expect(wrapper.vm.scannedItems).toEqual([]);
        expect(useNotification().notifications.value).toEqual([expect.objectContaining({
            type: 'error',
            message: 'errors.item_already_on_loan'
        })]);
    });

    it('shows the item-not-found error when returning an unknown item', async () => {
        vi.spyOn(apiClient, 'post').mockRejectedValue(new ApiError(
            ERROR_CODES.ITEM_NOT_FOUND,
            'Item does not exist',
            { item_id: 'I-404' },
            404
        ));
        const wrapper = mountCirculationPage('return');
        await flushPromises();

        await wrapper.vm.handleItemScanned('.I-404');

        expect(wrapper.vm.scannedItems).toEqual([]);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.item_not_found' })
        ]);
    });

    it('covers empty computed state, translated statuses, and return fallbacks', async () => {
        const empty = mountCirculationPage();
        expect(empty.vm.borrowerInitials).toBe('');
        expect(empty.vm.borrowerAtLimit).toBe(false);
        await empty.vm.renewAll();

        mockBorrowerRequests();
        globalThis.__testTranslate = key => key === 'item.status_mystery' ? 'Mystery' : key;
        const checkoutPost = vi.spyOn(apiClient, 'post').mockRejectedValue(
            new ApiError(ERROR_CODES.ITEM_NOT_AVAILABLE, 'unavailable', { status: 'mystery' }, 400)
        );
        const checkout = mountCirculationPage();
        await flushPromises();
        await checkout.vm.loadBorrower('B-101');
        await checkout.vm.handleItemScanned('.I-405');
        expect(checkoutPost).toHaveBeenCalledWith('/circulation/checkout', expect.any(Object));
        expect(useNotification().notifications.value.at(-1).message).toBe('errors.item_not_available');

        vi.restoreAllMocks();
        useNotification().clear();
        const returnPost = vi.spyOn(apiClient, 'post')
            .mockRejectedValueOnce(new ApiError(ERROR_CODES.ITEM_NOT_FOUND, 'missing', {}, 404))
            .mockRejectedValueOnce(new Error());
        const returned = mountCirculationPage('return');
        await flushPromises();
        await returned.vm.handleItemScanned('.I-406');
        await returned.vm.handleItemScanned('.I-407');
        expect(returnPost).toHaveBeenCalledTimes(2);
        expect(useNotification().notifications.value.at(-1).message).toBe('circulation.error_return_failed');
    });

    it('handles return errors and borrower blocked status', async () => {
        vi.spyOn(apiClient, 'post').mockRejectedValue(new ApiError(
            ERROR_CODES.ITEM_NOT_ON_LOAN,
            'Item is not on loan',
            { item_id: 'I-020' },
            400
        ));
        const returnWrapper = mountCirculationPage('return');
        await flushPromises();
        await returnWrapper.vm.handleItemScanned('.I-020');
        expect(returnWrapper.vm.scannedItems).toEqual([]);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.item_not_on_loan' })
        ]);
        returnWrapper.unmount();

        vi.restoreAllMocks();
        useNotification().clear();
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return { ...borrower, status: 'blocked' };
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') return [];
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const checkoutWrapper = mountCirculationPage();
        await flushPromises();
        await checkoutWrapper.vm.loadBorrower('B-101');

        expect(get).toHaveBeenCalledWith('/borrowers/B-101');
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'circulation.borrower_blocked_error' })
        ]);
    });

    it('shows a specific error when the borrower cannot be found', async () => {
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') {
                return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            }
            throw { statusCode: 404 };
        });
        const wrapper = mountCirculationPage();
        await flushPromises();

        await wrapper.vm.loadBorrower('%B-404');

        expect(get).toHaveBeenCalledWith('/borrowers/B-404');
        expect(wrapper.vm.borrower).toBe(null);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({
                type: 'error',
                message: 'circulation.error_borrower_not_found'
            })
        ]);
    });

    it('warns about overdue returns and holds ready for collection', async () => {
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            items: [{
                item_id: 'I-005',
                title: 'Matilda',
                was_overdue: true,
                days_overdue: 4,
                borrower_name: 'Amira Benali',
                hold_ready: { borrower_name: 'Louis Martin', class_name: 'CM1' }
            }]
        });
        const wrapper = mountCirculationPage('return');
        await flushPromises();

        await wrapper.vm.handleItemScanned('.I-005');

        expect(post).toHaveBeenCalledWith('/circulation/return', {
            item_ids: ['I-005'],
            returned_by: 'web-ui'
        });
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'warning', message: 'circulation.item_returned_overdue' }),
            expect.objectContaining({ type: 'warning', message: 'circulation.hold_ready_message' })
        ]);
    });

    it('quick-returns a borrower item, reloads the borrower, and refreshes the roster', async () => {
        mockBorrowerRequests();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            items: [{
                item_id: 'I-006',
                display_title: 'Le Petit Prince',
                shelf_location: 'Romans',
                call_number: 'R SAI',
                hold_ready: null
            }]
        });
        const emit = vi.spyOn(events, 'emit');
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.quickReturn('I-006');

        expect(post).toHaveBeenCalledWith('/circulation/return', {
            item_ids: ['I-006'],
            returned_by: 'web-ui'
        });
        expect(emit).toHaveBeenCalledWith('circulation:roster-refresh');
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success' })
        ]);
    });

    it('cancels holds, checks out an available held item, and opens record details', async () => {
        let catalogLookup = 0;
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return { ...borrower };
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') return [];
            if (endpoint === '/catalog/bibliographic/20/items') {
                catalogLookup += 1;
                return catalogLookup === 1 ? { items: [{ item_id: 'I-020', status: 'available' }] } : { items: [] };
            }
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ transactions: [] });
        const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.cancelHold('H-1');
        expect(remove).toHaveBeenCalledWith('/holds/H-1');
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'holds.hold_cancelled' })
        ]);

        await wrapper.vm.checkoutHold({ bibliographic_record_id: 20, title: 'Le Petit Prince' });
        expect(post).toHaveBeenCalledWith('/circulation/checkout', {
            borrower_id: 'B-101', item_ids: ['I-020'], checked_out_by: 'web-ui'
        });

        await wrapper.vm.checkoutHold({ bibliographic_record_id: 20, title: 'Unavailable' });
        expect(useNotification().notifications.value.at(-1)).toEqual(
            expect.objectContaining({ type: 'error', message: 'holds.no_available_item' })
        );

        wrapper.vm.removeItem('I-020');
        expect(wrapper.vm.scannedItems).toEqual([]);
        wrapper.vm.viewItem(20);
        expect(useGlobalModal().globalRecordId.value).toBe(20);
        expect(wrapper.vm.formatDate('2030-01-02')).not.toBe('');
        expect(get).toHaveBeenCalledWith('/holds/borrower/1');
    });

    describe('checkout error matrix', () => {
        const cases = [
            ['borrower_blocked', { borrower_id: 'B-101', reason: 'disciplinary' }],
            ['borrower_has_overdue', { overdue_count: 2 }],
            ['item_not_found', { item_id: 'I-X' }],
            ['item_not_available', { item_id: 'I-X', status: 'on_loan' }],
            ['item_not_available', { item_id: 'I-X', status: 'lost' }],
            ['item_not_loanable', { item_id: 'I-X' }],
            ['item_reserved_for_other', { reserved_for_name: 'Alex' }],
            ['borrower_not_found', { borrower_id: 'B-101' }],
        ];

        it.each(cases)('translates %s without recording an item', async (code, details) => {
            mockBorrowerRequests();
            vi.spyOn(apiClient, 'post').mockRejectedValue(new ApiError(code, 'failure', details, 400));
            const wrapper = mountCirculationPage();
            await flushPromises();
            await wrapper.vm.loadBorrower('B-101');
            await wrapper.vm.handleItemScanned('.I-X');

            expect(wrapper.vm.scannedItems).toEqual([]);
            expect(useNotification().notifications.value.at(-1)).toEqual(
                expect.objectContaining({ type: 'error' })
            );
        });

        it('uses the server message for a network or unknown checkout error', async () => {
            mockBorrowerRequests();
            vi.spyOn(apiClient, 'post').mockRejectedValue(new Error('Network down'));
            const wrapper = mountCirculationPage();
            await flushPromises();
            await wrapper.vm.loadBorrower('B-101');
            await wrapper.vm.handleItemScanned('.I-X');
            expect(useNotification().notifications.value.at(-1).message).toBe('Network down');
        });

        it('does not crash when checkout returns no transaction', async () => {
            mockBorrowerRequests();
            vi.spyOn(apiClient, 'post').mockResolvedValue({ transactions: [] });
            const wrapper = mountCirculationPage();
            await flushPromises();
            await wrapper.vm.loadBorrower('B-101');
            await wrapper.vm.handleItemScanned('.I-X');
            expect(wrapper.vm.scannedItems).toEqual([]);
            expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));
        });

        it('keeps a successful checkout when borrower reload fails', async () => {
            const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
                if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
                if (endpoint === '/borrowers/B-101') {
                    if (get.mock.calls.filter(([url]) => url === endpoint).length > 1) throw new Error('reload failed');
                    return { ...borrower };
                }
                if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
                if (endpoint === '/holds/borrower/1') return [];
                throw new Error(`Unexpected GET request: ${endpoint}`);
            });
            vi.spyOn(apiClient, 'post').mockResolvedValue({ transactions: [{ item_id: 'I-X', title: 'Book' }] });
            const wrapper = mountCirculationPage();
            await flushPromises();
            await wrapper.vm.loadBorrower('B-101');
            await wrapper.vm.handleItemScanned('.I-X');
            expect(wrapper.vm.scannedItems).toHaveLength(1);
        });
    });

    it('handles return network errors, missing metadata, and hold expiry', async () => {
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ items: [{ item_id: 'I-X', hold_ready: { borrower_name: 'A', expires_at: '2030-02-01' } }] });
        const wrapper = mountCirculationPage('return');
        await flushPromises();
        await wrapper.vm.handleItemScanned('.I-X');
        expect(wrapper.vm.scannedItems[0]).toEqual(expect.objectContaining({ title: 'Unknown', shelf_location: undefined }));
        expect(useNotification().notifications.value).toEqual([expect.objectContaining({ type: 'warning' })]);
        post.mockRejectedValueOnce(new Error('network'));
        await wrapper.vm.handleItemScanned('.I-Y');
        expect(useNotification().notifications.value.at(-1).message).toBe('network');
    });

    it('handles empty renewals and renewal API failures', async () => {
        mockBorrowerRequests();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ renewed: [], failed: [] });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');
        await wrapper.vm.renewAll();
        expect(post).toHaveBeenCalled();
        post.mockRejectedValueOnce(new Error('renew failed'));
        await wrapper.vm.renewAll();
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));
    });

    it('handles hold action failures and array item responses', async () => {
        mockBorrowerRequests();
        const get = apiClient.get;
        get.mockImplementation(async endpoint => endpoint.includes('/catalog/') ? [{ item_id: 'I-X', status: 'available' }] : endpoint === '/admin/settings' ? { borrower_barcode_prefix: '%', item_barcode_prefix: '.' } : endpoint === '/borrowers/B-101' ? { ...borrower } : endpoint.includes('/items') ? { loans: [] } : []);
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ transactions: [] });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');
        await wrapper.vm.checkoutHold({ bibliographic_record_id: 1, title: 'Book' });
        expect(post).toHaveBeenCalledWith('/circulation/checkout', expect.anything());
        vi.spyOn(apiClient, 'delete').mockRejectedValue(new Error('cancel failed'));
        await wrapper.vm.cancelHold('H-X');
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));
    });

    it('reports a reservation lookup failure and quick-return failures', async () => {
        mockBorrowerRequests();
        const get = apiClient.get;
        get.mockImplementation(async endpoint => {
            if (endpoint.includes('/catalog/')) throw new Error('catalog offline');
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return { ...borrower };
            if (endpoint.includes('/items')) return { loans: [] };
            return [];
        });
        const post = vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('return offline'));
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.checkoutHold({ bibliographic_record_id: 1, title: 'Book' });
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));
        await wrapper.vm.quickReturn('I-X');
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));

        post.mockResolvedValueOnce({ items: [{ item_id: 'I-X' }] });
        await wrapper.vm.quickReturn('I-X');
        expect(useNotification().notifications.value.at(-1).message).toContain('I-X');
        expect(useNotification().notifications.value.at(-1).message).toContain('circulation.ranger');
    });

    it('handles a borrower reload failure after quick-return', async () => {
        let borrowerLoads = 0;
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') {
                borrowerLoads += 1;
                if (borrowerLoads > 1) throw new Error('borrower reload offline');
                return { ...borrower };
            }
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') return [];
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        vi.spyOn(apiClient, 'post').mockResolvedValue({ items: [{ item_id: 'I-X', title: 'Book' }] });
        const emit = vi.spyOn(events, 'emit');
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');
        await wrapper.vm.quickReturn('I-X');
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));
        expect(emit).toHaveBeenCalledWith('circulation:roster-refresh');
    });

    it('keeps the page usable when cancelling a hold cannot reload reservations', async () => {
        useAppState().clearStorage();
        let holdLoads = 0;
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return { ...borrower };
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') {
                holdLoads += 1;
                if (holdLoads > 1) throw new Error('holds reload offline');
                return [{ id: 'H-1' }];
            }
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await expect(wrapper.vm.cancelHold('H-1')).resolves.toBeUndefined();

        expect(remove).toHaveBeenCalledWith('/holds/H-1');
        expect(wrapper.vm.borrower).toEqual(expect.objectContaining({ borrower_id: 'B-101' }));
        expect(useNotification().notifications.value).toEqual(expect.arrayContaining([
            expect.objectContaining({ type: 'success', message: 'holds.hold_cancelled' }),
            expect.objectContaining({ type: 'error' })
        ]));
        expect(get).toHaveBeenCalledWith('/holds/borrower/1');
    });

    it('handles checkout-hold failures and a failed borrower reload after success', async () => {
        useAppState().clearStorage();
        let borrowerLoads = 0;
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') {
                borrowerLoads += 1;
                if (borrowerLoads > 1) throw new Error('borrower reload offline');
                return { ...borrower };
            }
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') return [];
            if (endpoint === '/catalog/bibliographic/20/items') return { items: [{ item_id: 'I-20', status: 'available' }] };
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const post = vi.spyOn(apiClient, 'post')
            .mockRejectedValueOnce(new Error('checkout offline'))
            .mockResolvedValueOnce({});
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.checkoutHold({ bibliographic_record_id: 20, title: 'Book' });
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));

        await wrapper.vm.checkoutHold({ bibliographic_record_id: 20, title: 'Book' });
        expect(post).toHaveBeenNthCalledWith(2, '/circulation/checkout', expect.objectContaining({ item_ids: ['I-20'] }));
        expect(get).toHaveBeenCalledWith('/borrowers/B-101');
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));
    });

    it.each([
        {},
        { transactions: undefined }
    ])('reports a checkout response without transactions instead of crashing: %o', async response => {
        useAppState().clearStorage();
        mockBorrowerRequests();
        vi.spyOn(apiClient, 'post').mockResolvedValue(response);
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await expect(wrapper.vm.handleItemScanned('.I-invalid')).resolves.toBeUndefined();
        expect(wrapper.vm.scannedItems).toEqual([]);
        expect(useNotification().notifications.value.at(-1)).toEqual(expect.objectContaining({ type: 'error' }));
    });

    it('quick-returns with a borrower-id hold fallback, empty items, and reservation reload failure', async () => {
        useAppState().clearStorage();
        let holdLoads = 0;
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return { ...borrower };
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') {
                holdLoads += 1;
                if (holdLoads > 1) throw new Error('holds unavailable after return');
                return [];
            }
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const post = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
            items: [{ item_id: 'I-21', title: 'Book', hold_ready: { borrower_name: 'Noémie', borrower_id: 'B-202' } }]
        }).mockResolvedValueOnce({ items: [] });
        const emit = vi.spyOn(events, 'emit');
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.quickReturn('I-21');
        await wrapper.vm.quickReturn('I-22');

        expect(post).toHaveBeenNthCalledWith(2, '/circulation/return', expect.objectContaining({ item_ids: ['I-22'] }));
        expect(useNotification().notifications.value).toEqual(expect.arrayContaining([
            expect.objectContaining({ type: 'warning', message: 'circulation.hold_ready_message' }),
            expect.objectContaining({ type: 'success' })
        ]));
        expect(wrapper.vm.borrower).toBeTruthy();
        expect(emit).toHaveBeenCalledTimes(2);
        expect(emit).toHaveBeenCalledWith('circulation:roster-refresh');
        expect(get).toHaveBeenCalledWith('/holds/borrower/1');
    });

    it('removes a scanned item by either identifier without removing the others', () => {
        const wrapper = mountCirculationPage('return');
        wrapper.vm.scannedItems = [
            { item_id: 'I-1', barcode: '.I-1' },
            { item_id: 'I-2', barcode: '.I-2' },
            { item_id: 'I-3', barcode: '.I-3' }
        ];

        wrapper.vm.removeItem('.I-2');
        expect(wrapper.vm.scannedItems.map(item => item.item_id)).toEqual(['I-1', 'I-3']);
        wrapper.vm.removeItem('I-1');
        expect(wrapper.vm.scannedItems).toEqual([{ item_id: 'I-3', barcode: '.I-3' }]);
    });

    it('uses raw barcodes when settings have no configured prefixes', async () => {
        useAppState().clearStorage();
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return {};
            if (endpoint === '/borrowers/B-101' || endpoint === '/borrowers/.B-101') return { ...borrower };
            if (endpoint === '/circulation/borrower/B-101/items' || endpoint === '/circulation/borrower/.B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') return [];
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ transactions: [{ item_id: '.I-30', title: 'Book' }] });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('.B-101');
        await wrapper.vm.handleItemScanned('.I-30');

        expect(get).toHaveBeenCalledWith('/borrowers/.B-101');
        expect(post).toHaveBeenCalledWith('/circulation/checkout', expect.objectContaining({ item_ids: ['.I-30'] }));
        expect(wrapper.vm.scannerDisabled).toBe(false);
    });

    it('keeps the scanner disabled when settings cannot be loaded', async () => {
        useAppState().clearStorage();
        const get = vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('settings offline'));
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const wrapper = mountCirculationPage();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/settings', {}, { skipGlobalLoading: true });
        expect(wrapper.vm.settings).toEqual({ borrower_barcode_prefix: '%', item_barcode_prefix: '.' });
        expect(wrapper.vm.scannerDisabled).toBe(true);
        expect(consoleSpy).toHaveBeenCalled();
    });

    it.each([
        undefined,
        [],
        [{ item_id: 'I-40', was_overdue: false }]
    ])('handles a partially invalid return response: %o', async items => {
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ items });
        const wrapper = mountCirculationPage('return');
        await flushPromises();
        await expect(wrapper.vm.handleItemScanned('.I-40')).resolves.toBeUndefined();

        expect(wrapper.vm.scannedItems).toEqual(items?.length ? [expect.objectContaining({
            item_id: 'I-40', title: 'Unknown', call_number: undefined,
            shelf_location: undefined, hold_ready: undefined
        })] : []);
        expect(post).toHaveBeenCalledWith('/circulation/return', expect.any(Object));
    });

    it('reports the borrower as at its loan limit', async () => {
        const atLimit = { ...borrower, current_loans_count: 3, loan_limit: 3 };
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return atLimit;
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [] };
            if (endpoint === '/holds/borrower/1') return [];
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const wrapper = mountCirculationPage();
        await flushPromises();

        await wrapper.vm.loadBorrower('B-101');

        expect(get).toHaveBeenCalledWith('/borrowers/B-101');
        expect(wrapper.vm.borrowerAtLimit).toBe(true);
    });

    it('keeps two simultaneous circulation actions independent', async () => {
        mockBorrowerRequests();
        const pending = [];
        const post = vi.spyOn(apiClient, 'post').mockImplementation((endpoint, payload) => {
            if (endpoint !== '/circulation/checkout') return Promise.resolve({});
            return new Promise(resolve => pending.push(() => resolve({
                transactions: [{ item_id: payload.item_ids[0], title: payload.item_ids[0] }]
            })));
        });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        const first = wrapper.vm.handleItemScanned('.I-501');
        const second = wrapper.vm.handleItemScanned('.I-502');
        await flushPromises();

        expect(post).toHaveBeenCalledTimes(2);
        pending[1]();
        pending[0]();
        await Promise.all([first, second]);

        expect(wrapper.vm.scannedItems.map(item => item.item_id).sort()).toEqual(['I-501', 'I-502']);
    });

    it('covers missing optional borrower and transaction fields safely', async () => {
        useAppState().clearStorage();
        const minimalBorrower = { id: 1, borrower_id: 'B-101', current_loans_count: 0, loan_limit: 3 };
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return {};
            if (endpoint === '/borrowers/B-101') return { ...minimalBorrower };
            if (endpoint === '/circulation/borrower/B-101/items') return {};
            if (endpoint === '/holds/borrower/1') return null;
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ transactions: [{ item_id: 'I-700' }] });
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        expect(wrapper.vm.borrowerInitials).toBe('');
        expect(wrapper.vm.borrowerAtLimit).toBe(false);
        await wrapper.vm.handleItemScanned('I-700');

        expect(wrapper.vm.scannedItems[0]).toEqual(expect.objectContaining({
            item_id: 'I-700', title: 'Unknown'
        }));
        expect(get).toHaveBeenCalledWith('/circulation/borrower/B-101/items');
        expect(post).toHaveBeenCalledWith('/circulation/checkout', expect.objectContaining({ item_ids: ['I-700'] }));
    });

    it('uses barcode fallbacks for incomplete error details and empty messages', async () => {
        mockBorrowerRequests();
        const post = vi.spyOn(apiClient, 'post')
            .mockRejectedValueOnce(new ApiError(ERROR_CODES.ITEM_NOT_AVAILABLE, 'unavailable', { status: 'mystery' }, 400))
            .mockRejectedValueOnce(new Error());
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        await wrapper.vm.handleItemScanned('.I-701');
        expect(useNotification().notifications.value.at(-1).message).toBe('errors.item_not_available');
        await wrapper.vm.handleItemScanned('.I-702');
        expect(useNotification().notifications.value.at(-1).message).toBe('circulation.error_checkout_failed');
        expect(post).toHaveBeenCalledTimes(2);
    });

    it('handles no borrower actions and malformed hold item responses', async () => {
        const wrapper = mountCirculationPage();
        await flushPromises();
        await wrapper.vm.renewAll();
        vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        await wrapper.vm.cancelHold('H-empty');
        expect(wrapper.vm.borrower).toBe(null);

        mockBorrowerRequests();
        const get = apiClient.get;
        get.mockImplementation(async endpoint => {
            if (endpoint.includes('/catalog/')) return { items: null };
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return { ...borrower };
            if (endpoint.includes('/items')) return { loans: [] };
            return [];
        });
        const second = mountCirculationPage();
        await flushPromises();
        await second.vm.loadBorrower('B-101');
        await second.vm.checkoutHold({ bibliographic_record_id: 7, title: 'Unavailable' });
        expect(useNotification().notifications.value.at(-1)).toEqual(
            expect.objectContaining({ type: 'error', message: 'holds.no_available_item' })
        );
    });

    it('processes scans through the real ItemScanner and quick returns through BorrowerCard DOM', async () => {
        useAppState().clearStorage();
        const currentLoan = {
            item_id: 'I-600',
            bibliographic_record_id: 60,
            title: 'Loaned book',
            due_date: '2030-01-01'
        };
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { borrower_barcode_prefix: '%', item_barcode_prefix: '.' };
            if (endpoint === '/borrowers/B-101') return { ...borrower, current_loans: [currentLoan] };
            if (endpoint === '/circulation/borrower/B-101/items') return { loans: [currentLoan] };
            if (endpoint === '/holds/borrower/1') return [];
            if (endpoint === '/catalog/bibliographic/search') return { items: [] };
            throw new Error(`Unexpected GET request: ${endpoint}`);
        });
        const post = vi.spyOn(apiClient, 'post').mockImplementation(async endpoint => {
            if (endpoint === '/circulation/checkout') {
                return { transactions: [{ item_id: 'I-601', title: 'Scanned book' }] };
            }
            return { items: [{ item_id: 'I-600', title: 'Loaned book' }] };
        });
        const wrapper = mountRealCirculationPage();
        await flushPromises();
        await wrapper.vm.loadBorrower('B-101');

        const scanner = wrapper.findComponent({ name: 'ItemScanner' });
        expect(scanner.exists()).toBe(true);
        scanner.vm.itemBarcode = '.I-601';
        await scanner.find('form').trigger('submit');
        await flushPromises();

        expect(post).toHaveBeenCalledWith('/circulation/checkout', {
            borrower_id: 'B-101', item_ids: ['I-601'], checked_out_by: 'web-ui'
        });
        expect(wrapper.findComponent({ name: 'BorrowerCard' }).exists()).toBe(true);

        const returnButton = wrapper.findComponent({ name: 'BorrowerCard' }).find('button.btn-outline-primary');
        await returnButton.trigger('click');
        await flushPromises();

        expect(post).toHaveBeenCalledWith('/circulation/return', {
            item_ids: ['I-600'], returned_by: 'web-ui'
        });
        expect(get).toHaveBeenCalledWith('/borrowers/B-101');
        wrapper.unmount();
    });
});
