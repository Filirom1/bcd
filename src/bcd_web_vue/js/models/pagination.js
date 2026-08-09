/**
 * Pagination data models with TypeScript JSDoc type definitions
 */

/**
 * Pagination parameters for API requests
 * @typedef {Object} PaginationParams
 * @property {number} page - Current page number (1-indexed)
 * @property {number} page_size - Number of items per page
 * @property {number} offset - Calculated offset for database query
 * @property {number} limit - Same as page_size (for consistency)
 */

/**
 * Pagination metadata from API response
 * @typedef {Object} PaginationMeta
 * @property {number} page - Current page number
 * @property {number} page_size - Items per page
 * @property {number} total_items - Total number of items
 * @property {number} total_pages - Total number of pages
 * @property {boolean} has_next - Whether there is a next page
 * @property {boolean} has_previous - Whether there is a previous page
 */

/**
 * Paginated API response wrapper
 * @template T
 * @typedef {Object} PaginatedResponse
 * @property {T[]} items - Array of items for current page
 * @property {PaginationMeta} pagination - Pagination metadata
 */

/**
 * Normalize an API response into a canonical PaginatedResponse structure.
 * Validates required fields in development environment.
 * 
 * @template T
 * @param {any} response - Raw API response
 * @param {Object} [options] - Normalization options
 * @param {string} [options.fallbackItemsKey] - Expected key for items list (e.g. 'titles')
 * @param {string} [options.fallbackTotalKey] - Expected key for total count
 * @param {number} [options.defaultPageSize] - Default page size if not provided
 * @param {number} [options.defaultPage] - Default page number if not provided
 * @returns {PaginatedResponse<T>} Canonical PaginatedResponse
 * @throws {TypeError} If response is null/undefined or cannot be normalized
 */
export function normalizeCollection(response, options = {}) {
    if (response === null || response === undefined) {
        throw new TypeError("Cannot normalize null or undefined API response");
    }

    let items = null;
    const itemsKeys = options.fallbackItemsKey 
        ? [options.fallbackItemsKey, 'items', 'titles', 'data', 'classes']
        : ['items', 'titles', 'data', 'classes'];

    // Try finding items array in various standard keys
    if (Array.isArray(response)) {
        items = response;
    } else {
        for (const key of itemsKeys) {
            if (Array.isArray(response[key])) {
                items = response[key];
                break;
            }
        }
    }

    // Validation: Development validation to ensure we have a valid items array
    if (items === null) {
        const keys = Object.keys(response);
        throw new Error(
            `Invalid collection response: expected an array or an object containing an array. ` +
            `Available keys: [${keys.join(', ')}]. Fallback items key tried: [${itemsKeys.join(', ')}].`
        );
    }

    // Extract pagination metadata
    let totalItems = items.length;
    const totalKeys = options.fallbackTotalKey
        ? [options.fallbackTotalKey, 'total', 'total_count', 'total_overdue', 'total_holds', 'total_active_loans']
        : ['total', 'total_count', 'total_overdue', 'total_holds', 'total_active_loans'];

    if (!Array.isArray(response)) {
        for (const key of totalKeys) {
            if (typeof response[key] === 'number') {
                totalItems = response[key];
                break;
            }
        }
    }

    // Extract page, page_size / limit, offset
    let limit = response.limit !== undefined ? response.limit : (response.page_size !== undefined ? response.page_size : (options.defaultPageSize || items.length || 50));
    let offset = response.offset !== undefined ? response.offset : 0;
    
    let page = 1;
    if (response.page !== undefined) {
        page = response.page;
    } else if (limit > 0) {
        page = Math.floor(offset / limit) + 1;
    }

    let pageSize = limit;
    let totalPages = pageSize > 0 ? Math.ceil(totalItems / pageSize) : 1;
    if (totalPages === 0) totalPages = 1;

    const hasNext = page < totalPages;
    const hasPrevious = page > 1;

    // Strict validation of the pagination metadata structure
    if (typeof totalItems !== 'number' || isNaN(totalItems)) {
        throw new TypeError("Collection normalization error: total_items must be a valid number");
    }

    return {
        items,
        pagination: {
            page,
            page_size: pageSize,
            total_items: totalItems,
            total_pages: totalPages,
            has_next: hasNext,
            has_previous: hasPrevious
        }
    };
}

