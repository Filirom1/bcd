import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import { setTestTranslator } from '../../helpers/i18n.js';
import AdminDropdown from '../../../../src/bcd_web_vue/js/components/admin/AdminDropdown.js';

function mountDropdown(selectedCount, page = 'borrowers', translate = key => key) {
    setTestTranslator(translate);
    return mount(AdminDropdown, {
        props: {
            page,
            selectedCount
        }
    });
}

describe('AdminDropdown', () => {
    it('disables edit and bulk edit when no records are selected', async () => {
        const wrapper = mountDropdown(0);

        const editSelected = wrapper.get('[data-testid="admin-menu-edit-selected"]');
        const bulkEdit = wrapper.get('[data-testid="admin-menu-bulk-edit"]');
        expect(editSelected.classes()).toContain('disabled');
        expect(bulkEdit.classes()).toContain('disabled');

        await editSelected.trigger('click');
        await bulkEdit.trigger('click');

        expect(wrapper.emitted('edit-selected')).toBeUndefined();
        expect(wrapper.emitted('bulk-edit')).toBeUndefined();
    });

    it('enables only edit selected for exactly one selected record', async () => {
        const wrapper = mountDropdown(1);

        const editSelected = wrapper.get('[data-testid="admin-menu-edit-selected"]');
        const bulkEdit = wrapper.get('[data-testid="admin-menu-bulk-edit"]');
        expect(editSelected.classes()).not.toContain('disabled');
        expect(bulkEdit.classes()).toContain('disabled');

        await editSelected.trigger('click');
        await bulkEdit.trigger('click');

        expect(wrapper.emitted('edit-selected')).toHaveLength(1);
        expect(wrapper.emitted('bulk-edit')).toBeUndefined();
    });

    it('enables only bulk edit when multiple records are selected', async () => {
        const wrapper = mountDropdown(2);

        const editSelected = wrapper.get('[data-testid="admin-menu-edit-selected"]');
        const bulkEdit = wrapper.get('[data-testid="admin-menu-bulk-edit"]');
        expect(editSelected.classes()).toContain('disabled');
        expect(bulkEdit.classes()).not.toContain('disabled');

        await editSelected.trigger('click');
        await bulkEdit.trigger('click');

        expect(wrapper.emitted('edit-selected')).toBeUndefined();
        expect(wrapper.emitted('bulk-edit')).toHaveLength(1);
    });

    it('emits import and export actions for the parent page to handle', async () => {
        const wrapper = mountDropdown(0);

        await wrapper.get('[data-testid="admin-menu-import"]').trigger('click');
        await wrapper.get('[data-testid="admin-menu-export"]').trigger('click');

        expect(wrapper.emitted('import')).toHaveLength(1);
        expect(wrapper.emitted('export')).toHaveLength(1);
    });

    it.each([
        ['borrowers', 'admin.import_borrowers', 'admin.export_borrowers'],
        ['catalog', 'admin.import_catalog', 'admin.export_catalog'],
        ['inventory', 'admin.import_inventory', 'admin.export_inventory']
    ])('renders contextual labels for the %s page', (page, importKey, exportKey) => {
        const wrapper = mountDropdown(0, page, key => key);

        expect(wrapper.get('[data-testid="admin-menu-import"]').text()).toContain(importKey);
        expect(wrapper.get('[data-testid="admin-menu-export"]').text()).toContain(exportKey);
    });

    it('renders the expected borrower menu labels in English', () => {
        const translations = {
            'admin.import_borrowers': 'Import borrowers',
            'admin.export_borrowers': 'Export borrowers',
            'admin.edit_selected': 'Edit selected',
            'admin.bulk_edit': 'Bulk edit'
        };
        const wrapper = mountDropdown(0, 'borrowers', key => translations[key] || key);

        expect(wrapper.get('[data-testid="admin-menu-import"]').text()).toContain('Import borrowers');
        expect(wrapper.get('[data-testid="admin-menu-export"]').text()).toContain('Export borrowers');
        expect(wrapper.get('[data-testid="admin-menu-edit-selected"]').text()).toContain('Edit selected');
        expect(wrapper.get('[data-testid="admin-menu-bulk-edit"]').text()).toContain('Bulk edit');
    });
});
