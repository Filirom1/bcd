/**
 * Backup Section Component
 * Backup management UI for the Settings page.
 * Provides: list, create, restore, and cleanup of database backups.
 */

const { defineComponent, ref, computed, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'BackupSection',

    setup() {
        const { t } = useI18n();
        const { success } = useNotification();
        const { handleError } = useErrorHandler(t);

        const backups = ref([]);
        const loadingList = ref(false);
        const creating = ref(false);
        const restoring = ref(null);   // filename being restored, or null
        const cleaning = ref(false);

        const newestBackup = computed(() => backups.value[0] || null);

        const ageBadgeClass = (ageDays) => {
            if (ageDays < 7)  return 'badge-age-ok';
            if (ageDays < 30) return 'badge-age-warn';
            return 'badge-age-old';
        };

        const statusAlertClass = computed(() => {
            if (!newestBackup.value) return 'alert-danger';
            if (newestBackup.value.age_days < 7)  return 'alert-success';
            if (newestBackup.value.age_days < 30) return 'alert-warning';
            return 'alert-danger';
        });

        const statusIcon = computed(() => {
            if (!newestBackup.value) return 'bi-x-circle-fill';
            if (newestBackup.value.age_days < 7)  return 'bi-check-circle-fill';
            if (newestBackup.value.age_days < 30) return 'bi-exclamation-triangle-fill';
            return 'bi-exclamation-triangle-fill';
        });

        const statusText = computed(() => {
            if (!newestBackup.value) return t('settings.backup_none');
            if (newestBackup.value.age_days === 0) return t('settings.backup_today');
            return t('settings.backup_last', { days: newestBackup.value.age_days });
        });

        const formatDate = (isoString) => {
            const d = new Date(isoString);
            return d.toLocaleString();
        };

        const loadBackups = async () => {
            try {
                loadingList.value = true;
                const data = await apiClient.get('/admin/backups');
                backups.value = data.backups || [];
            } catch (error) {
                handleError(error);
            } finally {
                loadingList.value = false;
            }
        };

        const createBackup = async () => {
            try {
                creating.value = true;
                const data = await apiClient.post('/admin/backup', {});
                success(t('settings.backup_created', { filename: data.backup.filename }));
                await loadBackups();
            } catch (error) {
                handleError(error);
            } finally {
                creating.value = false;
            }
        };

        const restoreBackup = async (backup) => {
            if (!window.confirm(t('settings.backup_restore_confirm'))) return;
            try {
                restoring.value = backup.filename;
                await apiClient.post('/admin/restore', {}, {
                    backup_file: backup.file_path,
                    confirm: true
                });
                success(t('settings.backup_restored', { filename: backup.filename }));
                await loadBackups();
            } catch (error) {
                handleError(error);
            } finally {
                restoring.value = null;
            }
        };

        const cleanupOldBackups = async () => {
            if (!window.confirm(t('settings.backup_cleanup_confirm'))) return;
            try {
                cleaning.value = true;
                const data = await apiClient.delete('/admin/backups/cleanup', { keep_days: 30 });
                success(t('settings.backup_cleanup_done', { count: data.deleted_count }));
                await loadBackups();
            } catch (error) {
                handleError(error);
            } finally {
                cleaning.value = false;
            }
        };

        onMounted(() => {
            loadBackups();
        });

        return {
            t,
            backups,
            loadingList,
            creating,
            restoring,
            cleaning,
            newestBackup,
            ageBadgeClass,
            statusAlertClass,
            statusIcon,
            statusText,
            formatDate,
            createBackup,
            restoreBackup,
            cleanupOldBackups
        };
    },

    template: `
        <div>
            <!-- Section header -->
            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3">
                    <i class="bi bi-archive"></i>
                    {{ t('settings.backup_section') }}
                </h4>
            </div>

            <!-- Status bar -->
            <div class="col-12 mb-3">
                <div v-if="loadingList" class="alert alert-secondary d-flex align-items-center gap-2">
                    <div class="spinner-border spinner-border-sm" role="status"></div>
                    <span>...</span>
                </div>
                <div v-else :class="['alert', statusAlertClass, 'd-flex align-items-center gap-2']">
                    <i :class="['bi', statusIcon]"></i>
                    <span>{{ statusText }}</span>
                    <span v-if="newestBackup" class="text-muted ms-2 small">— {{ newestBackup.filename }}</span>
                </div>
                <small class="text-muted">
                    <i class="bi bi-info-circle"></i>
                    {{ t('settings.backup_auto_note') }}
                </small>
            </div>

            <!-- Action buttons -->
            <div class="col-12 mb-3 d-flex gap-2 flex-wrap">
                <button class="btn btn-primary" @click="createBackup" :disabled="creating || loadingList">
                    <span v-if="creating" class="spinner-border spinner-border-sm me-1" role="status"></span>
                    <i v-else class="bi bi-cloud-arrow-up me-1"></i>
                    {{ creating ? t('settings.backup_creating') : t('settings.backup_create') }}
                </button>
                <button class="btn btn-outline-danger" @click="cleanupOldBackups" :disabled="cleaning || loadingList">
                    <span v-if="cleaning" class="spinner-border spinner-border-sm me-1" role="status"></span>
                    <i v-else class="bi bi-trash me-1"></i>
                    {{ t('settings.backup_delete_old') }}
                </button>
            </div>

            <!-- Backup table -->
            <div class="col-12" v-if="!loadingList && backups.length > 0">
                <div class="table-responsive">
                    <table class="table table-sm table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th><i class="bi bi-file-earmark"></i> {{ t('settings.backup_filename') }}</th>
                                <th>{{ t('settings.backup_size') }}</th>
                                <th>{{ t('settings.backup_date') }}</th>
                                <th>{{ t('settings.backup_age') }}</th>
                                <th>{{ t('settings.backup_actions') }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="backup in backups" :key="backup.filename">
                                <td><code class="small">{{ backup.filename }}</code></td>
                                <td class="text-nowrap">{{ backup.size_mb }} MB</td>
                                <td class="text-nowrap">{{ formatDate(backup.created_at) }}</td>
                                <td>
                                    <span :class="['badge', ageBadgeClass(backup.age_days)]">
                                        {{ backup.age_days === 0 ? t('settings.backup_today') : t('settings.backup_days_ago', { days: backup.age_days }) }}
                                    </span>
                                </td>
                                <td>
                                    <button
                                        class="btn btn-sm btn-outline-warning"
                                        @click="restoreBackup(backup)"
                                        :disabled="restoring !== null || creating"
                                    >
                                        <span v-if="restoring === backup.filename" class="spinner-border spinner-border-sm me-1" role="status"></span>
                                        <i v-else class="bi bi-arrow-counterclockwise me-1"></i>
                                        {{ restoring === backup.filename ? t('settings.backup_restoring') : t('settings.backup_restore') }}
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="col-12" v-if="!loadingList && backups.length === 0">
                <p class="text-muted fst-italic">{{ t('settings.backup_none') }}</p>
            </div>
        </div>
    `
});
