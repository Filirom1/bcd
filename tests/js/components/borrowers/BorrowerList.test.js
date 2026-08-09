import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import { DataTableStub } from '../../helpers/stubs.js';
import BorrowerList from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerList.js';

function mountList(borrowers) {
    return mount(BorrowerList, {
        props: { borrowers },
        global: { stubs: { DataTable: DataTableStub } }
    });
}

describe('BorrowerList', () => {
    it('maps loan counts to neutral, warning, and limit badges', () => {
        const wrapper = mountList([]);

        expect(wrapper.vm.getLoanBadgeClass({ current_loans_count: 0, loan_limit: 3 })).toBe('bg-secondary');
        expect(wrapper.vm.getLoanBadgeClass({ current_loans_count: 2, loan_limit: 3, loan_limit_warning: 2 }))
            .toBe('bg-warning text-dark');
        expect(wrapper.vm.getLoanBadgeClass({ current_loans_count: 3, loan_limit: 3 })).toBe('bg-danger');
    });

    it('selects individual borrowers and emits the selected ids', () => {
        const wrapper = mountList([
            { borrower_id: 'B-1', full_name: 'A' },
            { borrower_id: 'B-2', full_name: 'B' }
        ]);

        wrapper.vm.toggleBorrowerSelection('B-1');
        wrapper.vm.toggleBorrowerSelection('B-2');
        wrapper.vm.toggleBorrowerSelection('B-1');

        expect(wrapper.vm.selectedBorrowerIds).toEqual(['B-2']);
        expect(wrapper.emitted('selection-changed')).toEqual([
            [['B-1']], [['B-1', 'B-2']], [['B-2']]
        ]);
    });

    it('selects all current borrowers and emits the detail navigation id', () => {
        const borrowers = [{ borrower_id: 'B-1', full_name: 'A' }, { borrower_id: 'B-2', full_name: 'B' }];
        const wrapper = mountList(borrowers);

        wrapper.vm.toggleSelectAll();
        wrapper.vm.viewBorrower(borrowers[1]);

        expect(wrapper.vm.selectAll).toBe(true);
        expect(wrapper.vm.selectedBorrowerIds).toEqual(['B-1', 'B-2']);
        expect(wrapper.emitted('view-borrower')).toEqual([['B-2']]);
    });
});
