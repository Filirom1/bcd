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

const SOURCE_FIELDS = [
    'bnf_enabled', 'bnf_timeout',
    'google_books_enabled', 'google_books_timeout',
    'sudoc_enabled', 'sudoc_timeout'
];

export default defineComponent({
    name: 'ExternalCatalogSourcesPage',

    components: {
        LoadingSpinner,
        HelpPanel,
        ExternalCatalogSourcesSection
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
            bnf_timeout: 4,
            google_books_enabled: true,
            google_books_timeout: 4,
            sudoc_enabled: true,
            sudoc_timeout: 5
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
            <div class="page-header">
                <div>
                    <h1 class="page-title">
                        <i class="bi bi-cloud-download me-2"></i>
                        {{ t('settings.external_catalog_sources') }}
                    </h1>
                    <p class="text-muted mb-0">
                        {{ t('settings.external_catalog_sources_page_help') }}
                    </p>
                </div>
                <div class="d-flex gap-2 align-items-center">
                    <help-panel section="settings" />
                </div>
            </div>

            <loading-spinner v-if="loading" />
            <form v-else @submit.prevent="saveSettings">
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

            <div v-if="appVersion" class="mt-3 text-muted small text-end">
                {{ t('settings.app_version') }} v{{ appVersion }} &mdash;
                <a href="https://github.com/Filirom1/bcd" target="_blank" rel="noopener">{{ t('settings.open_source') }}</a>
            </div>
        </div>
    `
});
