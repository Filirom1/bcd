// @ts-check
/**
 * Composable for a debounced action.
 * Automatically cleans up the timer on component unmount or when manual cancel is called.
 */

const { onUnmounted } = Vue;

/**
 * Composable for a debounced action.
 * Automatically cleans up the timer on component unmount.
 *
 * @template {(...args: any[]) => any} T
 * @param {T} action - The action function to debounce.
 * @param {number|import('vue').Ref<number>} delay - The debounce delay in milliseconds.
 * @returns {((...args: Parameters<T>) => void) & { cancel: () => void, flush: () => void }}
 */
export function useDebouncedAction(action, delay) {
    /** @type {any} */
    let timer = null;
    /** @type {any[]} */
    let lastArgs = [];

    const cancel = () => {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
    };

    const flush = () => {
        if (timer) {
            cancel();
            action(...lastArgs);
        }
    };

    /**
     * @param {Parameters<T>} args
     */
    const debounced = (...args) => {
        lastArgs = args;
        cancel();
        const d = typeof delay === 'number' ? delay : delay.value;
        timer = setTimeout(() => {
            timer = null;
            action(...args);
        }, d);
    };

    debounced.cancel = cancel;
    debounced.flush = flush;

    // Register onUnmounted only if called within setup context of a Vue component
    if (Vue.getCurrentInstance?.()) {
        onUnmounted(() => {
            cancel();
        });
    }

    return debounced;
}
