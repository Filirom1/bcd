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
    BORROWER_ID_NOT_AVAILABLE: 'borrower_id_not_available',

    // Item errors
    ITEM_NOT_FOUND: 'item_not_found',
    ITEM_UNAVAILABLE: 'item_unavailable',
    ITEM_NOT_AVAILABLE: 'item_not_available',
    ITEM_NOT_LOANABLE: 'item_not_loanable',
    ITEM_ALREADY_ON_LOAN: 'item_already_on_loan',
    ITEM_NOT_ON_LOAN: 'item_not_on_loan',
    ITEM_HAS_ACTIVE_LOAN: 'item_has_active_loan',
    ITEM_RESERVED_FOR_OTHER: 'item_reserved_for_other',
    DUPLICATE_ITEM_ID: 'duplicate_item_id',
    DUPLICATE_BARCODE: 'duplicate_barcode',

    // Circulation errors
    LOAN_LIMIT_EXCEEDED: 'loan_limit_exceeded',
    LOAN_LIMIT_WARNING_EXCEEDED: 'loan_limit_warning_exceeded',
    HOLD_LIMIT_EXCEEDED: 'hold_limit_exceeded',
    HOLD_ALREADY_EXISTS: 'hold_already_exists',
    RENEWAL_LIMIT_EXCEEDED: 'renewal_limit_exceeded',
    NO_RENEWABLE_ITEMS: 'no_renewable_items',
    ITEM_OVERDUE: 'item_overdue',
    ITEM_HAS_HOLDS: 'item_has_holds',
    NO_ITEMS_FOR_RECORD: 'no_items_for_record',

    // Catalog errors
    RECORD_NOT_FOUND: 'record_not_found',
    DUPLICATE_ISBN: 'duplicate_isbn',
    CLASS_NOT_FOUND: 'class_not_found',
    CLASS_HAS_BORROWERS: 'class_has_borrowers',
    DUPLICATE_CLASS_NAME: 'duplicate_class_name',
    BULK_OPERATION_FAILED: 'bulk_operation_failed',
    INVALID_ID_FORMAT: 'invalid_id_format',
    CSV_VALIDATION_ERROR: 'csv_validation_error',
    CSV_ENCODING_ERROR: 'csv_encoding_error',
    CSV_ROW_LIMIT_EXCEEDED: 'csv_row_limit_exceeded',
    EXPORT_TOO_LARGE: 'export_too_large',
    EXPORT_FAILED: 'export_failed',
    INTEGRITY_ERROR: 'integrity_error',
    ISBN_INVALID: 'isbn_invalid',
    BNF_LOOKUP_FAILED: 'bnf_lookup_failed',

    // Generic errors
    VALIDATION_ERROR: 'validation_error',
    PERMISSION_DENIED: 'permission_denied',
    NETWORK_ERROR: 'network_error',
    UNKNOWN_ERROR: 'unknown_error'
};

// The API normalizes error codes to lowercase, while some older translation
// keys are uppercase or live in feature-specific namespaces.
export const ERROR_TRANSLATION_KEYS = {
    borrower_id_not_available: 'errors.BORROWER_ID_NOT_AVAILABLE',
    borrower_inactive: 'errors.borrower_blocked',
    bulk_operation_failed: 'errors.BULK_OPERATION_FAILED',
    class_has_borrowers: 'errors.CLASS_HAS_BORROWERS',
    class_not_found: 'errors.CLASS_NOT_FOUND',
    duplicate_barcode: 'errors.DUPLICATE_BARCODE',
    duplicate_class_name: 'errors.DUPLICATE_CLASS_NAME',
    duplicate_isbn: 'cataloging.duplicate_isbn',
    bnf_lookup_failed: 'cataloging.lookup_error',
    integrity_error: 'errors.integrity_error',
    isbn_invalid: 'errors.isbn_invalid',
    hold_already_exists: 'holds.already_exists',
    hold_limit_exceeded: 'holds.hold_limit_exceeded',
    item_overdue: 'errors.item_overdue',
    no_items_for_record: 'holds.no_items_for_record',
    permission_denied: 'errors.permission_denied',
    validation_error: 'errors.validation_failed'
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
    getTranslatedMessage(t, fallbackMessage = null, translationKeyOverrides = {}) {
        const fallback = this.message || fallbackMessage || t('errors.unknown_error');
        if (this.code === ERROR_CODES.UNKNOWN_ERROR
            || !Object.values(ERROR_CODES).includes(this.code)) {
            return fallback;
        }

        const key = translationKeyOverrides[this.code]
            || ERROR_TRANSLATION_KEYS[this.code]
            || `errors.${this.code}`;
        const params = this.details && typeof this.details === 'object' && !Array.isArray(this.details)
            ? this.details
            : {};

        // Known API codes have translation keys validated in both locales. If
        // an unknown code arrives, keep the server detail rather than hiding
        // useful context behind a generic message.
        return t(key, params);
    }

    /**
     * Create ApiError from fetch response
     * @param {Response} response - Fetch response object
     * @returns {Promise<ApiError>}
     */
    static async fromResponse(response) {
        try {
            const data = await response.json();
            // Normalize error_code to lowercase for translation keys. The
            // FastAPI validation handler may provide structured details before
            // all clients have upgraded to the explicit error_code contract.
            const errorCode = data.error_code
                ? String(data.error_code).toLowerCase()
                : (Array.isArray(data.details) ? ERROR_CODES.VALIDATION_ERROR : ERROR_CODES.UNKNOWN_ERROR);

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

/**
 * Return a localized message when a translation exists, otherwise preserve the
 * original error detail before using the operation-specific fallback.
 *
 * @param {unknown} error
 * @param {Function} t
 * @param {string} [fallbackKey='errors.unknown_error']
 * @returns {string}
 */
export function getLocalizedErrorMessage(
    error,
    t,
    fallbackKey = 'errors.unknown_error',
    translationKeyOverrides = {}
) {
    const fallbackMessage = t(fallbackKey);
    if (error instanceof ApiError) {
        return error.getTranslatedMessage(t, fallbackMessage, translationKeyOverrides);
    }

    // Accept code-shaped errors from adapters and tests without requiring
    // callers to construct an ApiError instance themselves.
    if (error && typeof error === 'object' && typeof error.code === 'string') {
        const details = error.details && typeof error.details === 'object' ? error.details : {};
        return new ApiError(
            error.code.toLowerCase(),
            typeof error.message === 'string' ? error.message : '',
            details
        )
            .getTranslatedMessage(t, fallbackMessage, translationKeyOverrides);
    }

    if (error && typeof error === 'object' && typeof error.message === 'string' && error.message) {
        return error.message;
    }

    return fallbackMessage;
}
