import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import LanguageSwitcher from '../../../../src/bcd_web_vue/js/components/layout/LanguageSwitcher.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';

describe('LanguageSwitcher', () => {
    it('switches application locale and highlights active button', async () => {
        const { setLocale, locale } = useAppState();
        setLocale('fr');

        const wrapper = mount(LanguageSwitcher, {
            global: {
                mocks: {
                    $i18n: { locale: 'fr' }
                }
            }
        });

        // FR button should be active/primary, EN outline
        const buttons = wrapper.findAll('button');
        expect(buttons[0].classes()).toContain('btn-primary');
        expect(buttons[1].classes()).toContain('btn-outline-secondary');

        // Click EN button
        await buttons[1].trigger('click');

        expect(locale.value).toBe('en');
    });
});
