/**
 * Hold (Réservation) data models with TypeScript JSDoc type definitions.
 * Fully aligned with Pydantic and SQLAlchemy models.
 */

/**
 * Basic hold response details
 * @typedef {Object} Hold
 * @property {number} id - Hold database ID
 * @property {number} borrower_id - Borrower database ID
 * @property {number} bibliographic_record_id - Bibliographic record database ID
 * @property {string} hold_date - Date and time placed (ISO 8601)
 * @property {number} queue_position - Position in the queue
 * @property {string} status - Hold status: 'pending', 'ready_for_pickup', 'fulfilled', 'cancelled', 'expired'
 * @property {string|null} available_date - Date made available for pickup (ISO 8601)
 * @property {string|null} expiration_date - Date when pickup hold expires (YYYY-MM-DD)
 * @property {string|null} fulfilled_date - Date when hold was fulfilled (ISO 8601)
 * @property {boolean} notified - Whether notification has been sent
 * @property {string|null} notification_method - Notification method
 * @property {string|null} created_by - User/Librarian who placed the hold
 * @property {string|null} notes - Additional notes
 */

/**
 * Hold summary used in lists
 * @typedef {Object} HoldSummary
 * @property {number} id - Hold database ID
 * @property {number} borrower_id - Borrower database ID
 * @property {string} borrower_name - Borrower full name
 * @property {number} bibliographic_record_id - Bibliographic record database ID
 * @property {string} title - Book title
 * @property {number} queue_position - Position in hold queue
 * @property {string} status - Hold status
 * @property {string} hold_date - Hold date and time (ISO 8601)
 */

/**
 * Hold detailed info with complete borrower and record details
 * @typedef {Object} HoldWithDetails
 * @property {number} id - Hold database ID
 * @property {number} borrower_id - Borrower database ID
 * @property {number} bibliographic_record_id - Bibliographic record database ID
 * @property {string} hold_date - Date and time placed (ISO 8601)
 * @property {number} queue_position - Position in the queue
 * @property {string} status - Hold status
 * @property {string|null} available_date - Date made available for pickup (ISO 8601)
 * @property {string|null} expiration_date - Date when pickup hold expires (YYYY-MM-DD)
 * @property {string|null} fulfilled_date - Date when hold was fulfilled (ISO 8601)
 * @property {boolean} notified - Whether notification has been sent
 * @property {string|null} notification_method - Notification method
 * @property {string|null} created_by - User/Librarian who placed the hold
 * @property {string|null} notes - Additional notes
 * @property {string|null} borrower_name - Borrower full name
 * @property {string|null} borrower_string_id - Borrower student ID
 * @property {string|null} borrower_class - Borrower class name
 * @property {string|null} title - Bibliographic record title
 * @property {string|null} authors - Bibliographic record author(s)
 */

// Export empty object to make this a module
export {};
