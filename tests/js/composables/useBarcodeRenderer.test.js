import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useBarcodeRenderer } from '../../../src/bcd_web_vue/js/composables/useBarcodeRenderer.js';

beforeEach(() => {
    // Clear DOM body
    document.body.innerHTML = '';
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('useBarcodeRenderer', () => {
    it('calls JsBarcode on elements matching class with correct dataset', () => {
        const barcodeStub = vi.fn();
        vi.stubGlobal('JsBarcode', barcodeStub);

        // Add matching and non-matching elements to DOM
        document.body.innerHTML = `
            <svg class="barcode" data-code="BCD000123"></svg>
            <svg class="barcode" data-code="BCD000456"></svg>
            <svg class="no-barcode" data-code="BCD000789"></svg>
        `;

        const renderer = useBarcodeRenderer();
        renderer.renderBarcodes({ format: 'CODE128', height: 40 });

        expect(barcodeStub).toHaveBeenCalledTimes(2);
        expect(barcodeStub).toHaveBeenNthCalledWith(
            1,
            document.querySelectorAll('.barcode')[0],
            'BCD000123',
            expect.objectContaining({ format: 'CODE128', height: 40 })
        );
        expect(barcodeStub).toHaveBeenNthCalledWith(
            2,
            document.querySelectorAll('.barcode')[1],
            'BCD000456',
            expect.objectContaining({ format: 'CODE128', height: 40 })
        );
    });
});
