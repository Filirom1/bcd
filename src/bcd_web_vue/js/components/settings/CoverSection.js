/**
 * Cover Section Component
 * Maintenance tool for associating and downloading book covers.
 */

const { defineComponent, ref, computed, onMounted, onUnmounted } = Vue;
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

        // Background download state
        const downloading = ref(false);
        const downloadStatus = ref({
            running: false,
            processed: 0,
            total: 0,
            found: 0,
            last_processed_isbn: null
        });
        const pollingInterval = ref(null);

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

        const checkDownloadStatus = async () => {
            try {
                const status = await apiClient.get('/admin/covers/download-missing/status');
                const wasRunning = downloadStatus.value.running;
                downloadStatus.value = status;
                downloading.value = status.running;

                if (status.running) {
                    if (!pollingInterval.value) {
                        startPolling();
                    }
                } else {
                    stopPolling();
                    if (wasRunning) {
                        // If it just stopped, notify the user of the final result
                        if (status.total > 0 && status.processed < status.total) {
                            success(t('settings.covers_download_cancelled'));
                        } else if (status.total > 0) {
                            success(t('settings.covers_download_done', { found: status.found, total: status.total }));
                        }
                    }
                }
            } catch (error) {
                console.error("Error checking cover download status", error);
                stopPolling();
            }
        };

        const startPolling = () => {
            if (pollingInterval.value) return;
            pollingInterval.value = setInterval(checkDownloadStatus, 1500);
        };

        const stopPolling = () => {
            if (pollingInterval.value) {
                clearInterval(pollingInterval.value);
                pollingInterval.value = null;
            }
        };

        const startDownload = async () => {
            try {
                downloading.value = true;
                const data = await apiClient.post('/admin/covers/download-missing');
                if (data.status === 'started' || data.status === 'already_running') {
                    startPolling();
                }
            } catch (error) {
                handleError(error);
                downloading.value = false;
            }
        };

        const cancelDownload = async () => {
            try {
                await apiClient.post('/admin/covers/download-missing/cancel');
                await checkDownloadStatus();
            } catch (error) {
                handleError(error);
            }
        };

        const eta = computed(() => {
            const remaining = downloadStatus.value.total - downloadStatus.value.processed;
            if (remaining <= 0) return '';
            
            const totalSeconds = remaining * 60;
            const hours = Math.floor(totalSeconds / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            
            if (hours > 0) {
                return `${hours}h ${minutes}m`;
            }
            return `${minutes} min`;
        });

        onMounted(() => {
            checkDownloadStatus();
        });

        onUnmounted(() => {
            stopPolling();
        });

        return {
            t,
            backfilling,
            result,
            backfillCovers,
            downloading,
            downloadStatus,
            startDownload,
            cancelDownload,
            eta
        };
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
                <!-- Associer les couvertures existantes (Local) -->
                <div class="mb-4">
                    <p class="text-muted small mb-2">{{ t('settings.covers_backfill_help') }}</p>
                    <div v-if="result" class="alert alert-success small py-2 mb-2">
                        <i class="bi bi-check-circle me-1"></i>
                        {{ t('settings.covers_backfill_result', { updated: result.updated, scanned: result.scanned }) }}
                    </div>
                    <button
                        class="btn btn-secondary btn-sm"
                        :disabled="backfilling || downloading"
                        @click="backfillCovers"
                    >
                        <span v-if="backfilling" class="spinner-border spinner-border-sm me-1"></span>
                        <i v-else class="bi bi-file-earmark-image me-1"></i>
                        {{ t('settings.covers_backfill_button') }}
                    </button>
                </div>

                <hr />

                <!-- Télécharger les couvertures manquantes (Internet) -->
                <div>
                    <p class="text-muted small mb-2">{{ t('settings.covers_download_help') }}</p>
                    
                    <div v-if="downloading" class="alert alert-info small py-2 mb-2">
                        <span class="spinner-border spinner-border-sm me-2 text-primary align-middle" role="status"></span>
                        <span class="align-middle">
                            {{ t('settings.covers_download_running', { processed: downloadStatus.processed, total: downloadStatus.total, found: downloadStatus.found }) }}
                        </span>
                        <span v-if="downloadStatus.last_processed_isbn" class="text-muted d-block mt-1" style="font-size: 0.8rem;">
                            ISBN: {{ downloadStatus.last_processed_isbn }}
                        </span>
                        <span v-if="eta" class="text-muted d-block mt-1" style="font-size: 0.8rem;">
                            <i class="bi bi-clock me-1"></i>{{ t('settings.covers_download_eta', { eta: eta }) }}
                        </span>
                    </div>

                    <div class="d-flex gap-2">
                        <button
                            class="btn btn-primary btn-sm"
                            :disabled="backfilling || downloading"
                            @click="startDownload"
                        >
                            <i class="bi bi-cloud-arrow-down me-1"></i>
                            {{ t('settings.covers_download_button') }}
                        </button>
                        <button
                            v-if="downloading"
                            class="btn btn-danger btn-sm"
                            @click="cancelDownload"
                        >
                            <i class="bi bi-x-circle me-1"></i>
                            {{ t('settings.covers_download_cancel') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `
});
