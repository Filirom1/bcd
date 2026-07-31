import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import { makeClass } from '../../fixtures/classes.js';
import { DataTableStub } from '../../helpers/stubs.js';
import { setTestTranslator } from '../../helpers/i18n.js';
import ClassList from '../../../../src/bcd_web_vue/js/components/classes/ClassList.js';

describe('ClassList', () => {
    it('renders class data and emits edit/delete actions for the selected row', async () => {
        const wrapper = mount(ClassList, {
            props: {
                classes: [makeClass({ id: 4, name: 'CM2', homeroom_teacher: 'M. Petit', average_age: 10 })]
            },
            global: { components: { DataTable: DataTableStub } }
        });

        expect(wrapper.text()).toContain('CM2');
        expect(wrapper.text()).toContain('M. Petit');
        expect(wrapper.text()).toContain('10');

        const buttons = wrapper.findAll('button');
        await buttons[0].trigger('click');
        await buttons[1].trigger('click');

        expect(wrapper.emitted('edit-class')).toEqual([[expect.objectContaining({
            id: 4, name: 'CM2', homeroom_teacher: 'M. Petit', average_age: 10
        })]]);
        expect(wrapper.emitted('delete-class')).toHaveLength(1);
    });

    it('renders column labels in English', () => {
        const translations = {
            'admin.class_name': 'Class Name',
            'admin.homeroom_teacher': 'Homeroom Teacher',
            'admin.average_age': 'Average Age'
        };
        setTestTranslator(key => translations[key] || key);

        const wrapper = mount(ClassList, {
            props: {
                classes: []
            },
            global: { components: { DataTable: DataTableStub } }
        });

        expect(wrapper.vm.columns).toEqual(expect.arrayContaining([
            expect.objectContaining({ label: 'Class Name' }),
            expect.objectContaining({ label: 'Homeroom Teacher' }),
            expect.objectContaining({ label: 'Average Age' })
        ]));
    });
});
