// @ts-check
/**
 * Shared state for the blocking "hold ready" alert shown after an item return.
 * Any return flow can enqueue an alert; the app-level modal presents them one
 * at a time so a rapid series of scans cannot replace an unread instruction.
 */
const { ref } = Vue;

/** @type {import('vue').Ref<HoldReadyModalData|null>} */
const holdReady = ref(null);
/** @type {HoldReadyModalData[]} */
const pendingHoldReady = [];

/**
 * @typedef {Object} HoldReadyModalData
 * @property {string} title
 * @property {string} item_id
 * @property {string} borrower_name
 * @property {string} borrower_id
 * @property {string} class_name
 * @property {string} expiration_date
 */

/** @param {unknown} value */
const asText = (value) => value === null || value === undefined ? '' : String(value);

/**
 * @param {unknown} hold
 * @param {unknown} [item={}]
 */
const normalizeHoldReady = (hold, item = {}) => {
    if (!hold || typeof hold !== 'object' || Array.isArray(hold)) return null;
    const holdData = /** @type {Record<string, unknown>} */ (hold);
    const itemData = /** @type {Record<string, unknown>} */ (item);
    return {
        title: asText(itemData.display_title || itemData.title || itemData.item_id),
        item_id: asText(itemData.item_id),
        borrower_name: asText(holdData.borrower_name),
        borrower_id: asText(holdData.borrower_id),
        class_name: asText(holdData.class_name || holdData.borrower_id),
        expiration_date: asText(holdData.expiration_date)
    };
};

/**
 * Present a hold-ready alert, or queue it behind the currently visible alert.
 * @param {unknown} hold
 * @param {unknown} [item={}]
 */
const showHoldReady = (hold, item = {}) => {
    const normalized = normalizeHoldReady(hold, item);
    if (!normalized) return;

    if (holdReady.value) {
        pendingHoldReady.push(normalized);
    } else {
        holdReady.value = normalized;
    }
};

/** Dismiss the current alert and advance to the next queued return, if any. */
const dismissHoldReady = () => {
    holdReady.value = pendingHoldReady.shift() || null;
};

export function useHoldReadyModal() {
    return {
        holdReady,
        showHoldReady,
        dismissHoldReady
    };
}
