/** Settings for the fixed external catalog source route. */

const { defineComponent, computed, ref } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'ExternalCatalogSourcesSection',

    props: {
        settings: { type: Object, required: true }
    },

    setup(props) {
        const { t } = useI18n();
        const { success, error: showError, warning } = useNotification();
        const { handleError } = useErrorHandler(t);
        const testing = ref(null);
        const testStatus = ref({});

        const sources = computed(() => [
            { key: 'bnf', labelKey: 'cataloging.source_bnf', enabledKey: 'bnf_enabled', timeoutKey: 'bnf_timeout', sample: '9782070612758' },
            { key: 'google_books', labelKey: 'cataloging.source_google_books', enabledKey: 'google_books_enabled', timeoutKey: 'google_books_timeout', sample: '9782070612758' },
            { key: 'sudoc', labelKey: 'cataloging.source_sudoc', enabledKey: 'sudoc_enabled', timeoutKey: 'sudoc_timeout', sample: '1163-7706' }
        ]);

        const testSource = async (source) => {
            testing.value = source.key;
            try {
                const result = await apiClient.post(`/admin/settings/external-sources/${source.key}/test`, {
                    query: source.sample
                });
                testStatus.value[source.key] = result;
                const message = t('settings.external_source_test_result', {
                    source: t(source.labelKey),
                    status: t(`settings.external_source_status_${result.status}`)
                });
                if (result.status === 'error') {
                    showError(message);
                } else if (result.status === 'disabled') {
                    warning(message);
                } else {
                    success(message);
                }
            } catch (error) {
                handleError(error);
            } finally {
                testing.value = null;
            }
        };

        return { t, sources, testing, testStatus, testSource };
    },

    template: `
        <div class="col-12 mt-4" data-testid="external-catalog-sources">
            <h4 class="border-bottom pb-2 mb-3"><i class="bi bi-cloud-download me-1"></i>{{ t('settings.external_catalog_sources') }}</h4>
            <p class="text-muted small">{{ t('settings.external_catalog_sources_help') }}</p>
            <div class="table-responsive">
                <table class="table table-sm align-middle mb-0">
                    <thead>
                        <tr>
                            <th>{{ t('settings.external_source') }}</th>
                            <th>{{ t('settings.external_source_enabled') }}</th>
                            <th style="width:12rem">{{ t('settings.external_source_timeout') }}</th>
                            <th style="width:8rem">{{ t('settings.external_source_test') }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="source in sources" :key="source.key">
                            <td class="fw-semibold">{{ t(source.labelKey) }}</td>
                            <td>
                                <div class="form-check form-switch mb-0">
                                    <input :id="source.key + '-enabled'" v-model="settings[source.enabledKey]" type="checkbox" class="form-check-input" />
                                    <label class="form-check-label" :for="source.key + '-enabled'">{{ settings[source.enabledKey] ? t('common.yes') : t('common.no') }}</label>
                                </div>
                            </td>
                            <td>
                                <div class="input-group input-group-sm">
                                    <input :id="source.key + '-timeout'" v-model.number="settings[source.timeoutKey]" type="number" min="1" max="60" class="form-control" />
                                    <span class="input-group-text">{{ t('settings.seconds') }}</span>
                                </div>
                            </td>
                            <td>
                                <button type="button" class="btn btn-sm btn-outline-primary" :disabled="testing === source.key" @click="testSource(source)">
                                    <span v-if="testing === source.key" class="spinner-border spinner-border-sm"></span>
                                    <span v-else>{{ t('settings.test') }}</span>
                                </button>
                                <div v-if="testStatus[source.key]" class="small text-muted mt-1">{{ t('settings.external_source_status_' + testStatus[source.key].status) }}</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    `
});
