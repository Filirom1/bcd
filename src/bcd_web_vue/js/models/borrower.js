/**
 * Borrower data models with TypeScript JSDoc type definitions.
 * Fully aligned with Pydantic and SQLAlchemy models.
 */

/**
 * Current loan/circulation transaction details
 * @typedef {Object} CurrentLoan
 * @property {string} item_id - Item identifier (barcode)
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
 * @property {number} id - Database auto-increment ID
 * @property {string} borrower_id - Unique alphanumeric borrower ID
 * @property {string} first_name - First name
 * @property {string} last_name - Last name
 * @property {string} full_name - Full name (LAST First)
 * @property {string} role - Role: 'student', 'teacher', 'staff'
 * @property {number|null} class_id - Class database ID
 * @property {string|null} grade_level - Grade level (e.g., 'CP', 'CE1')
 * @property {string} barcode - Borrower barcode (e.g., '%101')
 * @property {boolean} active - Whether borrower is active (is_active in legacy, active in backend)
 * @property {string|null} blocked_reason - Reason why the borrower is blocked, if any
 * @property {string|null} email - Email address
 * @property {string|null} phone - Phone number
 * @property {string|null} notes - Additional notes
 */

/**
 * Detailed borrower information with current loans and stats
 * @typedef {Object} BorrowerDetailed
 * @property {number} id - Database ID
 * @property {string} borrower_id - Borrower identifier
 * @property {string} first_name - First name
 * @property {string} last_name - Last name
 * @property {string} full_name - Full name
 * @property {string} role - Role
 * @property {number|null} class_id - Class database ID
 * @property {string|null} grade_level - Grade level
 * @property {string} barcode - Borrower barcode
 * @property {boolean} active - Whether borrower is active
 * @property {string|null} blocked_reason - Reason for blocking (if blocked)
 * @property {string|null} email - Email address
 * @property {string|null} phone - Phone number
 * @property {string|null} notes - Additional notes
 * @property {number} current_loans_count - Current number of items on loan
 * @property {number} total_checkouts - Total number of checkouts (all time)
 * @property {number} overdue_count - Number of overdue items
 * @property {number} loan_limit - Maximum loans allowed
 * @property {number} loan_limit_warning - Soft warning threshold for loans
 * @property {string|null} class_name - Class name (if student)
 * @property {string|null} homeroom_teacher - Homeroom teacher for the class
 * @property {CurrentLoan[]} [loans] - Array of current active loans (if returned by detail endpoint)
 */

// Export empty object to make this a module
export {};
