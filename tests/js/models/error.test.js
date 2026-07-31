import { describe, expect, it } from 'vitest';

import { ApiError, ERROR_CODES } from '../../../src/bcd_web_vue/js/models/error.js';

describe('ApiError', () => {
    it('normalizes server error codes and preserves API context', async () => {
        const response = new Response(JSON.stringify({
            error_code: 'LOAN_LIMIT_EXCEEDED',
            message: 'Too many books',
            context: { current: 2, limit: 2 }
        }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
        });

        const error = await ApiError.fromResponse(response);

        expect(error).toBeInstanceOf(ApiError);
        expect(error).toMatchObject({
            code: ERROR_CODES.LOAN_LIMIT_EXCEEDED,
            message: 'Too many books',
            details: { current: 2, limit: 2 },
            statusCode: 400
        });
    });

    it('accepts legacy detail and details fields from an API response', async () => {
        const response = new Response(JSON.stringify({
            detail: 'Borrower not found',
            details: { borrower_id: '101' }
        }), {
            status: 404,
            headers: { 'Content-Type': 'application/json' }
        });

        const error = await ApiError.fromResponse(response);

        expect(error).toMatchObject({
            code: ERROR_CODES.UNKNOWN_ERROR,
            message: 'Borrower not found',
            details: { borrower_id: '101' },
            statusCode: 404
        });
    });

    it('creates a useful fallback for a non-JSON HTTP error', async () => {
        const response = new Response('Gateway unavailable', {
            status: 503,
            statusText: 'Service Unavailable'
        });

        const error = await ApiError.fromResponse(response);

        expect(error).toMatchObject({
            code: ERROR_CODES.UNKNOWN_ERROR,
            message: 'HTTP 503: Service Unavailable',
            details: {},
            statusCode: 503
        });
    });

    it('uses the translated message when the translation key exists', () => {
        const error = new ApiError(
            ERROR_CODES.ITEM_NOT_FOUND,
            'Item missing',
            { item_id: 'BC-42' },
            404
        );
        const translate = (key, params) => (
            key === 'errors.item_not_found' ? `Missing ${params.item_id}` : key
        );

        expect(error.getTranslatedMessage(translate)).toBe('Missing BC-42');
    });

    it('falls back to the server message when no translation exists', () => {
        const error = new ApiError('unmapped_error', 'A detailed server message');

        expect(error.getTranslatedMessage(key => key)).toBe('A detailed server message');
    });

    it('preserves the original failure in a network error', () => {
        const originalError = new Error('Connection refused');

        expect(ApiError.networkError(originalError)).toMatchObject({
            code: ERROR_CODES.NETWORK_ERROR,
            statusCode: 0,
            details: { originalError: 'Connection refused' }
        });
    });
});
