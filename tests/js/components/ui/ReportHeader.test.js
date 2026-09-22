import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import ReportHeader from '../../../../src/bcd_web_vue/js/components/ui/ReportHeader.js';

describe('ReportHeader', () => {
    it('renders the title and delegates print actions', async () => {
        const wrapper = mount(ReportHeader, {
            props: { title: 'Overdue books', showNotices: true }
        });

        expect(wrapper.text()).toContain('Overdue books');
        expect(wrapper.findAll('button')).toHaveLength(2);
        await wrapper.findAll('button')[0].trigger('click');
        await wrapper.findAll('button')[1].trigger('click');

        expect(wrapper.emitted('print-notices')).toHaveLength(1);
        expect(wrapper.emitted('print')).toHaveLength(1);
    });

    it('hides the notices action when it is not requested', () => {
        const wrapper = mount(ReportHeader, { props: { title: 'Collection' } });
        expect(wrapper.findAll('button')).toHaveLength(1);
    });
});
