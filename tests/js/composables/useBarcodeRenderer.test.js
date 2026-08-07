import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useBarcodeRenderer } from '../../../src/bcd_web_vue/js/composables/useBarcodeRenderer.js';

const barcodeStub = vi.fn();

beforeEach(() => {
    // Clear DOM body
    document.body.innerHTML = '';
    barcodeStub.mockClear();
    vi.stubGlobal('JsBarcode', barcodeStub);
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('useBarcodeRenderer', () => {
    it('calls JsBarcode on elements matching class with correct dataset', async () => {
        // Add matching and non-matching elements to DOM
        document.body.innerHTML = `
            <svg class="barcode" data-code="BCD000123"></svg>
            <svg class="barcode" data-code="BCD000456"></svg>
            <svg class="no-barcode" data-code="BCD000789"></svg>
        `;

        const renderer = useBarcodeRenderer();
        await renderer.renderBarcodes({ format: 'CODE128', height: 40 });

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

    it('calls JsBarcode on elements only within specified container', async () => {
        document.body.innerHTML = `
            <div id="container-1">
                <svg class="barcode" data-code="BCD000123"></svg>
            </div>
            <div id="container-2">
                <svg class="barcode" data-code="BCD000456"></svg>
            </div>
        `;

        const renderer = useBarcodeRenderer();
        await renderer.renderBarcodes({ format: 'CODE128', height: 40 }, '#container-1');

        expect(barcodeStub).toHaveBeenCalledTimes(1);
        expect(barcodeStub).toHaveBeenCalledWith(
            document.querySelector('#container-1 .barcode'),
            'BCD000123',
            expect.any(Object)
        );
    });
});
