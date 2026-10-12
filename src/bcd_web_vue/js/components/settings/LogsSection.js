/**
 * Logs section component for the Settings page.
 * Displays the most recent application log entries and can refresh them on demand.
 */

const { defineComponent, ref, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'LogsSection',

    setup() {
        const { t } = useI18n();
        const { handleError } = useErrorHandler(t);
        const content = ref('');
        const updatedAt = ref(null);
        const truncated = ref(false);
        const loading = ref(false);

        const loadLogs = async () => {
            try {
                loading.value = true;
                const data = await apiClient.get('/admin/logs');
                content.value = data.content || '';
                updatedAt.value = data.updated_at || null;
                truncated.value = Boolean(data.truncated);
            } catch (error) {
                handleError(error, { fallbackMessage: t('settings.logs_unavailable') });
            } finally {
                loading.value = false;
            }
        };

        onMounted(loadLogs);

        return { t, content, updatedAt, truncated, loading, loadLogs };
    },

    template: `
        <div>
            <div class="d-flex justify-content-between align-items-center border-bottom pb-2 mb-3 mt-4">
                <h4 class="mb-0"><i class="bi bi-journal-text me-2"></i>{{ t('settings.logs_title') }}</h4>
                <button class="btn btn-outline-primary" @click="loadLogs" :disabled="loading">
                    <i class="bi bi-arrow-clockwise me-2" :class="{ 'spinner-border spinner-border-sm': loading }"></i>
                    {{ t('settings.logs_refresh') }}
                </button>
            </div>

            <div v-if="truncated" class="alert alert-info py-2">
                <i class="bi bi-info-circle me-1"></i>{{ t('settings.logs_truncated') }}
            </div>
            <div v-if="content" class="bg-dark text-light rounded p-3 overflow-auto" style="max-height: 65vh;">
                <pre class="mb-0 font-monospace small">{{ content }}</pre>
            </div>
            <p v-else-if="!loading" class="text-muted fst-italic">{{ t('settings.logs_empty') }}</p>
            <div v-if="updatedAt" class="text-muted small mt-2">
                {{ t('settings.logs_updated') }}: {{ updatedAt }}
            </div>
        </div>
    `
});
