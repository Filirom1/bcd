/**
 * Env Editor Section Component
 * Allows editing the application's .env file directly from settings.
 */

const { defineComponent, ref, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'EnvSection',

    setup() {
        const { t } = useI18n();
        const { success } = useNotification();
        const { handleError } = useErrorHandler(t);

        const content = ref('');
        const loading = ref(false);
        const saving = ref(false);
        const isOpen = ref(false);

        const toggleOpen = () => {
            isOpen.value = !isOpen.value;
        };

        const loadEnv = async () => {
            try {
                loading.value = true;
                const res = await apiClient.get('/admin/env');
                content.value = res.content || '';
            } catch (error) {
                handleError(error);
            } finally {
                loading.value = false;
            }
        };

        const saveEnv = async () => {
            try {
                saving.value = true;
                await apiClient.put('/admin/env', { content: content.value });
                success(t('settings.env_save_success'));
            } catch (error) {
                handleError(error);
            } finally {
                saving.value = false;
            }
        };

        onMounted(() => {
            loadEnv();
        });

        return {
            content,
            loading,
            saving,
            isOpen,
            toggleOpen,
            saveEnv,
            t
        };
    },

    template: `
        <div>
            <!-- Section header -->
            <div class="col-12 mt-4" style="cursor: pointer;" @click="toggleOpen">
                <h4 class="border-bottom pb-2 mb-3 d-flex justify-content-between align-items-center">
                    <span>
                        <i class="bi bi-file-earmark-code me-2"></i>
                        {{ t('settings.env_title') }}
                    </span>
                    <i :class="['bi fs-5 text-muted', isOpen ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
                </h4>
            </div>

            <div v-if="isOpen" class="col-12 mb-3">
                <div class="card shadow-sm">
                    <div class="card-header bg-light d-flex justify-content-between align-items-center">
                        <span class="text-muted small font-monospace">.env</span>
                        <button 
                            @click="saveEnv" 
                            class="btn btn-sm btn-primary" 
                            :disabled="saving || loading"
                        >
                            <i class="bi bi-save me-1"></i>
                            {{ saving ? t('settings.backup_creating') : t('settings.save') }}
                        </button>
                    </div>
                    <div class="card-body p-0">
                        <div v-if="loading" class="text-center py-4">
                            <div class="spinner-border spinner-border-sm text-secondary" role="status"></div>
                        </div>
                        <textarea 
                            v-else
                            v-model="content" 
                            class="form-control font-monospace border-0 p-3" 
                            style="min-height: 250px; font-size: 0.85rem; resize: vertical; background-color: #fafbfc;"
                            placeholder="# Configuration"
                        ></textarea>
                    </div>
                    <div class="card-footer bg-light py-2">
                        <small class="text-muted">
                            <i class="bi bi-info-circle me-1"></i>
                            {{ t('settings.env_warning') }}
                        </small>
                    </div>
                </div>
            </div>
        </div>
    `
});
