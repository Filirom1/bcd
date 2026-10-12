import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import LogsSection from '../../../../src/bcd_web_vue/js/components/settings/LogsSection.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

afterEach(() => {
    vi.restoreAllMocks();
    useNotification().clear();
});

describe('LogsSection', () => {
    it('loads logs and refreshes them from the button', async () => {
        const get = vi.spyOn(apiClient, 'get')
            .mockResolvedValueOnce({ content: 'first\n', updated_at: '2026-10-12T10:00:00Z' })
            .mockResolvedValueOnce({ content: 'second\n', updated_at: '2026-10-12T10:01:00Z' });
        const wrapper = mount(LogsSection);
        await flushPromises();

        expect(get).toHaveBeenCalledWith('/admin/logs');
        expect(wrapper.vm.content).toBe('first\n');
        await wrapper.find('button').trigger('click');
        await flushPromises();

        expect(get).toHaveBeenCalledTimes(2);
        expect(wrapper.vm.content).toBe('second\n');
    });
});
