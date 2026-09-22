import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import BorrowerDeleteDialog from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerDeleteDialog.js';

function mountDialog(overrides = {}) {
    return mount(BorrowerDeleteDialog, {
        props: {
            show: true,
            borrowerData: {
                borrower_id: 'B-1',
                full_name: 'Amira Benali',
                role: 'student',
                current_loans_count: 0,
                ...overrides
            }
        },
        global: { stubs: { teleport: true } }
    });
}

describe('BorrowerDeleteDialog', () => {
    it('blocks deletion when the borrower has active loans', async () => {
        const wrapper = mountDialog({ current_loans_count: 2 });
        const deleteButton = wrapper.findAll('button').find(button => button.classes('btn-danger'));

        expect(deleteButton.attributes('disabled')).toBeDefined();
        await deleteButton.trigger('click');
        expect(wrapper.emitted('confirm')).toBeUndefined();
        expect(wrapper.text()).toContain('admin.error_delete_borrower_has_loans_detail');
    });

    it('confirms deletion for a borrower without active loans and supports closing', async () => {
        const wrapper = mountDialog();
        const deleteButton = wrapper.findAll('button').find(button => button.classes('btn-danger'));
        await deleteButton.trigger('click');
        expect(wrapper.emitted('confirm')).toEqual([['B-1']]);

        await wrapper.findAll('button').find(button => button.classes('btn-secondary')).trigger('click');
        expect(wrapper.emitted('close')).toHaveLength(1);
    });
});
