import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import AdvancedFilters from '../../../../src/bcd_web_vue/js/components/catalog/AdvancedFilters.js';

const FilterSelectStub = { template: '<select />' };
const ColumnSelectorStub = { template: '<div />' };

function mountFilters() {
    return mount(AdvancedFilters, {
        props: {
            filters: { availability: 'all', level: '', language: '', medium_type: '', shelf_location: '' },
            settings: {
                catalog_levels: 'CP, CE1, CE2',
                catalog_languages: 'fr, en',
                catalog_medium_types: 'Book, Magazine'
            },
            shelfLocations: ['Fiction', 'Reference']
        },
        global: { stubs: { FilterSelect: FilterSelectStub, ColumnSelector: ColumnSelectorStub } }
    });
}

describe('AdvancedFilters', () => {
    it('parses configured suggestions and shelf locations', () => {
        const wrapper = mountFilters();

        expect(wrapper.vm.levelSuggestions).toEqual(['CP', 'CE1', 'CE2']);
        expect(wrapper.vm.languageSuggestions).toEqual(['fr', 'en']);
        expect(wrapper.vm.mediumTypeSuggestions).toEqual(['Book', 'Magazine']);
        expect(wrapper.vm.locationOptions).toEqual([
            { value: 'Fiction', label: 'Fiction' },
            { value: 'Reference', label: 'Reference' }
        ]);
    });

    it('emits updated filters for availability and reset', () => {
        const wrapper = mountFilters();

        wrapper.vm.updateFilter('availability', 'available');
        wrapper.vm.clearFilters();

        expect(wrapper.emitted('update:filters')).toEqual([
            [{ availability: 'available', level: '', language: '', medium_type: '', shelf_location: '' }],
            [{ availability: 'all', level: '', language: '', medium_type: '', shelf_location: '' }]
        ]);
        expect(wrapper.emitted('filter')).toHaveLength(2);
    });

    it('toggles the advanced section and emits the selected view mode', async () => {
        const wrapper = mountFilters();

        expect(wrapper.vm.showAdvanced).toBe(false);
        wrapper.vm.toggleAdvanced();
        expect(wrapper.vm.showAdvanced).toBe(true);

        await wrapper.findAll('button').at(-1).trigger('click');
        expect(wrapper.emitted('update:view-mode')).toEqual([['cards']]);
    });
});
