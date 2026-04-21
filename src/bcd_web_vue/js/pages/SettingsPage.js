/**
 * Settings Page Component
 * System configuration and library settings
 * Matches HTMX version exactly with 14 fields
 */

const { defineComponent, ref, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../api/client.js';
import { useAppState } from '../composables/useAppState.js';
import { useNotification } from '../composables/useNotification.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import LoadingSpinner from '../components/ui/LoadingSpinner.js';
import SettingsForm from '../components/settings/SettingsForm.js';
import BackupSection from '../components/settings/BackupSection.js';
import CoverSection from '../components/settings/CoverSection.js';
import DataMaintenanceSection from '../components/settings/DataMaintenanceSection.js';
import HelpPanel from '../components/ui/HelpPanel.js';

export default defineComponent({
    name: 'SettingsPage',

    components: {
        LoadingSpinner,
        SettingsForm,
        BackupSection,
        CoverSection,
        DataMaintenanceSection,
        HelpPanel
    },

    setup() {
        const { t } = useI18n();
        const { saveSettings: saveGlobalSettings } = useAppState();
        const { success } = useNotification();
        const { handleError } = useErrorHandler(t);

        const loading = ref(true);
        const saving = ref(false);
        const appVersion = ref('');

        // Match HTMX version field structure exactly
        const settings = ref({
            library_name: '',
            library_code: '',
            loan_duration_days: 14,
            loan_limit_default: 3,
            loan_limit_teacher: 10,
            renewal_limit: 2,
            hold_expiration_days: 3,
            max_holds_per_borrower: 1,
            academic_year_start_month: 9,
            academic_year_current: '2024-2025',
            language: 'fr',
            date_format: 'DD/MM/YYYY'
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
                // Remove read-only fields (id, created_at, updated_at) before sending
                const { id, created_at, updated_at, ...updateData } = settings.value;

                // API expects data wrapped in "updates" field
                const payload = { updates: updateData };

                console.log('Saving settings (full):', JSON.stringify(payload, null, 2));
                await apiClient.put('/admin/settings', payload);
                originalSettings.value = { ...settings.value };
                saveGlobalSettings(settings.value);
                success(t('settings.save_success'));
            } catch (error) {
                console.error('Settings save error:', error);
                handleError(error);
            } finally {
                saving.value = false;
            }
        };

        const resetSettings = () => {
            settings.value = { ...originalSettings.value };
        };

        onMounted(() => {
            loadSettings();
        });

        return {
            loading,
            saving,
            settings,
            appVersion,
            saveSettings,
            resetSettings,
            t
        };
    },

    template: `
        <div class="page-container">
            <div class="page-header">
                <h1 class="page-title">
                    <i class="bi bi-gear me-2"></i>
                    {{ t('navigation.settings') }}
                </h1>
                <div class="d-flex gap-2">
                    <help-panel section="settings" />
                </div>
            </div>

            <loading-spinner v-if="loading" />

            <template v-else>
                <settings-form
                    :settings="settings"
                    :loading="saving"
                    @save="saveSettings"
                    @reset="resetSettings"
                />
                <backup-section class="mt-2" />
                <cover-section class="mt-2" />
                <data-maintenance-section class="mt-2" />
                <div v-if="appVersion" class="mt-3 text-muted small text-end">
                    {{ t('settings.app_version') }} v{{ appVersion }} &mdash; <a href="https://github.com/Filirom1/bcd" target="_blank" rel="noopener">{{ t('settings.open_source') }}</a>
                </div>
            </template>
        </div>
    `
});
