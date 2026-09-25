import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import EnvSection from '../../../../src/bcd_web_vue/js/components/settings/EnvSection.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('EnvSection', () => {
    it('loads the environment file only as content and saves edits', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ content: 'API_PORT=8888\n' });
        const put = vi.spyOn(apiClient, 'put').mockResolvedValue({});
        const wrapper = mount(EnvSection);
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/env');
        expect(wrapper.vm.content).toBe('API_PORT=8888\n');
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.find('textarea').exists()).toBe(true);
        wrapper.vm.content = 'API_PORT=9000\n';
        await wrapper.vm.saveEnv();

        expect(put).toHaveBeenCalledWith('/admin/env', { content: 'API_PORT=9000\n' });
        expect(wrapper.vm.saving).toBe(false);
        expect(useNotification().notifications.value).toContainEqual(
            expect.objectContaining({ message: 'settings.env_save_success' })
        );
    });

    it('keeps the editor usable when loading or saving fails', async () => {
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('offline'));
        const put = vi.spyOn(apiClient, 'put').mockRejectedValue(new Error('read-only'));
        const wrapper = mount(EnvSection);
        await flushPromises();

        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.content).toBe('');
        await wrapper.vm.saveEnv();
        expect(put).toHaveBeenCalledWith('/admin/env', { content: '' });
        expect(wrapper.vm.saving).toBe(false);
        expect(useNotification().notifications.value.filter(n => n.type === 'error')).toHaveLength(2);
    });
});
