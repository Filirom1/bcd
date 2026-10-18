import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import { makeClass } from '../../fixtures/classes.js';
import ClassDeleteDialog from '../../../../src/bcd_web_vue/js/components/classes/ClassDeleteDialog.js';

afterEach(() => {
    document.body.innerHTML = '';
});

describe('ClassDeleteDialog', () => {
    it('displays the student-unassignment warning', () => {
        const wrapper = mount(ClassDeleteDialog, {
            props: { show: true, classData: makeClass({ id: 7, name: 'CE1' }) },
            attachTo: document.body
        });

        expect(document.body.textContent).toContain('CE1');
        expect(document.body.querySelector('[role="alert"]')).not.toBeNull();
        wrapper.unmount();
    });

    it('emits close and the class id on the corresponding actions', async () => {
        const wrapper = mount(ClassDeleteDialog, {
            props: { show: true, classData: makeClass({ id: 7, name: 'CE1' }) },
            attachTo: document.body
        });

        document.body.querySelector('.btn-secondary').click();
        await wrapper.vm.$nextTick();
        document.body.querySelector('.btn-danger').click();
        await wrapper.vm.$nextTick();

        expect(wrapper.emitted('close')).toHaveLength(1);
        expect(wrapper.emitted('confirm')).toEqual([[7]]);
        wrapper.unmount();
    });
});
