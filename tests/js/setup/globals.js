import { afterEach } from 'vitest';
import * as Vue from 'vue';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// The source SPA expects Vue, Vue Router, and Vue I18n browser globals.
// Recreate the public contracts used by modules in the test runtime.
globalThis.Vue = Vue;
const themeStyles = document.createElement('style');
themeStyles.textContent = readFileSync(
    resolve(process.cwd(), 'src/bcd_web_vue/css/theme.css'),
    'utf8'
);
document.head.append(themeStyles);

const testRoute = {
    query: {},
    params: {},
    meta: {}
};
const testRouter = {
    push: () => Promise.resolve(),
    replace: () => Promise.resolve()
};
globalThis.VueRouter = {
    useRoute: () => testRoute,
    useRouter: () => testRouter
};
globalThis.__testRoute = testRoute;
globalThis.__testRouter = testRouter;
globalThis.__testTranslate = key => key;
const testLocale = Vue.ref('fr');
globalThis.VueI18n = {
    useI18n: () => ({
        locale: testLocale,
        t: (key, params) => globalThis.__testTranslate(key, params),
        d: value => String(value)
    })
};

afterEach(() => {
    globalThis.__testTranslate = key => key;
    globalThis.__testRoute.query = {};
    globalThis.__testRoute.params = {};
    globalThis.__testRoute.meta = {};
    globalThis.__testRouter.push = () => Promise.resolve();
    globalThis.__testRouter.replace = () => Promise.resolve();
    document.body.innerHTML = '';
});
