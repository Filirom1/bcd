import { describe, expect, it } from 'vitest';
import { DEWEY_DEFAULT_COLORS, ITEM_STATUS_META, normalizeText, parseCsv } from '../../../src/bcd_web_vue/js/utils/domain.js';

describe('domain utilities', () => {
    it('parses comma-separated values with whitespace and empties', () => {
        expect(parseCsv('  roman, , poésie,, théâtre ')).toEqual(['roman', 'poésie', 'théâtre']);
        expect(parseCsv('')).toEqual([]);
        expect(parseCsv(['a', '', 'b'])).toEqual(['a', 'b']);
    });

    it('normalizes accents, apostrophes and non-Latin text safely', () => {
        expect(normalizeText("Été d'été")).toBe("ete d'ete");
        expect(normalizeText('Русский 東京')).toBe('русский 東京'.normalize('NFD'));
        expect(normalizeText(null)).toBe('');
    });

    it('exposes one immutable source of truth for item statuses and Dewey colors', () => {
        expect(DEWEY_DEFAULT_COLORS).toHaveLength(10);
        expect(ITEM_STATUS_META.available.color).toBe('success');
        expect(Object.isFrozen(DEWEY_DEFAULT_COLORS)).toBe(true);
    });
});
