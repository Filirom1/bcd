import { describe, expect, it } from 'vitest';

import { groupTimelineActions } from '../../../src/bcd_web_vue/js/utils/activityTimeline.js';

const action = (id, actionType, occurredAt, borrowerId = 'S-1') => ({
    id,
    transaction_id: Number(id.split(':')[0]),
    action: actionType,
    occurred_at: occurredAt,
    borrower_id: borrowerId,
    borrower_name: borrowerId === 'S-1' ? 'Alice Martin' : 'Benoît Durand',
    class_id: 1,
    class_name: 'CE1',
    homeroom_teacher: 'Mme Martin',
    item_id: `I-${id}`,
    title: `Livre ${id}`
});

describe('groupTimelineActions', () => {
    it('groups returns followed by checkouts and starts a new group at the next return', () => {
        const groups = groupTimelineActions([
            action('1:return', 'return', '2026-10-19T09:00:00'),
            action('2:return', 'return', '2026-10-19T09:01:00', 'S-2'),
            action('3:checkout', 'checkout', '2026-10-19T09:05:00'),
            action('4:checkout', 'checkout', '2026-10-19T09:06:00', 'S-2'),
            action('5:return', 'return', '2026-10-19T09:20:00', 'S-2')
        ]);

        expect(groups).toHaveLength(2);
        expect(groups[0]).toMatchObject({
            startAt: '2026-10-19T09:00:00',
            endAt: '2026-10-19T09:06:00',
            checkoutCount: 2,
            returnCount: 2
        });
        expect(groups[0].students).toHaveLength(2);
        expect(groups[1]).toMatchObject({
            startAt: '2026-10-19T09:20:00',
            checkoutCount: 0,
            returnCount: 1
        });
    });

    it('keeps class timelines separate and orders groups by their start time', () => {
        const otherClass = {
            ...action('6:checkout', 'checkout', '2026-10-19T08:00:00'),
            class_id: 2,
            class_name: 'CE2'
        };

        const groups = groupTimelineActions([
            action('1:checkout', 'checkout', '2026-10-19T09:00:00'),
            action('2:return', 'return', '2026-10-19T09:10:00'),
            otherClass
        ]);

        expect(groups.map(group => group.className)).toEqual(['CE2', 'CE1', 'CE1']);
    });
});
