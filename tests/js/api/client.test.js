import { afterEach, describe, expect, it, vi } from 'vitest';

import { jsonResponse } from '../helpers/http.js';
import { ApiClient } from '../../../src/bcd_web_vue/js/api/client.js';
import { ApiError, ERROR_CODES } from '../../../src/bcd_web_vue/js/models/error.js';

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('ApiClient', () => {
    it('serializes query parameters and sends the active locale', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [] }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient('/api/v1', { getLocale: () => 'en' });

        await client.get('/catalog', { query: 'Le petit prince', page: 2, empty: null });

        const [url, options] = fetchMock.mock.calls[0];
        const parsedUrl = new URL(url);
        expect(parsedUrl.pathname).toBe('/api/v1/catalog');
        expect(parsedUrl.searchParams.get('query')).toBe('Le petit prince');
        expect(parsedUrl.searchParams.get('page')).toBe('2');
        expect(parsedUrl.searchParams.has('empty')).toBe(false);
        expect(options.method).toBe('GET');
        expect(options.headers.get('Accept-Language')).toBe('en');
        expect(options.headers.get('Accept')).toBe('application/json');
    });

    it('forwards request options such as AbortSignal to fetch', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [] }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient();
        const controller = new AbortController();

        await client.get('/catalog/search', { q: 'harry' }, { signal: controller.signal });

        expect(fetchMock).toHaveBeenCalledWith(
            expect.any(String),
            expect.objectContaining({ method: 'GET', signal: controller.signal })
        );
    });

    it('sends JSON bodies for write requests', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 42 }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient();

        await expect(client.post('/classes', { name: 'CM1' })).resolves.toEqual({ id: 42 });

        const [, options] = fetchMock.mock.calls[0];
        expect(options.method).toBe('POST');
        expect(options.body).toBe('{"name":"CM1"}');
        expect(options.headers.get('Content-Type')).toBe('application/json');
    });

    it('does not override the multipart content type for FormData', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ imported: 1 }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient();
        const formData = new FormData();
        formData.append('file', new Blob(['id,name\n1,Amira']), 'borrowers.csv');

        await client.post('/borrowers/import', formData);

        const [, options] = fetchMock.mock.calls[0];
        expect(options.body).toBe(formData);
        expect(options.headers.has('Content-Type')).toBe(false);
    });

    it('returns null for a 204 response', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
        const client = new ApiClient();

        await expect(client.delete('/holds/12')).resolves.toBeNull();
    });

    it('converts an API error response to ApiError', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({
            error_code: 'ITEM_NOT_FOUND',
            detail: 'Item missing',
            context: { item_id: 'BC-42' }
        }, { status: 404 })));
        const client = new ApiClient();

        await expect(client.get('/catalog/items/BC-42')).rejects.toMatchObject({
            name: 'ApiError',
            code: ERROR_CODES.ITEM_NOT_FOUND,
            message: 'Item missing',
            details: { item_id: 'BC-42' },
            statusCode: 404
        });
    });

    it('converts a network failure to a consistent ApiError', async () => {
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
        const client = new ApiClient();

        await expect(client.get('/catalog')).rejects.toMatchObject({
            name: 'ApiError',
            code: ERROR_CODES.NETWORK_ERROR,
            statusCode: 0,
            details: { originalError: 'Failed to fetch' }
        });
    });

    it('does not wrap AbortError and throws the original AbortError', async () => {
        const abortError = new DOMException('The user aborted a request.', 'AbortError');
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abortError));
        const client = new ApiClient();

        await expect(client.get('/catalog')).rejects.toBe(abortError);
    });

    it('keeps global loading active until concurrent requests have all completed', async () => {
        const loadingStates = [];
        let resolveFirst;
        let resolveSecond;
        const fetchMock = vi.fn()
            .mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve; }))
            .mockImplementationOnce(() => new Promise(resolve => { resolveSecond = resolve; }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient('/api/v1', {
            onLoadingChange: isLoading => loadingStates.push(isLoading)
        });

        const firstRequest = client.get('/first');
        const secondRequest = client.get('/second');
        resolveFirst(jsonResponse({ first: true }));
        await firstRequest;
        resolveSecond(jsonResponse({ second: true }));
        await secondRequest;

        expect(loadingStates).toEqual([true, true, true, false]);
        expect(client.activeRequests).toBe(0);
    });

    it('preserves an already normalized ApiError', async () => {
        const apiError = new ApiError(ERROR_CODES.VALIDATION_ERROR, 'Invalid input', {}, 422);
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(apiError));
        const client = new ApiClient();

        await expect(client.get('/catalog')).rejects.toBe(apiError);
    });

    it('supports blob responseType', async () => {
        const mockBlob = new Blob(['csv data'], { type: 'text/csv' });
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            blob: async () => mockBlob
        });
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient();

        const result = await client.get('/export', {}, { responseType: 'blob' });
        expect(result).toBe(mockBlob);
    });

    it('supports text responseType', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            text: async () => 'raw text'
        });
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient();

        const result = await client.get('/help/file', {}, { responseType: 'text' });
        expect(result).toBe('raw text');
    });

    it('supports skipping global loading state', async () => {
        const loadingStates = [];
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient('/api/v1', {
            onLoadingChange: isLoading => loadingStates.push(isLoading)
        });

        await client.get('/silent', {}, { skipGlobalLoading: true });

        expect(loadingStates).toHaveLength(0);
        expect(client.activeRequests).toBe(0);
    });

    it('merges custom headers with default headers', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient();

        await client.get('/headers', {}, {
            headers: {
                'X-Custom-Header': 'CustomValue',
                'Accept': 'text/plain' // overrides default Accept
            }
        });

        const [, options] = fetchMock.mock.calls[0];
        expect(options.headers.get('X-Custom-Header')).toBe('CustomValue');
        expect(options.headers.get('Accept')).toBe('text/plain');
        expect(options.headers.get('Accept-Language')).toBe('fr'); // preserved default
    });

    it('supports sending a JSON body with DELETE requests', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ deleted: 2 }));
        vi.stubGlobal('fetch', fetchMock);
        const client = new ApiClient();

        await client.delete('/inventory/items', [1, 2]);

        const [, options] = fetchMock.mock.calls[0];
        expect(options.method).toBe('DELETE');
        expect(options.body).toBe('[1,2]');
    });

    it('download helper performs GET request and triggers downloadBlob', async () => {
        const mockBlob = new Blob(['csv data'], { type: 'text/csv' });
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            blob: async () => mockBlob
        });
        vi.stubGlobal('fetch', fetchMock);

        const mockCreateObjectURL = vi.fn(() => 'blob:http://localhost/mock-uuid');
        const mockRevokeObjectURL = vi.fn();
        globalThis.URL.createObjectURL = mockCreateObjectURL;
        globalThis.URL.revokeObjectURL = mockRevokeObjectURL;

        const appendSpy = vi.spyOn(document.body, 'appendChild');
        const removeSpy = vi.spyOn(document.body, 'removeChild');

        const originalCreateElement = document.createElement.bind(document);
        const clickSpy = vi.fn();
        vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
            if (tagName === 'a') {
                const el = originalCreateElement('a');
                el.click = clickSpy;
                return el;
            }
            return originalCreateElement(tagName);
        });

        const client = new ApiClient();
        await client.download('/export', 'test.csv', { query: 'test' });

        const [url, options] = fetchMock.mock.calls[0];
        const parsedUrl = new URL(url);
        expect(parsedUrl.pathname).toBe('/api/v1/export');
        expect(parsedUrl.searchParams.get('query')).toBe('test');
        expect(options.method).toBe('GET');

        expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob);
        expect(appendSpy).toHaveBeenCalled();
        expect(clickSpy).toHaveBeenCalled();
        expect(removeSpy).toHaveBeenCalled();
        expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-uuid');
    });

    it('downloadPost helper performs POST request and triggers downloadBlob', async () => {
        const mockBlob = new Blob(['csv data'], { type: 'text/csv' });
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            blob: async () => mockBlob
        });
        vi.stubGlobal('fetch', fetchMock);

        const mockCreateObjectURL = vi.fn(() => 'blob:http://localhost/mock-uuid2');
        const mockRevokeObjectURL = vi.fn();
        globalThis.URL.createObjectURL = mockCreateObjectURL;
        globalThis.URL.revokeObjectURL = mockRevokeObjectURL;

        const appendSpy = vi.spyOn(document.body, 'appendChild');
        const removeSpy = vi.spyOn(document.body, 'removeChild');

        const originalCreateElement = document.createElement.bind(document);
        const clickSpy = vi.fn();
        vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
            if (tagName === 'a') {
                const el = originalCreateElement('a');
                el.click = clickSpy;
                return el;
            }
            return originalCreateElement(tagName);
        });

        const client = new ApiClient();
        await client.downloadPost('/export', { ids: [1, 2] }, 'test.csv');

        const [url, options] = fetchMock.mock.calls[0];
        const parsedUrl = new URL(url);
        expect(parsedUrl.pathname).toBe('/api/v1/export');
        expect(options.method).toBe('POST');
        expect(options.body).toBe('{"ids":[1,2]}');

        expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob);
        expect(appendSpy).toHaveBeenCalled();
        expect(clickSpy).toHaveBeenCalled();
        expect(removeSpy).toHaveBeenCalled();
        expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-uuid2');
    });
});
