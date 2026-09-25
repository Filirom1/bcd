import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import BibliographicFields from '../../../../src/bcd_web_vue/js/components/catalog/BibliographicFields.js';
import CatalogBulkEditModal from '../../../../src/bcd_web_vue/js/components/catalog/BulkEditModal.js';
import ColumnSelector from '../../../../src/bcd_web_vue/js/components/catalog/ColumnSelector.js';
import InventoryColumnSelector from '../../../../src/bcd_web_vue/js/components/inventory/InventoryColumnSelector.js';
import RecordDeleteDialog from '../../../../src/bcd_web_vue/js/components/catalog/RecordDeleteDialog.js';
import ItemEditForm from '../../../../src/bcd_web_vue/js/components/catalog/ItemEditForm.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';

const model = () => ({
    title: 'Book', subtitle: 'Subtitle', isbn: '9780000000000', authors: ['Doe', 'Roe'],
    illustrators: ['Artist'], publisher: 'Publisher', publication_year: 2020,
    collection: 'Collection', series_number: '1', medium_type: 'Livre', target_audience: 'child',
    level: 'CM2', language: 'fr', country_code: 'FR', binding_type: 'softcover', page_count: 80,
    has_illustrations: true, dimensions: '20 cm', physical_size: 'A4', keywords: ['magic'],
    description: 'Description'
});

afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
});

describe('BibliographicFields', () => {
    it('bridges arrays and CSV fields and exposes suggestions and validation', async () => {
        const value = model();
        const wrapper = mount(BibliographicFields, {
            props: {
                modelValue: value,
                errors: { title: 'Required' },
                settings: {
                    catalog_medium_types: 'Livre, DVD',
                    catalog_levels: 'CP, CM2',
                    catalog_languages: 'fr, en'
                }
            }
        });

        expect(wrapper.vm.authorsText).toBe('Doe, Roe');
        wrapper.vm.authorsText = 'Alice, Bob';
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted('update:modelValue').at(-1)[0].authors).toEqual(['Alice', 'Bob']);
        expect(wrapper.vm.mediumTypeSuggestions).toEqual(['Livre', 'DVD']);
        expect(wrapper.vm.levelSuggestions).toEqual(['CP', 'CM2']);
        expect(wrapper.vm.languageSuggestions).toEqual(['fr', 'en']);
        expect(wrapper.vm.hasValue('authors')).toBe(true);
        expect(wrapper.vm.labelFor(wrapper.vm.audienceOptions, 'child')).toBe('bibliographic.audience_child');
        expect(wrapper.find('[data-testid="error-title"]').exists()).toBe(true);

        await wrapper.get('select').setValue('adult');
        expect(wrapper.emitted('update:modelValue').at(-1)[0].target_audience).toBe('adult');
    });

    it('renders only populated fields in read-only mode', () => {
        const value = { title: 'Visible', target_audience: 'child', language: 'fr', binding_type: 'hardcover' };
        const wrapper = mount(BibliographicFields, {
            props: { modelValue: value, editMode: false, hideSeriesNumber: true }
        });
        expect(wrapper.find('input[readonly]').exists()).toBe(true);
        expect(wrapper.find('input[readonly]').element.value).toBe('Visible');
        expect(wrapper.vm.getLanguageDisplay).toBe('fr');
        expect(wrapper.vm.hasValue('missing')).toBe(false);
    });
});

describe('Column selectors', () => {
    it('opens, toggles, resets and closes the catalog selector', async () => {
        const wrapper = mount(ColumnSelector, { props: { visibleColumns: ['title'] } });
        expect(wrapper.vm.isColumnVisible('title')).toBe(true);
        expect(wrapper.vm.isColumnVisible('isbn')).toBe(false);
        await wrapper.find('button').trigger('click');
        expect(wrapper.vm.showDropdown).toBe(true);
        wrapper.vm.toggleColumn('isbn');
        expect(wrapper.emitted('toggle-column')).toEqual([['isbn']]);
        await wrapper.find('.dropdown-item').trigger('click');
        expect(wrapper.emitted('reset')).toHaveLength(1);
        expect(wrapper.vm.showDropdown).toBe(false);
        wrapper.vm.toggleDropdown();
        wrapper.vm.closeDropdown();
        expect(wrapper.vm.showDropdown).toBe(false);
    });

    it('handles the inventory selector with localized labels', async () => {
        const wrapper = mount(InventoryColumnSelector, { props: { visibleColumns: ['item_id'] } });
        await wrapper.find('button').trigger('click');
        expect(wrapper.find('.inventory-column-selector-menu').exists()).toBe(true);
        const column = wrapper.vm.INVENTORY_AVAILABLE_COLUMNS[0];
        expect(wrapper.vm.getColumnLabel(column)).toBe(column.label_fr);
        wrapper.vm.toggleColumn(column.id);
        expect(wrapper.emitted('toggle-column')).toEqual([[column.id]]);
        await wrapper.find('.dropdown-item').trigger('click');
        expect(wrapper.emitted('reset')).toHaveLength(1);
    });
});

describe('RecordDeleteDialog', () => {
    const record = {
        id: 4, title: 'Delete me', authors: ['Author'], isbn: true,
        isbn_value: '9780000000000', items: [{ status: 'on_loan' }, { status: 'available' }]
    };

    it('shows loan warnings and prevents confirmation while a copy is loaned', async () => {
        const wrapper = mount(RecordDeleteDialog, { props: { show: true, recordData: record } });
        expect(wrapper.vm.hasActiveLoans).toBe(true);
        expect(wrapper.vm.itemCount).toBe(2);
        expect(document.body.querySelector('.alert-danger')).not.toBeNull();
        expect(document.body.querySelector('button.btn-danger').disabled).toBe(true);
        wrapper.vm.handleClose();
        expect(wrapper.emitted('close')).toHaveLength(1);
    });

    it('emits the record identifier when deletion is allowed', async () => {
        const wrapper = mount(RecordDeleteDialog, {
            props: { show: true, recordData: { id: 5, title: 'Delete', items: [] } }
        });
        expect(wrapper.vm.hasActiveLoans).toBe(false);
        await wrapper.vm.handleConfirm();
        expect(wrapper.emitted('confirm')).toEqual([[5]]);
    });
});

describe('CatalogBulkEditModal', () => {
    it('runs the bulk edit wizard and emits only populated fields', async () => {
        const wrapper = mount(CatalogBulkEditModal, {
            props: {
                show: true,
                selectedRecords: [{ id: 1 }, { id: 2 }],
                settings: { catalog_levels: 'CP, CM2', catalog_languages: 'fr, en', catalog_medium_types: 'Livre, DVD' }
            }
        });
        expect(wrapper.vm.selectedCount).toBe(2);
        expect(wrapper.vm.canProceedStep1).toBe(false);
        wrapper.vm.selectOperation(wrapper.vm.OPERATIONS.BULK_EDIT);
        wrapper.vm.fields.level = 'CM2';
        wrapper.vm.fields.publisher = 'Gallimard';
        expect(wrapper.vm.canProceedStep1).toBe(true);
        expect(wrapper.vm.canProceedStep2).toBe(true);
        expect(wrapper.vm.fieldsSummary).toHaveLength(2);
        wrapper.vm.nextStep();
        wrapper.vm.goToStep(3);
        expect(wrapper.vm.confirmationMessage).toBe('admin.confirm_bulk_edit_records');
        wrapper.vm.handleExecute();
        expect(wrapper.emitted('execute')).toEqual([[
            { operation: 'bulk_edit', fields: { level: 'CM2', publisher: 'Gallimard' } }
        ]]);
        expect(wrapper.vm.currentStep).toBe(1);
    });

    it('supports delete, navigation and reset/close actions', async () => {
        const wrapper = mount(CatalogBulkEditModal, { props: { show: true, selectedRecords: [{ id: 1 }] } });
        wrapper.vm.selectOperation(wrapper.vm.OPERATIONS.DELETE);
        expect(wrapper.vm.canProceedStep2).toBe(true);
        wrapper.vm.nextStep();
        wrapper.vm.previousStep();
        expect(wrapper.vm.currentStep).toBe(1);
        wrapper.vm.goToStep(3);
        expect(wrapper.vm.confirmationMessage).toBe('admin.confirm_bulk_delete_records');
        wrapper.vm.handleExecute();
        expect(wrapper.emitted('execute')).toContainEqual([{ operation: 'delete' }]);
        wrapper.vm.handleClose();
        expect(wrapper.emitted('close')).toHaveLength(1);
    });
});

describe('ItemEditForm', () => {
    const item = {
        item_id: '.I-1', call_number: 'OLD', shelf_location: 'Fiction', condition: 'good',
        status: 'available', loanable: true, acquisition_date: '2030-01-01', funding_source: 'School'
    };
    const global = {
        stubs: {
            Modal: { template: '<div><slot name="header"/><slot/><slot name="footer"/></div>' },
            DeweyPicker: { template: '<div />' },
            ShelfLocationPicker: { template: '<div />' }
        }
    };

    it('uses the issue number field for periodicals identified by their medium', () => {
        const wrapper = mount(ItemEditForm, {
            props: {
                item,
                record: { title: 'J-magazine', medium_type: 'Périodique' },
                show: true
            },
            global
        });

        expect(wrapper.vm.isPeriodical).toBe(true);
        expect(wrapper.findAll('label')[1].text()).toBe('periodical.issue_number');
    });

    it('validates, saves and closes an item form', async () => {
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ ...item, condition: 'damaged' });
        const wrapper = mount(ItemEditForm, {
            props: { item, record: { title: 'Book', authors: ['Author'], dewey_number: '500' }, show: true },
            global
        });
        expect(wrapper.vm.formData).toMatchObject({ barcode: '.I-1', call_number: 'OLD' });
        wrapper.vm.formData.barcode = '';
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.barcode).toBe('errors.required_field');

        wrapper.vm.formData.barcode = '.I-1';
        wrapper.vm.formData.condition = 'damaged';
        await wrapper.vm.handleSubmit();
        expect(patch).toHaveBeenCalledWith('/catalog/items/.I-1', expect.objectContaining({ condition: 'damaged' }));
        expect(wrapper.emitted('saved')).toHaveLength(1);
        expect(wrapper.emitted('update:show')).toContainEqual([false]);
    });

    it('maps duplicate and validation API errors', async () => {
        const patch = vi.spyOn(apiClient, 'patch').mockRejectedValueOnce({
            statusCode: 409, details: { existing_item_id: '.I-9' }
        }).mockRejectedValueOnce({ statusCode: 400, message: 'Bad data' });
        const wrapper = mount(ItemEditForm, { props: { item, show: true }, global });
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.barcode).toBe('errors.DUPLICATE_BARCODE');
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('Bad data');
        wrapper.vm.handleCancel();
        expect(wrapper.emitted('update:show')).toContainEqual([false]);
    });

    it('saves all physical item fields and emits the catalogue refresh event', async () => {
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ item_id: '.I-1' });
        const wrapper = mount(ItemEditForm, {
            props: {
                item,
                record: { title: 'The Book', authors: ['Martin'], dewey_number: '500', medium_type: 'Book' },
                settings: {
                    catalog_shelf_locations: '[{"label":"Romans"}]',
                    catalog_call_number_rules: '[{"shelf_location":"Romans","pattern":"{DEWEY} {AUT3}"}]',
                    dewey_colors: '{"5":"#fff"}'
                },
                show: true
            },
            global
        });
        wrapper.vm.formData.condition = 'damaged';
        wrapper.vm.formData.status = 'lost';
        wrapper.vm.formData.loanable = false;
        wrapper.vm.formData.acquisition_date = '2024-06-01';
        wrapper.vm.formData.shelf_location = 'Romans';
        wrapper.vm.formData.funding_source = 'Donation';
        wrapper.vm.handleShelfLocationChange('Romans');
        await wrapper.vm.handleSubmit();

        expect(wrapper.vm.formData.call_number).toBe('500 MAR');
        expect(patch).toHaveBeenCalledWith('/catalog/items/.I-1', {
            call_number: '500 MAR', shelf_location: 'Romans', condition: 'damaged', status: 'lost',
            loanable: false, acquisition_date: '2024-06-01', funding_source: 'Donation'
        });
        expect(wrapper.emitted('saved')).toHaveLength(1);
    });

    it.each(['lost', 'withdrawn', 'in_repair'])('offers the %s status', status => {
        const wrapper = mount(ItemEditForm, { props: { item, show: true }, global });
        expect(wrapper.vm.statusOptions.map(option => option.value)).toContain(status);
        wrapper.vm.formData.status = status;
        expect(wrapper.vm.formData.status).toBe(status);
    });

    it('recalculates a call number when the shelf changes but keeps a manual call number without a matching rule', async () => {
        const wrapper = mount(ItemEditForm, {
            props: {
                item,
                record: { title: 'Book', authors: ['Doe'], dewey_number: '100' },
                settings: { catalog_call_number_rules: '[{"shelf_location":"Fiction","pattern":"{DEWEY}-{AUT3}"}]' },
                show: true
            },
            global
        });
        wrapper.vm.handleShelfLocationChange('Fiction');
        expect(wrapper.vm.formData.call_number).toBe('100-DOE');
        wrapper.vm.formData.call_number = 'MANUAL';
        wrapper.vm.handleShelfLocationChange('Other');
        expect(wrapper.vm.formData.call_number).toBe('MANUAL');
        expect(wrapper.vm.deweyColors).toBeUndefined();
        expect(wrapper.vm.shelfLocationOptions).toEqual([]);
    });

    it('reloads form state when item prop changes and cancels without an API request', async () => {
        const patch = vi.spyOn(apiClient, 'patch');
        const wrapper = mount(ItemEditForm, { props: { item, show: true }, global });
        const replacement = { item_id: '.I-2', status: 'in_repair', condition: 'damaged', loanable: false };
        await wrapper.setProps({ item: replacement });
        expect(wrapper.vm.formData).toMatchObject({ barcode: '.I-2', status: 'in_repair', condition: 'damaged', loanable: false });
        wrapper.vm.handleCancel();
        expect(patch).not.toHaveBeenCalled();
        expect(wrapper.emitted('update:show')).toContainEqual([false]);
    });

    it('clears the shelf and preserves the call number when the picker emits __clear__', async () => {
        const wrapper = mount(ItemEditForm, {
            props: {
                item,
                record: { title: 'Book', authors: ['Doe'], dewey_number: '100' },
                settings: { catalog_call_number_rules: '[{"shelf_location":"Fiction","pattern":"{DEWEY}-{AUT3}"}]' },
                show: true
            },
            global
        });
        wrapper.vm.handleShelfLocationChange('Fiction');
        expect(wrapper.vm.formData.call_number).toBe('100-DOE');
        wrapper.vm.handleShelfLocationChange('__clear__');
        expect(wrapper.vm.formData.shelf_location).toBe('');
        expect(wrapper.vm.formData.call_number).toBe('100-DOE');
    });

    it('does not generate a call number when bibliographic data is absent', () => {
        const wrapper = mount(ItemEditForm, { props: { item: { item_id: '.I-empty' }, show: true }, global });
        wrapper.vm.handleShelfLocationChange('Fiction');
        expect(wrapper.vm.formData.call_number).toBe('');
    });

    it('uses global settings when no item-form settings prop is supplied', () => {
        useAppState().saveSettings({
            catalog_call_number_rules: '[{"shelf_location":"Fiction","pattern":"{DEWEY} {AUT3}"}]',
            dewey_colors: '{"1":"#fff"}',
            catalog_shelf_locations: '[{"label":"Fiction"}]'
        });
        const wrapper = mount(ItemEditForm, {
            props: { item, record: { title: 'Book', authors: ['Doe'], dewey_number: '100' }, show: true },
            global
        });
        expect(wrapper.vm.deweyColors).toEqual({ '1': '#fff' });
        expect(wrapper.vm.shelfLocationOptions).toEqual([{ label: 'Fiction' }]);
        wrapper.vm.handleShelfLocationChange('Fiction');
        expect(wrapper.vm.formData.call_number).toBe('100 DOE');
        useAppState().clearStorage();
    });

    it.each(['withdrawn', 'in_repair'])('persists the %s status on save', async status => {
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ item_id: '.I-1', status });
        const wrapper = mount(ItemEditForm, { props: { item, show: true }, global });
        wrapper.vm.formData.status = status;
        await wrapper.vm.handleSubmit();
        expect(patch).toHaveBeenCalledWith('/catalog/items/.I-1', expect.objectContaining({ status }));
    });

    it('initializes safe defaults for an item without optional physical fields', () => {
        const wrapper = mount(ItemEditForm, { props: { item: { item_id: '.I-minimal' }, show: true }, global });
        expect(wrapper.vm.formData).toMatchObject({
            barcode: '.I-minimal', call_number: '', shelf_location: '', condition: 'good',
            status: 'available', loanable: true, acquisition_date: '', funding_source: ''
        });
    });

    it('displays a generic network error and tolerates malformed settings', async () => {
        const patch = vi.spyOn(apiClient, 'patch').mockRejectedValue(new Error('offline'));
        const wrapper = mount(ItemEditForm, {
            props: {
                item,
                settings: { catalog_call_number_rules: '{bad', catalog_shelf_locations: '{bad', dewey_colors: '{bad' },
                show: true
            },
            global
        });
        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('offline');
        expect(wrapper.vm.deweyColors).toBeUndefined();
        expect(wrapper.vm.shelfLocationOptions).toEqual([]);
    });

    it('uses safe fallbacks for message-less duplicate and validation errors', async () => {
        const patch = vi.spyOn(apiClient, 'patch')
            .mockRejectedValueOnce({ statusCode: 409, details: {} })
            .mockRejectedValueOnce({ statusCode: 400 })
            .mockRejectedValueOnce({ statusCode: 500 });
        const wrapper = mount(ItemEditForm, { props: { item, show: true }, global });

        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.barcode).toBe('errors.DUPLICATE_BARCODE');

        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('errors.validation_failed');

        await wrapper.vm.handleSubmit();
        expect(wrapper.vm.errors.general).toBe('errors.unknown_error');
        expect(wrapper.vm.isSubmitting).toBe(false);
    });

    it('updates the form through the real ShelfLocationPicker', async () => {
        vi.spyOn(apiClient, 'patch').mockResolvedValue({ item_id: item.item_id });
        const realPickerGlobal = {
            stubs: {
                Modal: global.stubs.Modal,
                DeweyPicker: global.stubs.DeweyPicker
            }
        };
        const wrapper = mount(ItemEditForm, {
            props: {
                item,
                record: { title: 'A book', authors: ['Doe'], dewey_number: '100' },
                settings: {
                    catalog_shelf_locations: '[{"label":"Fiction","color":"#123456"}]',
                    catalog_call_number_rules: '[{"shelf_location":"Fiction","pattern":"{DEWEY}-{AUT3}"}]'
                },
                show: true
            },
            global: realPickerGlobal
        });

        const picker = wrapper.findComponent({ name: 'ShelfLocationPicker' });
        expect(picker.exists()).toBe(true);
        await picker.get('button').trigger('click');
        await picker.find('.border.rounded.mt-1 button').trigger('click');
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.formData.shelf_location).toBe('Fiction');
        expect(wrapper.vm.formData.call_number).toBe('100-DOE');
    });

    it('supports alternate record fields and ignores a cleared item prop', async () => {
        const wrapper = mount(ItemEditForm, {
            props: {
                item,
                record: { name: 'Named record', authors: ['Doe'], deweyNumber: '200' },
                settings: {
                    catalog_call_number_rules: '[{"shelf_location":"Fiction","pattern":"{DEWEY} {AUT3}"}]'
                },
                show: true
            },
            global
        });
        wrapper.vm.handleShelfLocationChange('Fiction');
        expect(wrapper.vm.formData.call_number).toBe('200 DOE');
    });
});
