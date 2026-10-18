// @ts-check
/**
 * Color utilities
 */

/**
 * Returns '#000000' or '#ffffff' depending on the luminance of the given hex color,
 * so that text remains readable on colored backgrounds.
 * @param {string} hex - Hex color code (e.g. '#4D99F2')
 * @returns {'#000000'|'#ffffff'}
 */
export function autoTextColor(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55 ? '#000000' : '#ffffff';
}

/**
 * Read a required BCD theme token from the document root.
 * @param {string} token
 * @returns {string}
 */
export function getThemeToken(token) {
    const value = getComputedStyle(document.documentElement)
        .getPropertyValue(`--bcd-${token}`)
        .trim();
    if (!value) throw new Error(`Missing required BCD theme token: --bcd-${token}`);
    return value;
}

/**
 * Resolve a theme RGB token to a Canvas-compatible color.
 * @param {string} token
 * @returns {string}
 */
export function getThemeRgbColor(token) {
    return `rgb(${getThemeToken(`${token}-rgb`)})`;
}

/**
 * Resolve a theme RGB token with opacity for canvas/chart APIs.
 * @param {string} token
 * @param {number} alpha
 * @returns {string}
 */
export function getThemeRgbaColor(token, alpha) {
    if (!Number.isFinite(alpha) || alpha < 0 || alpha > 1) {
        throw new RangeError(`Theme color alpha must be between 0 and 1, received: ${alpha}`);
    }
    return `rgba(${getThemeToken(`${token}-rgb`)}, ${alpha})`;
}

/**
 * Resolve a theme radius token to pixels for canvas/chart APIs.
 * @param {string} token
 * @returns {number}
 */
export function getThemeRadius(token) {
    return getThemeLengthInPixels(getThemeToken(`radius-${token}`), `radius-${token}`);
}

/**
 * Resolve a theme font-size token to CSS pixels for canvas/chart APIs.
 * @param {string} token
 * @returns {number}
 */
export function getThemeFontSize(token) {
    return getThemeLengthInPixels(getThemeToken(`font-size-${token}`), `font-size-${token}`);
}

/**
 * @param {string} value
 * @param {string} token
 * @returns {number}
 */
function getThemeLengthInPixels(value, token) {
    const match = /^(\d*\.?\d+)(px|rem)$/.exec(value);
    if (!match) throw new Error(`Invalid BCD size token: --bcd-${token}`);

    const size = Number(match[1]);
    if (match[2] === 'px') return size;

    const rootSize = /^(\d*\.?\d+)px$/.exec(getThemeToken('root-font-size'));
    if (!rootSize) throw new Error('Invalid BCD root font-size token: --bcd-root-font-size');
    return size * Number(rootSize[1]);
}
