// @ts-check

/**
 * Event Bus utility for lightweight, decoupled inter-component communication.
 * 
 * CRITICAL ARCHITECTURAL RULE:
 * This Event Bus must strictly be limited to TRIGGERING REFRESHES (e.g., 'catalog:refresh', 'borrowers:refresh').
 * 
 * - DO NOT use this Event Bus to pass business data, objects, or complex states.
 * - For state and data flow, use standard Vue 3 mechanisms: props (down), native Vue events (up), 
 *   or reactive shared composables/stores (e.g., useAppState).
 * - This prevents the codebase from turning into hard-to-debug "spaghetti code" and maintains 
 *   a clear, single source of truth.
 */

/** @type {Record<string, Array<(...args: any[]) => void>>} */
const listeners = {};

/**
 * Event Bus utility for lightweight, decoupled inter-component communication.
 */
export const events = {
    /**
     * Subscribe to an event
     * @param {string} eventName
     * @param {(...args: any[]) => void} callback
     * @returns {() => void} unsubscribe function
     */
    on(eventName, callback) {
        if (!listeners[eventName]) {
            listeners[eventName] = [];
        }
        listeners[eventName].push(callback);
        return () => this.off(eventName, callback);
    },

    /**
     * Unsubscribe from an event
     * @param {string} eventName
     * @param {(...args: any[]) => void} callback
     */
    off(eventName, callback) {
        if (!listeners[eventName]) return;
        listeners[eventName] = listeners[eventName].filter(cb => cb !== callback);
    },

    /**
     * Emit an event to all subscribers
     * @param {string} eventName
     * @param {...any} args
     */
    emit(eventName, ...args) {
        if (!listeners[eventName]) return;
        // Create a copy of the list of listeners to prevent modification during iteration
        const eventListeners = [...listeners[eventName]];
        eventListeners.forEach(callback => {
            try {
                callback(...args);
            } catch (error) {
                console.error(`Error in event listener for ${eventName}:`, error);
            }
        });
    }
};
