/** Dedicated settings page for external catalog sources. */

const { defineComponent, ref, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../api/client.js';
import { useAppState } from '../composables/useAppState.js';
import { useNotification } from '../composables/useNotification.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import LoadingSpinner from '../components/ui/LoadingSpinner.js';
import HelpPanel from '../components/ui/HelpPanel.js';
import ExternalCatalogSourcesSection from '../components/settings/ExternalCatalogSourcesSection.js';
import CoverSection from '../components/settings/CoverSection.js';

const SOURCE_FIELDS = [
    'bnf_enabled', 'bnf_timeout',
    'google_books_enabled', 'google_books_timeout',
    'sudoc_enabled', 'sudoc_timeout',
    'cover_custom_url_enabled', 'cover_custom_url_timeout',
    'cover_image_url_pattern',
    'cover_amazon_enabled', 'cover_amazon_timeout',
    'cover_openlibrary_enabled', 'cover_openlibrary_timeout',
    'cover_google_books_enabled', 'cover_google_books_timeout',
    'cover_geobib_enabled', 'cover_geobib_timeout',
    'cover_download_delay_seconds'
];

import PageHeader from '../components/ui/PageHeader.js';

export default defineComponent({
    name: 'ExternalCatalogSourcesPage',

    components: {
        PageHeader,
        LoadingSpinner,
        HelpPanel,
        ExternalCatalogSourcesSection,
        CoverSection
    },

    setup() {
        const { t } = useI18n();
        const { saveSettings: saveGlobalSettings } = useAppState();
        const { success } = useNotification();
        const { handleError } = useErrorHandler(t);
        const loading = ref(true);
        const saving = ref(false);
        const appVersion = ref('');
        const settings = ref({
            bnf_enabled: true,
            bnf_timeout: 2,
            google_books_enabled: true,
            google_books_timeout: 2,
            sudoc_enabled: true,
            sudoc_timeout: 3,
            cover_custom_url_enabled: true,
            cover_custom_url_timeout: 2,
            cover_image_url_pattern: '',
            cover_amazon_enabled: true,
            cover_amazon_timeout: 2,
            cover_openlibrary_enabled: true,
            cover_openlibrary_timeout: 2,
            cover_google_books_enabled: true,
            cover_google_books_timeout: 2,
            cover_geobib_enabled: true,
            cover_geobib_timeout: 2,
            cover_download_delay_seconds: 60
        });
        const originalSettings = ref({});

        const loadSettings = async () => {
            try {
                loading.value = true;
                const [data, health] = await Promise.all([
                    apiClient.get('/admin/settings'),
                    apiClient.get('/health')
                ]);
                settings.value = { ...settings.value, ...data };
                originalSettings.value = { ...settings.value };
                appVersion.value = health.version || '';
            } catch (error) {
                handleError(error);
            } finally {
                loading.value = false;
            }
        };

        const saveSettings = async () => {
            try {
                saving.value = true;
                const updates = Object.fromEntries(
                    SOURCE_FIELDS.map(field => [field, settings.value[field]])
                );
                await apiClient.put('/admin/settings', { updates });
                originalSettings.value = { ...settings.value };
                saveGlobalSettings({ ...settings.value });
                success(t('settings.save_success'));
            } catch (error) {
                handleError(error);
            } finally {
                saving.value = false;
            }
        };

        const resetSettings = () => {
            settings.value = { ...originalSettings.value };
        };

        onMounted(loadSettings);

        return {
            t,
            loading,
            saving,
            settings,
            appVersion,
            saveSettings,
            resetSettings
        };
    },

    template: `
        <div class="page-container">
            <page-header>
                <template #heading>
                    <h1 class="page-title">
                        <i class="bi bi-cloud-download me-2"></i>
                        {{ t('settings.external_sources_settings') }}
                    </h1>
                </template>
                <template #actions>
                    <help-panel section="settings" />
                </template>
            </page-header>

            <loading-spinner v-if="loading" />
            <template v-else>
                <form @submit.prevent="saveSettings">
                    <div class="card">
                        <div class="card-body">
                            <external-catalog-sources-section :settings="settings" />
                        </div>
                    </div>
                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary" :disabled="saving">
                            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                            <i v-else class="bi bi-save me-1"></i>
                            {{ t('common.save') }}
                        </button>
                        <button type="button" class="btn btn-secondary ms-2" :disabled="saving" @click="resetSettings">
                            <i class="bi bi-x-circle me-1"></i>{{ t('common.cancel') }}
                        </button>
                    </div>
                </form>
                <cover-section class="mt-4" />
            </template>

            <div v-if="appVersion" class="mt-3 text-muted small text-end">
                {{ t('settings.app_version') }} v{{ appVersion }} &mdash;
                <a href="https://github.com/Filirom1/bcd" target="_blank" rel="noopener">{{ t('settings.open_source') }}</a>
            </div>
        </div>
    `
});
