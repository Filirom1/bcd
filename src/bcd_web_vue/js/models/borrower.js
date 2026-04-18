/**
 * Borrower data models with TypeScript JSDoc type definitions
 */

/**
 * Current loan information
 * @typedef {Object} CurrentLoan
 * @property {string} item_id - Item identifier
 * @property {number} bibliographic_record_id - Bibliographic record ID
 * @property {string} title - Book title
 * @property {string} author - Book author
 * @property {string} barcode - Item barcode
 * @property {string} due_date - Due date (ISO 8601 format)
 * @property {boolean} is_overdue - Whether the item is overdue
 * @property {number} days_overdue - Number of days overdue (0 if not overdue)
 * @property {number} renewals_count - Number of times renewed
 * @property {number} max_renewals - Maximum renewals allowed
 */

/**
 * Basic borrower information
 * @typedef {Object} Borrower
 * @property {string} borrower_id - Borrower identifier
 * @property {string} full_name - Full name (LAST First)
 * @property {string} role - Role: 'student', 'teacher', 'staff'
 * @property {string|null} class_name - Class name (e.g., 'CP-A', 'CE1-B')
 * @property {string|null} grade_level - Grade level (e.g., 'CP', 'CE1')
 * @property {string} barcode - Borrower barcode
 * @property {boolean} is_active - Whether borrower is active
 * @property {number} current_loans - Current number of items on loan
 * @property {number} loan_limit - Maximum loans allowed
 * @property {number} overdue_count - Number of overdue items
 * @property {Object|null} contact_info - Contact information
 * @property {string|null} contact_info.email - Email address
 * @property {string|null} contact_info.phone - Phone number
 */

/**
 * Detailed borrower information with current loans
 * @typedef {Object} BorrowerDetailed
 * @property {string} borrower_id - Borrower identifier
 * @property {string} full_name - Full name (LAST First)
 * @property {string} role - Role: 'student', 'teacher', 'staff'
 * @property {string|null} class_name - Class name
 * @property {string|null} grade_level - Grade level
 * @property {string} barcode - Borrower barcode
 * @property {boolean} is_active - Whether borrower is active
 * @property {string|null} blocked_reason - Reason for blocking (if blocked)
 * @property {number} current_loans - Current number of items on loan
 * @property {number} loan_limit - Maximum loans allowed
 * @property {number} overdue_count - Number of overdue items
 * @property {CurrentLoan[]} loans - Array of current loans
 * @property {Object|null} contact_info - Contact information
 * @property {string|null} contact_info.email - Email address
 * @property {string|null} contact_info.phone - Phone number
 */

// Export empty object to make this a module
export {};
