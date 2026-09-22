import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import CollectionsPage from '../../../src/bcd_web_vue/js/pages/CollectionsPage.js';
import PrintBorrowerReference from '../../../src/bcd_web_vue/js/pages/PrintBorrowerReference.js';
import PrintStudentCards from '../../../src/bcd_web_vue/js/pages/PrintStudentCards.js';
import PrintItemLabels from '../../../src/bcd_web_vue/js/pages/PrintItemLabels.js';
import { apiClient } from '../../../src/bcd_web_vue/js/api/client.js';
import { useAppState } from '../../../src/bcd_web_vue/js/composables/useAppState.js';

const settings = {
    library_name: 'BCD',
    library_code: 'ECOLE',
    borrower_barcode_prefix: '%',
    item_barcode_prefix: '.',
    barcode_type: 'code39'
};

const borrowers = [
    { id: 1, borrower_id: '102', first_name: 'Zoé', last_name: 'Martin', class_name: 'CM2', role: 'student', homeroom_teacher: 'Mme A' },
    { id: 2, borrower_id: '101', first_name: 'Amir', last_name: 'Martin', class_name: 'CM2', role: 'student' },
    { id: 3, borrower_id: '103', first_name: 'Lou', last_name: 'Bernard', class_name: null, role: 'teacher' }
];

beforeEach(() => {
    useAppState().saveSettings(settings);
});

afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
});

describe('CollectionsPage', () => {
    it('loads local information and network peers', async () => {
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { library_code: 'ECOLE-42' };
            return [{ name: 'peer-1', library_code: 'ANNEXE', url: 'http://annexe' }];
        });
        const wrapper = mount(CollectionsPage, { global: { stubs: { HelpPanel: true } } });
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/settings');
        expect(get).toHaveBeenCalledWith('/collections/peers');
        expect(wrapper.vm.localLibraryCode).toBe('ECOLE-42');
        expect(wrapper.vm.localUrl).toBe(window.location.origin);
        expect(wrapper.vm.peers).toHaveLength(1);
        expect(wrapper.text()).toContain('ANNEXE');

        await wrapper.vm.loadPeers();
        expect(wrapper.vm.loading).toBe(false);
    });

    it('falls back to BCD and an empty peer list on API failures', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('offline'));
        const wrapper = mount(CollectionsPage, { global: { stubs: { HelpPanel: true } } });
        await flushPromises();

        expect(wrapper.vm.localLibraryCode).toBe('BCD');
        expect(wrapper.vm.peers).toEqual([]);
        expect(wrapper.vm.loading).toBe(false);
    });
});

describe('PrintBorrowerReference', () => {
    it('groups and sorts borrowers with the configured barcode prefix', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue({ items: borrowers });
        const print = vi.spyOn(window, 'print').mockImplementation(() => {});
        const wrapper = mount(PrintBorrowerReference);
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.error).toBe(null);
        expect(wrapper.vm.totalCount).toBe(3);
        expect(Object.keys(wrapper.vm.borrowersByClass)).toEqual(['CM2', 'Sans classe']);
        expect(wrapper.vm.borrowersByClass.CM2.students.map(student => student.borrower_id)).toEqual(['101', '102']);
        expect(wrapper.findAll('.barcode')[0].attributes('data-code')).toBe('%101');
        await wrapper.vm.printPage();
        expect(print).toHaveBeenCalledTimes(1);
    });

    it('renders an error when borrowers cannot be loaded', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('cannot load'));
        const wrapper = mount(PrintBorrowerReference);
        await flushPromises();
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.error).toBe('Failed to load borrowers');
    });
});

describe('PrintStudentCards', () => {
    it('renders cards and applies library and borrower barcode settings', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue({ items: borrowers });
        const wrapper = mount(PrintStudentCards);
        await flushPromises();

        expect(wrapper.vm.libraryName).toBe('BCD');
        expect(wrapper.vm.borrowers[0].barcodeWithPrefix).toBe('%102');
        expect(wrapper.findAll('.library-card')).toHaveLength(3);
        expect(wrapper.find('.card-header').text()).toContain('BCD');
    });
});

describe('PrintItemLabels', () => {
    it('generates labels, computes sheets and supports customisation', async () => {
        vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/catalog/items/available-ids') return { ids: ['.I-001', '.I-002', '.I-003'] };
            return settings;
        });
        const print = vi.spyOn(window, 'print').mockImplementation(() => {});
        const wrapper = mount(PrintItemLabels);
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.generatedIds).toEqual(['.I-001', '.I-002', '.I-003']);
        expect(wrapper.vm.totalCount).toBe(3);
        expect(wrapper.vm.labelsPerSheet).toBeGreaterThan(0);
        expect(wrapper.vm.sheetsCount).toBe(1);
        expect(wrapper.vm.libraryName).toBe('BCD');
        expect(wrapper.vm.barcodePrefix).toBe('.');
        expect(wrapper.vm.formatDims(wrapper.vm.labelFormats[0])).toContain('mm');

        wrapper.vm.customParams.layout.cols = 2;
        wrapper.vm.customParams.layout.rows = 2;
        expect(wrapper.vm.labelsPerSheet).toBe(4);
        wrapper.vm.generatedIds = ['1', '2', '3', '4', '5'];
        expect(wrapper.vm.labelSheets).toHaveLength(2);
        wrapper.vm.customParams.label.height_mm = 100;
        expect(wrapper.vm.isModified).toBe(true);
        wrapper.vm.resetToPreset();
        expect(wrapper.vm.isModified).toBe(false);
        wrapper.vm.fillOneSheet();
        expect(wrapper.vm.labelCount).toBe(wrapper.vm.labelsPerSheet);
        wrapper.vm.advancedOpen = true;
        await wrapper.vm.printPage();
        expect(print).toHaveBeenCalledTimes(1);
    });

    it('passes generation parameters and exposes generation errors', async () => {
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/catalog/items/available-ids') return { ids: ['.I-010'] };
            return settings;
        });
        const wrapper = mount(PrintItemLabels);
        await flushPromises();

        wrapper.vm.startId = '  .I-010  ';
        wrapper.vm.contiguous = false;
        wrapper.vm.labelCount = 1;
        await wrapper.vm.generateIds();
        expect(get).toHaveBeenLastCalledWith('/catalog/items/available-ids', {
            count: 1, start_from: '.I-010', contiguous: 'false'
        });

        get.mockImplementation(async endpoint => {
            if (endpoint === '/catalog/items/available-ids') throw new Error('generation failed');
            return settings;
        });
        await wrapper.vm.generateIds();
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.error).toBe('generation failed');
    });
});
