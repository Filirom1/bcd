import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import SettingsPage from '../../../../src/bcd_web_vue/js/pages/SettingsPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';
import { ApiError } from '../../../../src/bcd_web_vue/js/models/error.js';

const settings = {
    id: 1,
    library_name: 'BCD',
    library_code: 'ECOLE-01',
    loan_duration_days: 14,
    loan_limit_default: 3,
    language: 'fr'
};
const mountedWrappers = [];

function mountSettingsPage() {
    const wrapper = shallowMount(SettingsPage);
    mountedWrappers.push(wrapper);
    return wrapper;
}

function mockSettingsApi() {
    return vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
        if (endpoint === '/admin/settings') return { ...settings };
        if (endpoint === '/health') return { version: '1.4.0' };
        if (endpoint === '/admin/shelf-suggestion/status') {
            return { enabled: true, trained_at: null, trained_on_records: 0, ready: false };
        }
        throw new Error(`Unexpected GET request: ${endpoint}`);
    });
}

beforeEach(() => {
    useNotification().clear();
    globalThis.__testRoute.params.section = 'general';
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('SettingsPage', () => {
    it('loads settings, health information, and optional model status', async () => {
        const get = mockSettingsApi();
        const wrapper = mountSettingsPage();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/settings');
        expect(get).toHaveBeenCalledWith('/health');
        expect(get).toHaveBeenCalledWith('/admin/shelf-suggestion/status');
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.settings).toMatchObject(settings);
        expect(wrapper.vm.appVersion).toBe('1.4.0');
        expect(wrapper.vm.activeSection).toBe('general');
        expect(wrapper.vm.isSettingsForm).toBe(true);
    });

    it('saves only editable settings and reports success', async () => {
        mockSettingsApi();
        const put = vi.spyOn(apiClient, 'put').mockResolvedValue({});
        const wrapper = mountSettingsPage();
        await flushPromises();

        wrapper.vm.settings.loan_duration_days = 21;
        await wrapper.vm.saveSettings();

        expect(put).toHaveBeenCalledWith('/admin/settings', {
            updates: expect.objectContaining({
                library_name: 'BCD',
                loan_duration_days: 21
            })
        });
        expect(put.mock.calls[0][1].updates).not.toHaveProperty('id');
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'settings.save_success' })
        ]);
    });

    it('restores the last loaded settings when reset is requested', async () => {
        mockSettingsApi();
        const wrapper = mountSettingsPage();
        await flushPromises();

        wrapper.vm.settings.library_name = 'Changed locally';
        wrapper.vm.resetSettings();

        expect(wrapper.vm.settings.library_name).toBe('BCD');
    });

    it('trains shelf suggestions and stores the returned status', async () => {
        mockSettingsApi();
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
            status: 'completed',
            enabled: true,
            ready: true,
            trained_on_records: 42
        });
        const wrapper = mountSettingsPage();
        await flushPromises();

        await wrapper.vm.trainShelfSuggestion();

        expect(post).toHaveBeenCalledWith('/admin/shelf-suggestion/train', {});
        expect(wrapper.vm.shelfSuggestionStatus).toMatchObject({
            status: 'completed',
            trained_on_records: 42
        });
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'settings.shelf_suggestion_train_done' })
        ]);
    });

    it('selects non-form sections from the route', async () => {
        globalThis.__testRoute.params.section = 'backup';
        mockSettingsApi();

        const wrapper = mountSettingsPage();
        await flushPromises();

        expect(wrapper.vm.activeSection).toBe('backup');
        expect(wrapper.vm.isSettingsForm).toBe(false);
    });

    it('keeps the page usable when settings cannot be loaded', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(ApiError.networkError(new Error('offline')));

        const wrapper = mountSettingsPage();
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.network_error' })
        ]);
    });

    it('continues when optional shelf suggestion status is unavailable', async () => {
        const get = vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { ...settings };
            if (endpoint === '/health') return { version: '1.4.0' };
            throw new Error('optional endpoint unavailable');
        });
        const wrapper = mountSettingsPage();
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/shelf-suggestion/status');
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.settings.library_name).toBe('BCD');
    });

    it('reports save failures and always clears the saving state', async () => {
        mockSettingsApi();
        vi.spyOn(apiClient, 'put').mockRejectedValue(ApiError.networkError(new Error('offline')));
        const wrapper = mountSettingsPage();
        await flushPromises();

        await wrapper.vm.saveSettings();
        expect(wrapper.vm.saving).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.network_error' })
        ]);
    });

    it('handles insufficient and failed shelf suggestion training', async () => {
        mockSettingsApi();
        const post = vi.spyOn(apiClient, 'post')
            .mockResolvedValueOnce({ status: 'insufficient', trained_on_records: 3 })
            .mockRejectedValueOnce(ApiError.networkError(new Error('offline')));
        const wrapper = mountSettingsPage();
        await flushPromises();

        await wrapper.vm.trainShelfSuggestion();
        expect(wrapper.vm.shelfSuggestionStatus.status).toBe('insufficient');
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'settings.shelf_suggestion_train_insufficient' })
        ]);

        useNotification().clear();
        await wrapper.vm.trainShelfSuggestion();
        expect(post).toHaveBeenCalledTimes(2);
        expect(wrapper.vm.shelfSuggestionTraining).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.network_error' })
        ]);
    });

    it('navigates only to valid settings sections', async () => {
        mockSettingsApi();
        const push = vi.fn().mockResolvedValue(undefined);
        globalThis.__testRouter.push = push;
        const wrapper = mountSettingsPage();
        await flushPromises();

        wrapper.vm.navigateTo('catalog');
        wrapper.vm.navigateTo('not-a-section');
        expect(push).toHaveBeenCalledTimes(1);
        expect(push).toHaveBeenCalledWith('/settings/catalog');
    });
});
