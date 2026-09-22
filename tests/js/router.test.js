import { beforeAll, describe, expect, it } from 'vitest';
import { nextTick, ref } from 'vue';

import * as VueRouterPackage from 'vue-router';
import { useAppState } from '../../src/bcd_web_vue/js/composables/useAppState.js';

let createAppRouter;

beforeAll(async () => {
    // The application consumes Vue Router as a browser global. Install the real
    // router only for this module so the route table and title hooks are tested
    // without changing the lightweight global used by component tests.
    Object.assign(globalThis.VueRouter, VueRouterPackage);
    ({ createAppRouter } = await import('../../src/bcd_web_vue/js/router.js'));
});

function makeI18n() {
    const locale = ref('fr');
    return {
        global: {
            locale,
            t: key => `${locale.value}:${key}`
        }
    };
}

describe('application router', () => {
    it('registers the main routes and redirects the root to checkout', async () => {
        const router = createAppRouter(makeI18n());
        const paths = router.getRoutes().map(route => route.path);

        expect(paths).toEqual(expect.arrayContaining([
            '/',
            '/checkout',
            '/return',
            '/catalog',
            '/cataloging',
            '/borrowers',
            '/classes',
            '/reports/:type?',
            '/inventory',
            '/settings/:section?'
        ]));

        await router.push('/');
        expect(router.currentRoute.value.path).toBe('/checkout');
    });

    it('updates the document title with the library identity and locale', async () => {
        useAppState().saveSettings({ library_code: 'ECOLE-01', library_name: 'BCD' });
        const i18n = makeI18n();
        const router = createAppRouter(i18n);

        await router.push('/catalog');
        expect(document.title).toBe('ECOLE-01 - fr:navigation.catalog');

        i18n.global.locale.value = 'en';
        await nextTick();
        expect(document.title).toBe('ECOLE-01 - en:navigation.catalog');
    });
});
