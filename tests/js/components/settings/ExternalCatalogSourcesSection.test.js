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
    it('exposes configurable cover providers beside catalog sources', () => {
        const wrapper = mount(ExternalCatalogSourcesSection, {
            props: {
                settings: {
                    cover_custom_url_enabled: true, cover_custom_url_timeout: 2,
                    cover_amazon_enabled: true, cover_amazon_timeout: 2,
                    cover_openlibrary_enabled: true, cover_openlibrary_timeout: 2,
                    cover_google_books_enabled: true, cover_google_books_timeout: 2,
                    cover_geobib_enabled: true, cover_geobib_timeout: 2
                }
            }
        });

        expect(wrapper.vm.coverSources.map(source => source.key)).toEqual([
            'custom_url', 'amazon', 'openlibrary', 'google_books', 'geobib'
        ]);
        expect(wrapper.find('[data-testid="external-cover-sources"]').exists()).toBe(true);
    });

    it('tests a cover source through the cover-source endpoint', async () => {
        vi.spyOn(apiClient, 'post').mockResolvedValue({
            source: 'amazon', status: 'reachable', ok: true, found: true
        });
        const wrapper = mount(ExternalCatalogSourcesSection, {
            props: {
                settings: {
                    cover_custom_url_enabled: true,
                    cover_image_url_pattern: '',
                    cover_amazon_enabled: true,
                    cover_amazon_timeout: 2
                }
            }
        });

        await wrapper.vm.testCoverSource(
            wrapper.vm.coverSources.find(source => source.key === 'amazon')
        );

        expect(apiClient.post).toHaveBeenCalledWith(
            '/admin/settings/cover-sources/amazon/test',
            {
                cover_amazon_enabled: true,
                cover_amazon_timeout: 2,
                cover_image_url_pattern: ''
            }
        );
    });

    it('uses an error notification when a source is unavailable', async () => {
        vi.spyOn(apiClient, 'post').mockResolvedValue({
            source: 'google_books', status: 'error', ok: false
        });
        const wrapper = mount(ExternalCatalogSourcesSection, {
            props: {
                settings: {
                    bnf_enabled: true, bnf_timeout: 2,
                    google_books_enabled: true, google_books_timeout: 2,
                    sudoc_enabled: true, sudoc_timeout: 3
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
