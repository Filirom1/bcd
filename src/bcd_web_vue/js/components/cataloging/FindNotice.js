/**
 * Find-a-notice component.
 *
 * The field is deliberately not an ISBN-only lookup: it performs a
 * local database search first and only then calls the one applicable external
 * source at a time.
 */

const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';

const SOURCES = ['bnf', 'google_books', 'sudoc'];

function classifyInput(value) {
    const raw = (value || '').trim();
    if (!raw) return { kind: 'text', identifierType: null, normalized: null, sources: [] };

    const explicit = raw.toLowerCase();
    let candidate = raw;
    if (explicit.startsWith('isbn:') || explicit.startsWith('issn:')) candidate = raw.slice(5);
    if (explicit.startsWith('issn:')) {
        const digits = candidate.replace(/[-\s]/g, '');
        if (/^\d{7}[\dXx]$/.test(digits)) {
            const issn = `${digits.slice(0, 4)}-${digits.slice(4).toUpperCase()}`;
            return { kind: 'issn', identifierType: 'issn', normalized: `issn:${issn}`, sources: ['sudoc'] };
        }
    }

    const compact = candidate.replace(/[\s-]/g, '');
    if (/^\d{13}$/.test(compact) && compact.startsWith('977')) {
        return { kind: 'ean977', identifierType: 'issn', normalized: null, sources: ['sudoc'] };
    }
    if (/^\d{7}[\dXx]$/.test(compact)) {
        const issn = `${compact.slice(0, 4)}-${compact.slice(4).toUpperCase()}`;
        return { kind: 'issn', identifierType: 'issn', normalized: `issn:${issn}`, sources: ['sudoc'] };
    }
    if (/^(?:\d{9}[\dXx]|(?:978|979)\d{10})$/.test(compact)) {
        return { kind: 'isbn', identifierType: 'isbn', normalized: `isbn:${compact.toUpperCase()}`, sources: ['bnf', 'google_books'] };
    }
    if (/^[\d-]{8,20}$/.test(raw.replace(/\s/g, ''))) {
        return { kind: 'unsupported_barcode', identifierType: null, normalized: null, sources: [] };
    }
    return { kind: 'text', identifierType: null, normalized: null, sources: [] };
}

export default defineComponent({
    name: 'FindNotice',

    emits: [
        'lookup-success',
        'lookup-not-found',
        'manual-entry',
        'local-results',
        'notice-selected',
        'unsupported-barcode'
    ],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { error: showError } = useNotification();

        const query = ref('');
        const titleQuery = ref('');
        const queryInput = ref(null);
        const titleInput = ref(null);
        const loading = ref(false);
        const searchingLocal = ref(false);
        const localResults = ref([]);
        const localTotal = ref(0);
        const classification = ref(classifyInput(''));
        const originalInput = ref('');
        const sourceStates = ref([]);
        const externalSearchVisible = ref(false);
        const currentSourceIndex = ref(-1);
        const activeRequest = ref(null);
        let searchGeneration = 0;

        const normalizeISBN = (value) => {
            const trimmed = (value || '').trim();
            const stripped = trimmed.replace(/[\s-]/g, '');
            if (/^\d{13}$/.test(stripped) && stripped.startsWith('977')) return stripped;
            if (/^\d{7}[\dXx]$/.test(stripped)) {
                return `${stripped.slice(0, 4)}-${stripped.slice(4).toUpperCase()}`;
            }
            return stripped;
        };

        const isbn = computed({
            get: () => query.value,
            set: (value) => { query.value = value; }
        });

        const sourceLabel = (source) => t(`cataloging.source_${source}`);
        const sourceState = (source) => sourceStates.value.find(item => item.source === source);
        const hasLocalResults = computed(() => localResults.value.length > 0);
        const isUnsupportedBarcode = computed(() => classification.value.kind === 'unsupported_barcode');
        const canUseExternal = computed(() => classification.value.sources.length > 0);

        const resetResults = () => {
            localResults.value = [];
            localTotal.value = 0;
            sourceStates.value = [];
            externalSearchVisible.value = false;
            currentSourceIndex.value = -1;
        };

        const emitManualEntry = (value = query.value, kind = classification.value.kind) => {
            emit('manual-entry', {
                value: (value || '').trim(),
                originalInput: originalInput.value || query.value.trim(),
                inputType: kind,
                title: kind === 'unsupported_barcode' ? titleQuery.value.trim() : (value || '').trim()
            });
        };

        const focusQuery = () => {
            nextTick(() => queryInput.value?.focus());
        };

        const handleLocalResults = (response, generation, searchedValue) => {
            if (generation !== searchGeneration) return;
            const items = Array.isArray(response?.items) ? response.items : [];
            localResults.value = items;
            localTotal.value = typeof response?.total === 'number' ? response.total : items.length;
            classification.value = {
                ...classifyInput(searchedValue),
                kind: response?.input_type || classifyInput(searchedValue).kind,
                identifierType: response?.identifier_type || classifyInput(searchedValue).identifierType,
                normalized: response?.normalized_identifier || classifyInput(searchedValue).normalized,
                sources: Array.isArray(response?.external_sources)
                    ? response.external_sources : classifyInput(searchedValue).sources
            };
            emit('local-results', {
                items,
                total: localTotal.value,
                inputType: classification.value.kind,
                normalizedIdentifier: classification.value.normalized
            });
        };

        const initialiseSources = () => {
            sourceStates.value = classification.value.sources.map(source => ({
                source,
                status: 'waiting',
                elapsedMs: null,
                error: null
            }));
        };

        const moveToManualIfFinished = (value) => {
            externalSearchVisible.value = false;
            loading.value = false;
            emit('lookup-not-found', {
                value,
                originalInput: originalInput.value || value,
                inputType: classification.value.kind,
                title: classification.value.kind === 'text' ? value : ''
            });
        };

        const runSource = async (index, generation = searchGeneration) => {
            if (generation !== searchGeneration) return;
            const state = sourceStates.value[index];
            if (!state) {
                moveToManualIfFinished(query.value.trim());
                return;
            }

            currentSourceIndex.value = index;
            state.status = 'searching';
            state.error = null;
            externalSearchVisible.value = true;
            loading.value = true;
            const controller = new AbortController();
            activeRequest.value = controller;

            try {
                const response = await apiClient.post(
                    '/catalog/notices/lookup',
                    { query: query.value.trim(), source: state.source },
                    {},
                    { signal: controller.signal, skipGlobalLoading: true }
                );
                if (generation !== searchGeneration) return;

                state.status = response?.status || 'not_found';
                state.elapsedMs = response?.elapsed_ms ?? null;
                if (response?.status === 'found' && response.data) {
                    externalSearchVisible.value = false;
                    loading.value = false;
                    emit('lookup-success', response.data);
                    return;
                }
                if (response?.status === 'local' && response.items?.length) {
                    localResults.value = response.items;
                    localTotal.value = response.total || response.items.length;
                    externalSearchVisible.value = false;
                    loading.value = false;
                    emit('local-results', { items: localResults.value, total: localTotal.value });
                    return;
                }
                await runSource(index + 1, generation);
            } catch (error) {
                if (error?.name === 'AbortError') return;
                if (generation !== searchGeneration) return;
                state.status = 'error';
                state.error = error?.message || t('cataloging.external_lookup_error');
                await runSource(index + 1, generation);
            } finally {
                if (activeRequest.value === controller) activeRequest.value = null;
                if (generation === searchGeneration && currentSourceIndex.value === index && state.status !== 'searching') {
                    loading.value = false;
                }
            }
        };

        const searchLocal = async (value, { preserveOriginal = true } = {}) => {
            const searchedValue = (value || '').trim();
            if (!searchedValue) {
                showError(t('cataloging.error_no_search_value'));
                focusQuery();
                return;
            }

            searchGeneration += 1;
            const generation = searchGeneration;
            activeRequest.value?.abort();
            resetResults();
            if (preserveOriginal && !originalInput.value) originalInput.value = searchedValue;
            searchingLocal.value = true;
            loading.value = true;

            try {
                const response = await apiClient.get('/catalog/notices/search', {
                    q: searchedValue,
                    limit: 20,
                    offset: 0
                }, { skipGlobalLoading: true });
                handleLocalResults(response, generation, searchedValue);
                if (generation !== searchGeneration) return;

                if (localTotal.value > 0) {
                    loading.value = false;
                    return;
                }

                if (classification.value.kind === 'unsupported_barcode') {
                    titleQuery.value = '';
                    emit('unsupported-barcode', { barcode: searchedValue });
                    loading.value = false;
                    nextTick(() => titleInput.value?.focus());
                    return;
                }

                if (!canUseExternal.value) {
                    loading.value = false;
                    emit('lookup-not-found', {
                        value: searchedValue,
                        originalInput: originalInput.value || searchedValue,
                        inputType: classification.value.kind,
                        title: classification.value.kind === 'text' ? searchedValue : ''
                    });
                    return;
                }

                initialiseSources();
                externalSearchVisible.value = true;
                await runSource(0, generation);
            } catch (error) {
                if (generation !== searchGeneration) return;
                // A failed local query must not silently turn into an external
                // request: the librarian can retry or continue manually.
                loading.value = false;
                showError(error?.message || t('cataloging.local_search_error'));
            } finally {
                if (generation === searchGeneration) searchingLocal.value = false;
            }
        };

        const search = async () => {
            originalInput.value = query.value.trim();
            classification.value = classifyInput(query.value);
            await searchLocal(query.value, { preserveOriginal: false });
        };

        const searchTitle = async () => {
            query.value = titleQuery.value.trim();
            classification.value = classifyInput(query.value);
            await searchLocal(query.value, { preserveOriginal: false });
        };

        const useNotice = (notice) => {
            emit('notice-selected', notice);
        };

        const skipCurrentSource = () => {
            const index = currentSourceIndex.value;
            const state = sourceStates.value[index];
            if (!state) return;
            state.status = 'skipped';
            activeRequest.value?.abort();
            activeRequest.value = null;
            runSource(index + 1, searchGeneration);
        };

        const startSource = (index) => {
            if (index < 0 || index >= sourceStates.value.length) return;
            activeRequest.value?.abort();
            runSource(index, searchGeneration);
        };

        const switchToManualEntry = () => emitManualEntry();

        const handleKeypress = (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                search();
            }
        };

        onMounted(() => {
            nextTick(() => queryInput.value?.focus());
        });

        return {
            query,
            isbn,
            titleQuery,
            queryInput,
            titleInput,
            loading,
            searchingLocal,
            localResults,
            localTotal,
            classification,
            originalInput,
            sourceStates,
            externalSearchVisible,
            currentSourceIndex,
            hasLocalResults,
            isUnsupportedBarcode,
            canUseExternal,
            sourceLabel,
            sourceState,
            normalizeISBN,
            classifyInput,
            search,
            searchTitle,
            useNotice,
            skipCurrentSource,
            startSource,
            switchToManualEntry,
            emitManualEntry,
            handleKeypress
        };
    },

    template: `
        <div class="find-notice">
            <h5 class="mb-3">
                <i class="bi bi-search me-2"></i>
                {{ $t('cataloging.find_notice_title') }}
            </h5>
            <p class="text-muted mb-3">{{ $t('cataloging.find_notice_help') }}</p>

            <form @submit.prevent="search">
                <label for="notice-search-input" class="form-label">
                    {{ $t('cataloging.find_notice_label') }}
                </label>
                <div class="input-group input-group-lg">
                    <span class="input-group-text"><i class="bi bi-upc-scan"></i></span>
                    <input
                        id="notice-search-input"
                        ref="queryInput"
                        v-model="query"
                        type="text"
                        class="form-control"
                        :placeholder="$t('cataloging.find_notice_placeholder')"
                        :disabled="loading"
                        @keypress="handleKeypress"
                    />
                    <button type="submit" class="btn btn-primary" :disabled="loading || !query.trim()">
                        <span v-if="searchingLocal" class="spinner-border spinner-border-sm me-2"></span>
                        <i v-else class="bi bi-search me-2"></i>
                        {{ searchingLocal ? $t('common.searching') : $t('cataloging.lookup_button') }}
                    </button>
                </div>
            </form>

            <div v-if="hasLocalResults" class="mt-4" data-testid="local-notice-results">
                <h6>{{ $t('cataloging.local_results_title') }}</h6>
                <div v-for="notice in localResults" :key="notice.id || notice.notice_id" class="card mb-2">
                    <div class="card-body py-3 d-flex justify-content-between align-items-start gap-3">
                        <div class="flex-grow-1">
                            <strong>{{ notice.title }}</strong>
                            <div v-if="notice.authors && notice.authors.length" class="small text-muted">
                                {{ notice.authors.join(', ') }}
                            </div>
                            <div class="small text-muted">
                                <span v-if="notice.medium_type">{{ notice.medium_type }}</span>
                                <span v-if="notice.identifier" class="ms-2">· {{ notice.identifier_type === 'issn' ? $t('catalog.issn') : $t('catalog.isbn') }} {{ notice.identifier }}</span>
                            </div>
                            <div class="small text-muted">
                                <span v-if="notice.publisher">{{ notice.publisher }}</span>
                                <span v-if="notice.publication_year" class="ms-2">· {{ notice.publication_year }}</span>
                                <span class="ms-2">· {{ $t('cataloging.copies_count', { count: notice.copies ?? notice.total_items ?? 0 }) }}</span>
                            </div>
                            <div v-if="notice.issues_present && notice.issues_present.length" class="small text-muted mt-1">
                                {{ $t('cataloging.issues_present') }}: {{ notice.issues_present.join(', ') }}
                            </div>
                        </div>
                        <button type="button" class="btn btn-outline-primary flex-shrink-0" @click="useNotice(notice)">
                            {{ $t('cataloging.use_notice') }}
                        </button>
                    </div>
                </div>
            </div>

            <div v-if="isUnsupportedBarcode" class="alert alert-warning mt-4" data-testid="unsupported-barcode-message">
                <p class="mb-2"><strong>{{ $t('cataloging.unsupported_barcode_title') }}</strong></p>
                <p class="mb-2 small">{{ $t('cataloging.unsupported_barcode_help') }}</p>
                <form @submit.prevent="searchTitle">
                    <label for="title-search-input" class="form-label">{{ $t('cataloging.search_by_title') }}</label>
                    <div class="input-group">
                        <input id="title-search-input" ref="titleInput" v-model="titleQuery" class="form-control" :placeholder="$t('cataloging.title_search_placeholder')" />
                        <button type="submit" class="btn btn-outline-primary" :disabled="!titleQuery.trim()">
                            <i class="bi bi-search me-1"></i>{{ $t('cataloging.lookup_button') }}
                        </button>
                    </div>
                    <div class="small text-muted mt-2">{{ $t('cataloging.original_barcode', { barcode: originalInput }) }}</div>
                </form>
            </div>

            <div v-if="externalSearchVisible && sourceStates.length" class="border rounded p-3 mt-4" data-testid="external-search-status">
                <h6>{{ $t('cataloging.external_search_title') }}</h6>
                <div v-for="(state, index) in sourceStates" :key="state.source" class="d-flex align-items-center gap-2 small mb-2">
                    <span class="fw-semibold" style="min-width:7rem">{{ sourceLabel(state.source) }}</span>
                    <span v-if="state.status === 'searching'" class="text-primary"><span class="spinner-border spinner-border-sm me-1"></span>{{ $t('cataloging.external_searching') }}</span>
                    <span v-else-if="state.status === 'waiting'" class="text-muted">{{ $t('cataloging.external_waiting') }}</span>
                    <span v-else-if="state.status === 'skipped'" class="text-muted">{{ $t('cataloging.external_skipped') }}</span>
                    <span v-else-if="state.status === 'found'" class="text-success">{{ $t('cataloging.external_found') }}</span>
                    <span v-else-if="state.status === 'error'" class="text-danger">{{ $t('cataloging.external_error') }}</span>
                    <span v-else class="text-muted">{{ $t('cataloging.external_not_found') }}</span>
                    <button v-if="state.status === 'searching'" type="button" class="btn btn-sm btn-link" @click="skipCurrentSource">{{ $t('cataloging.skip_source') }}</button>
                    <button v-else-if="state.status === 'waiting'" type="button" class="btn btn-sm btn-link" @click="startSource(index)">{{ $t('cataloging.start_source') }}</button>
                </div>
            </div>

            <div class="mt-3 d-flex flex-wrap gap-3 align-items-center">
                <button type="button" class="btn btn-link text-decoration-none p-0" @click="switchToManualEntry">
                    <i class="bi bi-pencil-square me-1"></i>{{ $t('cataloging.create_notice_manually') }}
                </button>
                <button v-if="externalSearchVisible" type="button" class="btn btn-link text-decoration-none p-0" @click="emitManualEntry()">
                    {{ $t('cataloging.continue_manual_entry') }}
                </button>
            </div>
        </div>
    `
});
