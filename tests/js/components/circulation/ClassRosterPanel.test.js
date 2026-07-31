import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import ClassRosterPanel from '../../../../src/bcd_web_vue/js/components/circulation/ClassRosterPanel.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

const mockClasses = [
    { id: 1, name: 'CP' },
    { id: 2, name: 'CE1' }
];

const mockRoster = [
    { id: 101, borrower_id: '101', first_name: 'Amira', last_name: 'BENALI', full_name: 'Amira BENALI', overdue_count: 0, current_loans_count: 0 },
    { id: 102, borrower_id: '102', first_name: 'Pierre', last_name: 'MARTIN', full_name: 'Pierre MARTIN', overdue_count: 1, current_loans_count: 2 }
];

beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => {
        if (endpoint === '/classes') {
            return mockClasses;
        }
        if (endpoint.includes('/borrowers')) {
            return mockRoster;
        }
        return [];
    });
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('ClassRosterPanel', () => {
    it('populates classes and filters the roster by search query', async () => {
        const wrapper = mount(ClassRosterPanel, {
            props: {
                settings: { borrower_barcode_prefix: '%' }
            }
        });
        await flushPromises();

        expect(wrapper.vm.classes).toEqual(mockClasses);

        // Initially without filter, full roster returned
        wrapper.vm.roster = mockRoster;
        expect(wrapper.vm.filteredRoster).toHaveLength(2);

        // Type search query to filter
        wrapper.vm.filterQuery = 'Ami';
        expect(wrapper.vm.filteredRoster).toHaveLength(1);
        expect(wrapper.vm.filteredRoster[0].first_name).toBe('Amira');
    });

    it('strips barcode prefix during filtering', async () => {
        const wrapper = mount(ClassRosterPanel, {
            props: {
                settings: { borrower_barcode_prefix: '%' }
            }
        });
        await flushPromises();

        wrapper.vm.roster = mockRoster;
        wrapper.vm.filterQuery = '%102'; // Scanned barcode

        expect(wrapper.vm.filteredRoster).toHaveLength(1);
        expect(wrapper.vm.filteredRoster[0].first_name).toBe('Pierre');
    });

    it('reports correct status for students', async () => {
        const wrapper = mount(ClassRosterPanel, {
            props: {
                settings: { borrower_barcode_prefix: '%' }
            }
        });
        await flushPromises();

        wrapper.vm.roster = mockRoster;

        expect(wrapper.vm.studentStatus(mockRoster[0])).toBe('none');
        expect(wrapper.vm.studentStatus(mockRoster[1])).toBe('overdue');
    });
});
