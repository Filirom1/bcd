import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useErrorHandler } from '../../../src/bcd_web_vue/js/composables/useErrorHandler.js';
import { useNotification } from '../../../src/bcd_web_vue/js/composables/useNotification.js';
import { ApiError, ERROR_CODES } from '../../../src/bcd_web_vue/js/models/error.js';

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('useErrorHandler', () => {
    const t = key => `translated:${key}`;

    it('displays certain business rule violations as warnings instead of errors', () => {
        const handler = useErrorHandler(t);
        const limitError = new ApiError(ERROR_CODES.LOAN_LIMIT_EXCEEDED, 'Limit reached', {}, 400);

        handler.handleError(limitError);

        const notifications = useNotification().notifications.value;
        expect(notifications).toHaveLength(1);
        expect(notifications[0].type).toBe('warning');
        expect(notifications[0].message).toBe('translated:errors.loan_limit_exceeded');
    });

    it('displays network failure as network error', () => {
        const handler = useErrorHandler(t);
        const netError = ApiError.networkError(new TypeError('Failed'));

        handler.handleError(netError);

        const notifications = useNotification().notifications.value;
        expect(notifications).toHaveLength(1);
        expect(notifications[0].type).toBe('error');
        expect(notifications[0].message).toBe('translated:errors.network_error');
    });

    it('uses localized fallbacks instead of leaking unexpected error messages', () => {
        const handler = useErrorHandler(t);
        handler.handleError(new ApiError('future_error', 'Internal English detail'), {
            fallbackMessage: 'Translated operation fallback'
        });
        handler.handleError(new Error(), 'errors.network_error');

        expect(useNotification().notifications.value.map(item => item.message)).toEqual([
            'Internal English detail',
            'translated:errors.network_error'
        ]);
    });

    it('maps legacy and FastAPI validation details to translated field messages', () => {
        const handler = useErrorHandler(t);
        const legacyError = new ApiError(
            ERROR_CODES.VALIDATION_ERROR,
            'Validation failed',
            { name: ['validation.required_field'] },
            422
        );
        const pydanticError = new ApiError(
            ERROR_CODES.VALIDATION_ERROR,
            'Validation error',
            [{ loc: ['body', 'title'], type: 'missing' }],
            422
        );

        expect(handler.handleValidationError(legacyError)).toEqual({
            name: 'translated:validation.required_field'
        });
        expect(handler.handleValidationError(pydanticError)).toEqual({
            title: 'translated:validation.required_field'
        });
    });
});
