/**
 * Small runtime adapter for JsBarcode.
 *
 * Development keeps using the browser global served from node_modules. Vite
 * bundles the fallback import into a lazy chunk for production, so barcode
 * code is not part of the initial application payload.
 */
let barcodeLibrary;

export async function getBarcodeLibrary() {
    if (barcodeLibrary) return barcodeLibrary;

    if (typeof globalThis.JsBarcode === 'function') {
        barcodeLibrary = globalThis.JsBarcode;
    } else {
        barcodeLibrary = (await import('jsbarcode')).default;
    }

    return barcodeLibrary;
}
