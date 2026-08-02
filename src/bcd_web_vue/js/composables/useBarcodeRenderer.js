import { getBarcodeLibrary } from '../vendor/jsbarcode-adapter.js';

const { ref } = Vue;

/**
 * Composable for rendering barcodes using JsBarcode library.
 *
 * Provides a reusable function to render all barcodes on a page,
 * respecting system settings for barcode format.
 */
export function useBarcodeRenderer() {
    /**
     * Render all barcodes on the page.
     * Searches for SVG elements with class 'barcode' and data-code attribute.
     *
     * @param {Object} options - JsBarcode options to override defaults
     * @param {string} options.format - Barcode format (CODE39, CODE128, etc.)
     * @param {number} options.width - Bar width
     * @param {number} options.height - Barcode height in pixels
     * @param {boolean} options.displayValue - Show text below barcode
     * @param {number} options.margin - Margin around barcode
     */
    const renderBarcodes = async (options = {}) => {
        const JsBarcode = await getBarcodeLibrary();
        const defaults = {
            format: 'CODE39',
            width: 2,
            height: 50,
            displayValue: false,
            margin: 0
        };

        const barcodeOptions = { ...defaults, ...options };

        document.querySelectorAll('.barcode').forEach((svg) => {
            if (svg.dataset.code) {
                JsBarcode(svg, svg.dataset.code, barcodeOptions);
            }
        });
    };

    return { renderBarcodes };
}
