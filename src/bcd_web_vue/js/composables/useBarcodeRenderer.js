// @ts-check
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
     * Render all barcodes inside a specific container or on the entire page.
     *
     * @param {Object} [options] - JsBarcode options to override defaults
     * @param {string} [options.format] - Barcode format (CODE39, CODE128, etc.)
     * @param {number} [options.width] - Bar width
     * @param {number} [options.height] - Barcode height in pixels
     * @param {boolean} [options.displayValue] - Show text below barcode
     * @param {number} [options.margin] - Margin around barcode
     * @param {HTMLElement|{value: HTMLElement|null}|string|null} [container] - Container element, ref, or selector string to search within (defaults to document)
     */
    const renderBarcodes = async (options = {}, container = null) => {
        const JsBarcode = await getBarcodeLibrary();
        const defaults = {
            format: 'CODE39',
            width: 2,
            height: 50,
            displayValue: false,
            margin: 0
        };

        const barcodeOptions = { ...defaults, ...options };

        let root = /** @type {Document|Element} */ (document);
        if (container) {
            if (typeof container === 'string') {
                const found = document.querySelector(container);
                if (found) root = found;
            } else if (container && typeof container === 'object') {
                if ('value' in container) {
                    root = container.value || document;
                } else if (container instanceof HTMLElement) {
                    root = container;
                }
            }
        }

        const elements = /** @type {NodeListOf<HTMLElement>} */ (root.querySelectorAll('.barcode'));
        elements.forEach((svg) => {
            if (svg.dataset.code) {
                JsBarcode(svg, svg.dataset.code, barcodeOptions);
            }
        });
    };

    return { renderBarcodes };
}
