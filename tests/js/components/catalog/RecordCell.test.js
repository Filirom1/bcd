import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import RecordCell from '../../../../src/bcd_web_vue/js/components/catalog/RecordCell.js';
import { useGlobalModal } from '../../../../src/bcd_web_vue/js/composables/useGlobalModal.js';

afterEach(() => {
    useGlobalModal().closeRecord();
});

describe('RecordCell', () => {
    it('renders record metadata in a single table cell and opens its record', async () => {
        const wrapper = mount(RecordCell, {
            props: {
                recordId: 42,
                title: 'Le livre',
                subtitle: 'Son histoire',
                collection: 'Les classiques',
                seriesNumber: '3',
                itemId: '10423',
                shelfLocation: 'Romans',
                callNumber: '800.000'
            }
        });

        expect(wrapper.element.tagName).toBe('TD');
        expect(wrapper.text()).toContain('Le livre : Son histoire — Les classiques, 3');
        expect(wrapper.text()).toContain('10423');
        expect(wrapper.text()).toContain('Romans');
        expect(wrapper.text()).toContain('800.000');

        await wrapper.find('a').trigger('click');
        expect(useGlobalModal().globalRecordId.value).toBe(42);

        wrapper.unmount();
    });
});
