import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import { makeClass } from '../../fixtures/classes.js';
import ClassDeleteDialog from '../../../../src/bcd_web_vue/js/components/classes/ClassDeleteDialog.js';

describe('ClassDeleteDialog', () => {
    it('displays the student-unassignment warning', () => {
        const wrapper = mount(ClassDeleteDialog, {
            props: { show: true, classData: makeClass({ id: 7, name: 'CE1' }) }
        });

        expect(wrapper.text()).toContain('CE1');
        expect(wrapper.find('[role="alert"]').exists()).toBe(true);
    });

    it('emits close and the class id on the corresponding actions', async () => {
        const wrapper = mount(ClassDeleteDialog, {
            props: { show: true, classData: makeClass({ id: 7, name: 'CE1' }) }
        });

        await wrapper.find('.btn-secondary').trigger('click');
        await wrapper.find('.btn-danger').trigger('click');

        expect(wrapper.emitted('close')).toHaveLength(1);
        expect(wrapper.emitted('confirm')).toEqual([[7]]);
    });
});
