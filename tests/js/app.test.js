import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../src/bcd_web_vue/js/api/client.js';
import { useAppState } from '../../src/bcd_web_vue/js/composables/useAppState.js';

vi.mock('../../src/bcd_web_vue/js/router.js', () => ({
    createAppRouter: vi.fn(() => ({
        install() {},
        push: vi.fn(() => Promise.resolve())
    }))
}));

vi.mock('../../src/bcd_web_vue/js/components/App.js', () => ({
    default: {
        name: 'TestApp',
        setup() {
            return () => null;
        }
    }
}));

let initApp;

beforeAll(async () => {
    // app.js normally starts itself at import time. Disable that one automatic
    // start so each test can exercise initApp() with an isolated bootstrap.
    window.__BCD_DISABLE_AUTO_INIT__ = true;
    globalThis.VueI18n.createI18n = options => ({
        global: {
            locale: globalThis.Vue.ref(options.locale),
            t(key) {
                return key.split('.').reduce((value, part) => value?.[part], options.messages[this.locale.value]) ?? key;
            }
        },
        install() {}
    });
    ({ initApp } = await import('../../src/bcd_web_vue/js/app.js'));
});

beforeEach(() => {
    useAppState().clearStorage();
    document.body.innerHTML = '<div id="app"></div><div class="bcd-loading"></div>';
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    document.body.innerHTML = '';
});

afterAll(() => {
    delete window.__BCD_DISABLE_AUTO_INIT__;
});

function localeFetch({ fr = {}, en = {}, frResponse, enResponse } = {}) {
    return vi.fn(async url => {
        if (url.endsWith('/locales/fr.json')) {
            return frResponse || new Response(JSON.stringify(fr), { status: 200 });
        }
        return enResponse || new Response(JSON.stringify(en), { status: 200 });
    });
}

describe('initApp', () => {
    it('loads settings and both locales, creates the router/i18n, and exposes readiness', async () => {
        const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ language: 'en', library_code: 'BCD' });
        const fetch = localeFetch({ fr: { greeting: 'Bonjour' }, en: { greeting: 'Hello' } });
        vi.stubGlobal('fetch', fetch);

        await initApp();

        expect(get).toHaveBeenCalledWith('/admin/settings', {}, { skipGlobalLoading: true });
        expect(fetch).toHaveBeenCalledTimes(2);
        expect(window.__BCD_APP__).toMatchObject({ ready: true, error: null });
        expect(window.__BCD_APP__.router).toBeTruthy();
        expect(window.__BCD_APP__.i18n.global.locale.value).toBe('en');
        expect(window.__BCD_APP__.i18n.global.t('greeting')).toBe('Hello');
        expect(document.querySelector('.bcd-loading').style.opacity).toBe('0');
    });

    it('continues when the initial settings request fails', async () => {
        const error = vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('settings offline'));
        vi.stubGlobal('fetch', localeFetch({ fr: {}, en: {} }));

        await initApp();

        expect(window.__BCD_APP__.ready).toBe(true);
        expect(window.__BCD_APP__.error).toBe(null);
        expect(error).toHaveBeenCalledWith('Failed to load settings:', expect.any(Error));
    });

    it.each([
        ['HTTP errors', new Response('missing', { status: 503 }), 'Failed to load fr.json: 503'],
        ['invalid JSON', new Response('{invalid', { status: 200 }), 'Invalid JSON in fr.json: {invalid']
    ])('exposes a startup error for %s', async (_label, frResponse, expectedMessage) => {
        vi.spyOn(apiClient, 'get').mockResolvedValue(null);
        vi.stubGlobal('fetch', localeFetch({
            en: {},
            frResponse
        }));
        const error = vi.spyOn(console, 'error').mockImplementation(() => {});

        await initApp();

        expect(window.__BCD_APP__.ready).toBe(false);
        expect(window.__BCD_APP__.error.message).toBe(expectedMessage);
        expect(document.querySelector('#app .alert-danger').textContent).toContain(expectedMessage);
        expect(error).toHaveBeenCalledWith('❌ Failed to initialize app:', expect.any(Error));
    });
});
