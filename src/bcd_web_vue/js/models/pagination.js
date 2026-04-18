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

// Export empty object to make this a module
export {};
