/**
 * Color utilities
 */

/**
 * Returns '#000000' or '#ffffff' depending on the luminance of the given hex color,
 * so that text remains readable on colored backgrounds.
 */
export function autoTextColor(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55 ? '#000000' : '#ffffff';
}
