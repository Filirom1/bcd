import { afterEach } from 'vitest';
import * as Vue from 'vue';

// The production SPA loads Vue, Vue Router, and Vue I18n as vendored browser
// globals. Recreate the public contracts used by modules in the test runtime.
globalThis.Vue = Vue;
globalThis.VueRouter = {
    useRoute: () => ({ query: {} }),
    useRouter: () => ({ replace: () => {} })
};
globalThis.__testTranslate = key => key;
const testLocale = Vue.ref('fr');
globalThis.VueI18n = {
    useI18n: () => ({
        locale: testLocale,
        t: key => globalThis.__testTranslate(key),
        d: value => String(value)
    })
};

afterEach(() => {
    globalThis.__testTranslate = key => key;
    document.body.innerHTML = '';
});
