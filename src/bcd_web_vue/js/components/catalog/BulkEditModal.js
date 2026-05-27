/**
 * BulkEditModal Component (Catalog variant)
 *
 * 3-step wizard modal for bulk catalog record operations:
 * - Step 1: Select operation (Bulk Edit Metadata, Delete Records)
 * - Step 2: Configure operation (select fields to update or confirm delete)
 * - Step 3: Confirm operation (show summary with selected count)
 *
 * Props:
 * - show (Boolean): Show/hide modal
 * - selectedRecords (Array): Array of selected record objects
 *
 * Emits:
 * - close: User closed modal
 * - execute: User confirmed operation { operation, fields? }
 */

const { ref, computed, watch, toRef } = Vue;
const { useI18n } = VueI18n;

export default {
    name: 'BulkEditModal',

    props: {
        show: {
            type: Boolean,
            default: false
        },
        selectedRecords: {
            type: Array,
            default: () => []
        },
        settings: {
            type: Object,
            default: null
        }
    },

    emits: ['close', 'execute'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Wizard state
        const currentStep = ref(1);
        const selectedOperation = ref(null);

        // Bulk edit fields
        const fields = ref({
            genre: '',
            target_audience: '',
            language: '',
            medium_type: ''
        });

        // Operation types
        const OPERATIONS = {
            BULK_EDIT: 'bulk_edit',
            DELETE: 'delete'
        };

        const parseCsv = (str) => {
            if (!str) return [];
            return str.split(',').map(s => s.trim()).filter(Boolean);
        };

        const genreSuggestions = computed(() => parseCsv(props.settings?.catalog_genres));
        const languageSuggestions = computed(() => parseCsv(props.settings?.catalog_languages));
        const mediumTypeSuggestions = computed(() => parseCsv(props.settings?.catalog_medium_types));

        const audienceOptions = [
            { value: 'child', label: t('bibliographic.audience_child') },
            { value: 'youth', label: t('bibliographic.audience_youth') },
            { value: 'adult', label: t('bibliographic.audience_adult') }
        ];

        // Selected count
        const selectedCount = computed(() => props.selectedRecords.length);

        // Can proceed to next step?
        const canProceedStep1 = computed(() => selectedOperation.value !== null);
        const canProceedStep2 = computed(() => {
            if (selectedOperation.value === OPERATIONS.BULK_EDIT) {
                // At least one field must be filled
                return Object.values(fields.value).some(val => val && val !== '');
            } else if (selectedOperation.value === OPERATIONS.DELETE) {
                return true; // No config needed for delete
            }
            return false;
        });

        // Confirmation message
        const confirmationMessage = computed(() => {
            if (selectedOperation.value === OPERATIONS.BULK_EDIT) {
                return t('admin.confirm_bulk_edit_records', {
                    count: selectedCount.value
                });
            } else if (selectedOperation.value === OPERATIONS.DELETE) {
                return t('admin.confirm_bulk_delete_records', {
                    count: selectedCount.value
                });
            }
            return '';
        });

        // Get summary of fields to update
        const fieldsSummary = computed(() => {
            const summary = [];
            if (fields.value.genre) {
                summary.push(`${t('admin.genre')}: ${fields.value.genre}`);
            }
            if (fields.value.target_audience) {
                const audience = audienceOptions.find(a => a.value === fields.value.target_audience);
                summary.push(`${t('admin.target_audience')}: ${audience?.label || fields.value.target_audience}`);
            }
            if (fields.value.language) {
                summary.push(`${t('admin.language')}: ${fields.value.language}`);
            }
            if (fields.value.medium_type) {
                summary.push(`${t('admin.medium_type')}: ${fields.value.medium_type}`);
            }
            return summary;
        });

        // Reset wizard state
        const resetWizard = () => {
            currentStep.value = 1;
            selectedOperation.value = null;
            fields.value = {
                genre: '',
                target_audience: '',
                language: '',
                medium_type: ''
            };
        };

        // Handle operation selection
        const selectOperation = (operation) => {
            selectedOperation.value = operation;
        };

        // Navigate between steps
        const goToStep = (step) => {
            currentStep.value = step;
        };

        const nextStep = () => {
            if (currentStep.value < 3) {
                currentStep.value++;
            }
        };

        const previousStep = () => {
            if (currentStep.value > 1) {
                currentStep.value--;
            }
        };

        // Handle close
        const handleClose = () => {
            resetWizard();
            emit('close');
        };

        // Handle execute operation
        const handleExecute = () => {
            const payload = {
                operation: selectedOperation.value
            };

            if (selectedOperation.value === OPERATIONS.BULK_EDIT) {
                // Only include non-empty fields
                payload.fields = {};
                Object.entries(fields.value).forEach(([key, value]) => {
                    if (value && value !== '') {
                        payload.fields[key] = value;
                    }
                });
            }

            emit('execute', payload);
            resetWizard();
        };

        // Watch show prop to reset wizard
        watch(() => props.show, (newValue) => {
            if (newValue) {
                resetWizard();
            }
        });

        return {
            t,
            currentStep,
            selectedOperation,
            fields,
            genreSuggestions,
            audienceOptions,
            languageSuggestions,
            mediumTypeSuggestions,
            selectedCount,
            canProceedStep1,
            canProceedStep2,
            confirmationMessage,
            fieldsSummary,
            OPERATIONS,
            selectOperation,
            goToStep,
            nextStep,
            previousStep,
            handleClose,
            handleExecute
        };
    },

    template: `
        <div
            class="modal fade"
            :class="{ show: show }"
            :style="{ display: show ? 'block' : 'none' }"
            tabindex="-1"
            aria-labelledby="catalogBulkEditModalLabel"
            :aria-hidden="!show"
            @click.self="handleClose"
        >
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content">
                    <!-- Modal Header -->
                    <div class="modal-header">
                        <h5 class="modal-title" id="catalogBulkEditModalLabel">
                            <i class="bi bi-pencil"></i>
                            {{ t('admin.bulk_edit_title') }}
                            <span class="badge bg-secondary ms-2">{{ selectedCount }} {{ t('catalog.records_imported') }}</span>
                        </h5>
                        <button
                            type="button"
                            class="btn-close"
                            @click="handleClose"
                            :aria-label="t('common.close')"
                        ></button>
                    </div>

                    <!-- Modal Body -->
                    <div class="modal-body">
                        <!-- Progress Indicator -->
                        <div class="mb-4">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <div class="d-flex align-items-center">
                                    <div
                                        class="rounded-circle d-flex align-items-center justify-content-center me-2"
                                        :class="currentStep >= 1 ? 'bg-primary text-white' : 'bg-secondary text-white'"
                                        style="width: 32px; height: 32px; font-size: 14px;"
                                    >
                                        1
                                    </div>
                                    <span :class="currentStep === 1 ? 'fw-bold' : ''">
                                        {{ t('admin.select_operation') }}
                                    </span>
                                </div>
                                <div class="flex-grow-1 mx-2" style="height: 2px; background-color: #dee2e6;"></div>
                                <div class="d-flex align-items-center">
                                    <div
                                        class="rounded-circle d-flex align-items-center justify-content-center me-2"
                                        :class="currentStep >= 2 ? 'bg-primary text-white' : 'bg-secondary text-white'"
                                        style="width: 32px; height: 32px; font-size: 14px;"
                                    >
                                        2
                                    </div>
                                    <span :class="currentStep === 2 ? 'fw-bold' : ''">
                                        {{ t('admin.configure_operation') }}
                                    </span>
                                </div>
                                <div class="flex-grow-1 mx-2" style="height: 2px; background-color: #dee2e6;"></div>
                                <div class="d-flex align-items-center">
                                    <div
                                        class="rounded-circle d-flex align-items-center justify-content-center me-2"
                                        :class="currentStep >= 3 ? 'bg-primary text-white' : 'bg-secondary text-white'"
                                        style="width: 32px; height: 32px; font-size: 14px;"
                                    >
                                        3
                                    </div>
                                    <span :class="currentStep === 3 ? 'fw-bold' : ''">
                                        {{ t('admin.confirm_operation') }}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Step 1: Select Operation -->
                        <div v-if="currentStep === 1">
                            <p class="text-muted mb-3">
                                {{ t('admin.select_operation') }}
                            </p>
                            <div class="list-group">
                                <button
                                    type="button"
                                    class="list-group-item list-group-item-action"
                                    :class="{ active: selectedOperation === OPERATIONS.BULK_EDIT }"
                                    @click="selectOperation(OPERATIONS.BULK_EDIT)"
                                >
                                    <div class="d-flex w-100 justify-content-between">
                                        <h6 class="mb-1">
                                            <i class="bi bi-pencil-square"></i>
                                            {{ t('admin.bulk_edit') }}
                                        </h6>
                                    </div>
                                    <p class="mb-0 small">
                                        {{ t('admin.bulk_edit_description') }}
                                    </p>
                                </button>

                                <button
                                    type="button"
                                    class="list-group-item list-group-item-action list-group-item-danger"
                                    :class="{ active: selectedOperation === OPERATIONS.DELETE }"
                                    @click="selectOperation(OPERATIONS.DELETE)"
                                >
                                    <div class="d-flex w-100 justify-content-between">
                                        <h6 class="mb-1">
                                            <i class="bi bi-trash"></i>
                                            {{ t('admin.delete') }}
                                        </h6>
                                    </div>
                                    <p class="mb-0 small">
                                        {{ t('admin.delete_description_catalog') }}
                                    </p>
                                </button>
                            </div>
                        </div>

                        <!-- Step 2: Configure Operation -->
                        <div v-if="currentStep === 2">
                            <!-- Bulk Edit Configuration -->
                            <div v-if="selectedOperation === OPERATIONS.BULK_EDIT">
                                <p class="text-muted mb-3">
                                    {{ t('admin.common_fields') }} - Select fields to update (leave blank to keep existing values)
                                </p>

                                <!-- Genre -->
                                <div class="mb-3">
                                    <label class="form-label">{{ t('admin.genre') }}</label>
                                    <input
                                        type="text"
                                        class="form-control"
                                        v-model="fields.genre"
                                        list="bulk-genre-suggestions"
                                        :placeholder="t('admin.genre_placeholder') || 'e.g., Adventure, Policier, Fantastique'"
                                    />
                                    <datalist id="bulk-genre-suggestions">
                                        <option v-for="genre in genreSuggestions" :key="genre" :value="genre">
                                            {{ genre }}
                                        </option>
                                    </datalist>
                                    <small class="form-text text-muted">{{ t('admin.genre_hint') || 'Type any value or select from suggestions' }}</small>
                                </div>

                                <!-- Target Audience -->
                                <div class="mb-3">
                                    <label class="form-label">{{ t('admin.target_audience') }}</label>
                                    <select class="form-select" v-model="fields.target_audience">
                                        <option value="">— {{ t('common.no') }} {{ t('common.change') }} —</option>
                                        <option v-for="audience in audienceOptions" :key="audience.value" :value="audience.value">
                                            {{ audience.label }}
                                        </option>
                                    </select>
                                </div>

                                <!-- Language -->
                                <div class="mb-3">
                                    <label class="form-label">{{ t('admin.language') }}</label>
                                    <input
                                        type="text"
                                        class="form-control"
                                        v-model="fields.language"
                                        list="bulk-language-suggestions"
                                        :placeholder="t('admin.language_placeholder') || 'e.g., fr, en, es'"
                                    />
                                    <datalist id="bulk-language-suggestions">
                                        <option v-for="lang in languageSuggestions" :key="lang" :value="lang" />
                                    </datalist>
                                    <small class="form-text text-muted">{{ t('admin.language_hint') || 'Type any value or select from suggestions' }}</small>
                                </div>

                                <!-- Medium Type -->
                                <div class="mb-3">
                                    <label class="form-label">{{ t('admin.medium_type') }}</label>
                                    <input
                                        type="text"
                                        class="form-control"
                                        v-model="fields.medium_type"
                                        list="bulk-medium-type-suggestions"
                                        :placeholder="t('admin.medium_type_placeholder') || 'e.g., Livre, CD, DVD, Bande dessinée'"
                                    />
                                    <datalist id="bulk-medium-type-suggestions">
                                        <option v-for="medium in mediumTypeSuggestions" :key="medium" :value="medium">
                                            {{ medium }}
                                        </option>
                                    </datalist>
                                    <small class="form-text text-muted">{{ t('admin.medium_type_hint') || 'Type any value or select from suggestions' }}</small>
                                </div>
                            </div>

                            <!-- Delete Confirmation (no config needed) -->
                            <div v-if="selectedOperation === OPERATIONS.DELETE">
                                <div class="alert alert-danger">
                                    <h6 class="alert-heading">
                                        <i class="bi bi-exclamation-triangle"></i>
                                        {{ t('admin.warning') }}
                                    </h6>
                                    <p class="mb-0">
                                        {{ t('admin.delete_warning_message') }}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <!-- Step 3: Confirm Operation -->
                        <div v-if="currentStep === 3">
                            <div class="alert alert-info">
                                <h6 class="alert-heading">
                                    <i class="bi bi-info-circle"></i>
                                    {{ t('admin.confirm_operation') }}
                                </h6>
                                <p class="mb-0">
                                    {{ confirmationMessage }}
                                </p>
                            </div>

                            <!-- Show fields that will be updated (for bulk edit) -->
                            <div v-if="selectedOperation === OPERATIONS.BULK_EDIT && fieldsSummary.length > 0" class="card mb-3">
                                <div class="card-header">
                                    <strong>{{ t('admin.common_fields') }}</strong>
                                </div>
                                <ul class="list-group list-group-flush">
                                    <li
                                        v-for="(field, index) in fieldsSummary"
                                        :key="index"
                                        class="list-group-item"
                                    >
                                        {{ field }}
                                    </li>
                                </ul>
                            </div>

                            <!-- List of selected records (first 5) -->
                            <div class="card">
                                <div class="card-header">
                                    <strong>{{ t('admin.selected_records') }} ({{ selectedCount }})</strong>
                                </div>
                                <ul class="list-group list-group-flush" style="max-height: 300px; overflow-y: auto;">
                                    <li
                                        v-for="(record, index) in selectedRecords.slice(0, 10)"
                                        :key="record.id"
                                        class="list-group-item"
                                    >
                                        <strong>{{ record.title }}</strong>
                                        <div class="small text-muted">
                                            <span v-if="record.authors">{{ Array.isArray(record.authors) ? record.authors.join(', ') : record.authors }}</span>
                                            <span v-if="record.isbn" class="ms-2">(ISBN: {{ record.isbn_value }})</span>
                                        </div>
                                    </li>
                                    <li v-if="selectedCount > 10" class="list-group-item text-muted">
                                        {{ t('admin.and_n_more', { count: selectedCount - 10 }) }}
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <!-- Modal Footer -->
                    <div class="modal-footer">
                        <button
                            v-if="currentStep > 1"
                            type="button"
                            class="btn btn-secondary"
                            @click="previousStep"
                        >
                            <i class="bi bi-arrow-left"></i>
                            {{ t('common.back') }}
                        </button>
                        <button
                            type="button"
                            class="btn btn-secondary"
                            @click="handleClose"
                        >
                            {{ t('common.cancel') }}
                        </button>
                        <button
                            v-if="currentStep < 3"
                            type="button"
                            class="btn btn-primary"
                            :disabled="currentStep === 1 ? !canProceedStep1 : !canProceedStep2"
                            @click="nextStep"
                        >
                            {{ t('common.next') }}
                            <i class="bi bi-arrow-right"></i>
                        </button>
                        <button
                            v-if="currentStep === 3"
                            type="button"
                            class="btn btn-danger"
                            @click="handleExecute"
                        >
                            <i class="bi bi-check-lg"></i>
                            {{ t('common.confirm') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal Backdrop -->
        <div
            v-if="show"
            class="modal-backdrop fade show"
        ></div>
    `
};
