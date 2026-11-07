import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import ExternalCatalogSourcesPage from '../../../../src/bcd_web_vue/js/pages/ExternalCatalogSourcesPage.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const sourceSettings = {
    id: 1,
    bnf_enabled: true,
    bnf_timeout: 2,
    google_books_enabled: true,
    google_books_timeout: 2,
    sudoc_enabled: true,
    sudoc_timeout: 3,
    cover_custom_url_enabled: true,
    cover_custom_url_timeout: 2,
    cover_image_url_pattern: '',
    cover_amazon_enabled: true,
    cover_amazon_timeout: 2,
    cover_openlibrary_enabled: true,
    cover_openlibrary_timeout: 2,
    cover_google_books_enabled: true,
    cover_google_books_timeout: 2,
    cover_geobib_enabled: true,
    cover_geobib_timeout: 2,
    cover_download_delay_seconds: 60
};

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('ExternalCatalogSourcesPage', () => {
    it('loads and saves catalog and cover source settings', async () => {
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
        wrapper.vm.settings.cover_geobib_enabled = false;
        wrapper.vm.settings.cover_geobib_timeout = 14;
        wrapper.vm.settings.cover_image_url_pattern = 'https://covers.example/{isbn}.jpg';
        wrapper.vm.settings.cover_download_delay_seconds = 18;
        await wrapper.vm.saveSettings();

        expect(put).toHaveBeenCalledWith('/admin/settings', {
            updates: {
                bnf_enabled: true,
                bnf_timeout: 2,
                google_books_enabled: false,
                google_books_timeout: 9,
                sudoc_enabled: true,
                sudoc_timeout: 3,
                cover_custom_url_enabled: true,
                cover_custom_url_timeout: 2,
                cover_image_url_pattern: 'https://covers.example/{isbn}.jpg',
                cover_amazon_enabled: true,
                cover_amazon_timeout: 2,
                cover_openlibrary_enabled: true,
                cover_openlibrary_timeout: 2,
                cover_google_books_enabled: true,
                cover_google_books_timeout: 2,
                cover_geobib_enabled: false,
                cover_geobib_timeout: 14,
                cover_download_delay_seconds: 18
            }
        });
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'settings.save_success' })
        ]);
    });
});
