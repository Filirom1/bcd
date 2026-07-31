import { describe, expect, it } from 'vitest';

import { useSelection } from '../../../src/bcd_web_vue/js/composables/useSelection.js';

describe('useSelection', () => {
    it('toggles a selected identifier and exposes the reactive count', () => {
        const selection = useSelection();

        selection.toggleSelection('record-1');
        expect(selection.isSelected('record-1')).toBe(true);
        expect(selection.selectedCount.value).toBe(1);

        selection.toggleSelection('record-1');
        expect(selection.isSelected('record-1')).toBe(false);
        expect(selection.selectedCount.value).toBe(0);
    });

    it('selects, clears and returns all identifiers from a page', () => {
        const selection = useSelection();
        const records = [{ id: 1 }, { id: 2 }, { id: 3 }];

        selection.selectAll(records);
        expect(selection.getSelectedIds()).toEqual([1, 2, 3]);
        expect(selection.isAllSelected(records)).toBe(true);
        expect(selection.isSomeSelected(records)).toBe(false);

        selection.clearSelection();
        expect(selection.getSelectedIds()).toEqual([]);
    });

    it('reports a partial selection only when some current rows are selected', () => {
        const selection = useSelection();
        const records = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];

        selection.toggleSelection('a');

        expect(selection.isAllSelected(records)).toBe(false);
        expect(selection.isSomeSelected(records)).toBe(true);
    });

    it('selects the current page when a same-sized stale selection exists', () => {
        const selection = useSelection();
        const currentRecords = [{ id: 'a' }, { id: 'b' }];

        selection.selectAll([{ id: 'old-a' }, { id: 'old-b' }]);
        selection.toggleSelectAll(currentRecords);

        expect(selection.getSelectedIds()).toEqual(['a', 'b']);
        expect(selection.isAllSelected(currentRecords)).toBe(true);
    });

    it('calculates partial selection from current rows instead of stale identifiers', () => {
        const selection = useSelection();
        const currentRecords = [{ id: 'a' }, { id: 'b' }];

        selection.selectAll([{ id: 'a' }, { id: 'old-a' }]);

        expect(selection.isAllSelected(currentRecords)).toBe(false);
        expect(selection.isSomeSelected(currentRecords)).toBe(true);
    });
});
