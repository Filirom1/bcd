/**
 * Bibliographic Form Component
 * Form for creating/editing bibliographic records with BNF auto-fill
 */

const { defineComponent, ref, reactive, watch, computed, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useAppState } from '../../composables/useAppState.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'BibliographicForm',

    props: {
        bnfData: {
            type: Object,
            default: null
        },
        isbn: {
            type: String,
            default: ''
        },
        existingRecord: {
            type: Object,
            default: null
        }
    },

    emits: ['record-created', 'cancel'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { settings } = useAppState();
        const { success, error: showError } = useNotification();
        const { handleError } = useErrorHandler(t);

        const parseCsv = (str) => str ? str.split(',').map(s => s.trim()).filter(Boolean) : [];
        const genreSuggestions = computed(() => parseCsv(settings.value?.catalog_genres));
        const languageSuggestions = computed(() => parseCsv(settings.value?.catalog_languages));
        const mediumTypeSuggestions = computed(() => parseCsv(settings.value?.catalog_medium_types));

        // Form state
        const formData = reactive({
            isbn: '',
            title: '',
            subtitle: '',
            authors: [],
            illustrators: [],
            publisher: '',
            publication_year: null,
            collection: '',
            series_number: '',
            language: 'fr',
            binding_type: null,
            genre: '',
            level: '',
            medium_type: 'Livre',
            target_audience: 'child',
            keywords: [],
            description: '',
            page_count: null,
            has_illustrations: null,
            dimensions: ''
        });

        // UI state
        const loading = ref(false);
        const authorsText = ref('');
        const illustratorsText = ref('');
        const keywordsText = ref('');
        /**
         * Normalize ISBN (remove dashes and spaces)
         */
        const normalizeISBN = (isbn) => {
            if (!isbn) return '';
            return isbn.replace(/^(isbn:|issn:)/, '').replace(/[-\s]/g, '');
        };

        // Pre-fill from existing record if provided, otherwise auto-fill from BNF data
        const prefillForm = () => {
            if (props.existingRecord) {
                const rec = props.existingRecord;
                formData.isbn = normalizeISBN(rec.isbn_value || rec.isbn || props.isbn);
                formData.title = rec.title || '';
                formData.subtitle = rec.subtitle || '';
                formData.publisher = rec.publisher || '';
                formData.publication_year = rec.publication_year || null;
                formData.collection = rec.collection || '';
                formData.series_number = rec.series_number || '';
                formData.language = rec.language || 'fr';
                formData.genre = rec.genre || '';
                formData.level = rec.level || '';
                formData.medium_type = rec.medium_type || 'Livre';
                formData.target_audience = rec.target_audience || 'child';
                formData.description = rec.description || '';
                formData.page_count = rec.page_count || null;
                formData.has_illustrations = rec.has_illustrations !== null ? rec.has_illustrations : false;
                formData.dimensions = rec.dimensions || '';

                // Handle arrays
                formData.authors = Array.isArray(rec.authors) ? rec.authors : [];
                formData.illustrators = Array.isArray(rec.illustrators) ? rec.illustrators : [];
                formData.keywords = Array.isArray(rec.keywords) ? rec.keywords : [];

                // Convert arrays to text for textarea
                authorsText.value = formData.authors.join('\n');
                illustratorsText.value = formData.illustrators.join('\n');
                keywordsText.value = formData.keywords.join(', ');
            } else if (props.bnfData) {
                const bnf = props.bnfData;
                formData.isbn = normalizeISBN(bnf.isbn || props.isbn);
                formData.title = bnf.title || '';
                formData.subtitle = bnf.subtitle || '';
                formData.publisher = bnf.publisher || '';
                formData.publication_year = bnf.publication_year || null;
                formData.collection = bnf.collection || '';
                formData.series_number = bnf.series_number || '';
                formData.language = bnf.language || 'fr';
                formData.genre = bnf.genre || '';
                formData.level = bnf.level || '';
                formData.medium_type = bnf.medium_type || 'Livre';
                formData.target_audience = bnf.target_audience || 'child';
                formData.description = bnf.description || '';
                formData.page_count = bnf.page_count || null;
                formData.has_illustrations = bnf.has_illustrations !== null ? bnf.has_illustrations : false;
                formData.dimensions = bnf.dimensions || '';

                // Handle arrays
                formData.authors = bnf.authors || [];
                formData.illustrators = bnf.illustrators || [];
                formData.keywords = bnf.keywords || [];

                // Convert arrays to text for textarea
                authorsText.value = formData.authors.join('\n');
                illustratorsText.value = formData.illustrators.join('\n');
                keywordsText.value = formData.keywords.join(', ');
            } else if (props.isbn) {
                formData.isbn = normalizeISBN(props.isbn);
            }
        };

        // Watchers/Lifecycle
        watch(() => props.existingRecord, prefillForm, { immediate: true });
        watch(() => props.bnfData, prefillForm, { immediate: true });
        onMounted(prefillForm);

        /**
         * Submit bibliographic record
         */
        const submitRecord = async () => {
            // Validate required fields
            if (!formData.title.trim()) {
                showError(t('cataloging.error_title_required'));
                return;
            }

            try {
                loading.value = true;

                // Convert text fields to arrays
                formData.authors = authorsText.value
                    .split('\n')
                    .map(a => a.trim())
                    .filter(a => a);

                formData.illustrators = illustratorsText.value
                    .split('\n')
                    .map(i => i.trim())
                    .filter(i => i);

                formData.keywords = keywordsText.value
                    .split(',')
                    .map(k => k.trim())
                    .filter(k => k);

                let record;
                if (props.existingRecord) {
                    const recordId = props.existingRecord.id || props.existingRecord.record_id;
                    const payload = { ...formData };
                    if (payload.publication_year === '') payload.publication_year = null;
                    if (payload.page_count === '') payload.page_count = null;

                    record = await apiClient.patch(`/catalog/records/${recordId}`, payload);
                    success(t('cataloging.record_updated', { title: record.title }));
                } else {
                    // Create record via API
                    record = await apiClient.post('/catalog/bibliographic', formData);
                    success(t('cataloging.record_created', { title: record.title }));
                }

                // Emit success with created record
                emit('record-created', record);

            } catch (err) {
                handleError(err);
            } finally {
                loading.value = false;
            }
        };

        /**
         * Cancel and reset
         */
        const cancel = () => {
            emit('cancel');
        };

        // Computed
        const isBnfData = computed(() => props.bnfData !== null);
        const lookupSource = computed(() => props.bnfData?._source || 'bnf');
        const coverPreviewUrl = computed(() => {
            // Local cover pre-downloaded during lookup (most reliable)
            if (props.bnfData?.cover_image) return `/covers/${props.bnfData.cover_image}`;
            // Google Books thumbnail (already fetched)
            if (props.bnfData?.cover_url) return props.bnfData.cover_url;
            // Open Library direct URL as last resort
            const isbn = normalizeISBN(formData.isbn || props.isbn);
            if (isbn) return `https://covers.openlibrary.org/b/isbn/${isbn}-M.jpg?default=false`;
            return null;
        });

        const handleCoverError = (event) => {
            const src = event.target.src;
            // If local cover failed, try Open Library before giving up
            if (src.includes('/covers/')) {
                const isbn = normalizeISBN(formData.isbn || props.isbn);
                if (isbn) {
                    event.target.src = `https://covers.openlibrary.org/b/isbn/${isbn}-M.jpg?default=false`;
                    return;
                }
            }
            event.target.style.display = 'none';
        };

        return {
            formData,
            loading,
            authorsText,
            illustratorsText,
            keywordsText,
            genreSuggestions,
            languageSuggestions,
            mediumTypeSuggestions,
            submitRecord,
            cancel,
            isBnfData,
            lookupSource,
            coverPreviewUrl,
            handleCoverError,
            existingRecord: computed(() => props.existingRecord)
        };
    },

    template: `
        <div class="bibliographic-form">
            <!-- Existing Record Banner -->
            <div v-if="existingRecord" class="alert alert-warning mb-4 d-flex gap-3 align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-2">
                        <i class="bi bi-exclamation-triangle"></i>
                        {{ $t('cataloging.editing_existing_record') }}
                    </h6>
                    <p class="mb-0 small">
                        {{ $t('cataloging.editing_existing_record_help') }}
                    </p>
                </div>
            </div>

            <!-- Lookup Data Banner -->
            <div v-if="isBnfData && !existingRecord" class="alert alert-success mb-4 d-flex gap-3 align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-2">
                        <i class="bi bi-check-circle"></i>
                        {{ $t('cataloging.' + lookupSource + '_data_found') }}
                    </h6>
                    <p class="mb-0 small">
                        {{ $t('cataloging.' + lookupSource + '_data_help') }}
                    </p>
                </div>
                <img
                    v-if="coverPreviewUrl"
                    :src="coverPreviewUrl"
                    alt=""
                    class="rounded shadow-sm flex-shrink-0"
                    style="max-height:120px; max-width:85px; object-fit:contain;"
                    @error="handleCoverError"
                />
            </div>
            <!-- Cover preview when no lookup data (manual entry with ISBN) -->
            <div v-else-if="coverPreviewUrl" class="text-end mb-3">
                <img
                    :src="coverPreviewUrl"
                    alt=""
                    class="rounded shadow-sm"
                    style="max-height:120px; max-width:85px; object-fit:contain;"
                    @error="handleCoverError"
                />
            </div>

            <form @submit.prevent="submitRecord">
                <div class="row g-3">
                    <!-- ISBN / ISSN -->
                    <div class="col-md-4">
                        <label for="isbn" class="form-label">
                            {{ $t('bibliographic.isbn') }}
                        </label>
                        <input
                            id="isbn"
                            v-model="formData.isbn"
                            type="text"
                            class="form-control"
                            maxlength="17"
                            :placeholder="$t('cataloging.isbn_placeholder')"
                        />
                        <small class="form-text text-muted">
                            {{ $t('cataloging.isbn_format_help') }}
                        </small>
                    </div>

                    <!-- Title (required) -->
                    <div class="col-md-8">
                        <label for="title" class="form-label">
                            {{ $t('bibliographic.title') }} <span class="text-danger">*</span>
                        </label>
                        <input
                            id="title"
                            v-model="formData.title"
                            type="text"
                            class="form-control"
                            maxlength="500"
                            required
                        />
                    </div>

                    <!-- Subtitle -->
                    <div class="col-md-8">
                        <label for="subtitle" class="form-label">
                            {{ $t('bibliographic.subtitle') }}
                        </label>
                        <input
                            id="subtitle"
                            v-model="formData.subtitle"
                            type="text"
                            class="form-control"
                            maxlength="500"
                        />
                    </div>

                    <!-- Authors (one per line) -->
                    <div class="col-md-6">
                        <label for="authors" class="form-label">
                            {{ $t('bibliographic.authors') }}
                        </label>
                        <textarea
                            id="authors"
                            v-model="authorsText"
                            class="form-control"
                            rows="3"
                            :placeholder="$t('cataloging.authors_placeholder')"
                        ></textarea>
                        <small class="form-text text-muted">
                            {{ $t('cataloging.one_per_line') }}
                        </small>
                    </div>

                    <!-- Illustrators -->
                    <div class="col-md-6">
                        <label for="illustrators" class="form-label">
                            {{ $t('bibliographic.illustrators') }}
                        </label>
                        <textarea
                            id="illustrators"
                            v-model="illustratorsText"
                            class="form-control"
                            rows="3"
                            :placeholder="$t('cataloging.illustrators_placeholder')"
                        ></textarea>
                        <small class="form-text text-muted">
                            {{ $t('cataloging.one_per_line') }}
                        </small>
                    </div>

                    <!-- Publisher -->
                    <div class="col-md-6">
                        <label for="publisher" class="form-label">
                            {{ $t('bibliographic.publisher') }}
                        </label>
                        <input
                            id="publisher"
                            v-model="formData.publisher"
                            type="text"
                            class="form-control"
                            maxlength="200"
                        />
                    </div>

                    <!-- Publication Year -->
                    <div class="col-md-3">
                        <label for="publication_year" class="form-label">
                            {{ $t('bibliographic.publication_year') }}
                        </label>
                        <input
                            id="publication_year"
                            v-model.number="formData.publication_year"
                            type="number"
                            class="form-control"
                            min="1000"
                            max="2100"
                        />
                    </div>

                    <!-- Collection -->
                    <div class="col-md-6">
                        <label for="collection" class="form-label">
                            {{ $t('bibliographic.collection') }}
                        </label>
                        <input
                            id="collection"
                            v-model="formData.collection"
                            type="text"
                            class="form-control"
                            maxlength="200"
                        />
                    </div>

                    <!-- Series Number -->
                    <div class="col-md-3">
                        <label for="series_number" class="form-label">
                            {{ $t('bibliographic.series_number') }}
                        </label>
                        <input
                            id="series_number"
                            v-model="formData.series_number"
                            type="text"
                            class="form-control"
                            maxlength="50"
                        />
                    </div>

                    <!-- Language -->
                    <div class="col-md-3">
                        <label for="language" class="form-label">
                            {{ $t('bibliographic.language') }}
                        </label>
                        <input
                            id="language"
                            v-model="formData.language"
                            type="text"
                            class="form-control"
                            list="biblio-language-suggestions"
                            maxlength="10"
                        />
                        <datalist id="biblio-language-suggestions">
                            <option v-for="s in languageSuggestions" :key="s" :value="s" />
                        </datalist>
                    </div>

                    <!-- Genre -->
                    <div class="col-md-4">
                        <label for="genre" class="form-label">
                            {{ $t('bibliographic.genre') }}
                        </label>
                        <input
                            id="genre"
                            v-model="formData.genre"
                            type="text"
                            class="form-control"
                            list="biblio-genre-suggestions"
                            maxlength="100"
                        />
                        <datalist id="biblio-genre-suggestions">
                            <option v-for="s in genreSuggestions" :key="s" :value="s" />
                        </datalist>
                    </div>

                    <!-- Medium Type -->
                    <div class="col-md-4">
                        <label for="medium_type" class="form-label">
                            {{ $t('bibliographic.medium_type') }}
                        </label>
                        <input
                            id="medium_type"
                            v-model="formData.medium_type"
                            type="text"
                            class="form-control"
                            list="biblio-medium-type-suggestions"
                            maxlength="50"
                        />
                        <datalist id="biblio-medium-type-suggestions">
                            <option v-for="s in mediumTypeSuggestions" :key="s" :value="s" />
                        </datalist>
                    </div>

                    <!-- Target Audience -->
                    <div class="col-md-4">
                        <label for="target_audience" class="form-label">
                            {{ $t('bibliographic.target_audience') }}
                        </label>
                        <select
                            id="target_audience"
                            v-model="formData.target_audience"
                            class="form-select"
                        >
                            <option value="child">{{ $t('bibliographic.audience_child') }}</option>
                            <option value="youth">{{ $t('bibliographic.audience_youth') }}</option>
                            <option value="adult">{{ $t('bibliographic.audience_adult') }}</option>
                        </select>
                    </div>

                    <!-- Description -->
                    <div class="col-12">
                        <label for="description" class="form-label">
                            {{ $t('bibliographic.description') }}
                        </label>
                        <textarea
                            id="description"
                            v-model="formData.description"
                            class="form-control"
                            rows="3"
                        ></textarea>
                    </div>

                    <!-- Keywords (comma-separated) -->
                    <div class="col-md-8">
                        <label for="keywords" class="form-label">
                            {{ $t('bibliographic.keywords') }}
                        </label>
                        <input
                            id="keywords"
                            v-model="keywordsText"
                            type="text"
                            class="form-control"
                            :placeholder="$t('cataloging.keywords_placeholder')"
                        />
                        <small class="form-text text-muted">
                            {{ $t('cataloging.comma_separated') }}
                        </small>
                    </div>

                    <!-- Page Count -->
                    <div class="col-md-2">
                        <label for="page_count" class="form-label">
                            {{ $t('bibliographic.page_count') }}
                        </label>
                        <input
                            id="page_count"
                            v-model.number="formData.page_count"
                            type="number"
                            class="form-control"
                            min="0"
                        />
                    </div>

                    <!-- Has Illustrations -->
                    <div class="col-md-2">
                        <label class="form-label d-block">
                            {{ $t('bibliographic.has_illustrations') }}
                        </label>
                        <div class="form-check">
                            <input
                                id="has_illustrations"
                                v-model="formData.has_illustrations"
                                type="checkbox"
                                class="form-check-input"
                            />
                            <label for="has_illustrations" class="form-check-label">
                                {{ $t('common.yes') }}
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Submit Buttons -->
                <div class="mt-4 d-flex gap-2">
                    <button
                        type="submit"
                        class="btn btn-primary"
                        :disabled="loading"
                    >
                        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                        <i v-else class="bi bi-save me-2"></i>
                        {{ loading ? $t('common.saving') : $t('cataloging.save_record') }}
                    </button>

                    <button
                        type="button"
                        class="btn btn-secondary"
                        :disabled="loading"
                        @click="cancel"
                    >
                        <i class="bi bi-x-circle me-2"></i>
                        {{ $t('common.cancel') }}
                    </button>
                </div>
            </form>
        </div>
    `
});
