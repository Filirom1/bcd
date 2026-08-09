import { describe, expect, it } from 'vitest';

import {
    getLocalCivilDate,
    parseLocalCivilDate,
    formatCivilDate,
    formatDateTime
} from '../../../src/bcd_web_vue/js/utils/date.js';

describe('Date Utilities', () => {
    describe('getLocalCivilDate', () => {
        it('returns YYYY-MM-DD for a specified date using local time', () => {
            const date = new Date(2026, 7, 1); // August 1st, 2026 local time
            expect(getLocalCivilDate(date)).toBe('2026-08-01');
        });
    });

    describe('parseLocalCivilDate', () => {
        it('parses YYYY-MM-DD correctly without UTC shift', () => {
            const parsed = parseLocalCivilDate('2026-08-01');
            expect(parsed).not.toBeNull();
            expect(parsed.getFullYear()).toBe(2026);
            expect(parsed.getMonth()).toBe(7); // 0-indexed August
            expect(parsed.getDate()).toBe(1);
        });

        it('returns null for invalid strings', () => {
            expect(parseLocalCivilDate(null)).toBeNull();
            expect(parseLocalCivilDate('invalid')).toBeNull();
            expect(parseLocalCivilDate('2026-08')).toBeNull();
        });
    });

    describe('formatCivilDate', () => {
        it('formats localized dates correctly without timezone shift', () => {
            // French format usually like "1 août 2026" or "1 Aug 2026" depending on platform / env locale
            const formattedFr = formatCivilDate('2026-08-01', 'fr');
            expect(formattedFr).toContain('2026');
            expect(formattedFr).toContain('1');

            const formattedEn = formatCivilDate('2026-08-01', 'en');
            expect(formattedEn).toContain('2026');
            expect(formattedEn).toContain('1');
        });

        it('returns empty string for invalid dates', () => {
            expect(formatCivilDate('', 'fr')).toBe('');
            expect(formatCivilDate(null, 'fr')).toBe('');
        });
    });

    describe('formatDateTime', () => {
        it('formats ISO timestamps with time', () => {
            const ts = '2026-08-01T14:35:00';
            const formatted = formatDateTime(ts, 'en');
            expect(formatted).toContain('2026');
            expect(formatted).toContain('35');
        });
    });
});
