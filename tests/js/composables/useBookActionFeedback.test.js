import { afterEach, describe, expect, it, vi } from 'vitest';

import { showBookActionFeedback, useBookActionFeedback } from '../../../src/bcd_web_vue/js/composables/useBookActionFeedback.js';

afterEach(() => {
    vi.useRealTimers();
});

describe('useBookActionFeedback', () => {
    it('shows each successful book action for one second in queue order', () => {
        vi.useFakeTimers();
        const { activeBookActionFeedback } = useBookActionFeedback();

        showBookActionFeedback({
            item_id: 'I-1',
            title: 'Le livre des étoiles',
            authors: ['A. Auteur'],
            illustrators: ['I. Illustratrice'],
            cover_image: 'cover.jpg'
        }, 'checkout');
        showBookActionFeedback({ item_id: 'I-2', title: 'La grande aventure' }, 'return');

        expect(activeBookActionFeedback.value).toMatchObject({
            action: 'checkout',
            item: {
                item_id: 'I-1',
                title: 'Le livre des étoiles',
                authors: ['A. Auteur'],
                illustrators: ['I. Illustratrice'],
                cover_image: 'cover.jpg'
            }
        });

        vi.advanceTimersByTime(999);
        expect(activeBookActionFeedback.value.item.item_id).toBe('I-1');

        vi.advanceTimersByTime(1);
        expect(activeBookActionFeedback.value).toMatchObject({
            action: 'return',
            item: { item_id: 'I-2', title: 'La grande aventure' }
        });

        vi.advanceTimersByTime(1000);
        expect(activeBookActionFeedback.value).toBeNull();
    });
});
