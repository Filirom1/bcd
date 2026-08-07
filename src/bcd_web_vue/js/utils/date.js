/**
 * Robust Date Utility for BCD Web UI
 * Centralizes civil dates parsing, formatting, and prevents timezone/UTC shift bugs.
 * @ts-check
 */

/**
 * Get current or specified date as local civil date string (YYYY-MM-DD).
 * Prevents UTC-shift bugs around midnight.
 * @param {Date} [date=new Date()]
 * @returns {string} YYYY-MM-DD
 */
export function getLocalCivilDate(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Parse a local civil date string (YYYY-MM-DD) without timezone shifts.
 * @param {string|null|undefined} dateStr - YYYY-MM-DD
 * @returns {Date|null} Date object representing local midnight
 */
export function parseLocalCivilDate(dateStr) {
    if (!dateStr) return null;
    const parts = String(dateStr).split('-');
    if (parts.length !== 3) return null;
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    if (isNaN(year) || isNaN(month) || isNaN(day)) return null;
    return new Date(year, month, day);
}

/**
 * Format a local civil date string (YYYY-MM-DD) into a human readable format.
 * Uses active locale and avoids timezone/UTC shift bugs.
 * @param {string|null|undefined} dateStr - YYYY-MM-DD
 * @param {string} [locale='fr'] - 'fr' or 'en'
 * @param {string|null} [dateFormat=null] - Date format pattern
 * @returns {string} Formatted date
 */
export function formatCivilDate(dateStr, locale = 'fr', dateFormat = null) {
    const date = parseLocalCivilDate(dateStr);
    if (!date) return '';
    if (dateFormat) return formatDatePattern(date, dateFormat);
    return new Intl.DateTimeFormat(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(date);
}

/**
 * @param {Date} date
 * @param {string} [pattern='DD/MM/YYYY']
 * @returns {string}
 */
export function formatDatePattern(date, pattern = 'DD/MM/YYYY') {
    /** @type {Record<string, string>} */
    const values = {
        YYYY: String(date.getFullYear()),
        MM: String(date.getMonth() + 1).padStart(2, '0'),
        DD: String(date.getDate()).padStart(2, '0')
    };
    return pattern.replace(/YYYY|MM|DD/g, token => values[token]);
}

/**
 * Format a time.
 * @param {string|Date|null|undefined} timestamp
 * @param {string} [locale='fr']
 * @returns {string}
 */
export function formatTime(timestamp, locale = 'fr') {
    if (!timestamp) return '';
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    if (isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(date);
}

/**
 * Format date and time.
 * @param {string|Date|null|undefined} timestamp
 * @param {string} [locale='fr']
 * @returns {string}
 */
export function formatDateTime(timestamp, locale = 'fr') {
    if (!timestamp) return '';
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    if (isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}
