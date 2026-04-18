/**
 * Notification composable
 * Toast notification system with auto-dismiss
 */

const { ref, computed } = Vue;

// Global notifications state (shared across all component instances)
const notifications = ref([]);
let nextId = 1;

/**
 * Notification composable
 * @returns {Object} Notification methods
 */
export function useNotification() {
    /**
     * Add a notification
     * @param {string} type - success, error, warning, info
     * @param {string} message - Notification message
     * @param {string} [title] - Optional title
     * @param {number} [duration=5000] - Auto-dismiss duration (0 = no auto-dismiss)
     */
    const add = (type, message, title = null, duration = 5000) => {
        const notification = {
            id: nextId++,
            type,
            message,
            title: title || capitalize(type),
            duration,
            timestamp: new Date()
        };

        notifications.value.push(notification);

        return notification.id;
    };

    /**
     * Dismiss a notification
     * @param {number} id - Notification ID
     */
    const dismiss = (id) => {
        const index = notifications.value.findIndex(n => n.id === id);
        if (index !== -1) {
            notifications.value.splice(index, 1);
        }
    };

    /**
     * Clear all notifications
     */
    const clear = () => {
        notifications.value = [];
    };

    /**
     * Show success notification
     * @param {string} message
     * @param {number} [duration=5000]
     */
    const success = (message, duration = 5000) => {
        return add('success', message, null, duration);
    };

    /**
     * Show error notification
     * @param {string} message
     * @param {number} [duration=8000]
     */
    const error = (message, duration = 8000) => {
        return add('error', message, null, duration);
    };

    /**
     * Show warning notification
     * @param {string} message
     * @param {number} [duration=6000]
     */
    const warning = (message, duration = 6000) => {
        return add('warning', message, null, duration);
    };

    /**
     * Show info notification
     * @param {string} message
     * @param {number} [duration=5000]
     */
    const info = (message, duration = 5000) => {
        return add('info', message, null, duration);
    };

    /**
     * Helper: Capitalize first letter
     */
    const capitalize = (str) => {
        return str.charAt(0).toUpperCase() + str.slice(1);
    };

    return {
        // State
        notifications: computed(() => notifications.value),

        // Methods
        add,
        dismiss,
        clear,
        success,
        error,
        warning,
        info
    };
}
