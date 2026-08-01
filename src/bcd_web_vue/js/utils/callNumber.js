/**
 * Call Number Generation Engine (Moteur de génération de cote)
 * Handles all pure logic for generating call numbers and suggesting shelf locations
 */

// AUT1: first 1 uppercase letter of author's last name (NFD-normalized, no accents, only A-Z)
export function computeAut1(authors) {
    if (!authors || !authors.length) return '';
    const first = authors[0];
    const lastName = (first.includes(',') ? first.split(',')[0] : first.split(' ').slice(-1)[0]).trim();
    const cleanLastName = lastName.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z]/g, '');
    return cleanLastName.slice(0, 1);
}

// AUT3: first 3 uppercase letters of author's last name (NFD-normalized, no accents, only A-Z)
export function computeAut3(authors) {
    if (!authors || !authors.length) return '';
    const first = authors[0];
    const lastName = (first.includes(',') ? first.split(',')[0] : first.split(' ').slice(-1)[0]).trim();
    const cleanLastName = lastName.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z]/g, '');
    return cleanLastName.slice(0, 3);
}

// Clean string by stripping leading articles and trimming
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

// SER1: first 1 uppercase letter/digit of series/collection name (fallback to AUT1 if empty)
export function computeSer1(collection, fallbackAut1) {
    if (!collection || !collection.trim()) return fallbackAut1;
    const cleaned = stripLeadingArticles(collection);
    const normalized = cleaned.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 1) || fallbackAut1;
}

// SER3: first 3 uppercase letters/digits of series/collection name (fallback to AUT3 if empty)
export function computeSer3(collection, fallbackAut3) {
    if (!collection || !collection.trim()) return fallbackAut3;
    const cleaned = stripLeadingArticles(collection);
    const normalized = cleaned.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 3) || fallbackAut3;
}

// TIT1: first 1 uppercase letter/digit of title (NFD-normalized, no accents, only A-Z0-9, ignoring leading articles)
export function computeTit1(title) {
    if (!title) return '';
    const cleaned = stripLeadingArticles(title);
    const normalized = cleaned.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 1);
}

// TIT3: first 3 uppercase letters/digits of title (NFD-normalized, no accents, only A-Z0-9, ignoring leading articles)
export function computeTit3(title) {
    if (!title) return '';
    const cleaned = stripLeadingArticles(title);
    const normalized = cleaned.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    return normalized.slice(0, 3);
}

// Suggest a shelf location based on medium type matching the available options
export function suggestShelfLocation(mediumType, locations) {
    if (!locations || !locations.length) return '';
    
    const norm = (s) => s ? s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/s$/, '').trim() : '';
    const query = norm(mediumType);
    
    const found = locations.find(l => norm(l.label) === query);
    return found ? found.label : '';
}

// Check if string matches wildcard rule (e.g. "Documentaires*") without RegExp
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
 * @param {Object} record - Bibliographic record details
 * @param {string} currentShelf - Current selected shelf location
 * @param {Array} rules - Rules list from settings
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
