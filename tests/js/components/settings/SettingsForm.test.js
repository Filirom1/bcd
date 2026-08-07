import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import SettingsForm from '../../../../src/bcd_web_vue/js/components/settings/SettingsForm.js';

const settings = () => ({
    library_name: 'BCD',
    dewey_colors: ['#000000'],
    catalog_shelf_locations: [{ label: 'Fiction', color: '#ffffff' }],
    catalog_call_number_rules: [{ medium_type: 'Book', shelf_location: 'Fiction', pattern: '' }],
    catalog_medium_types: 'Book, Magazine'
});

describe('SettingsForm', () => {
    it('falls back to default Dewey colors for malformed settings', () => {
        const wrapper = mount(SettingsForm, { props: { settings: settings() } });

        expect(wrapper.vm.deweyColorsList).toHaveLength(10);
        expect(wrapper.vm.shelfLocationLabels).toEqual(['Fiction']);
        expect(wrapper.vm.mediumTypesOptions).toEqual(['Book', 'Magazine']);
    });

    it('manages shelf locations and call-number rules', async () => {
        const value = settings();
        const wrapper = mount(SettingsForm, { props: { settings: value } });

        wrapper.vm.addShelfLocation();
        wrapper.vm.updateShelfLocationLabel(1, 'Non-fiction');
        wrapper.vm.addCallNumberRule();
        await wrapper.vm.$nextTick();

        expect(value.catalog_shelf_locations).toEqual([
            { label: 'Fiction', color: '#ffffff' },
            { label: 'Non-fiction', color: null }
        ]);
        expect(value.catalog_call_number_rules).toHaveLength(2);
    });

    it('emits save and reset actions', async () => {
        const wrapper = mount(SettingsForm, { props: { settings: settings() } });

        await wrapper.vm.handleSubmit();
        await wrapper.vm.handleReset();

        expect(wrapper.emitted('save')).toHaveLength(1);
        expect(wrapper.emitted('reset')).toHaveLength(1);
    });

    it('enforces native validation constraints on inputs', () => {
        const wrapper = mount(SettingsForm, { props: { settings: settings() } });

        const loanDurationInput = wrapper.get('#loan_duration_days');
        expect(loanDurationInput.attributes('min')).toBe('1');
        expect(loanDurationInput.attributes('required')).toBeDefined();

        const loanLimitInput = wrapper.get('#loan_limit_default');
        expect(loanLimitInput.attributes('min')).toBe('1');
        expect(loanLimitInput.attributes('required')).toBeDefined();
    });
});
