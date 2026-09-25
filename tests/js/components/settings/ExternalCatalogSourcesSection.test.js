import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import ExternalCatalogSourcesSection from '../../../../src/bcd_web_vue/js/components/settings/ExternalCatalogSourcesSection.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('ExternalCatalogSourcesSection', () => {
    it('uses an error notification when a source is unavailable', async () => {
        vi.spyOn(apiClient, 'post').mockResolvedValue({
            source: 'google_books', status: 'error', ok: false
        });
        const wrapper = mount(ExternalCatalogSourcesSection, {
            props: {
                settings: {
                    bnf_enabled: true, bnf_timeout: 4,
                    google_books_enabled: true, google_books_timeout: 4,
                    sudoc_enabled: true, sudoc_timeout: 5
                }
            }
        });

        const googleBooks = wrapper.vm.sources.find(source => source.key === 'google_books');
        await wrapper.vm.testSource(googleBooks);

        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error' })
        ]);
    });

    it('uses a warning notification when a source is disabled', async () => {
        vi.spyOn(apiClient, 'post').mockResolvedValue({
            source: 'google_books', status: 'disabled', ok: false
        });
        const wrapper = mount(ExternalCatalogSourcesSection, {
            props: { settings: { google_books_enabled: false } }
        });

        const googleBooks = wrapper.vm.sources.find(source => source.key === 'google_books');
        await wrapper.vm.testSource(googleBooks);

        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'warning' })
        ]);
    });
});
