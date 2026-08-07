import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { downloadBlob } from '../../../src/bcd_web_vue/js/utils/download.js';

describe('downloadBlob', () => {
    let mockCreateObjectURL;
    let mockRevokeObjectURL;

    beforeEach(() => {
        mockCreateObjectURL = vi.fn(() => 'blob:http://localhost/mock-uuid');
        mockRevokeObjectURL = vi.fn();

        globalThis.URL.createObjectURL = mockCreateObjectURL;
        globalThis.URL.revokeObjectURL = mockRevokeObjectURL;
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('downloads the blob, appends anchor, clicks it, and cleans up completely', () => {
        const blob = new Blob(['hello world'], { type: 'text/plain' });
        const appendSpy = vi.spyOn(document.body, 'appendChild');
        const removeSpy = vi.spyOn(document.body, 'removeChild');

        // Spy on document.createElement specifically for 'a'
        const originalCreateElement = document.createElement.bind(document);
        const clickSpy = vi.fn();
        vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
            if (tagName === 'a') {
                const el = originalCreateElement('a');
                el.click = clickSpy;
                return el;
            }
            return originalCreateElement(tagName);
        });

        downloadBlob(blob, 'hello.txt');

        expect(mockCreateObjectURL).toHaveBeenCalledWith(blob);
        expect(appendSpy).toHaveBeenCalled();
        expect(clickSpy).toHaveBeenCalled();
        expect(removeSpy).toHaveBeenCalled();
        expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-uuid');
    });

    it('guarantees cleanup even if click throws an error', () => {
        const blob = new Blob(['hello world'], { type: 'text/plain' });
        const removeSpy = vi.spyOn(document.body, 'removeChild');

        const originalCreateElement = document.createElement.bind(document);
        vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
            if (tagName === 'a') {
                const el = originalCreateElement('a');
                el.click = () => {
                    throw new Error('Click failed');
                };
                return el;
            }
            return originalCreateElement(tagName);
        });

        expect(() => downloadBlob(blob, 'hello.txt')).toThrow('Click failed');

        // Cleanup must still run
        expect(removeSpy).toHaveBeenCalled();
        expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-uuid');
    });
});
