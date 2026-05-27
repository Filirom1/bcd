/**
 * useItemBadge composable
 *
 * Returns helper functions to render shelf-location and call-number badges
 * based on the current system settings (catalog_shelf_locations, dewey_colors).
 *
 * Badge shape convention:
 *   - Shelf location : border-radius 4px  (square)
 *   - Call number    : border-radius 20px (rounded pill)
 *
 * Color logic for shelf badge:
 *   - label found in catalog_shelf_locations AND color is a non-null hex → colored badge
 *   - label found but color is null → neutral gray (bg-light, border)
 *   - label NOT in the list          → Bootstrap secondary gray (#6c757d)
 *
 * Usage:
 *   const { getShelfBadge, getCoteBadge } = useItemBadge(settings);
 *   // settings is a Vue ref or reactive containing the SystemSettings object
 */

import { autoTextColor } from '../utils/colors.js';

const { computed } = Vue;

/**
 * @param {import('vue').Ref} settings - ref to the SystemSettings object (may be null)
 * @returns {{ getShelfBadge: Function, getCoteBadge: Function }}
 */
export function useItemBadge(settings) {
    // Parse catalog_shelf_locations once per settings change
    const shelfLocations = computed(() => {
        const raw = settings.value?.catalog_shelf_locations;
        if (!raw) return [];
        try {
            return JSON.parse(raw);
        } catch {
            return [];
        }
    });

    // Parse dewey_colors (10-element array of hex strings)
    const deweyColors = computed(() => {
        const raw = settings.value?.dewey_colors;
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    });

    /**
     * Returns an inline style object for a shelf-location badge.
     * @param {string|null} label
     * @returns {{ background: string, color: string, border?: string, borderRadius: string }}
     */
    function getShelfBadge(label) {
        const base = { borderRadius: '4px', padding: '2px 6px', fontSize: '.75rem', fontWeight: '600', display: 'inline-block' };
        if (!label) return null;

        const entry = shelfLocations.value.find(e => e.label === label);

        if (!entry) {
            // Unknown location — transparent with border
            return { ...base, background: 'transparent', color: 'inherit', border: '1px solid currentColor' };
        }

        if (!entry.color) {
            // Known location without color — transparent
            return { ...base, background: 'transparent', color: 'inherit', border: '1px solid currentColor' };
        }

        // Known location with color
        return { ...base, background: entry.color, color: autoTextColor(entry.color) };
    }

    /**
     * Returns an inline style object for a call-number (cote) badge.
     * Color is derived from the first digit of the Dewey number in call_number.
     * @param {string|null} callNumber
     * @returns {{ background: string, color: string, borderRadius: string }|null}
     */
    function getCoteBadge(callNumber) {
        const base = { borderRadius: '20px', padding: '2px 8px', fontSize: '.75rem', fontWeight: '600', display: 'inline-block' };
        if (!callNumber) return null;

        const firstChar = callNumber.trim()[0];
        const colors = deweyColors.value;

        if (firstChar >= '0' && firstChar <= '9' && colors && colors.length === 10) {
            const idx = parseInt(firstChar);
            const hex = colors[idx] || null;
            if (!hex) return { ...base, background: 'transparent', color: 'inherit', border: '1px solid currentColor' };
            const outline = (hex === '#ffffff' || hex === '#fff') ? '1px solid #ddd' : 'none';
            return { ...base, background: hex, color: autoTextColor(hex), outline };
        }

        // No Dewey color — transparent
        return { ...base, background: 'transparent', color: 'inherit', border: '1px solid currentColor' };
    }

    return { getShelfBadge, getCoteBadge };
}
