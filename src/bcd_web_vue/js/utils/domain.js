/**
 * Pure Web domain helpers shared by components.
 * @ts-check
 */

/**
 * Parses a JSON setting.
 * @template T
 * @param {any} value
 * @param {T} fallback
 * @returns {T}
 */
export function parseJsonSetting(value, fallback) {
    if (value === null || value === undefined || value === '') return fallback;
    try {
        const parsed = typeof value === 'string' ? JSON.parse(value) : value;
        return parsed ?? fallback;
    } catch {
        return fallback;
    }
}

/**
 * Parse a comma-separated setting, ignoring whitespace and empty values.
 * @param {string[]|string|null|undefined} value
 * @returns {string[]}
 */
export function parseCsv(value) {
    if (Array.isArray(value)) return value.filter(Boolean);
    if (typeof value !== 'string' || !value.trim()) return [];
    return value.split(',').map(part => part.trim()).filter(Boolean);
}

/**
 * Accent-insensitive value suitable for search and comparison.
 * @param {string|null|undefined} value
 * @returns {string}
 */
export function normalizeAscii(value) {
    return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

/**
 * Normalizes text.
 * @param {string|null|undefined} value
 * @returns {string}
 */
export function normalizeText(value) {
    return String(value ?? '').normalize('NFD').replace(/([A-Za-z])[\u0300-\u036f]/g, '$1').toLowerCase().trim();
}

export const DEWEY_DEFAULT_COLORS = Object.freeze([
    '#000000', '#9e6633', '#f20000', '#ff9813', '#ffee00',
    '#409d42', '#0fafe9', '#98238b', '#d3d5d4', '#ffffff'
]);

/**
 * Returns the status class.
 * @param {string} status
 * @returns {string}
 */
export function itemStatusClass(status) {
    // @ts-ignore
    return `bg-${ITEM_STATUS_META[status]?.color || 'secondary'}`;
}

export const AUDIENCE_VALUES = Object.freeze(['child', 'youth', 'adult']);
export const BINDING_TYPE_VALUES = Object.freeze(['hardcover', 'paperback', 'spiral', 'other']);

/** Stable bibliographic identifier types returned by the API. */
export const IDENTIFIER_TYPES = Object.freeze({
    ISBN: 'isbn',
    ISSN: 'issn',
});

export const isPeriodicalIdentifier = (identifierType) =>
    String(identifierType || '').toLowerCase() === IDENTIFIER_TYPES.ISSN;

/**
 * Detect a periodical from a complete bibliographic record.
 *
 * Some imported/manual periodicals have no ISSN (or have an identifier stored
 * without the `issn:` prefix), so checking identifier_type alone is not enough
 * to decide whether an item's call_number is actually an issue number.
 */
export const isPeriodicalRecord = (record) => {
    if (!record) return false;

    const identifierType = record.identifier_type || record.identifierType;
    const identifier = record.isbn || record.isbn_value || record.issn || '';
    if (isPeriodicalIdentifier(identifierType) || /^issn:/i.test(String(identifier))) {
        return true;
    }

    const medium = normalizeText(record.medium_type || record.mediumType);
    return ['periodique', 'periodical', 'magazine', 'journal', 'revue'].some(
        value => medium === value || medium.startsWith(`${value} /`)
    );
};

/**
 * Format authors.
 * @param {string[]|string|null|undefined} value
 * @returns {string}
 */
export function formatAuthors(value) {
    return Array.isArray(value) ? value.join(', ') : String(value ?? '');
}

export const ITEM_STATUS_META = Object.freeze({
    available: Object.freeze({ color: 'success' }),
    on_loan: Object.freeze({ color: 'primary' }),
    on_hold: Object.freeze({ color: 'warning' }),
    in_repair: Object.freeze({ color: 'secondary' }),
    lost: Object.freeze({ color: 'danger' }),
    withdrawn: Object.freeze({ color: 'dark' }),
});

