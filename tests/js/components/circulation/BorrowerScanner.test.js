import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import { AutocompleteInputStub } from '../../helpers/stubs.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import BorrowerScanner from '../../../../src/bcd_web_vue/js/components/circulation/BorrowerScanner.js';

afterEach(() => vi.restoreAllMocks());

describe('BorrowerScanner', () => {
    it('queries borrowers with the input and forwards the AbortSignal', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ items: [{ borrower_id: 'B-1' }] });
        const wrapper = mount(BorrowerScanner, {
            props: { mode: 'checkout' },
            global: { stubs: { AutocompleteInput: AutocompleteInputStub } }
        });
        const signal = new AbortController().signal;

        await expect(wrapper.vm.fetchBorrowers('Amira', signal)).resolves.toEqual([{ borrower_id: 'B-1' }]);
        expect(get).toHaveBeenCalledWith('/borrowers', { q: 'Amira', limit: 10 }, { signal });
    });

    it('emits the borrower id for manual and autocomplete selection', async () => {
        const wrapper = mount(BorrowerScanner, {
            props: { mode: 'checkout' },
            global: { stubs: { AutocompleteInput: AutocompleteInputStub } }
        });

        wrapper.vm.handleSubmit('  B-42  ');
        wrapper.vm.handleBorrowerSelect({ borrower_id: 'B-43' });
        wrapper.vm.handleSubmit('   ');

        expect(wrapper.emitted('borrower-loaded')).toEqual([['B-42'], ['B-43']]);
        expect(wrapper.vm.borrowerId).toBe('');
    });

    it('normalizes API collections, formats blocked and overdue badges, and forwards errors', async () => {
        const wrapper = mount(BorrowerScanner, {
            props: { mode: 'return' },
            global: { stubs: { AutocompleteInput: AutocompleteInputStub } }
        });
        const signal = new AbortController().signal;
        vi.spyOn(apiClient, 'get').mockResolvedValue({ data: [{ borrower_id: 'B-1' }] });
        await expect(wrapper.vm.fetchBorrowers('B', signal)).resolves.toEqual([{ borrower_id: 'B-1' }]);

        const html = wrapper.vm.formatBorrowerResult({
            borrower_id: 'B-1', first_name: 'A', last_name: 'B', blocked: true, has_overdue: true
        });
        expect(html).toContain('circulation.status_blocked');
        expect(html).toContain('common.overdue');
        expect(wrapper.vm.formatBorrowerResult({
            borrower_id: 'B-2', first_name: 'C', last_name: 'D', class_name: '', current_loans_count: 0, loan_limit: 3
        })).toContain('common.not_available');

        const error = new Error('offline');
        vi.mocked(apiClient.get).mockRejectedValue(error);
        await expect(wrapper.vm.fetchBorrowers('B', signal)).rejects.toBe(error);
    });
});
