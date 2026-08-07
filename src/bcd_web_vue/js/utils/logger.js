/**
 * Small production-safe logger. Debug output is opt-in so normal use never
 * writes business data or development traces to the browser console.
 */
const debugEnabled = () => globalThis.__BCD_DEBUG__ === true;

export const logger = {
    debug(message) {
        if (debugEnabled()) console.debug(`[BCD] ${message}`);
    },
    error(message, error) {
        // Keep diagnostics useful without serialising request payloads.
        if (debugEnabled() && error) console.error(`[BCD] ${message}`, error);
    }
};
