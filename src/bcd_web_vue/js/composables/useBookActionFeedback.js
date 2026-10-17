// @ts-check
const { ref } = Vue;

const DISPLAY_DURATION_MS = 1000;
/**
 * @typedef {Object} BookActionFeedback
 * @property {number} id
 * @property {'checkout'|'return'} action
 * @property {Object} item
 * @property {string} item.item_id
 * @property {string} item.title
 * @property {string[]} item.authors
 * @property {string[]} item.illustrators
 * @property {string} item.cover_image
 */

/** @type {import('vue').Ref<BookActionFeedback|null>} */
const activeBookActionFeedback = ref(null);
/** @type {BookActionFeedback[]} */
const pendingActions = [];
let actionSequence = 0;

/** @param {unknown} value */
const toText = (value) => value === null || value === undefined ? '' : String(value);
/** @param {unknown} value */
const toList = (value) => {
    if (Array.isArray(value)) return value.map(toText).filter(Boolean);
    return value ? [toText(value)] : [];
};

/**
 * @param {unknown} item
 * @param {'checkout'|'return'} action
 * @returns {Omit<BookActionFeedback, 'id'>|null}
 */
const normalizeBookActionFeedback = (item, action) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return null;
    const data = /** @type {Record<string, unknown>} */ (item);
    return {
        action,
        item: {
            item_id: toText(data.item_id),
            title: toText(data.title || data.display_title || data.item_id),
            authors: toList(data.authors || data.author),
            illustrators: toList(data.illustrators || data.illustrator),
            cover_image: toText(data.cover_image)
        }
    };
};

const showNextActionFeedback = () => {
    const nextAction = pendingActions.shift();
    if (!nextAction) {
        activeBookActionFeedback.value = null;
        return;
    }

    activeBookActionFeedback.value = nextAction;
    setTimeout(showNextActionFeedback, DISPLAY_DURATION_MS);
};

/**
 * Queue a celebratory book card after a successful checkout or return.
 * @param {unknown} item
 * @param {'checkout'|'return'} action
 */
export const showBookActionFeedback = (item, action) => {
    const feedback = normalizeBookActionFeedback(item, action);
    if (!feedback) return;

    pendingActions.push({ ...feedback, id: actionSequence++ });
    if (activeBookActionFeedback.value === null) showNextActionFeedback();
};

export function useBookActionFeedback() {
    return { activeBookActionFeedback };
}
