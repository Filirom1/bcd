/**
 * Error codes and ApiError class for centralized error handling
 */

/**
 * Standard error codes from the BCD API
 * @enum {string}
 */
export const ERROR_CODES = {
    // Borrower errors
    BORROWER_NOT_FOUND: 'borrower_not_found',
    BORROWER_BLOCKED: 'borrower_blocked',
    BORROWER_INACTIVE: 'borrower_inactive',
    BORROWER_HAS_OVERDUE: 'borrower_has_overdue',
    BORROWER_HAS_ACTIVE_LOANS: 'borrower_has_active_loans',

    // Item errors
    ITEM_NOT_FOUND: 'item_not_found',
    ITEM_UNAVAILABLE: 'item_unavailable',
    ITEM_NOT_AVAILABLE: 'item_not_available',
    ITEM_NOT_LOANABLE: 'item_not_loanable',
    ITEM_ALREADY_ON_LOAN: 'item_already_on_loan',
    ITEM_NOT_ON_LOAN: 'item_not_on_loan',
    ITEM_HAS_ACTIVE_LOAN: 'item_has_active_loan',

    // Circulation errors
    LOAN_LIMIT_EXCEEDED: 'loan_limit_exceeded',
    HOLD_LIMIT_EXCEEDED: 'hold_limit_exceeded',
    RENEWAL_LIMIT_EXCEEDED: 'renewal_limit_exceeded',
    NO_RENEWABLE_ITEMS: 'no_renewable_items',
    ITEM_OVERDUE: 'item_overdue',

    // Catalog errors
    RECORD_NOT_FOUND: 'record_not_found',
    DUPLICATE_ISBN: 'duplicate_isbn',
    ISBN_INVALID: 'isbn_invalid',
    BNF_LOOKUP_FAILED: 'bnf_lookup_failed',

    // Generic errors
    VALIDATION_ERROR: 'validation_error',
    PERMISSION_DENIED: 'permission_denied',
    NETWORK_ERROR: 'network_error',
    UNKNOWN_ERROR: 'unknown_error'
};

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
    /**
     * @param {string} code - Error code from ERROR_CODES
     * @param {string} message - Human-readable error message
     * @param {Object} [details={}] - Additional error context
     * @param {number} [statusCode=500] - HTTP status code
     */
    constructor(code, message, details = {}, statusCode = 500) {
        super(message);
        this.name = 'ApiError';
        this.code = code;
        this.details = details;
        this.statusCode = statusCode;
    }

    /**
     * Get translated error message using vue-i18n
     * @param {Function} t - Translation function from vue-i18n
     * @returns {string} Translated error message
     */
    getTranslatedMessage(t) {
        const key = `errors.${this.code}`;

        // Check if translation exists
        const translated = t(key, this.details);

        // If translation key not found, return fallback message
        if (translated === key) {
            return this.message || t('errors.unknown_error');
        }

        return translated;
    }

    /**
     * Create ApiError from fetch response
     * @param {Response} response - Fetch response object
     * @returns {Promise<ApiError>}
     */
    static async fromResponse(response) {
        try {
            const data = await response.json();
            // Normalize error_code to lowercase for translation keys
            const errorCode = data.error_code
                ? data.error_code.toLowerCase()
                : ERROR_CODES.UNKNOWN_ERROR;

            return new ApiError(
                errorCode,
                data.message || data.detail || data.error || 'An error occurred',
                data.context || data.details || {},
                response.status
            );
        } catch (e) {
            // If response is not JSON, create generic error
            return new ApiError(
                ERROR_CODES.UNKNOWN_ERROR,
                `HTTP ${response.status}: ${response.statusText}`,
                {},
                response.status
            );
        }
    }

    /**
     * Create network error
     * @param {Error} error - Original network error
     * @returns {ApiError}
     */
    static networkError(error) {
        return new ApiError(
            ERROR_CODES.NETWORK_ERROR,
            'Network error: Unable to reach server',
            { originalError: error.message },
            0
        );
    }
}
