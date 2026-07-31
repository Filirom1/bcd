import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';

import {
    AVAILABLE_COLUMNS,
    useColumnSettings
} from '../../../src/bcd_web_vue/js/composables/useColumnSettings.js';

const STORAGE_KEY = 'bcd_catalog_columns';
const defaultColumns = AVAILABLE_COLUMNS.filter(column => column.default).map(column => column.id);

beforeEach(() => {
    localStorage.clear();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
});

describe('useColumnSettings', () => {
    it('uses the documented default column set when no preference is stored', () => {
        const settings = useColumnSettings();

        expect(settings.visibleColumns.value).toEqual(defaultColumns);
        expect(settings.isColumnVisible('title')).toBe(true);
        expect(settings.isColumnVisible('isbn')).toBe(false);
    });

    it('restores a saved preference', () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(['title', 'isbn']));

        const settings = useColumnSettings();

        expect(settings.visibleColumns.value).toEqual(['title', 'isbn']);
    });

    it('recovers from malformed persisted data by using defaults', () => {
        localStorage.setItem(STORAGE_KEY, '{not-json');

        const settings = useColumnSettings();

        expect(settings.visibleColumns.value).toEqual(defaultColumns);
    });

    it('persists toggles and can reset to defaults', async () => {
        const settings = useColumnSettings();

        settings.toggleColumn('isbn');
        await nextTick();
        expect(JSON.parse(localStorage.getItem(STORAGE_KEY))).toContain('isbn');

        settings.resetToDefaults();
        await nextTick();
        expect(settings.visibleColumns.value).toEqual(defaultColumns);
        expect(JSON.parse(localStorage.getItem(STORAGE_KEY))).toEqual(defaultColumns);
    });
});
