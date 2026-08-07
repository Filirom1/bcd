/**
 * Small production-safe logger. Debug output is opt-in so normal use never
 * writes business data or development traces to the browser console.
 * @ts-check
 */
// @ts-ignore
const debugEnabled = () => globalThis.__BCD_DEBUG__ === true;

export const logger = {
    /**
     * @param {string} message
     */
    debug(message) {
        if (debugEnabled()) console.debug(`[BCD] ${message}`);
    },
    /**
     * @param {string} message
     * @param {any} [error]
     */
    error(message, error) {
        // Keep diagnostics useful without serialising request payloads.
        if (debugEnabled() && error) console.error(`[BCD] ${message}`, error);
    }
};

