/**
 * HelpPanel Component
 * Bootstrap offcanvas help panel that loads page-specific markdown content
 * and renders it with marked.js. Supports FR/EN locale switching.
 */

const { defineComponent, ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import { useAppState } from '../../composables/useAppState.js';
import LoadingSpinner from './LoadingSpinner.js';

const SECTION_FILES = {
    checkout:     { fr: 'emprunter.md',   en: 'checkout.md' },
    return:       { fr: 'retourner.md',   en: 'return.md' },
    catalog:      { fr: 'catalogue.md',   en: 'catalog.md' },
    cataloging:   { fr: 'catalogage.md',  en: 'cataloging.md' },
    borrowers:    { fr: 'eleves.md',      en: 'borrowers.md' },
    classes:      { fr: 'classes.md',     en: 'classes.md' },
    reports:      { fr: 'rapports.md',    en: 'reports.md' },
    settings:     { fr: 'parametres.md',  en: 'settings.md' },
    inventory:    { fr: 'inventaire.md',  en: 'inventory.md' },
    collections:  { fr: 'fonds.md',       en: 'collections.md' },
};

export default defineComponent({
    name: 'HelpPanel',

    components: { LoadingSpinner },

    props: {
        section: {
            type: String,
            required: true,
            validator: (value) => Object.keys(SECTION_FILES).includes(value)
        }
    },

    setup(props) {
        const { t } = useI18n();
        const { locale } = useAppState();

        const rawMd = ref(null);
        const loading = ref(false);
        const error = ref(false);

        const fetchHelp = async () => {
            loading.value = true;
            error.value = false;
            rawMd.value = null;

            const files = SECTION_FILES[props.section];
            if (!files) {
                error.value = true;
                loading.value = false;
                return;
            }

            const filename = files[locale.value] || files.en;

            // Direct fetch is used here because these are local static Markdown resource files, not API endpoints
            try {
                const res = await fetch(`/help/${locale.value}/${filename}`);
                if (!res.ok) throw new Error(res.status);
                rawMd.value = await res.text();
            } catch {
                // Fallback to EN if locale file missing
                try {
                    const res2 = await fetch(`/help/en/${files.en}`);
                    if (res2.ok) {
                        rawMd.value = await res2.text();
                    } else {
                        rawMd.value = null;
                        error.value = true;
                    }
                } catch {
                    rawMd.value = null;
                    error.value = true;
                }
            } finally {
                loading.value = false;
            }
        };

        const renderedMarkdown = ref('');

        watch(rawMd, async (value) => {
            if (!value) {
                renderedMarkdown.value = '';
                return;
            }
            // Load Markdown only after help content has actually been fetched.
            const { marked } = await import('marked');
            const mdWithAbsolutePaths = value.replace(/\.\.\/(images\/[^)]+)/g, '/help/$1');
            renderedMarkdown.value = marked.parse(mdWithAbsolutePaths);
        }, { immediate: true });

        watch([() => props.section, locale], fetchHelp, { immediate: true });

        return {
            t,
            loading,
            error,
            renderedMarkdown
        };
    },

    template: `
        <div>
            <!-- Trigger button — placed inline in the page header -->
            <button
                class="btn btn-outline-secondary btn-sm"
                type="button"
                data-bs-toggle="offcanvas"
                data-bs-target="#bcd-help-offcanvas"
                aria-controls="bcd-help-offcanvas"
                :title="t('help.button')"
            >
                <i class="bi bi-question-circle me-1"></i>{{ t('help.button') }}
            </button>

            <!-- Offcanvas panel — rendered once, shown/hidden by Bootstrap -->
            <div
                class="offcanvas offcanvas-end"
                id="bcd-help-offcanvas"
                tabindex="-1"
                :aria-label="t('help.button')"
                style="width: min(480px, 100vw)"
            >
                <div class="offcanvas-header border-bottom">
                    <h5 class="offcanvas-title">
                        <i class="bi bi-question-circle me-2 text-primary"></i>
                        {{ t('help.sections.' + section) }}
                    </h5>
                    <button
                        type="button"
                        class="btn-close"
                        data-bs-dismiss="offcanvas"
                        :aria-label="t('common.close')"
                    ></button>
                </div>
                <div class="offcanvas-body">
                    <loading-spinner v-if="loading" :text="t('help.loading')" />
                    <div v-else-if="error" class="alert alert-warning" role="alert">
                        {{ t('help.error') }}
                    </div>
                    <div
                        v-else
                        v-html="renderedMarkdown"
                        class="help-markdown"
                    ></div>
                </div>
            </div>
        </div>
    `
});
