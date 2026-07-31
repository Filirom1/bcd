import { describe, expect, it } from 'vitest';

import { autoTextColor } from '../../../src/bcd_web_vue/js/utils/colors.js';

describe('autoTextColor', () => {
    it('uses black text on light colours', () => {
        expect(autoTextColor('#ffffff')).toBe('#000000');
        expect(autoTextColor('#f2bf33')).toBe('#000000');
    });

    it('uses white text on dark colours', () => {
        expect(autoTextColor('#000000')).toBe('#ffffff');
        expect(autoTextColor('#003366')).toBe('#ffffff');
    });
});
