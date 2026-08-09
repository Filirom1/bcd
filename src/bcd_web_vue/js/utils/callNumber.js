/**
 * Call Number Generation Engine (Moteur de génération de cote)
 * Handles all pure logic for generating call numbers and suggesting shelf locations
 * @ts-check
 */

import { normalizeAscii } from './domain.js';

/**
 * @param {string[]|null|undefined} authors
 * @returns {string}
 */
export function computeAut1(authors) {
    if (!authors || !authors.length) return '';
    const first = authors[0];
    const lastName = (first.includes(',') ? first.split(',')[0] : first.split(' ').slice(-1)[0]).trim();
    const cleanLastName = normalizeAscii(lastName).toUpperCase().replace(/[^A-Z]/g, '');
    return cleanLastName.slice(0, 1);
}

/**
 * @param {string[]|null|undefined} authors
 * @returns {string}
 */
export function computeAut3(authors) {
    if (!authors || !authors.length) return '';
    const first = authors[0];
    const lastName = (first.includes(',') ? first.split(',')[0] : first.split(' ').slice(-1)[0]).trim();
    const cleanLastName = normalizeAscii(lastName).toUpperCase().replace(/[^A-Z]/g, '');
    return cleanLastName.slice(0, 3);
}

/**
 * Clean string by stripping leading articles and trimming
 * @param {string|null|undefined} text
 * @returns {string}
 */
export function stripLeadingArticles(text) {
    if (!text) return '';
    let s = text.trim();
    const articles = [
        /^(les?|la|l'|une?|des?|d')\s+/i,
        /^(the|an?)\s+/i,
        /^l'/i,
        /^d'/i
    ];
    for (const re of articles) {
        if (re.test(s)) {
            s = s.replace(re, '');
            break;
        }
    }
    return s;
}

/**
 * SER1: first 1 uppercase letter/digit of series/collection name (fallback to AUT1 if empty)
 * @param {string|null|undefined} collection
 * @param {string} fallbackAut1
 * @returns {string}
 */
export function computeSer1(collection, fallbackAut1) {
    if (!collection || !collection.trim()) return fallbackAut1;
    const cleaned = stripLeadingArticles(collection);
    const normalized = normalizeAscii(cleaned).toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 1) || fallbackAut1;
}

/**
 * SER3: first 3 uppercase letters/digits of series/collection name (fallback to AUT3 if empty)
 * @param {string|null|undefined} collection
 * @param {string} fallbackAut3
 * @returns {string}
 */
export function computeSer3(collection, fallbackAut3) {
    if (!collection || !collection.trim()) return fallbackAut3;
    const cleaned = stripLeadingArticles(collection);
    const normalized = normalizeAscii(cleaned).toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 3) || fallbackAut3;
}

/**
 * TIT1: first 1 uppercase letter/digit of title (NFD-normalized, no accents, only A-Z0-9, ignoring leading articles)
 * @param {string|null|undefined} title
 * @returns {string}
 */
export function computeTit1(title) {
    if (!title) return '';
    const cleaned = stripLeadingArticles(title);
    const normalized = normalizeAscii(cleaned).toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 1);
}

/**
 * TIT3: first 3 uppercase letters/digits of title (NFD-normalized, no accents, only A-Z0-9, ignoring leading articles)
 * @param {string|null|undefined} title
 * @returns {string}
 */
export function computeTit3(title) {
    if (!title) return '';
    const cleaned = stripLeadingArticles(title);
    const normalized = normalizeAscii(cleaned).toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 3);
}

/**
 * Suggest a shelf location based on medium type matching the available options
 * @param {string|null|undefined} mediumType
 * @param {any[]|null|undefined} locations
 * @returns {string}
 */
export function suggestShelfLocation(mediumType, locations) {
    if (!locations || !locations.length) return '';
    
    const norm = (/** @type {string|null|undefined} */ s) => s ? normalizeAscii(s).toLowerCase().replace(/s$/, '').trim() : '';
    const query = norm(mediumType);
    
    const found = locations.find((/** @type {any} */ l) => norm(l.label) === query);
    return found ? found.label : '';
}

/**
 * Check if string matches wildcard rule (e.g. "Documentaires*") without RegExp
 * @param {string} str
 * @param {string} rule
 * @returns {boolean}
 */
export function matchWildcard(str, rule) {
    if (rule.startsWith('*') && rule.endsWith('*')) {
        return str.includes(rule.slice(1, -1));
    }
    if (rule.endsWith('*')) {
        return str.startsWith(rule.slice(0, -1));
    }
    if (rule.startsWith('*')) {
        return str.endsWith(rule.slice(1));
    }
    return str === rule;
}

/**
 * Computes a suggested call number based on dynamic settings rules.
 * @param {import('../models/item.js').BibliographicRecord} record - Bibliographic record details
 * @param {string} [currentShelf] - Current selected shelf location
 * @param {any[]} [rules] - Rules list from settings
 * @returns {string} Suggested call number
 */
export function computeCallNumber(record, currentShelf = '', rules = []) {
    const aut1 = computeAut1(record.authors);
    const aut3 = computeAut3(record.authors);
    const ser1 = computeSer1(record.collection, aut1);
    const ser3 = computeSer3(record.collection, aut3);
    const ill1 = computeAut1(record.illustrators) || aut1;
    const ill3 = computeAut3(record.illustrators) || aut3;
    const tit1 = computeTit1(record.title);
    const tit3 = computeTit3(record.title);
    const dewey = record.deweyNumber ? record.deweyNumber.trim() : '';
    const mediumType = record.mediumType ? record.mediumType.trim() : '';
    const shelf = currentShelf ? currentShelf.trim() : '';

    // Find first matching rule
    const matchedRule = rules.find(rule => {
        if (rule.medium_type) {
            const ruleMedium = rule.medium_type.trim().toLowerCase();
            const itemMedium = mediumType.toLowerCase();
            if (!matchWildcard(itemMedium, ruleMedium)) {
                return false;
            }
        }
        if (rule.shelf_location) {
            const ruleShelf = rule.shelf_location.trim().toLowerCase();
            const itemShelf = shelf.toLowerCase();
            if (!matchWildcard(itemShelf, ruleShelf)) {
                return false;
            }
        }
        return true;
    });

    if (!matchedRule) {
        return aut3;
    }

    const pattern = matchedRule.pattern || '';
    if (!pattern.trim()) {
        return '';
    }

    return pattern
        .replace(/{AUT1}/g, aut1)
        .replace(/{AUT3}/g, aut3)
        .replace(/{SER1}/g, ser1)
        .replace(/{SER3}/g, ser3)
        .replace(/{ILL1}/g, ill1)
        .replace(/{ILL3}/g, ill3)
        .replace(/{TIT1}/g, tit1)
        .replace(/{TIT3}/g, tit3)
        .replace(/{DEWEY}/g, dewey)
        .trim()
        .replace(/\s+/g, ' ');
}
