import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import { makeBorrower } from '../../fixtures/borrowers.js';
import { jsonResponse } from '../../helpers/http.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';
import { ApiError, ERROR_CODES } from '../../../../src/bcd_web_vue/js/models/error.js';
import CirculationPage from '../../../../src/bcd_web_vue/js/pages/CirculationPage.js';

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
});
