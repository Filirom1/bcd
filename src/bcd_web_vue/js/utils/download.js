// @ts-check

/**
 * Downloads a Blob as a file with the given filename.
 * Guarantees cleanup of the object URL and removal of the link from DOM.
 *
 * @param {Blob} blob - The blob to download.
 * @param {string} filename - The target filename.
 */
export function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    try {
        a.click();
    } finally {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
}
