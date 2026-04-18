/**
 * Item and bibliographic record data models with TypeScript JSDoc type definitions
 */

/**
 * Basic bibliographic record information
 * @typedef {Object} BibliographicRecord
 * @property {number} record_id - Bibliographic record ID
 * @property {string|null} isbn - ISBN-13 or ISBN-10
 * @property {string} title - Book title
 * @property {string|null} author - Author name(s)
 * @property {string|null} publisher - Publisher name
 * @property {number|null} publication_year - Year of publication
 * @property {string|null} language - Language code (e.g., 'fr', 'en')
 * @property {string|null} target_audience - Target audience (e.g., 'Enfant', 'Adulte')
 * @property {string|null} summary - Book summary/description
 * @property {string[]|null} subjects - Subject keywords
 * @property {number} total_copies - Total number of physical copies
 * @property {number} available_copies - Number of available copies
 */

/**
 * Physical item/copy information
 * @typedef {Object} Item
 * @property {string} item_id - Item identifier
 * @property {number} bibliographic_record_id - Parent bibliographic record ID
 * @property {string} barcode - Item barcode
 * @property {number} copy_number - Copy number (1, 2, 3, etc.)
 * @property {string} status - Status: 'available', 'on_loan', 'damaged', 'lost', 'in_repair'
 * @property {string|null} location - Physical location in library
 * @property {string} condition - Condition: 'excellent', 'good', 'fair', 'poor'
 * @property {string} acquisition_date - Date acquired (ISO 8601)
 * @property {number|null} acquisition_price - Price paid (in cents)
 */

/**
 * Detailed item with current loan information
 * @typedef {Object} ItemDetailed
 * @property {string} item_id - Item identifier
 * @property {number} bibliographic_record_id - Parent bibliographic record ID
 * @property {string} barcode - Item barcode
 * @property {number} copy_number - Copy number
 * @property {string} status - Item status
 * @property {string|null} location - Physical location
 * @property {string} condition - Item condition
 * @property {string} acquisition_date - Date acquired
 * @property {number|null} acquisition_price - Price paid
 * @property {Object|null} current_loan - Current loan info (null if available)
 * @property {string} current_loan.borrower_id - Borrower ID
 * @property {string} current_loan.borrower_name - Borrower name
 * @property {string} current_loan.due_date - Due date (ISO 8601)
 * @property {boolean} current_loan.is_overdue - Whether overdue
 * @property {number} current_loan.days_overdue - Days overdue
 */

/**
 * Bibliographic record with all items/copies
 * @typedef {Object} BibliographicRecordWithItems
 * @property {number} record_id - Bibliographic record ID
 * @property {string|null} isbn - ISBN
 * @property {string} title - Book title
 * @property {string|null} author - Author name(s)
 * @property {string|null} publisher - Publisher name
 * @property {number|null} publication_year - Year of publication
 * @property {string|null} language - Language code
 * @property {string|null} target_audience - Target audience
 * @property {string|null} summary - Book summary
 * @property {string[]|null} subjects - Subject keywords
 * @property {number} total_copies - Total number of copies
 * @property {number} available_copies - Available copies
 * @property {ItemDetailed[]} items - Array of all physical items/copies
 */

// Export empty object to make this a module
export {};
