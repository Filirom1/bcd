import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import BackupSection from '../../../../src/bcd_web_vue/js/components/settings/BackupSection.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const backups = [
    {
        filename: 'bcd-new.db',
        file_path: '/tmp/bcd-new.db',
        size_mb: 1.2,
        created_at: '2030-01-15T12:00:00Z',
        age_days: 0
    },
    {
        filename: 'bcd-old.db',
        file_path: '/tmp/bcd-old.db',
        size_mb: 2.4,
        created_at: '2029-12-01T12:00:00Z',
        age_days: 31
    }
];

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('BackupSection', () => {
    it('loads backups and exposes age/status presentation helpers', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ backups });
        const wrapper = mount(BackupSection);
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/backups');
        expect(wrapper.vm.backups).toEqual(backups);
        expect(wrapper.vm.newestBackup.filename).toBe('bcd-new.db');
        expect(wrapper.vm.statusAlertClass).toBe('alert-success');
        expect(wrapper.vm.statusIcon).toBe('bi-check-circle-fill');
        expect(wrapper.vm.statusText).toBe('settings.backup_today');
        expect(wrapper.vm.ageBadgeClass(0)).toBe('badge-age-ok');
        expect(wrapper.vm.ageBadgeClass(7)).toBe('badge-age-warn');
        expect(wrapper.vm.ageBadgeClass(30)).toBe('badge-age-old');
        expect(wrapper.find('table').exists()).toBe(true);

        wrapper.vm.backups = [{ ...backups[0], age_days: 10 }];
        expect(wrapper.vm.statusAlertClass).toBe('alert-warning');
        expect(wrapper.vm.statusText).toBe('settings.backup_last');
        wrapper.vm.backups = [{ ...backups[0], age_days: 31 }];
        expect(wrapper.vm.statusAlertClass).toBe('alert-danger');
        wrapper.vm.backups = [];
        expect(wrapper.vm.statusAlertClass).toBe('alert-danger');
        expect(wrapper.vm.statusIcon).toBe('bi-x-circle-fill');
        expect(wrapper.vm.statusText).toBe('settings.backup_none');
    });

    it('creates, exports, imports, restores and cleans up backups', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue({ backups });
        const post = vi.spyOn(apiClient, 'post').mockImplementation(async endpoint => {
            if (endpoint === '/admin/backup') return { backup: backups[0] };
            return {};
        });
        const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue({ deleted_count: 2 });
        const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
        const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
        const inputClick = vi.spyOn(HTMLInputElement.prototype, 'click').mockImplementation(() => {});
        const wrapper = mount(BackupSection);
        await flushPromises();

        await wrapper.vm.createBackup();
        expect(post).toHaveBeenCalledWith('/admin/backup', {});
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ message: 'settings.backup_created' })
        );

        wrapper.vm.downloadBackup(backups[0]);
        expect(anchorClick).toHaveBeenCalled();
        const link = anchorClick.mock.instances.at(-1);
        expect(link.href).toContain('/api/v1/admin/backups/bcd-new.db/download');
        expect(link.download).toBe('bcd-new.db');

        wrapper.vm.triggerImport();
        expect(inputClick).toHaveBeenCalledTimes(1);
        const file = new File(['sqlite'], 'import.db', { type: 'application/octet-stream' });
        const fileInput = wrapper.vm.fileInput;
        Object.defineProperty(fileInput, 'files', { configurable: true, value: [file] });
        await wrapper.vm.importBackup({ target: fileInput });
        expect(post).toHaveBeenCalledWith('/admin/backups/import', expect.any(FormData));

        await wrapper.vm.restoreBackup(backups[0]);
        expect(confirm).toHaveBeenCalled();
        expect(post).toHaveBeenCalledWith('/admin/restore', {}, {
            backup_file: '/tmp/bcd-new.db',
            confirm: true
        });

        await wrapper.vm.cleanupOldBackups();
        expect(remove).toHaveBeenCalledWith('/admin/backups/cleanup', { keep_days: 30 });
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ message: 'settings.backup_cleanup_done' })
        );

        await wrapper.vm.exportCurrentDb();
        expect(post).toHaveBeenCalledWith('/admin/backup', {});
        expect(anchorClick.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    it('does not restore or clean up when the confirmation is declined', async () => {
        vi.spyOn(apiClient, 'get').mockResolvedValue({ backups });
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue({});
        const remove = vi.spyOn(apiClient, 'delete').mockResolvedValue({ deleted_count: 0 });
        vi.spyOn(window, 'confirm').mockReturnValue(false);
        const wrapper = mount(BackupSection);
        await flushPromises();

        await wrapper.vm.restoreBackup(backups[0]);
        await wrapper.vm.cleanupOldBackups();

        expect(post).not.toHaveBeenCalled();
        expect(remove).not.toHaveBeenCalled();
    });
});
