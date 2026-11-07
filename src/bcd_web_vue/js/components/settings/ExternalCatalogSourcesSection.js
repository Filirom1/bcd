/** Settings for the fixed external catalog source route. */

const { defineComponent, computed, ref } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';
import DataTable from '../ui/DataTable.js';

export default defineComponent({
    name: 'ExternalCatalogSourcesSection',
    components: { DataTable },

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
        const coverSources = [
            { key: 'custom_url', labelKey: 'settings.cover_source_custom_url', enabledKey: 'cover_custom_url_enabled', timeoutKey: 'cover_custom_url_timeout' },
            { key: 'amazon', labelKey: 'settings.cover_source_amazon', enabledKey: 'cover_amazon_enabled', timeoutKey: 'cover_amazon_timeout' },
            { key: 'openlibrary', labelKey: 'settings.cover_source_openlibrary', enabledKey: 'cover_openlibrary_enabled', timeoutKey: 'cover_openlibrary_timeout' },
            { key: 'google_books', labelKey: 'settings.cover_source_google_books', enabledKey: 'cover_google_books_enabled', timeoutKey: 'cover_google_books_timeout' },
            { key: 'geobib', labelKey: 'settings.cover_source_geobib', enabledKey: 'cover_geobib_enabled', timeoutKey: 'cover_geobib_timeout' }
        ];

        const showTestResult = (source, result, statusKey) => {
            testStatus.value[statusKey] = result;
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
        };

        const testSource = async (source) => {
            testing.value = source.key;
            try {
                const result = await apiClient.post(`/admin/settings/external-sources/${source.key}/test`, {
                    query: source.sample
                });
                showTestResult(source, result, source.key);
            } catch (error) {
                handleError(error);
            } finally {
                testing.value = null;
            }
        };

        const testCoverSource = async (source) => {
            const statusKey = `cover:${source.key}`;
            if (
                source.key === 'custom_url'
                && props.settings.cover_custom_url_enabled
                && !String(props.settings.cover_image_url_pattern || '').trim()
            ) {
                warning(t('settings.cover_source_pattern_required'));
                return;
            }
            testing.value = statusKey;
            try {
                const result = await apiClient.post(
                    `/admin/settings/cover-sources/${source.key}/test`,
                    {
                        [source.enabledKey]: props.settings[source.enabledKey],
                        [source.timeoutKey]: props.settings[source.timeoutKey],
                        cover_image_url_pattern: props.settings.cover_image_url_pattern
                    }
                );
                showTestResult(source, result, statusKey);
            } catch (error) {
                handleError(error);
            } finally {
                testing.value = null;
            }
        };

        return { t, sources, coverSources, testing, testStatus, testSource, testCoverSource };
    },

    template: `
        <div class="col-12 mt-4" data-testid="external-catalog-sources">
            <h4 class="border-bottom pb-2 mb-3"><i class="bi bi-cloud-download me-1"></i>{{ t('settings.external_catalog_sources') }}</h4>
            <p class="text-muted small">{{ t('settings.external_catalog_sources_help') }}</p>
            <div class="table-responsive">
                <data-table
                    :columns="[
                        { key: 'source', label: t('settings.external_source') },
                        { key: 'enabled', label: t('settings.external_source_enabled') },
                        { key: 'timeout', label: t('settings.external_source_timeout'), width: '12rem' },
                        { key: 'test', label: t('settings.external_source_test'), width: '8rem' },
                    ]"
                    :rows="sources"
                    row-key="key"
                    table-class="table-sm align-middle"
                    bare
                >
                    <template #row="{ row: source }">
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
                    </template>
                </data-table>
            </div>
        </div>

        <div class="col-12 mt-5" data-testid="external-cover-sources">
            <h4 class="border-bottom pb-2 mb-3"><i class="bi bi-image me-1"></i>{{ t('settings.cover_sources') }}</h4>
            <p class="text-muted small">{{ t('settings.cover_sources_help') }}</p>
            <div class="table-responsive">
                <data-table
                    :columns="[
                        { key: 'source', label: t('settings.external_source') },
                        { key: 'enabled', label: t('settings.external_source_enabled') },
                        { key: 'timeout', label: t('settings.external_source_timeout'), width: '12rem' },
                        { key: 'test', label: t('settings.external_source_test'), width: '8rem' }
                    ]"
                    :rows="coverSources"
                    row-key="key"
                    table-class="table-sm align-middle"
                    bare
                >
                    <template #row="{ row: source }">
                        <td class="fw-semibold">{{ t(source.labelKey) }}</td>
                        <td>
                            <div class="form-check form-switch mb-0">
                                <input :id="'cover-' + source.key + '-enabled'" v-model="settings[source.enabledKey]" type="checkbox" class="form-check-input" />
                                <label class="form-check-label" :for="'cover-' + source.key + '-enabled'">{{ settings[source.enabledKey] ? t('common.yes') : t('common.no') }}</label>
                            </div>
                        </td>
                        <td>
                            <div class="input-group input-group-sm">
                                <input :id="'cover-' + source.key + '-timeout'" v-model.number="settings[source.timeoutKey]" type="number" min="1" max="60" class="form-control" />
                                <span class="input-group-text">{{ t('settings.seconds') }}</span>
                            </div>
                        </td>
                        <td>
                            <button type="button" class="btn btn-sm btn-outline-primary" :disabled="testing === 'cover:' + source.key" @click="testCoverSource(source)">
                                <span v-if="testing === 'cover:' + source.key" class="spinner-border spinner-border-sm"></span>
                                <span v-else>{{ t('settings.test') }}</span>
                            </button>
                            <div v-if="testStatus['cover:' + source.key]" class="small text-muted mt-1">{{ t('settings.external_source_status_' + testStatus['cover:' + source.key].status) }}</div>
                        </td>
                    </template>
                </data-table>
            </div>
            <div class="mt-3">
                <label for="cover_image_url_pattern" class="form-label">{{ t('settings.cover_custom_url_pattern') }}</label>
                <input
                    id="cover_image_url_pattern"
                    v-model="settings.cover_image_url_pattern"
                    type="text"
                    maxlength="2000"
                    class="form-control"
                    placeholder="https://example.org/covers/{isbn[-1]}/{isbn}.jpg"
                />
                <small class="form-text text-muted">{{ t('settings.cover_custom_url_pattern_help') }}</small>
            </div>
            <div class="mt-3">
                <label for="cover_download_delay_seconds" class="form-label">{{ t('settings.cover_download_delay') }}</label>
                <div class="input-group">
                    <input
                        id="cover_download_delay_seconds"
                        v-model.number="settings.cover_download_delay_seconds"
                        type="number"
                        min="0"
                        max="300"
                        step="1"
                        class="form-control"
                    />
                    <span class="input-group-text">{{ t('settings.seconds') }}</span>
                </div>
                <small class="form-text text-muted">{{ t('settings.cover_download_delay_help') }}</small>
            </div>
        </div>
    `
});
