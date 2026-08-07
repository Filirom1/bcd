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

        let message;
        let isWarning = false;

        if (error instanceof ApiError) {
            message = error.getTranslatedMessage(t);

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
            // Generic error
            message = options.fallbackMessage || t('errors.unknown_error');
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
        const details = /** @type {Record<string, any>} */ (error.details || {});

        // Map API validation errors to field names
        Object.entries(details).forEach(([field, messages]) => {
            if (Array.isArray(messages)) {
                fieldErrors[field] = messages.map(msg => t(msg)).join(', ');
            } else {
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
