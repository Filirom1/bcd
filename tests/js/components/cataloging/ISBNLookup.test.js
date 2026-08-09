import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import ISBNLookup from '../../../../src/bcd_web_vue/js/components/cataloging/ISBNLookup.js';

function mountLookup() {
    return mount(ISBNLookup, {
        global: { mocks: { $t: key => key } }
    });
}

afterEach(() => vi.restoreAllMocks());

describe('ISBNLookup', () => {
    it('normalizes ISBN, ISSN, and kiosk EAN values', () => {
        const wrapper = mountLookup();

        expect(wrapper.vm.normalizeISBN('978-2 1234-5678-9')).toBe('9782123456789');
        expect(wrapper.vm.normalizeISBN('17629330')).toBe('1762-9330');
        expect(wrapper.vm.normalizeISBN('1762-933x')).toBe('1762-933X');
        expect(wrapper.vm.normalizeISBN('9771234567890')).toBe('9771234567890');
    });

    it('emits lookup success after local search finds no existing record', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ items: [] });
        vi.spyOn(apiClient, 'post').mockResolvedValue({ title: 'New book', isbn: '9782123456789' });
        const wrapper = mountLookup();
        wrapper.vm.isbn = '978-2-1234-5678-9';

        await wrapper.vm.lookupISBN();

        expect(get).toHaveBeenCalledWith('/catalog/bibliographic/search', {
            q: '9782123456789', limit: 1
        });
        expect(wrapper.emitted('lookup-success')).toEqual([[{
            title: 'New book', isbn: '9782123456789'
        }]]);
    });

    it('emits manual-entry with the current value', () => {
        const wrapper = mountLookup();
        wrapper.vm.isbn = '978-2-1234-5678-9';

        wrapper.vm.switchToManualEntry();

        expect(wrapper.emitted('manual-entry')).toEqual([['978-2-1234-5678-9']]);
    });

    it('emits lookup-not-found for a missing external record', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue({ items: [] });
        vi.spyOn(apiClient, 'post').mockRejectedValue({ statusCode: 404 });
        const wrapper = mountLookup();
        wrapper.vm.isbn = '9782123456789';

        await wrapper.vm.lookupISBN();

        expect(wrapper.emitted('lookup-not-found')).toEqual([['9782123456789']]);
    });

    it('emits existing-record-found when the local catalog already contains the ISBN', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue({ items: [{ record_id: 4, title: 'Existing' }] });
        const post = vi.spyOn(apiClient, 'post');
        const wrapper = mountLookup();
        wrapper.vm.isbn = '9782123456789';

        await wrapper.vm.lookupISBN();

        expect(wrapper.emitted('existing-record-found')).toEqual([[{ record_id: 4, title: 'Existing' }]]);
        expect(post).not.toHaveBeenCalled();
    });
});
