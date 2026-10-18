// @ts-check
/**
 * useItemBadge composable
 *
 * Returns helper functions to render shelf-location and call-number badges
 * based on the current system settings (catalog_shelf_locations, dewey_colors).
 *
 * Badge shape convention:
 *   - Shelf location and call number use the shared compact radius.
 *
 * Color logic for shelf badge:
 *   - label found in catalog_shelf_locations AND color is a non-null hex → colored badge
 *   - label found but color is null → neutral gray (bg-light, border)
 *   - label NOT in the list          → transparent badge with a neutral outline
 *
 * Usage:
 *   const { getShelfBadge, getCoteBadge } = useItemBadge(settings);
 *   // settings is a Vue ref or reactive containing the SystemSettings object
 */

import { autoTextColor } from '../utils/colors.js';

const { computed } = Vue;
import { parseJsonSetting } from '../utils/domain.js';

const baseBadgeStyle = {
    borderRadius: 'var(--bcd-radius-sm)',
    fontSize: 'var(--bcd-font-size-xs)',
    fontWeight: '600',
    display: 'inline-block'
};

/**
 * @param {import('vue').Ref} settings - ref to the SystemSettings object (may be null)
 * @returns {{ getShelfBadge: Function, getCoteBadge: Function }}
 */
export function useItemBadge(settings) {
    // Parse catalog_shelf_locations once per settings change
    /** @type {import('vue').ComputedRef<Array<{label: string, color?: string}>>} */
    const shelfLocations = computed(() => parseJsonSetting(settings.value?.catalog_shelf_locations, []));

    // Parse dewey_colors (10-element array of hex strings)
    const deweyColors = computed(() => /** @type {string[]|null} */ (parseJsonSetting(settings.value?.dewey_colors, null)));
    const deweyEnabled = computed(() => settings.value?.dewey_colors_enabled !== false);

    /**
     * Returns an inline style object for a shelf-location badge.
     * @param {string|null} label
     * @returns {Record<string, string>|null}
     */
    function getShelfBadge(label) {
        const base = { ...baseBadgeStyle, padding: '2px 6px' };
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
     * @returns {Record<string, string>|null}
     */
    function getCoteBadge(callNumber) {
        const base = { ...baseBadgeStyle, padding: '2px 8px' };
        if (!callNumber) return null;

        const firstChar = callNumber.trim()[0];
        const colors = deweyColors.value;

        if (deweyEnabled.value && firstChar >= '0' && firstChar <= '9' && colors && colors.length === 10) {
            const idx = parseInt(firstChar);
            const hex = colors[idx] || null;
            if (!hex) return { ...base, background: 'transparent', color: 'inherit', border: '1px solid currentColor' };
            const outline = (hex === '#ffffff' || hex === '#fff') ? '1px solid var(--bcd-border)' : 'none';
            return { ...base, background: hex, color: autoTextColor(hex), outline };
        }

        // No Dewey color — transparent
        return { ...base, background: 'transparent', color: 'inherit', border: '1px solid currentColor' };
    }

    return { getShelfBadge, getCoteBadge };
}
