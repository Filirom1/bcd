import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import { DataTableStub } from '../../helpers/stubs.js';
import SearchResults from '../../../../src/bcd_web_vue/js/components/catalog/SearchResults.js';

function mountResults(results = []) {
    return mount(SearchResults, {
        props: { results, query: 'prince', visibleColumns: ['title', 'author', 'availability'] },
        global: { stubs: { DataTable: DataTableStub } }
    });
}

describe('SearchResults', () => {
    it('reports result/query state and builds visible table columns', () => {
        const wrapper = mountResults([{ record_id: 1, title: 'The Prince' }]);

        expect(wrapper.vm.hasResults).toBe(true);
        expect(wrapper.vm.hasQuery).toBe(true);
        expect(wrapper.vm.tableColumns.map(column => column.key)).toEqual([
            'select', 'title', 'author', 'availability'
        ]);
    });

    it.each([
        [{ total_items: 0, available_copies: 0 }, 'bg-secondary'],
        [{ total_items: 2, available_copies: 0 }, 'bg-danger'],
        [{ total_items: 2, available_copies: 2 }, 'bg-success'],
        [{ total_items: 2, available_copies: 1 }, 'bg-warning']
    ])('maps availability state to a badge', (record, expectedClass) => {
        const wrapper = mountResults();
        expect(wrapper.vm.getAvailabilityBadge(record).class).toBe(expectedClass);
    });

    it('normalizes array, JSON, and plain-text author values', () => {
        const wrapper = mountResults();

        expect(wrapper.vm.getAuthors({ authors: ['A', 'B'] })).toBe('A, B');
        expect(wrapper.vm.getAuthors({ authors: '["A", "B"]' })).toBe('A, B');
        expect(wrapper.vm.getAuthors({ authors: 'Unknown' })).toBe('Unknown');
        expect(wrapper.vm.getAuthors({ publisher: 'Publisher' })).toBe('Publisher');
    });

    it('emits record and selection interactions', async () => {
        const record = { record_id: 42, title: 'Book' };
        const wrapper = mountResults([record]);

        wrapper.vm.handleRecordClick(record);
        wrapper.vm.toggleRecordSelection(42);
        wrapper.vm.toggleSelectAll();

        expect(wrapper.emitted('record-click')).toEqual([[record]]);
        expect(wrapper.emitted('toggle-selection')).toEqual([[42]]);
        expect(wrapper.emitted('toggle-select-all')).toHaveLength(1);
    });
});
