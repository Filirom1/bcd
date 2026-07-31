import { describe, expect, it } from 'vitest';

import { useBlockReasonTranslation } from '../../../src/bcd_web_vue/js/composables/useBlockReasonTranslation.js';

describe('useBlockReasonTranslation', () => {
    it('translates known database block reasons into localized keys', () => {
        const utils = useBlockReasonTranslation();

        expect(utils.translateBlockReason('Lost Book')).toBe('borrowers.reason_lost_book');
        expect(utils.translateBlockReason('Damaged Materials')).toBe('borrowers.reason_damaged');
        expect(utils.translateBlockReason('Other')).toBe('borrowers.reason_other');
    });

    it('falls back on the raw string for unknown or custom reasons', () => {
        const utils = useBlockReasonTranslation();

        expect(utils.translateBlockReason('Custom penalty reason')).toBe('Custom penalty reason');
        expect(utils.translateBlockReason('')).toBe('');
    });
});
