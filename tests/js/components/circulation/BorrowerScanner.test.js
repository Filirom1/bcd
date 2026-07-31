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

        expect(wrapper.emitted('borrower-loaded')).toEqual([['B-42'], ['B-43']]);
        expect(wrapper.vm.borrowerId).toBe('');
    });
});
