import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import CoverSection from '../../../../src/bcd_web_vue/js/components/settings/CoverSection.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('CoverSection', () => {
    it('loads status, backfills local covers and calculates the ETA', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            running: false,
            processed: 0,
            total: 0,
            found: 0,
            last_processed_isbn: null
        });
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ updated: 7, scanned: 12 });
        const wrapper = mount(CoverSection);
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/covers/download-missing/status');
        expect(wrapper.vm.downloading).toBe(false);
        await wrapper.vm.backfillCovers();
        expect(post).toHaveBeenCalledWith('/admin/covers/backfill');
        expect(wrapper.vm.result).toEqual({ updated: 7, scanned: 12 });
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ message: 'settings.covers_backfill_done' })
        );

        wrapper.vm.downloadStatus = { running: true, processed: 60, total: 130, found: 40, last_processed_isbn: '978' };
        expect(wrapper.vm.eta).toBe('1h 10m');
        wrapper.vm.downloadStatus = { running: true, processed: 130, total: 130, found: 100, last_processed_isbn: null };
        expect(wrapper.vm.eta).toBe('');
    });

    it('starts polling for a background download and cancels it', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
            running: false,
            processed: 0,
            total: 0,
            found: 0,
            last_processed_isbn: null
        });
        const post = vi.spyOn(apiClient, 'post').mockImplementation(async endpoint => {
            if (endpoint === '/admin/covers/download-missing') return { status: 'started' };
            return {};
        });
        const wrapper = mount(CoverSection);
        await flushPromises();

        await wrapper.vm.startDownload();
        expect(post).toHaveBeenCalledWith('/admin/covers/download-missing');
        expect(wrapper.vm.downloading).toBe(true);

        await wrapper.vm.cancelDownload();
        expect(post).toHaveBeenCalledWith('/admin/covers/download-missing/cancel');
        expect(get.mock.calls.length).toBeGreaterThanOrEqual(2);
        expect(wrapper.vm.downloading).toBe(false);
    });

    it('stops cleanly when the status transitions from running to complete', async () => {
        const statuses = [
            { running: true, processed: 2, total: 4, found: 1, last_processed_isbn: '111' },
            { running: false, processed: 4, total: 4, found: 3, last_processed_isbn: '222' }
        ];
        vi.spyOn(apiClient, 'get').mockImplementation(async () => statuses.shift());
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({});
        const wrapper = mount(CoverSection);
        await flushPromises();

        expect(wrapper.vm.downloading).toBe(true);
        await wrapper.vm.cancelDownload();
        expect(post).toHaveBeenCalledWith('/admin/covers/download-missing/cancel');
        expect(wrapper.vm.downloading).toBe(false);
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ message: 'settings.covers_download_done' })
        );
    });
});
