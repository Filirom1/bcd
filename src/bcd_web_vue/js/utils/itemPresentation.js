/**
 * Shared presentation helpers for physical copies.
 *
 * Keep status/condition labels in one place so cataloging, catalog detail and
 * any future copy list render the same information.
 */

export const ITEM_STATUS_PRESENTATION = {
    available: { class: 'bg-success', icon: 'bi-check-circle' },
    on_loan: { class: 'bg-warning', icon: 'bi-clock' },
    on_hold: { class: 'bg-info', icon: 'bi-pause-circle' },
    in_repair: { class: 'bg-primary', icon: 'bi-tools' },
    lost: { class: 'bg-danger', icon: 'bi-question-circle' },
    withdrawn: { class: 'bg-dark', icon: 'bi-x-circle' },
    overdue: { class: 'bg-danger', icon: 'bi-exclamation-triangle' }
};

export function getItemStatusBadge(t, status) {
    const meta = ITEM_STATUS_PRESENTATION[status];
    if (!meta) {
        return { class: 'bg-secondary', icon: 'bi-dash-circle', text: status };
    }
    const labelKey = status === 'overdue' ? 'catalog.overdue' : `item.status_${status}`;
    return {
        ...meta,
        text: t(labelKey) || status
    };
}

export function getItemConditionLabel(t, condition) {
    const keys = {
        good: 'item.condition_good',
        damaged: 'item.condition_damaged',
        lost: 'item.status_lost',
        withdrawn: 'item.status_withdrawn'
    };
    return keys[condition] ? (t(keys[condition]) || condition) : condition;
}
