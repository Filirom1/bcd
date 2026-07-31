import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import BorrowerCard from '../../../../src/bcd_web_vue/js/components/circulation/BorrowerCard.js';

const borrower = {
    first_name: 'Amira', last_name: 'Benali', status: 'active', overdue_count: 1,
    current_loans_count: 1, loan_limit: 3,
    current_loans: [{ item_id: 'I-1', due_date: '2000-01-01' }]
};

describe('BorrowerCard', () => {
    it('exposes overdue/status presentation state and loan visibility', () => {
        const wrapper = mount(BorrowerCard, { props: { borrower, holds: [] } });

        expect(wrapper.vm.hasCurrentLoans).toBe(true);
        expect(wrapper.vm.hasAnythingToShow).toBe(true);
        expect(wrapper.vm.statusIcon).toBe('bi-exclamation-triangle-fill');
        expect(wrapper.vm.statusText).toBe('borrowers.status_active');
        expect(wrapper.vm.isOverdue('2000-01-01')).toBe(true);
        expect(wrapper.vm.daysOverdue('2000-01-01')).toBeGreaterThan(0);
    });

    it('emits quick-return and item-view actions for loan interactions', async () => {
        const wrapper = mount(BorrowerCard, {
            props: {
                borrower: {
                    ...borrower,
                    current_loans: [{ item_id: 'I-1', bibliographic_record_id: 9, due_date: '2000-01-01' }]
                },
                holds: []
            }
        });

        const loanRow = wrapper.find('tbody tr');
        await loanRow.find('button').trigger('click');
        await loanRow.find('a').trigger('click');

        expect(wrapper.emitted('quick-return')).toEqual([['I-1']]);
        expect(wrapper.emitted('view-item')).toEqual([[9]]);
    });

    it('emits renew and edit actions', () => {
        const wrapper = mount(BorrowerCard, { props: { borrower, holds: [] } });

        wrapper.vm.renewAll();
        wrapper.vm.edit();

        expect(wrapper.emitted('renew-all')).toHaveLength(1);
        expect(wrapper.emitted('edit')).toHaveLength(1);
    });
});
