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
        expect(wrapper.vm.bookCountLabel(mockRoster[0])).toContain('book_singular');
        expect(wrapper.vm.bookCountLabel(mockRoster[1])).toContain('books_plural');
        expect(wrapper.vm.stats).toEqual({ borrowed: 0, overdue: 1, notYet: 1 });
    });

    it('auto-selects a single class and loads its student roster', async () => {
        const get = vi.mocked(apiClient.get).mockImplementation(async (endpoint) => {
            if (endpoint === '/classes') return [{ id: 9, name: 'CM2' }];
            if (endpoint === '/borrowers') return { data: mockRoster };
            return [];
        });
        const wrapper = mount(ClassRosterPanel);
        await flushPromises();

        expect(wrapper.vm.selectedClassId).toBe(9);
        expect(wrapper.vm.roster).toEqual(mockRoster);
        expect(get).toHaveBeenCalledWith('/borrowers', { class_id: 9, role: 'student', limit: 500 });
    });

    it('selects roster students from prefixed scans and leaves text filters local', async () => {
        vi.useFakeTimers();
        const wrapper = mount(ClassRosterPanel, {
            props: { settings: { borrower_barcode_prefix: '%' } }
        });
        await flushPromises();
        wrapper.vm.selectedClassId = 1;
        wrapper.vm.roster = mockRoster;

        wrapper.vm.handleFilterInput('%102');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.emitted('borrower-selected')).toEqual([['102']]);
        expect(wrapper.vm.filterQuery).toBe('');

        const before = apiClient.get.mock.calls.length;
        wrapper.vm.handleFilterInput('Amira');
        vi.advanceTimersByTime(500);
        await flushPromises();
        expect(wrapper.vm.filterQuery).toBe('Amira');
        expect(apiClient.get.mock.calls.length).toBe(before);
        vi.useRealTimers();
    });

    it('looks up unknown numeric scans, switches class, and leaves unknown IDs visible', async () => {
        vi.useFakeTimers();
        const get = vi.mocked(apiClient.get);
        get.mockImplementation(async (endpoint) => {
            if (endpoint === '/classes') return mockClasses;
            if (endpoint === '/borrowers') return mockRoster;
            if (endpoint === '/borrowers/999') return { borrower_id: '999', class_id: 2 };
            return [];
        });
        const wrapper = mount(ClassRosterPanel, { props: { settings: {} } });
        await flushPromises();
        wrapper.vm.selectedClassId = 1;
        wrapper.vm.roster = mockRoster;

        wrapper.vm.handleFilterInput('999');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.emitted('borrower-selected')).toEqual([['999']]);
        expect(wrapper.vm.selectedClassId).toBe(2);

        get.mockRejectedValueOnce(new Error('not found'));
        wrapper.vm.handleFilterInput('123');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.vm.filterQuery).toBe('123');
        vi.useRealTimers();
    });

    it('renders the no-class state when class loading fails or is empty', async () => {
        vi.mocked(apiClient.get).mockResolvedValueOnce([]);
        const wrapper = mount(ClassRosterPanel);
        await flushPromises();

        expect(wrapper.vm.classes).toEqual([]);
        expect(wrapper.vm.selectedClassId).toBeNull();
        expect(wrapper.text()).toContain('circulation.no_class_selected');
    });
});
