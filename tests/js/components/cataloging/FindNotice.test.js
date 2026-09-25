import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import FindNotice from '../../../../src/bcd_web_vue/js/components/cataloging/FindNotice.js';

function mountLookup() {
    return mount(FindNotice, {
        global: { mocks: { $t: key => key } }
    });
}

const localMiss = (inputType = 'isbn', sources = ['bnf', 'google_books']) => ({
    items: [], total: 0, input_type: inputType,
    identifier_type: inputType === 'isbn' ? 'isbn' : 'issn',
    external_sources: sources
});

afterEach(() => vi.restoreAllMocks());

describe('FindNotice', () => {
    it('normalizes identifiers and classifies unsupported press barcodes', () => {
        const wrapper = mountLookup();

        expect(wrapper.vm.normalizeISBN('978-2 1234-5678-9')).toBe('9782123456789');
        expect(wrapper.vm.normalizeISBN('17629330')).toBe('1762-9330');
        expect(wrapper.vm.classifyInput('3780237306003').kind).toBe('unsupported_barcode');
        expect(wrapper.vm.classifyInput('9771144165005')).toMatchObject({
            kind: 'ean977', identifierType: 'issn', sources: ['sudoc']
        });
    });

    it('shows a local notice without calling an external source', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            items: [{ notice_id: 4, title: 'Wapiti', identifier: '0984-2314', copies: 12 }],
            total: 1,
            input_type: 'text',
            external_sources: []
        });
        const post = vi.spyOn(apiClient, 'post');
        const wrapper = mountLookup();
        wrapper.vm.query = 'Wapiti';

        await wrapper.vm.search();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/notices/search', {
            q: 'Wapiti', limit: 20, offset: 0
        }, { skipGlobalLoading: true });
        expect(post).not.toHaveBeenCalled();
        expect(wrapper.vm.localResults[0].title).toBe('Wapiti');
    });

    it('searches for Wapiti after an unsupported press barcode', async () => {
        const get = vi.spyOn(apiClient, 'get')
            .mockResolvedValueOnce({ items: [], total: 0, input_type: 'unsupported_barcode', external_sources: [] })
            .mockResolvedValueOnce({ items: [{ notice_id: 7, title: 'Wapiti' }], total: 1, input_type: 'text', external_sources: [] });
        const wrapper = mountLookup();
        wrapper.vm.query = '3780237306003';

        await wrapper.vm.search();
        await flushPromises();
        expect(wrapper.emitted('unsupported-barcode')).toEqual([[{ barcode: '3780237306003' }]]);

        wrapper.vm.titleQuery = 'Wapiti';
        await wrapper.vm.searchTitle();
        await flushPromises();

        expect(get).toHaveBeenLastCalledWith('/catalog/notices/search', {
            q: 'Wapiti', limit: 20, offset: 0
        }, { skipGlobalLoading: true });
        expect(wrapper.vm.localResults[0].title).toBe('Wapiti');
    });

    it('uses BnF then Google Books for an ISBN and never SUDOC', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue(localMiss());
        const post = vi.spyOn(apiClient, 'post')
            .mockResolvedValueOnce({ status: 'not_found', source: 'bnf' })
            .mockResolvedValueOnce({ status: 'found', source: 'google_books', data: { title: 'Book' } });
        const wrapper = mountLookup();
        wrapper.vm.query = '9782123456789';

        await wrapper.vm.search();
        await flushPromises();

        expect(post.mock.calls.map(call => call[1].source)).toEqual(['bnf', 'google_books']);
        expect(post.mock.calls.map(call => call[1].source)).not.toContain('sudoc');
        expect(wrapper.emitted('lookup-success')).toEqual([[{ title: 'Book' }]]);
    });

    it('uses SUDOC only for an ISSN and for a derived EAN-977 ISSN', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValueOnce(localMiss('issn', ['sudoc']))
            .mockResolvedValueOnce(localMiss('ean977', ['sudoc']));
        const post = vi.spyOn(apiClient, 'post')
            .mockResolvedValueOnce({ status: 'not_found', source: 'sudoc' })
            .mockResolvedValueOnce({ status: 'not_found', source: 'sudoc' });
        const wrapper = mountLookup();

        wrapper.vm.query = '1163-7706';
        await wrapper.vm.search();
        await flushPromises();
        wrapper.vm.query = '9771144165005';
        await wrapper.vm.search();
        await flushPromises();

        expect(post.mock.calls).toHaveLength(2);
        expect(post.mock.calls.every(call => call[1].source === 'sudoc')).toBe(true);
    });

    it('continues to the next enabled source when the first source is disabled', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue(localMiss());
        const post = vi.spyOn(apiClient, 'post')
            .mockResolvedValueOnce({ status: 'disabled', source: 'bnf' })
            .mockResolvedValueOnce({ status: 'not_found', source: 'google_books' });
        const wrapper = mountLookup();
        wrapper.vm.query = '9782123456789';

        await wrapper.vm.search();
        await flushPromises();

        expect(post.mock.calls.map(call => call[1].source)).toEqual(['bnf', 'google_books']);
    });

    it('always exposes manual entry and preserves the scanned value', () => {
        const wrapper = mountLookup();
        wrapper.vm.query = '3780237306003';

        wrapper.vm.switchToManualEntry();

        expect(wrapper.emitted('manual-entry')).toEqual([[
            expect.objectContaining({
                value: '3780237306003', originalInput: '3780237306003'
            })
        ]]);
    });
});
