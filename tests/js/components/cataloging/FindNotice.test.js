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
    identifier_type: inputType === 'isbn' ? 'isbn' : inputType === 'issn' ? 'issn' : null,
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
        expect(wrapper.vm.classifyInput('Le Petit Prince')).toMatchObject({
            kind: 'text', sources: ['bnf', 'google_books', 'sudoc']
        });
    });

    it('prefills the lookup field from restored route state', () => {
        const wrapper = mount(FindNotice, {
            props: { initialQuery: 'Le Petit Prince' },
            global: { mocks: { $t: key => key } }
        });

        expect(wrapper.vm.query).toBe('Le Petit Prince');
    });

    it('can refocus the lookup field after returning to cataloging', async () => {
        const wrapper = mount(FindNotice, {
            attachTo: document.body,
            global: { mocks: { $t: key => key } }
        });
        await wrapper.vm.focusQuery();

        expect(document.activeElement).toBe(wrapper.find('input').element);
        wrapper.unmount();
    });

    it('shows local and remote text results in separate lists', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            items: [{
                notice_id: 4,
                title: 'Wapiti',
                identifier_type: 'isbn',
                identifier: '9781234567897',
                isbn: '9781234567897',
                cover_image: 'local-wapiti.jpg',
                copies: 12
            }],
            total: 1,
            input_type: 'text',
            external_sources: ['bnf', 'google_books', 'sudoc']
        });
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            status: 'results',
            source: 'bnf',
            items: [{
                title: 'Wapiti nouvelle édition',
                _source: 'bnf',
                cover_url: 'https://books.example/wapiti.jpg'
            }],
            total: 1
        });
        const wrapper = mountLookup();
        wrapper.vm.query = 'Wapiti';

        await wrapper.vm.search();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/notices/search', {
            q: 'Wapiti', limit: 20, offset: 0
        }, { skipGlobalLoading: true });
        expect(post.mock.calls.map(call => call[1].source)).toEqual(['bnf']);
        expect(wrapper.vm.localResults[0].title).toBe('Wapiti');
        expect(wrapper.vm.remoteResults[0].title).toBe('Wapiti nouvelle édition');
        expect(wrapper.find('[data-testid="local-notice-results"]').text()).toContain('Wapiti');
        expect(wrapper.find('[data-testid="local-notice-results"]').text())
            .not.toContain('Wapiti nouvelle édition');
        expect(wrapper.find('[data-testid="remote-candidates"]').text())
            .toContain('Wapiti nouvelle édition');
        expect(wrapper.find('[data-testid="local-notice-results"] img').attributes('src'))
            .toBe('/covers/local-wapiti.jpg');
        expect(wrapper.find('[data-testid="remote-candidates"] img').attributes('src'))
            .toBe('https://books.example/wapiti.jpg');
    });

    it('runs the identifier lookup on Enter from the scanner field', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            items: [], total: 0, input_type: 'unsupported_barcode', external_sources: []
        });
        const wrapper = mountLookup();
        wrapper.vm.query = '3780237306003';

        await wrapper.get('#notice-search-input').trigger('keydown.enter');
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/notices/search', {
            q: '3780237306003', limit: 20, offset: 0
        }, { skipGlobalLoading: true });
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

    it('runs the title search on Enter', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            items: [], total: 0, input_type: 'text', external_sources: []
        });
        const wrapper = mountLookup();
        wrapper.vm.query = '3780237306003';
        wrapper.vm.classification = wrapper.vm.classifyInput(wrapper.vm.query);
        wrapper.vm.titleQuery = 'Wapiti';
        await wrapper.vm.$nextTick();

        await wrapper.get('#title-search-input').trigger('keydown.enter');
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/catalog/notices/search', {
            q: 'Wapiti', limit: 20, offset: 0
        }, { skipGlobalLoading: true });
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

    it('keeps text candidates selectable and lets the librarian start the next source', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue(
            localMiss('text', ['bnf', 'google_books', 'sudoc'])
        );
        const post = vi.spyOn(apiClient, 'post')
            .mockResolvedValueOnce({
                status: 'results',
                source: 'bnf',
                items: [{ title: 'Le Petit Prince', _source: 'bnf' }],
                total: 1
            })
            .mockResolvedValueOnce({
                status: 'results',
                source: 'google_books',
                items: [{
                    title: 'Le Petit Prince illustré',
                    cover_url: 'https://books.example/cover.jpg'
                }],
                total: 1
            });
        const wrapper = mountLookup();
        wrapper.vm.query = 'Le Petit Prince';

        await wrapper.vm.search();
        await flushPromises();
        expect(post.mock.calls.map(call => call[1].source)).toEqual(['bnf']);
        expect(wrapper.vm.remoteResults).toHaveLength(1);
        expect(wrapper.vm.sourceStates[0].status).toBe('found');
        expect(wrapper.find('[data-testid="remote-candidates"]').exists()).toBe(true);

        wrapper.vm.startSource(1);
        await flushPromises();

        expect(post.mock.calls.map(call => call[1].source)).toEqual(['bnf', 'google_books']);
        expect(wrapper.vm.remoteResults).toHaveLength(2);
        expect(wrapper.find('[data-testid="remote-candidates"] img').attributes('src'))
            .toBe('https://books.example/cover.jpg');

        wrapper.vm.selectCandidate(wrapper.vm.remoteResults[0]);
        expect(wrapper.emitted('lookup-success')).toEqual([
            [{ title: 'Le Petit Prince', _source: 'bnf' }]
        ]);
    });

    it('offers manual entry after every text provider returns no candidates', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue(
            localMiss('text', ['bnf', 'google_books', 'sudoc'])
        );
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            status: 'not_found',
            items: []
        });
        const wrapper = mountLookup();
        wrapper.vm.query = 'Le Petit Prince';

        await wrapper.vm.search();
        await flushPromises();

        expect(post.mock.calls.map(call => call[1].source)).toEqual([
            'bnf', 'google_books', 'sudoc'
        ]);
        expect(wrapper.emitted('lookup-not-found')).toEqual([[
            expect.objectContaining({
                value: 'Le Petit Prince',
                inputType: 'text',
                title: 'Le Petit Prince'
            })
        ]]);
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
