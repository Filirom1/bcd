import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import { makeClass } from '../../fixtures/classes.js';
import ClassForm from '../../../../src/bcd_web_vue/js/components/classes/ClassForm.js';

function mountForm(classData = null) {
    return mount(ClassForm, { props: { show: true, classData } });
}

describe('ClassForm', () => {
    it('rejects an empty class name without emitting save', async () => {
        const wrapper = mountForm();

        await wrapper.vm.handleSave();

        expect(wrapper.vm.errors.name).toBe('validation.required_field');
        expect(wrapper.emitted('save')).toBeUndefined();
    });

    it('emits the complete create payload for valid data', async () => {
        const wrapper = mountForm();
        wrapper.vm.form.name = 'CM1';
        wrapper.vm.form.homeroom_teacher = 'M. Martin';
        wrapper.vm.form.average_age = 9;

        await wrapper.vm.handleSave();

        expect(wrapper.emitted('save')).toEqual([[
            { id: undefined, name: 'CM1', homeroom_teacher: 'M. Martin', notes: '', average_age: 9 }
        ]]);
    });

    it('initializes edit fields from class data', () => {
        const wrapper = mountForm(makeClass({
            id: 12,
            name: 'CE2',
            homeroom_teacher: 'Mme Dupont',
            notes: 'Library project',
            average_age: 8
        }));

        expect(wrapper.vm.isEdit).toBe(true);
        expect(wrapper.vm.form).toMatchObject({
            name: 'CE2', homeroom_teacher: 'Mme Dupont', notes: 'Library project', average_age: 8
        });
    });
});
