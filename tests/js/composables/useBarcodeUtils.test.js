import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useBarcodeUtils } from '../../../src/bcd_web_vue/js/composables/useBarcodeUtils.js';

describe('useBarcodeUtils', () => {
    it('strips barcode prefix correctly when prefix matches', () => {
        const utils = useBarcodeUtils();

        expect(utils.stripBarcodePrefix('.101', '.')).toBe('101');
        expect(utils.stripBarcodePrefix('101', '.')).toBe('101');
        expect(utils.stripBarcodePrefix('.101', null)).toBe('.101');
        expect(utils.stripBarcodePrefix('', '.')).toBe('');
    });

    it('adds barcode prefix correctly', () => {
        const utils = useBarcodeUtils();

        expect(utils.addBarcodePrefix('101', '.')).toBe('.101');
        expect(utils.addBarcodePrefix('101', null)).toBe('101');
        expect(utils.addBarcodePrefix('', '.')).toBe('');
    });

    it('normalizes inputs to IDs by stripping borrower or item prefixes', () => {
        const utils = useBarcodeUtils();

        // Strips borrower prefix (%)
        expect(utils.normalizeToId('%1001', '%', '.')).toBe('1001');

        // Strips item prefix (.)
        expect(utils.normalizeToId('.I-42', '%', '.')).toBe('I-42');

        // Leaves bare ID unmodified
        expect(utils.normalizeToId('1001', '%', '.')).toBe('1001');
        expect(utils.normalizeToId('', '%', '.')).toBe('');
    });
});
