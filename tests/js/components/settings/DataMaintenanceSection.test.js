import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import DataMaintenanceSection from '../../../../src/bcd_web_vue/js/components/settings/DataMaintenanceSection.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('DataMaintenanceSection', () => {
    it('requires confirmation before setting acquisition dates', async () => {
        const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ updated_count: 3 });
        const wrapper = mount(DataMaintenanceSection);

        await wrapper.vm.setAcquisitionDatesFromPublicationYear();
        expect(confirm).toHaveBeenCalledWith('settings.data_maintenance_acquisition_dates_confirm');
        expect(post).not.toHaveBeenCalled();

        confirm.mockReturnValue(true);
        await wrapper.vm.setAcquisitionDatesFromPublicationYear();
        expect(post).toHaveBeenCalledWith('/admin/data-maintenance/set-acquisition-dates', {});
        expect(wrapper.vm.settingAcquisitionDates).toBe(false);
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ message: 'settings.data_maintenance_acquisition_dates_success' })
        );
    });

    it('handles a maintenance request failure and resets its busy state', async () => {
        vi.spyOn(window, 'confirm').mockReturnValue(true);
        vi.spyOn(apiClient, 'post').mockRejectedValue(new Error('server error'));
        const wrapper = mount(DataMaintenanceSection);

        await wrapper.vm.setAcquisitionDatesFromPublicationYear();
        await flushPromises();

        expect(wrapper.vm.settingAcquisitionDates).toBe(false);
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ type: 'error', message: 'errors.unknown_error' })
        );
    });
});
