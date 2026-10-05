import { afterEach, describe, expect, it } from 'vitest';

import { useHoldReadyModal } from '../../../src/bcd_web_vue/js/composables/useHoldReadyModal.js';

const clearQueue = () => {
    const modal = useHoldReadyModal();
    while (modal.holdReady.value) modal.dismissHoldReady();
};

afterEach(clearQueue);

describe('useHoldReadyModal', () => {
    it('normalizes hold-ready details and presents queued returns in order', () => {
        const modal = useHoldReadyModal();

        modal.showHoldReady(
            { borrower_name: 'Lina Martin', borrower_id: 'B-9', class_name: 'CE2', expiration_date: '2030-02-01' },
            { item_id: 'I-1', display_title: 'Le Petit Nicolas' }
        );
        modal.showHoldReady(
            { borrower_name: 'Noé Dupont', borrower_id: 'B-10' },
            { item_id: 'I-2', title: 'Matilda' }
        );

        expect(modal.holdReady.value).toEqual({
            title: 'Le Petit Nicolas',
            item_id: 'I-1',
            borrower_name: 'Lina Martin',
            borrower_id: 'B-9',
            class_name: 'CE2',
            expiration_date: '2030-02-01'
        });

        modal.dismissHoldReady();
        expect(modal.holdReady.value).toEqual({
            title: 'Matilda',
            item_id: 'I-2',
            borrower_name: 'Noé Dupont',
            borrower_id: 'B-10',
            class_name: 'B-10',
            expiration_date: ''
        });

        modal.dismissHoldReady();
        expect(modal.holdReady.value).toBeNull();
    });

    it('ignores empty or non-object hold data', () => {
        const modal = useHoldReadyModal();

        modal.showHoldReady(null);
        modal.showHoldReady('not a hold');

        expect(modal.holdReady.value).toBeNull();
    });
});
