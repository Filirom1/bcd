import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import FilterChips from '../../../../src/bcd_web_vue/js/components/reports/FilterChips.js';
import { setTestTranslator } from '../../helpers/i18n.js';

describe('FilterChips', () => {
    it('renders active filters and emits clear actions', async () => {
        setTestTranslator(key => key === 'reports.clearAll' ? 'Clear all' : key);
        const wrapper = mount(FilterChips, {
            props: {
                chips: [
                    { key: 'medium_type', label: 'Support', value: 'Book' },
                    { key: 'pub_year', label: 'Year', value: '2010 – …' }
                ]
            }
        });

        expect(wrapper.text()).toContain('Support : Book');
        expect(wrapper.text()).toContain('Year : 2010 – …');
        expect(wrapper.text()).toContain('Clear all');
        expect(wrapper.findAll('span.badge')).toHaveLength(2);

        await wrapper.findAll('span.badge')[0].find('button').trigger('click');
        await wrapper.get('button.btn-link').trigger('click');

        expect(wrapper.emitted('clear')).toEqual([['medium_type']]);
        expect(wrapper.emitted('clear-all')).toHaveLength(1);
    });

    it('does not render a container when no filters are active', () => {
        const wrapper = mount(FilterChips, { props: { chips: [] } });
        expect(wrapper.element.firstChild).toBeNull();
        expect(wrapper.find('button').exists()).toBe(false);
    });
});
