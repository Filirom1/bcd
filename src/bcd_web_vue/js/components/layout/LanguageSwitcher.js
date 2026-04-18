/**
 * Language Switcher Component
 * FR/EN toggle buttons
 */

const { defineComponent } = Vue;
const { useI18n } = VueI18n;
import { useAppState } from '../../composables/useAppState.js';

export default defineComponent({
    name: 'LanguageSwitcher',

    setup() {
        const { locale } = useI18n();
        const { setLocale } = useAppState();

        const switchLanguage = (lang) => {
            locale.value = lang;
            setLocale(lang);
        };

        return {
            locale,
            switchLanguage
        };
    },

    template: `
        <div class="language-switcher btn-group btn-group-sm" role="group">
            <button
                type="button"
                class="btn"
                :class="locale === 'fr' ? 'btn-primary' : 'btn-outline-secondary'"
                @click="switchLanguage('fr')"
            >
                FR
            </button>
            <button
                type="button"
                class="btn"
                :class="locale === 'en' ? 'btn-primary' : 'btn-outline-secondary'"
                @click="switchLanguage('en')"
            >
                EN
            </button>
        </div>
    `
});
