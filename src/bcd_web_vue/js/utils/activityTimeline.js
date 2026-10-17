// @ts-check

/**
 * @typedef {Object} CirculationAction
 * @property {string} id
 * @property {number} transaction_id
 * @property {'checkout'|'return'} action
 * @property {string} occurred_at
 * @property {string} borrower_id
 * @property {string} borrower_name
 * @property {number|null} class_id
 * @property {string|null} class_name
 * @property {string|null} homeroom_teacher
 * @property {string} item_id
 * @property {string} title
 */

/**
 * @typedef {Object} TimelineStudent
 * @property {string} borrowerId
 * @property {string} borrowerName
 * @property {CirculationAction[]} checkouts
 * @property {CirculationAction[]} returns
 */

/**
 * @typedef {Object} TimelineGroup
 * @property {string} id
 * @property {number|null} classId
 * @property {string|null} className
 * @property {string|null} homeroomTeacher
 * @property {string} startAt
 * @property {string} endAt
 * @property {CirculationAction[]} actions
 * @property {TimelineStudent[]} students
 * @property {number} checkoutCount
 * @property {number} returnCount
 */

/**
 * Group each class's return-then-checkout cycles while keeping action timestamps.
 * A return after a checkout starts the next group for that class.
 * @param {CirculationAction[]} actions
 * @returns {TimelineGroup[]}
 */
export function groupTimelineActions(actions) {
    /** @type {Map<string, CirculationAction[]>} */
    const byClass = new Map();
    for (const action of actions) {
        const classKey = action.class_id === null ? 'none' : String(action.class_id);
        const classActions = byClass.get(classKey) || [];
        classActions.push(action);
        byClass.set(classKey, classActions);
    }

    /** @type {TimelineGroup[]} */
    const groups = [];
    for (const classActions of byClass.values()) {
        classActions.sort((left, right) => {
            const timeDifference = Date.parse(left.occurred_at) - Date.parse(right.occurred_at);
            if (timeDifference !== 0) return timeDifference;
            if (left.action !== right.action) return left.action === 'return' ? -1 : 1;
            return left.id.localeCompare(right.id);
        });

        /** @type {TimelineGroup|null} */
        let currentGroup = null;
        let hasCheckout = false;

        for (const action of classActions) {
            if (currentGroup && action.action === 'return' && hasCheckout) {
                currentGroup = null;
                hasCheckout = false;
            }

            if (!currentGroup) {
                currentGroup = {
                    id: action.id,
                    classId: action.class_id,
                    className: action.class_name,
                    homeroomTeacher: action.homeroom_teacher,
                    startAt: action.occurred_at,
                    endAt: action.occurred_at,
                    actions: [],
                    students: [],
                    checkoutCount: 0,
                    returnCount: 0
                };
                groups.push(currentGroup);
            }

            currentGroup.actions.push(action);
            currentGroup.endAt = action.occurred_at;
            if (action.action === 'checkout') {
                currentGroup.checkoutCount += 1;
                hasCheckout = true;
            } else {
                currentGroup.returnCount += 1;
            }
        }
    }

    for (const group of groups) {
        /** @type {Map<string, TimelineStudent>} */
        const students = new Map();
        for (const action of group.actions) {
            let student = students.get(action.borrower_id);
            if (!student) {
                student = {
                    borrowerId: action.borrower_id,
                    borrowerName: action.borrower_name,
                    checkouts: [],
                    returns: []
                };
                students.set(action.borrower_id, student);
            }
            student[action.action === 'checkout' ? 'checkouts' : 'returns'].push(action);
        }
        group.students = [...students.values()].sort((left, right) =>
            left.borrowerName.localeCompare(right.borrowerName)
        );
    }

    return groups.sort((left, right) => Date.parse(left.startAt) - Date.parse(right.startAt));
}
