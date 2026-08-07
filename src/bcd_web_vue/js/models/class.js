/**
 * Class data models with TypeScript JSDoc type definitions.
 * Fully aligned with Pydantic and SQLAlchemy models.
 */

/**
 * Basic school class information
 * @typedef {Object} ClassModel
 * @property {number} id - Database auto-increment ID
 * @property {string} name - Class name (e.g., 'CP-A', 'CE1-B')
 * @property {string|null} homeroom_teacher - Name of the homeroom teacher
 * @property {string|null} notes - Additional notes
 * @property {number|null} average_age - Average age of students (used for sorting)
 */

/**
 * Class information with borrower stats
 * @typedef {Object} ClassWithBorrowerCount
 * @property {number} id - Database ID
 * @property {string} name - Class name
 * @property {string|null} homeroom_teacher - Homeroom teacher
 * @property {string|null} notes - Additional notes
 * @property {number|null} average_age - Average age of students
 * @property {number} borrower_count - Number of borrowers in this class
 */

// Export empty object to make this a module
export {};
