/**
 * ISBN Lookup Component
 * Handles ISBN scanning and BNF catalog lookup
 */

const { defineComponent, ref, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';

export default defineComponent({
    name: 'ISBNLookup',

    emits: ['lookup-success', 'lookup-not-found', 'manual-entry', 'existing-record-found'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { error: showError, warning, info } = useNotification();

        // State
        const isbn = ref('');
        const isbnInput = ref(null);
        const loading = ref(false);

        onMounted(async () => {
            await nextTick();
            isbnInput.value?.focus();
        });

        /**
         * Normalize ISBN/ISSN
         * - For ISBNs: remove dashes and spaces
         * - For ISSNs: preserve hyphen (required for ISSN format NNNN-NNNX)
         */
        const normalizeISBN = (value) => {
            const trimmed = value.trim();

            // EAN-13 kiosk barcode for periodicals (prefix 977) — pass through as-is.
            // Backend _ean13_to_issn() extracts and validates the ISSN.
            const stripped = trimmed.replace(/[-\s]/g, '');
            if (/^\d{13}$/.test(stripped) && stripped.startsWith('977')) {
                return stripped;
            }

            // ISSN pattern: NNNN-NNNX (4 digits, hyphen, 3 digits + check digit)
            const issnPattern = /^\d{4}-?\d{3}[\dXx]$/;

            // If it looks like an ISSN, preserve the hyphen (add if missing)
            if (issnPattern.test(trimmed.replace(/\s/g, ''))) {
                const clean = trimmed.replace(/\s/g, '');
                // Ensure hyphen is present: 1762-9330 or 17629330 → 1762-9330
                if (clean.length === 8 && !clean.includes('-')) {
                    return clean.slice(0, 4) + '-' + clean.slice(4);
                }
                return clean.toUpperCase(); // Normalize X to uppercase
            }

            // Otherwise treat as ISBN - remove all hyphens and spaces
            return trimmed.replace(/[-\s]/g, '');
        };

        /**
         * Lookup ISBN/ISSN in BNF/SUDOC catalog
         */
        const lookupISBN = async () => {
            const isbnValue = normalizeISBN(isbn.value.trim());

            if (!isbnValue) {
                showError(t('cataloging.error_no_isbn'));
                return;
            }

            try {
                loading.value = true;

                // First check if ISBN/ISSN already exists in local database
                const searchResponse = await apiClient.get('/catalog/bibliographic/search', {
                    q: isbnValue,
                    limit: 1
                });

                if (searchResponse.items && searchResponse.items.length > 0) {
                    const existingRecord = searchResponse.items[0];

                    // ISBN/ISSN already exists - skip to item creation
                    info(t('cataloging.isbn_already_exists', {
                        title: existingRecord.title
                    }));

                    // Emit existing record event
                    emit('existing-record-found', existingRecord);
                    return;
                }

                // ISBN/ISSN not in database - proceed with catalog lookup
                const response = await apiClient.post('/catalog/lookup-isbn', null, {
                    isbn: isbnValue
                });

                // BNF lookup successful
                emit('lookup-success', response);

            } catch (err) {
                console.error('Error looking up ISBN:', err);

                // Handle specific error cases
                // Note: ApiError uses statusCode property
                if (err.statusCode === 404) {
                    // ISBN not found in BNF
                    warning(t('cataloging.isbn_not_found', { isbn: isbnValue }));
                    emit('lookup-not-found', isbnValue);
                } else if (err.statusCode === 409) {
                    // ISBN already exists - should have been caught earlier, but handle it
                    const detail = err.details || {};
                    info(t('cataloging.isbn_already_exists', {
                        title: detail.title || 'Unknown'
                    }));
                    emit('existing-record-found', {
                        record_id: detail.record_id,
                        id: detail.record_id,
                        title: detail.title,
                        medium_type: detail.medium_type
                    });
                } else {
                    showError(err.message || t('cataloging.lookup_error'));
                }
            } finally {
                loading.value = false;
            }
        };

        /**
         * Handle Enter key on ISBN input (scanner compatibility)
         */
        const handleKeypress = (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                lookupISBN();
            }
        };

        /**
         * Switch to manual entry mode
         */
        const switchToManualEntry = () => {
            // Pass the current ISBN value to manual entry
            const isbnValue = isbn.value.trim();
            emit('manual-entry', isbnValue);
        };

        return {
            isbn,
            isbnInput,
            loading,
            lookupISBN,
            handleKeypress,
            switchToManualEntry
        };
    },

    template: `
        <div class="isbn-lookup mb-4">
            <h5 class="mb-3">
                <i class="bi bi-upc-scan"></i>
                {{ $t('cataloging.isbn_lookup_title') }}
            </h5>

            <form @submit.prevent="lookupISBN">
                <div class="row g-3">
                    <div class="col-md-8">
                        <label for="isbn-input" class="form-label">
                            {{ $t('cataloging.isbn_label') }}
                        </label>
                        <div class="input-group input-group-lg">
                            <span class="input-group-text">
                                <i class="bi bi-barcode"></i>
                            </span>
                            <input
                                id="isbn-input"
                                ref="isbnInput"
                                v-model="isbn"
                                type="text"
                                class="form-control"
                                :placeholder="$t('cataloging.isbn_placeholder')"
                                :disabled="loading"
                                @keypress="handleKeypress"
                            />
                        </div>
                        <small class="form-text text-muted">
                            {{ $t('cataloging.isbn_help') }}
                        </small>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">&nbsp;</label>
                        <button
                            type="submit"
                            class="btn btn-primary btn-lg w-100"
                            :disabled="loading || !isbn.trim()"
                        >
                            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                            <i v-else class="bi bi-search me-2"></i>
                            {{ loading ? $t('common.searching') : $t('cataloging.lookup_button') }}
                        </button>
                    </div>
                </div>
            </form>

            <div class="mt-3">
                <button
                    type="button"
                    class="btn btn-link text-decoration-none p-0"
                    @click="switchToManualEntry"
                >
                    <i class="bi bi-pencil-square"></i>
                    {{ $t('cataloging.manual_entry_link') }}
                </button>
            </div>
        </div>
    `
});
