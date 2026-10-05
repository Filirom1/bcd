// @ts-check
/**
 * Centralized error handling composable
 * Handles ApiError instances with special cases and i18n integration
 */

import { useNotification } from './useNotification.js';
import { ApiError, ERROR_CODES } from '../models/error.js';

/**
 * Error handler composable
 * @param {Function} t - Translation function from vue-i18n
 * @returns {Object} Error handling methods
 */
export function useErrorHandler(t) {
    const { error: showError, warning: showWarning } = useNotification();

    /**
     * Handle an error and display appropriate notification
     * @param {Error|ApiError} error - Error to handle
     * @param {Object} [options] - Handler options
     * @param {string} [options.fallbackMessage] - Fallback message if translation fails
     * @param {Function} [options.onError] - Custom error callback
     * @returns {void}
     */
    const handleError = (error, options = {}) => {
        console.error('Error occurred:', error);

        // Accept the former string form as a translation key while callers
        // migrate to the documented { fallbackMessage } options object.
        const fallbackMessage = typeof options === 'string'
            ? t(options)
            : (options.fallbackMessage || t('errors.unknown_error'));
        let message = fallbackMessage;
        let isWarning = false;

        if (error instanceof ApiError) {
            message = error.getTranslatedMessage(t, fallbackMessage);

            // Special handling for certain error codes
            switch (error.code) {
                case ERROR_CODES.LOAN_LIMIT_EXCEEDED:
                case ERROR_CODES.BORROWER_BLOCKED:
                case ERROR_CODES.ITEM_OVERDUE:
                    isWarning = true; // Show as warning instead of error
                    break;

                case ERROR_CODES.NETWORK_ERROR:
                    message = t('errors.network_error');
                    break;

                default:
                    break;
            }
        } else {
            // Prefer a useful diagnostic over a generic label when there is no
            // API translation available. This may be English, but avoids
            // hiding the server's explanation.
            message = error?.message || fallbackMessage;
        }

        // Show notification
        if (isWarning) {
            showWarning(message);
        } else {
            showError(message);
        }

        // Call custom error callback if provided
        if (options.onError) {
            options.onError(error);
        }
    };

    /**
     * Handle validation errors from API
     * @param {ApiError} error - Validation error
     * @returns {Object} Field-specific error messages
     */
    const handleValidationError = (error) => {
        if (error.code !== ERROR_CODES.VALIDATION_ERROR) {
            return {};
        }

        /** @type {Record<string, string>} */
        const fieldErrors = {};
        const details = error.details || {};

        // FastAPI/Pydantic sends validation details as [{loc, msg, type}],
        // while older endpoints may send a field -> translated-key mapping.
        if (Array.isArray(details)) {
            const validationDetails = /** @type {Array<{loc?: unknown[], type?: string}>} */ (details);
            validationDetails.forEach((detail) => {
                const location = Array.isArray(detail.loc) ? detail.loc : [];
                const field = String(location.filter((part) => part !== 'body').at(-1) || 'general');
                const messageKey = detail.type === 'missing'
                    ? 'validation.required_field'
                    : 'errors.validation_failed';
                fieldErrors[field] = t(messageKey);
            });
            return fieldErrors;
        }

        if (!details || typeof details !== 'object') {
            return fieldErrors;
        }

        Object.entries(details).forEach(([field, messages]) => {
            if (Array.isArray(messages)) {
                fieldErrors[field] = messages.map(msg => t(msg)).join(', ');
            } else if (typeof messages === 'string') {
                fieldErrors[field] = t(messages);
            }
        });

        return fieldErrors;
    };

    /**
     * Check if error is a specific type
     * @param {Error} error - Error to check
     * @param {string} code - Error code to check against
     * @returns {boolean}
     */
    const isErrorType = (error, code) => {
        return error instanceof ApiError && error.code === code;
    };

    return {
        handleError,
        handleValidationError,
        isErrorType
    };
}
