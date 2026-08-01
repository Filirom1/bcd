/**
 * Robust localStorage Adapter Utility
 * Centralizes localStorage access, exception handling, and JSON serialization.
 */

const PREFIX = 'bcd_';

/**
 * Prefix a key to avoid namespace collisions.
 * @param {string} key
 * @returns {string} Prefixed key
 */
function getPrefixedKey(key) {
    if (key.startsWith(PREFIX)) return key;
    return `${PREFIX}${key}`;
}

/**
 * Safely get a raw string value from localStorage.
 * @param {string} key
 * @param {any} fallback
 * @returns {string|any}
 */
export function getItem(key, fallback = null) {
    try {
        const value = localStorage.getItem(getPrefixedKey(key));
        return value !== null ? value : fallback;
    } catch (e) {
        console.warn(`localStorage.getItem('${key}') blocked by browser:`, e.message);
        return fallback;
    }
}

/**
 * Safely set a raw string value in localStorage.
 * @param {string} key
 * @param {string} value
 */
export function setItem(key, value) {
    try {
        localStorage.setItem(getPrefixedKey(key), value);
    } catch (e) {
        console.warn(`localStorage.setItem('${key}') blocked by browser:`, e.message);
    }
}

/**
 * Safely remove a value from localStorage.
 * @param {string} key
 */
export function removeItem(key) {
    try {
        localStorage.removeItem(getPrefixedKey(key));
    } catch (e) {
        console.warn(`localStorage.removeItem('${key}') blocked by browser:`, e.message);
    }
}

/**
 * Safely get and parse a JSON value from localStorage.
 * @param {string} key
 * @param {any} fallback
 * @returns {any}
 */
export function getJSON(key, fallback = null) {
    const val = getItem(key);
    if (val === null) return fallback;
    try {
        return JSON.parse(val);
    } catch (e) {
        console.error(`Failed to parse stored JSON for key '${key}':`, e);
        return fallback;
    }
}

/**
 * Safely stringify and set a JSON value in localStorage.
 * @param {string} key
 * @param {any} value
 */
export function setJSON(key, value) {
    try {
        setItem(key, JSON.stringify(value));
    } catch (e) {
        console.error(`Failed to serialize JSON for key '${key}':`, e);
    }
}

/**
 * Clear all localStorage items that have the BCD prefix.
 */
export function clearStorage() {
    try {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(PREFIX)) {
                keysToRemove.push(key);
            }
        }
        for (const key of keysToRemove) {
            localStorage.removeItem(key);
        }
    } catch (e) {
        console.warn('localStorage.clear blocked by browser:', e.message);
    }
}
