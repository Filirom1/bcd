import { describe, expect, it } from 'vitest';

import {
    autoTextColor,
    getThemeFontSize,
    getThemeRadius,
    getThemeRgbaColor,
    getThemeRgbColor,
    getThemeToken
} from '../../../src/bcd_web_vue/js/utils/colors.js';

describe('autoTextColor', () => {
    it('uses black text on light colours', () => {
        expect(autoTextColor('#ffffff')).toBe('#000000');
        expect(autoTextColor('#f2bf33')).toBe('#000000');
    });

    it('uses white text on dark colours', () => {
        expect(autoTextColor('#000000')).toBe('#ffffff');
        expect(autoTextColor('#003366')).toBe('#ffffff');
    });

    it('reads shared theme tokens and resolves RGB colors', () => {
        expect(getThemeToken('chart-muted')).toBe('#94a3b8');
        expect(getThemeRgbColor('primary')).toBe('rgb(2, 132, 199)');
        expect(getThemeRgbaColor('primary', 0.27)).toBe('rgba(2, 132, 199, 0.27)');
        expect(getThemeFontSize('chart')).toBe(11);
        expect(getThemeRadius('sm')).toBe(4);
    });

    it('reports missing theme tokens explicitly', () => {
        expect(() => getThemeToken('missing-token')).toThrow(
            'Missing required BCD theme token: --bcd-missing-token'
        );
    });

    it('rejects opacity outside the supported range', () => {
        expect(() => getThemeRgbaColor('primary', 1.1)).toThrow(RangeError);
    });
});
