/**
 * Bibliographic Form Component
 * Form for creating/editing bibliographic records with BNF auto-fill
 */

const { defineComponent, ref, reactive, watch, computed, onMounted } = Vue;
const { useI18n } = VueI18n;
import BibliographicFields from '../catalog/BibliographicFields.js';
import { apiClient } from '../../api/client.js';
import { useAppState } from '../../composables/useAppState.js';
import { parseCsv } from '../../utils/domain.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'BibliographicForm',
    components: { BibliographicFields },

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

        // Reactive wrapper so BibliographicFields v-model can spread-merge updates
        const formDataModel = computed({
            get: () => ({ ...formData }),
            set: (val) => Object.assign(formData, val)
        });

        return {
            formData,
            formDataModel,
            loading,
            settings,
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
                    <p class="mb-0 small">{{ $t('cataloging.editing_existing_record_help') }}</p>
                </div>
            </div>

            <!-- Lookup Data Banner -->
            <div v-if="isBnfData && !existingRecord" class="alert alert-success mb-4 d-flex gap-3 align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-2">
                        <i class="bi bi-check-circle"></i>
                        {{ $t('cataloging.' + lookupSource + '_data_found') }}
                    </h6>
                    <p class="mb-0 small">{{ $t('cataloging.' + lookupSource + '_data_help') }}</p>
                </div>
                <img v-if="coverPreviewUrl" :src="coverPreviewUrl" alt=""
                    class="rounded shadow-sm flex-shrink-0"
                    style="max-height:120px; max-width:85px; object-fit:contain;"
                    @error="handleCoverError" />
            </div>
            <div v-else-if="coverPreviewUrl" class="text-end mb-3">
                <img :src="coverPreviewUrl" alt="" class="rounded shadow-sm"
                    style="max-height:120px; max-width:85px; object-fit:contain;"
                    @error="handleCoverError" />
            </div>

            <form @submit.prevent="submitRecord">
                <bibliographic-fields
                    v-model="formDataModel"
                    :edit-mode="true"
                    :settings="settings"
                />

                <div class="mt-4 d-flex gap-2">
                    <button type="submit" class="btn btn-primary" :disabled="loading">
                        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                        <i v-else class="bi bi-save me-2"></i>
                        {{ loading ? $t('common.saving') : $t('cataloging.save_record') }}
                    </button>
                    <button type="button" class="btn btn-secondary" :disabled="loading" @click="cancel">
                        <i class="bi bi-x-circle me-2"></i>
                        {{ $t('common.cancel') }}
                    </button>
                </div>
            </form>
        </div>
    `
});
