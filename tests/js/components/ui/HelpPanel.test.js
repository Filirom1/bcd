import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import HelpPanel from '../../../../src/bcd_web_vue/js/components/ui/HelpPanel.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';

beforeEach(() => {
    vi.stubGlobal('marked', {
        parse: (val) => `<p>${val}</p>`
    });
    const { setLocale } = useAppState();
    setLocale('fr');
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('HelpPanel', () => {
    it('fetches correct markdown content for checkout section', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response('### Étape 1', { status: 200 }));
        vi.stubGlobal('fetch', fetchMock);

        const wrapper = mount(HelpPanel, {
            props: { section: 'checkout' },
            global: { mocks: { $t: key => key } }
        });
        await flushPromises();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith('/help/fr/emprunter.md');
        expect(wrapper.vm.error).toBe(false);
        await vi.waitFor(() => {
            expect(wrapper.vm.renderedMarkdown).toBe('<h3>Étape 1</h3>\n');
        });
    });

    it('updates help file content on language switch', async () => {
        const fetchMock = vi.fn()
            .mockResolvedValueOnce(new Response('### Étape 1', { status: 200 }))
            .mockResolvedValueOnce(new Response('### Step 1', { status: 200 }));
        vi.stubGlobal('fetch', fetchMock);

        const wrapper = mount(HelpPanel, {
            props: { section: 'checkout' },
            global: { mocks: { $t: key => key } }
        });
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith('/help/fr/emprunter.md');

        const { setLocale } = useAppState();
        setLocale('en');
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith('/help/en/checkout.md');
    });

    it('displays error state when content is missing', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response('Not Found', { status: 404 }));
        vi.stubGlobal('fetch', fetchMock);

        const wrapper = mount(HelpPanel, {
            props: { section: 'checkout' },
            global: { mocks: { $t: key => key } }
        });
        await flushPromises();

        expect(wrapper.vm.error).toBe(true);
        expect(wrapper.vm.renderedMarkdown).toBe('');
    });
});
