import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';

import { useAppState } from '../../../src/bcd_web_vue/js/composables/useAppState.js';

beforeEach(() => {
    localStorage.clear();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
});

describe('useAppState', () => {
    it('initializes with default locale and persists updates', async () => {
        const state = useAppState();

        // Default should be fr
        expect(state.locale.value).toBe('fr');

        state.setLocale('en');
        await nextTick();

        expect(state.locale.value).toBe('en');
        expect(localStorage.getItem('bcd_locale')).toBe('en');
        expect(document.documentElement.lang).toBe('en');
    });

    it('toggles locale correctly', async () => {
        const state = useAppState();
        state.setLocale('fr');
        await nextTick();

        state.toggleLocale();
        await nextTick();

        expect(state.locale.value).toBe('en');

        state.toggleLocale();
        await nextTick();

        expect(state.locale.value).toBe('fr');
    });

    it('persists and loads settings', async () => {
        const state = useAppState();
        const mockSettings = { library_name: 'School Lib' };

        state.saveSettings(mockSettings);
        expect(state.settings.value).toEqual(mockSettings);
        expect(JSON.parse(localStorage.getItem('bcd_settings'))).toEqual(mockSettings);

        // Clear reactive state and re-load to simulate page reload
        state.clearStorage();
        expect(state.settings.value).toBeNull();

        localStorage.setItem('bcd_settings', JSON.stringify(mockSettings));
        state.loadSettings();
        expect(state.settings.value).toEqual(mockSettings);
    });

    it('safely handles browser blocking localStorage exceptions', () => {
        // Mock localStorage.getItem to throw error (simulates Safari in Private Mode or privacy extensions)
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
            throw new Error('SecurityError: The operation is insecure.');
        });
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
            throw new Error('SecurityError: The operation is insecure.');
        });

        // Should not crash and fallback gracefully to default values
        const state = useAppState();
        expect(state.locale.value).toBe('fr');

        expect(() => state.saveSettings({ foo: 'bar' })).not.toThrow();
    });
});
