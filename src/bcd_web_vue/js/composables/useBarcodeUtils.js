/**
 * Barcode Utilities Composable
 * Helper functions for working with barcodes and IDs
 */

import { useBorrowerData } from './useBorrowerData.js';

export function useBarcodeUtils() {
    const { fetchSettings } = useBorrowerData();

    /**
     * Strip barcode prefix from a barcode to get the ID
     * @param {string} barcode - The full barcode (e.g., ".101")
     * @param {string} prefix - The barcode prefix from settings (e.g., ".")
     * @returns {string} - The ID without prefix (e.g., "101")
     */
    const stripBarcodePrefix = (barcode, prefix) => {
        if (!barcode || !prefix) {
            return barcode;
        }

        const trimmedBarcode = barcode.trim();
        const trimmedPrefix = prefix.trim();

        if (trimmedBarcode.startsWith(trimmedPrefix)) {
            return trimmedBarcode.substring(trimmedPrefix.length);
        }

        return trimmedBarcode;
    };

    /**
     * Add barcode prefix to an ID to get the full barcode
     * @param {string} id - The ID (e.g., "101")
     * @param {string} prefix - The barcode prefix from settings (e.g., ".")
     * @returns {string} - The full barcode (e.g., ".101")
     */
    const addBarcodePrefix = (id, prefix) => {
        if (!id || !prefix) {
            return id;
        }

        return `${prefix.trim()}${id.trim()}`;
    };

    /**
     * Normalize input to ID (strip prefix if present)
     * Useful when accepting input that could be either a barcode or an ID
     * @param {string} input - User input (could be barcode or ID)
     * @param {string} borrowerPrefix - Borrower barcode prefix
     * @param {string} itemPrefix - Item barcode prefix
     * @returns {string} - The ID without prefix
     */
    const normalizeToId = (input, borrowerPrefix, itemPrefix) => {
        if (!input) {
            return input;
        }

        const trimmedInput = input.trim();

        // Try stripping borrower prefix
        if (borrowerPrefix) {
            const withoutBorrowerPrefix = stripBarcodePrefix(trimmedInput, borrowerPrefix);
            if (withoutBorrowerPrefix !== trimmedInput) {
                return withoutBorrowerPrefix;
            }
        }

        // Try stripping item prefix
        if (itemPrefix) {
            const withoutItemPrefix = stripBarcodePrefix(trimmedInput, itemPrefix);
            if (withoutItemPrefix !== trimmedInput) {
                return withoutItemPrefix;
            }
        }

        // No prefix found, return as-is
        return trimmedInput;
    };

    return {
        stripBarcodePrefix,
        addBarcodePrefix,
        normalizeToId,
        fetchSettings
    };
}
