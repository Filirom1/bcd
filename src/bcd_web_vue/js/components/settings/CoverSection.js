/**
 * Cover Section Component
 * Maintenance tool for associating existing cover files with catalog records.
 */

const { defineComponent, ref } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'CoverSection',

    setup() {
        const { t } = useI18n();
        const { success } = useNotification();
        const { handleError } = useErrorHandler(t);

        const backfilling = ref(false);
        const result = ref(null);

        const backfillCovers = async () => {
            backfilling.value = true;
            result.value = null;
            try {
                const data = await apiClient.post('/admin/covers/backfill');
                result.value = data;
                success(t('settings.covers_backfill_done', { count: data.updated }));
            } catch (error) {
                handleError(error);
            } finally {
                backfilling.value = false;
            }
        };

        return { t, backfilling, result, backfillCovers };
    },

    template: `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="bi bi-image me-2"></i>
                    {{ t('settings.covers_title') }}
                </h5>
            </div>
            <div class="card-body">
                <p class="text-muted small mb-3">{{ t('settings.covers_backfill_help') }}</p>

                <div v-if="result" class="alert alert-success small py-2 mb-3">
                    <i class="bi bi-check-circle me-1"></i>
                    {{ t('settings.covers_backfill_result', { updated: result.updated, scanned: result.scanned }) }}
                </div>

                <button
                    class="btn btn-secondary"
                    :disabled="backfilling"
                    @click="backfillCovers"
                >
                    <span v-if="backfilling" class="spinner-border spinner-border-sm me-1"></span>
                    <i v-else class="bi bi-image-fill me-1"></i>
                    {{ t('settings.covers_backfill_button') }}
                </button>
            </div>
        </div>
    `
});
