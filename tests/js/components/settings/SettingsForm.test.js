import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import SettingsForm from '../../../../src/bcd_web_vue/js/components/settings/SettingsForm.js';

const settings = () => ({
    library_name: 'BCD',
    dewey_colors_enabled: true,
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

    it('updates, toggles, and disables individual Dewey colors', async () => {
        const value = settings();
        value.dewey_colors = Array.from({ length: 10 }, (_, index) => `#${index}${index}${index}${index}${index}${index}`);
        const wrapper = mount(SettingsForm, { props: { settings: value } });

        wrapper.vm.updateDeweyColor(2, '#abcdef');
        expect(wrapper.vm.deweyColorsList[2]).toBe('#abcdef');
        wrapper.vm.toggleDeweyColor(2);
        expect(wrapper.vm.deweyColorsList[2]).toBeNull();
        wrapper.vm.toggleDeweyColor(2);
        expect(wrapper.vm.deweyColorsList[2]).toBeTruthy();
        await wrapper.vm.$nextTick();
        expect(value.dewey_colors[2]).toBeTruthy();
    });

    it('adds, edits, colors, reorders, and removes shelf locations', async () => {
        const value = settings();
        const wrapper = mount(SettingsForm, { props: { settings: value } });

        wrapper.vm.addShelfLocation();
        wrapper.vm.updateShelfLocationLabel(1, 'Non-fiction');
        wrapper.vm.updateShelfLocationColor(1, '#123456');
        wrapper.vm.toggleShelfLocationColor(0);
        expect(wrapper.vm.shelfLocationsList).toEqual([
            { label: 'Fiction', color: null },
            { label: 'Non-fiction', color: '#123456' }
        ]);
        wrapper.vm.toggleShelfLocationColor(0);
        expect(wrapper.vm.shelfLocationsList[0].color).toBe('#6c757d');
        wrapper.vm.removeShelfLocation(1);
        expect(wrapper.vm.shelfLocationsList).toHaveLength(1);
        await wrapper.vm.$nextTick();
        expect(value.catalog_shelf_locations).toHaveLength(1);
    });

    it('reorders and removes call-number rules while respecting list boundaries', () => {
        const value = settings();
        value.catalog_call_number_rules = [
            { medium_type: 'Book', pattern: 'A' },
            { medium_type: 'Magazine', pattern: 'B' }
        ];
        const wrapper = mount(SettingsForm, { props: { settings: value } });

        wrapper.vm.moveCallNumberRuleUp(0);
        wrapper.vm.moveCallNumberRuleDown(1);
        wrapper.vm.moveCallNumberRuleUp(1);
        expect(wrapper.vm.localRules).toEqual([
            { medium_type: 'Magazine', pattern: 'B' },
            { medium_type: 'Book', pattern: 'A' }
        ]);
        wrapper.vm.moveCallNumberRuleDown(0);
        expect(wrapper.vm.localRules[0].medium_type).toBe('Book');
        wrapper.vm.removeCallNumberRule(1);
        expect(wrapper.vm.localRules).toHaveLength(1);
    });

    it('handles absent catalog settings and exposes shelf training props', () => {
        const wrapper = mount(SettingsForm, {
            props: {
                settings: {},
                shelfSuggestionStatus: { ready: false, trained_on_records: 2 },
                shelfSuggestionTraining: true
            }
        });
        expect(wrapper.vm.shelfLocationsList).toEqual([]);
        expect(wrapper.vm.localRules).toEqual([]);
        expect(wrapper.vm.shelfSuggestionStatus).toEqual({ ready: false, trained_on_records: 2 });
        expect(wrapper.vm.shelfSuggestionTraining).toBe(true);
    });
});
