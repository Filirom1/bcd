import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import ExternalCatalogSourcesPage from '../../../../src/bcd_web_vue/js/pages/ExternalCatalogSourcesPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const sourceSettings = {
    id: 1,
    bnf_enabled: true,
    bnf_timeout: 4,
    google_books_enabled: true,
    google_books_timeout: 4,
    sudoc_enabled: true,
    sudoc_timeout: 5
};

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('ExternalCatalogSourcesPage', () => {
    it('loads and saves only external source settings', async () => {
        vi.spyOn(apiClient, 'get').mockImplementation(async endpoint => {
            if (endpoint === '/admin/settings') return { ...sourceSettings };
            if (endpoint === '/health') return { version: '1.4.0' };
            throw new Error(`Unexpected endpoint: ${endpoint}`);
        });
        const put = vi.spyOn(apiClient, 'put').mockResolvedValue({});
        const wrapper = shallowMount(ExternalCatalogSourcesPage);
        await flushPromises();

        wrapper.vm.settings.google_books_enabled = false;
        wrapper.vm.settings.google_books_timeout = 9;
        await wrapper.vm.saveSettings();

        expect(put).toHaveBeenCalledWith('/admin/settings', {
            updates: {
                bnf_enabled: true,
                bnf_timeout: 4,
                google_books_enabled: false,
                google_books_timeout: 9,
                sudoc_enabled: true,
                sudoc_timeout: 5
            }
        });
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'settings.save_success' })
        ]);
    });
});
