/**
 * Settings page.
 * Like reports, each section has its own URL so the page stays focused and fast.
 */

const { defineComponent, ref, computed, onMounted } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;
import { apiClient } from '../api/client.js';
import { useAppState } from '../composables/useAppState.js';
import { useNotification } from '../composables/useNotification.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { logger } from '../utils/logger.js';
import LoadingSpinner from '../components/ui/LoadingSpinner.js';
import HelpPanel from '../components/ui/HelpPanel.js';
import SettingsForm from '../components/settings/SettingsForm.js';
import BackupSection from '../components/settings/BackupSection.js';
import CoverSection from '../components/settings/CoverSection.js';
import EnvSection from '../components/settings/EnvSection.js';
import DataMaintenanceSection from '../components/settings/DataMaintenanceSection.js';

const VALID_SECTIONS = ['general', 'catalog', 'backup', 'covers', 'maintenance', 'env', 'external-sources'];

export default defineComponent({
    name: 'SettingsPage',

    components: {
        LoadingSpinner, HelpPanel, SettingsForm,
        BackupSection, CoverSection, EnvSection, DataMaintenanceSection
    },

    setup() {
        const { t } = useI18n();
        const route = useRoute();
        const { saveSettings: saveGlobalSettings } = useAppState();
        const { success } = useNotification();
        const { handleError } = useErrorHandler(t);
        const loading = ref(true);
        const saving = ref(false);
        const shelfSuggestionTraining = ref(false);
        const shelfSuggestionStatus = ref({
            enabled: true,
            trained_at: null,
            trained_on_records: null,
            ready: false
        });
        const appVersion = ref('');
        const settings = ref({
            library_name: '', library_code: '', loan_duration_days: 14,
            loan_limit_default: 3, loan_limit_warning: 1, loan_limit_teacher: 10,
            renewal_limit: 2, hold_expiration_days: 3, max_holds_per_borrower: 1,
            academic_year_start_month: 9, academic_year_current: '2024-2025',
            language: 'fr', date_format: 'DD/MM/YYYY', catalog_call_number_rules: null
        });
        const originalSettings = ref({});
        const activeSection = computed(() => VALID_SECTIONS.includes(route.params.section)
            ? route.params.section : 'general');
        const isSettingsForm = computed(() => ['general', 'catalog'].includes(activeSection.value));

        const loadSettings = async () => {
            try {
                loading.value = true;
                const [data, health] = await Promise.all([
                    apiClient.get('/admin/settings'), apiClient.get('/health')
                ]);
                settings.value = { ...settings.value, ...data };
                originalSettings.value = { ...settings.value };
                appVersion.value = health.version || '';
                try {
                    shelfSuggestionStatus.value = await apiClient.get('/admin/shelf-suggestion/status');
                } catch (statusError) {
                    // An older server can still serve the settings page without
                    // the optional model management endpoint.
                    console.warn('Unable to load shelf suggestion status:', statusError);
                }
            } catch (error) {
                handleError(error);
            } finally {
                loading.value = false;
            }
        };

        const saveSettings = async () => {
            try {
                saving.value = true;
                const { id, created_at, updated_at, ...updates } = settings.value;
                logger.debug('Saving settings');
                await apiClient.put('/admin/settings', { updates });
                originalSettings.value = { ...settings.value };
                saveGlobalSettings(settings.value);
                success(t('settings.save_success'));
            } catch (error) {
                handleError(error);
            } finally {
                saving.value = false;
            }
        };

        const trainShelfSuggestion = async () => {
            try {
                shelfSuggestionTraining.value = true;
                const result = await apiClient.post('/admin/shelf-suggestion/train', {});
                shelfSuggestionStatus.value = result;
                // Training metadata is read from the model manifest, not saved
                // back into the SQLite settings record.
                if (result.status === 'completed') {
                    success(t('settings.shelf_suggestion_train_done'));
                } else {
                    success(t('settings.shelf_suggestion_train_insufficient'));
                }
            } catch (error) {
                handleError(error);
            } finally {
                shelfSuggestionTraining.value = false;
            }
        };

        const resetSettings = () => {
            settings.value = { ...originalSettings.value };
        };

        onMounted(loadSettings);

        return {
            t, loading, saving, settings, appVersion, activeSection, isSettingsForm,
            shelfSuggestionTraining, shelfSuggestionStatus,
            saveSettings, resetSettings, trainShelfSuggestion
        };
    },

    template: `
        <div class="page-container">
            <div class="page-header">
                <h1 class="page-title"><i class="bi bi-gear me-2"></i>{{ t('navigation.settings') }}</h1>
                <div class="d-flex gap-2 align-items-center">
                    <help-panel section="settings" />
                </div>
            </div>

            <loading-spinner v-if="loading" />
            <template v-else>
                <settings-form
                    v-if="isSettingsForm"
                    :section="activeSection"
                    :settings="settings"
                    :loading="saving"
                    :shelf-suggestion-status="shelfSuggestionStatus"
                    :shelf-suggestion-training="shelfSuggestionTraining"
                    @save="saveSettings"
                    @reset="resetSettings"
                    @train-shelf-suggestion="trainShelfSuggestion"
                />
                <backup-section v-else-if="activeSection === 'backup'" />
                <cover-section v-else-if="activeSection === 'covers'" />
                <data-maintenance-section v-else-if="activeSection === 'maintenance'" />
                <env-section v-else-if="activeSection === 'env'" />
                <div v-if="appVersion" class="mt-3 text-muted small text-end">
                    {{ t('settings.app_version') }} v{{ appVersion }} &mdash;
                    <a href="https://github.com/Filirom1/bcd" target="_blank" rel="noopener">{{ t('settings.open_source') }}</a>
                </div>
            </template>
        </div>
    `
});
