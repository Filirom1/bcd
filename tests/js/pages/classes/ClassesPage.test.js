import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import ClassesPage from '../../../../src/bcd_web_vue/js/pages/ClassesPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';
import { makeClass } from '../../fixtures/classes.js';
import { ApiError } from '../../../../src/bcd_web_vue/js/models/error.js';

const mountedWrappers = [];

function mountClassesPage() {
    const wrapper = shallowMount(ClassesPage);
    mountedWrappers.push(wrapper);
    return wrapper;
}

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('ClassesPage', () => {
    it('loads classes on mount and exposes them to the list', async () => {
        const classes = [makeClass({ id: 3, name: 'CE2' })];
        vi.spyOn(apiClient, 'get').mockResolvedValue(classes);

        const wrapper = mountClassesPage();
        await flushPromises();

        expect(apiClient.get).toHaveBeenCalledWith('/classes', { limit: 500 });
        expect(wrapper.vm.classes).toEqual(classes);
        expect(wrapper.vm.loading).toBe(false);
    });

    it('creates a class, refreshes the list, and closes the form', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue([]);
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue(makeClass({ id: 9 }));
        const wrapper = mountClassesPage();
        await flushPromises();

        wrapper.vm.showFormModal = true;
        wrapper.vm.selectedClass = null;
        await wrapper.vm.handleSaveClass({
            name: 'CP-A',
            homeroom_teacher: '',
            notes: '',
            average_age: 6
        });

        expect(post).toHaveBeenCalledWith('/classes', {
            name: 'CP-A',
            homeroom_teacher: null,
            notes: null,
            average_age: 6
        });
        expect(get).toHaveBeenCalledTimes(2);
        expect(wrapper.vm.showFormModal).toBe(false);
        expect(wrapper.vm.selectedClass).toBe(null);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'admin.class_created' })
        ]);
    });

    it('updates an existing class with a normalized payload', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue([]);
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({});
        const wrapper = mountClassesPage();
        await flushPromises();

        await wrapper.vm.handleSaveClass({
            id: 12,
            name: 'CM2',
            homeroom_teacher: 'Mme Martin',
            notes: '',
            average_age: null
        });

        expect(patch).toHaveBeenCalledWith('/classes/12', {
            name: 'CM2',
            homeroom_teacher: 'Mme Martin',
            notes: null,
            average_age: null
        });
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'admin.class_updated' })
        ]);
    });

    it('deletes a class only after the confirmation handler is called', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue([]);
        const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue(null);
        const wrapper = mountClassesPage();
        await flushPromises();

        wrapper.vm.handleDeleteClass(makeClass({ id: 21, name: 'CE1' }));
        expect(wrapper.vm.classToDelete.name).toBe('CE1');
        expect(remove).not.toHaveBeenCalled();

        await wrapper.vm.handleConfirmDelete(21);

        expect(remove).toHaveBeenCalledWith('/classes/21');
        expect(wrapper.vm.showDeleteDialog).toBe(false);
        expect(wrapper.vm.classToDelete).toBe(null);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'admin.class_deleted' })
        ]);
    });

    it('clears the list and reports an API failure', async () => {
        const error = ApiError.networkError(new Error('server unavailable'));
        vi.spyOn(apiClient, 'get').mockRejectedValue(error);

        const wrapper = mountClassesPage();
        await flushPromises();

        expect(wrapper.vm.classes).toEqual([]);
        expect(wrapper.vm.loading).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.network_error' })
        ]);
    });
});
