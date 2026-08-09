/**
 * Item and bibliographic record data models with TypeScript JSDoc type definitions.
 * Fully aligned with Pydantic and SQLAlchemy models.
 */

/**
 * Basic bibliographic record information
 * @typedef {Object} BibliographicRecord
 * @property {number} id - Bibliographic record database ID
 * @property {string|null} isbn - ISBN-13 or ISBN-10
 * @property {string} title - Book title
 * @property {string[]|null} authors - List of authors
 * @property {string|null} publisher - Publisher name
 * @property {number|null} publication_year - Year of publication
 * @property {string|null} language - Language code (e.g., 'fr', 'en')
 * @property {string|null} target_audience - Target audience
 * @property {string|null} summary - Book summary/description
 * @property {string[]|null} subjects - Subject keywords
 * @property {string|null} medium_type - Medium/support type
 * @property {string|null} collection - Series or collection name
 * @property {string|null} dewey_number - Dewey decimal number
 * @property {number} total_copies - Total number of physical copies
 * @property {number} available_copies - Number of available copies
 */

/**
 * Physical item/copy information
 * @typedef {Object} Item
 * @property {number} id - Item database auto-increment ID
 * @property {string} item_id - Unique alphanumeric item ID
 * @property {number} bibliographic_record_id - Parent bibliographic record ID
 * @property {string} barcode - Item barcode (equal to item_id)
 * @property {string|null} call_number - Call number (Dewey/CDU)
 * @property {string|null} shelf_location - Physical shelf location
 * @property {string} condition - Condition: 'good', 'damaged'
 * @property {string} status - Status: 'available', 'on_loan', 'on_hold', 'in_repair', 'lost', 'withdrawn'
 * @property {boolean} loanable - Whether the item can be borrowed
 * @property {string|null} acquisition_date - Date acquired (ISO 8601)
 * @property {string|null} funding_source - Funding source
 * @property {string|null} last_borrowed_at - Timestamp of last checkout (ISO 8601)
 * @property {string|null} last_inventoried_at - Timestamp of last inventory scan (ISO 8601)
 */

/**
 * Detailed item with current loan information
 * @typedef {Object} ItemDetailed
 * @property {number} id - Item database ID
 * @property {string} item_id - Item identifier
 * @property {string|null} call_number - Call number
 * @property {string|null} shelf_location - Physical shelf location
 * @property {string} status - Item status
 * @property {string} condition - Item condition
 * @property {boolean} loanable - Whether item is loanable
 * @property {string|null} acquisition_date - Date acquired (ISO 8601)
 * @property {string|null} funding_source - Funding source
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
 * @property {number} id - Bibliographic record ID
 * @property {string|null} isbn - ISBN
 * @property {string} title - Book title
 * @property {string[]|null} authors - List of authors
 * @property {string|null} publisher - Publisher name
 * @property {number|null} publication_year - Year of publication
 * @property {string|null} language - Language code
 * @property {string|null} target_audience - Target audience
 * @property {string|null} summary - Book summary
 * @property {string[]|null} subjects - Subject keywords
 * @property {string|null} medium_type - Medium type
 * @property {string|null} collection - Series/collection
 * @property {string|null} dewey_number - Dewey decimal number
 * @property {number} total_copies - Total number of copies
 * @property {number} available_copies - Available copies
 * @property {ItemDetailed[]} items - Array of all physical items/copies with detailed loan info
 */

// Export empty object to make this a module
export {};
