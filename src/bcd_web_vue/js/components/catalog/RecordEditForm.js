/**
 * RecordEditForm.js
 *
 * Modal form for editing a single bibliographic record's metadata.
 * Supports updating ALL fields from BiblographicRecordUpdate schema.
 *
 * User Story 6 from specs/006-admin-features/spec.md:
 * - Edit individual catalog record metadata with comprehensive field coverage
 * - Validate and save changes
 */

const { ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import ItemEditForm from './ItemEditForm.js';
import RecordDeleteDialog from './RecordDeleteDialog.js';
import { ApiError } from '../../models/error.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default {
  name: 'RecordEditForm',
  components: {
    ItemEditForm,
    RecordDeleteDialog
  },
  props: {
    record: {
      type: Object,
      required: true
    },
    show: {
      type: Boolean,
      required: true
    },
    settings: {
      type: Object,
      default: null
    }
  },
  emits: ['update:show', 'saved', 'deleted'],
  setup(props, { emit }) {
    const { t } = useI18n();
    const { handleError } = useErrorHandler(t);

    // Items state
    const items = ref([]);
    const loadingItems = ref(false);
    const showItemEditModal = ref(false);
    const editingItem = ref(null);
    const showDeleteDialog = ref(false);

    // Form data (all 23 editable fields from BiblographicRecordUpdate)
    const formData = ref({
      // Basic information
      isbn: '',
      title: '',
      subtitle: '',

      // Authors & contributors
      authors: [],
      illustrators: [],

      // Publication information
      publisher: '',
      publication_year: null,
      collection: '',
      series_number: '',

      // Classification
      genre: '',
      level: '',
      medium_type: '',
      target_audience: '',
      language: '',
      country_code: '',

      // Physical description
      binding_type: '',
      page_count: null,
      has_illustrations: false,
      dimensions: '',
      physical_size: '',

      // Content description
      keywords: [],
      description: ''
    });

    const errors = ref({});
    const isSubmitting = ref(false);

    const parseCsv = (str) => {
      if (!str) return [];
      return str.split(',').map(s => s.trim()).filter(Boolean);
    };

    // Suggestions from settings (user can type any value)
    const genreSuggestions = computed(() => parseCsv(props.settings?.catalog_genres));

    const audienceOptions = [
      { value: 'child', label: t('bibliographic.audience_child') },
      { value: 'youth', label: t('bibliographic.audience_youth') },
      { value: 'adult', label: t('bibliographic.audience_adult') }
    ];

    const languageOptions = [
      { value: 'fr', label: 'Français' },
      { value: 'en', label: 'English' },
      { value: 'es', label: 'Español' },
      { value: 'de', label: 'Deutsch' },
      { value: 'it', label: 'Italiano' }
    ];

    const mediumTypeSuggestions = computed(() => parseCsv(props.settings?.catalog_medium_types));

    const bindingTypeOptions = [
      { value: 'hardcover', label: t('bibliographic.binding_hardcover') },
      { value: 'paperback', label: t('bibliographic.binding_paperback') },
      { value: 'spiral', label: t('bibliographic.binding_spiral') },
      { value: 'other', label: t('bibliographic.binding_other') }
    ];

    // Load form data when record prop changes
    watch(() => props.record, (newRecord) => {
      if (newRecord) {
        formData.value = {
          isbn: newRecord.isbn || '',
          title: newRecord.title || '',
          subtitle: newRecord.subtitle || '',
          authors: Array.isArray(newRecord.authors) ? newRecord.authors : [],
          illustrators: Array.isArray(newRecord.illustrators) ? newRecord.illustrators : [],
          publisher: newRecord.publisher || '',
          publication_year: newRecord.publication_year || null,
          collection: newRecord.collection || '',
          series_number: newRecord.series_number || '',
          genre: newRecord.genre || '',
          level: newRecord.level || '',
          medium_type: newRecord.medium_type || '',
          target_audience: newRecord.target_audience || '',
          language: newRecord.language || '',
          country_code: newRecord.country_code || '',
          binding_type: newRecord.binding_type || '',
          page_count: newRecord.page_count || null,
          has_illustrations: newRecord.has_illustrations || false,
          dimensions: newRecord.dimensions || '',
          physical_size: newRecord.physical_size || '',
          keywords: Array.isArray(newRecord.keywords) ? newRecord.keywords : [],
          description: newRecord.description || ''
        };
        errors.value = {};
      }
    }, { immediate: true });

    /**
     * Load items (exemplaires) for this record
     */
    const loadItems = async (recordId) => {
      if (!recordId) {
        console.warn('loadItems: No recordId provided');
        return;
      }

      try {
        loadingItems.value = true;
        const response = await fetch(`/api/v1/catalog/bibliographic/${recordId}/items`);

        if (!response.ok) {
          const errorText = await response.text();
          console.error('Failed to load items:', response.status, errorText);
          items.value = [];
          return;
        }

        const data = await response.json();
        items.value = Array.isArray(data) ? data : (data.items || []);
      } catch (error) {
        console.error('Error loading items:', error);
        items.value = [];
      } finally {
        loadingItems.value = false;
      }
    };

    // Watch for modal show state AND record to load items
    watch([() => props.show, () => props.record], ([show, record]) => {
      if (show && record && record.id) {
        loadItems(record.id);
      }
    }, { immediate: true });

    // Watch for item edit modal close to reset editingItem
    watch(showItemEditModal, (isShown) => {
      if (!isShown) {
        editingItem.value = null;
      }
    });

    /**
     * Handle edit item click
     */
    const handleEditItem = (item) => {
      editingItem.value = item;
      showItemEditModal.value = true;
    };

    /**
     * Handle item saved
     */
    const handleItemSaved = (updatedItem) => {
      // Reload items to reflect changes
      if (props.record && props.record.id) {
        loadItems(props.record.id);
      }
      // Close the item edit modal
      showItemEditModal.value = false;
      editingItem.value = null;
    };

    /**
     * Get translated condition label
     */
    const getConditionLabel = (condition) => {
      const conditionMap = {
        'good': t('item.condition_good'),
        'damaged': t('item.condition_damaged'),
        'lost': t('item.condition_lost'),
        'withdrawn': t('item.condition_withdrawn')
      };
      return conditionMap[condition] || condition;
    };

    /**
     * Get translated status label
     */
    const getStatusLabel = (status) => {
      const statusMap = {
        'available': t('item.status_available'),
        'on_loan': t('item.status_on_loan'),
        'on_hold': t('item.status_on_hold'),
        'in_repair': t('item.status_in_repair'),
        'lost': t('item.status_lost'),
        'withdrawn': t('item.status_withdrawn')
      };
      return statusMap[status] || status;
    };

    /**
     * Handle delete item
     */
    const handleDeleteItem = async (item) => {
      if (!confirm(t('admin.confirm_delete_item', { item_id: item.item_id }) || `Delete item ${item.item_id}?`)) {
        return;
      }

      try {
        const response = await fetch(`/api/v1/catalog/items/${item.item_id}`, {
          method: 'DELETE'
        });

        if (!response.ok) {
          const apiError = await ApiError.fromResponse(response);
          handleError(apiError);
          return;
        }

        // Reload items after deletion
        if (props.record && props.record.id) {
          loadItems(props.record.id);
        }
      } catch (error) {
        console.error('Error deleting item:', error);
        handleError(error);
      }
    };

    // Helper functions for array fields
    const authorsText = computed({
      get: () => formData.value.authors.join(', '),
      set: (value) => {
        formData.value.authors = value.split(',').map(a => a.trim()).filter(a => a);
      }
    });

    const illustratorsText = computed({
      get: () => formData.value.illustrators.join(', '),
      set: (value) => {
        formData.value.illustrators = value.split(',').map(i => i.trim()).filter(i => i);
      }
    });

    const keywordsText = computed({
      get: () => formData.value.keywords.join(', '),
      set: (value) => {
        formData.value.keywords = value.split(',').map(k => k.trim()).filter(k => k);
      }
    });

    /**
     * Validate form data
     */
    const validateForm = () => {
      const newErrors = {};

      // Title is required
      if (!formData.value.title || formData.value.title.trim() === '') {
        newErrors.title = t('errors.required_field');
      }

      // Validate year range if provided
      if (formData.value.publication_year) {
        const year = parseInt(formData.value.publication_year);
        if (isNaN(year) || year < 1000 || year > 2100) {
          newErrors.publication_year = t('errors.invalid_year_range');
        }
      }

      // Validate page count if provided
      if (formData.value.page_count && formData.value.page_count < 0) {
        newErrors.page_count = t('errors.must_be_positive');
      }

      errors.value = newErrors;
      return Object.keys(newErrors).length === 0;
    };

    /**
     * Submit form
     */
    const handleSubmit = async () => {
      if (!validateForm()) {
        return;
      }

      isSubmitting.value = true;
      errors.value = {};

      try {
        // Prepare payload (convert empty strings to null for optional fields)
        const payload = {};
        Object.entries(formData.value).forEach(([key, value]) => {
          if (value === '' || value === null) {
            payload[key] = null;
          } else if (key === 'publication_year' || key === 'page_count') {
            payload[key] = value ? parseInt(value) : null;
          } else {
            payload[key] = value;
          }
        });

        const response = await fetch(`/api/v1/catalog/records/${props.record.id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorData = await response.json();

          if (response.status === 400) {
            // Validation error
            errors.value.general = errorData.detail || t('errors.validation_failed');
          } else {
            errors.value.general = errorData.detail || t('errors.unknown_error');
          }
          return;
        }

        const updatedRecord = await response.json();
        emit('saved', updatedRecord);
        closeModal();
      } catch (error) {
        console.error('Error updating record:', error);
        errors.value.general = t('errors.network_error');
      } finally {
        isSubmitting.value = false;
      }
    };

    /**
     * Close modal
     */
    const closeModal = () => {
      emit('update:show', false);
      errors.value = {};
      // Clean up any Bootstrap backdrop that may have been added
      const backdrop = document.querySelector('.modal-backdrop');
      if (backdrop) {
        backdrop.remove();
      }
    };

    /**
     * Cancel editing
     */
    const handleCancel = () => {
      closeModal();
    };

    /**
     * Handle delete button click
     */
    const handleDeleteClick = () => {
      showDeleteDialog.value = true;
    };

    /**
     * Handle delete confirmation
     */
    const handleDeleteConfirm = async (record_id) => {
      try {
        const response = await fetch(`/api/v1/catalog/records/${record_id}`, {
          method: 'DELETE'
        });

        if (!response.ok) {
          const errorData = await response.json();
          if (response.status === 400) {
            errors.value.general = errorData.detail;
          } else {
            errors.value.general = t('admin.error_delete_record');
          }
          showDeleteDialog.value = false;
          return;
        }

        // Success - emit deleted event and close both modals
        showDeleteDialog.value = false;
        emit('deleted', record_id);
        closeModal();
      } catch (error) {
        console.error('Error deleting record:', error);
        errors.value.general = t('errors.network_error');
        showDeleteDialog.value = false;
      }
    };

    return {
      formData,
      errors,
      isSubmitting,
      genreSuggestions,
      audienceOptions,
      languageOptions,
      mediumTypeSuggestions,
      bindingTypeOptions,
      authorsText,
      illustratorsText,
      keywordsText,
      handleSubmit,
      handleCancel,
      handleDeleteClick,
      handleDeleteConfirm,
      showDeleteDialog,
      // Items state & handlers
      items,
      loadingItems,
      showItemEditModal,
      editingItem,
      handleEditItem,
      handleItemSaved,
      getConditionLabel,
      getStatusLabel,
      handleDeleteItem,
      t
    };
  },
  template: `
    <div v-if="show" class="modal fade show d-block" data-testid="record-edit-modal" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" data-testid="modal-title">
              <i class="bi bi-pencil-square me-2"></i>
              {{ t('admin.edit_record') }}
            </h5>
            <button type="button" class="btn-close" data-testid="modal-close-button" @click="handleCancel" :disabled="isSubmitting"></button>
          </div>

          <div class="modal-body">
            <!-- Record Info -->
            <div class="alert alert-info mb-3">
              <h6 class="mb-1"><strong>{{ record.title }}</strong></h6>
              <p class="mb-0 small text-muted">
                <span v-if="record.authors">{{ Array.isArray(record.authors) ? record.authors.join(', ') : record.authors }}</span>
                <span v-if="record.isbn" class="ms-2">(ISBN: {{ record.isbn }})</span>
              </p>
            </div>

            <!-- General Error -->
            <div v-if="errors.general" class="alert alert-danger" data-testid="general-error">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              {{ errors.general }}
            </div>

            <form @submit.prevent="handleSubmit">
              <!-- Basic Information Section -->
              <h6 class="border-bottom pb-2 mb-3">
                <i class="bi bi-info-circle me-2"></i>{{ t('bibliographic.section_basic_info') }}
              </h6>

              <div class="row">
                <!-- Title -->
                <div class="col-md-8 mb-3">
                  <label for="title" class="form-label">
                    {{ t('bibliographic.title') }} *
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    :class="{ 'is-invalid': errors.title }"
                    id="title"
                    data-testid="input-title"
                    v-model="formData.title"
                    required
                  />
                  <div v-if="errors.title" class="invalid-feedback" data-testid="error-title">
                    {{ errors.title }}
                  </div>
                </div>

                <!-- ISBN -->
                <div class="col-md-4 mb-3">
                  <label for="isbn" class="form-label">
                    {{ t('bibliographic.isbn') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="isbn"
                    data-testid="input-isbn"
                    v-model="formData.isbn"
                    :placeholder="t('bibliographic.placeholder_isbn')"
                  />
                </div>
              </div>

              <!-- Subtitle -->
              <div class="mb-3">
                <label for="subtitle" class="form-label">
                  {{ t('bibliographic.subtitle') }}
                </label>
                <input
                  type="text"
                  class="form-control"
                  id="subtitle"
                  data-testid="input-subtitle"
                  v-model="formData.subtitle"
                />
              </div>

              <!-- Authors & Contributors Section -->
              <h6 class="border-bottom pb-2 mb-3 mt-4">
                <i class="bi bi-people me-2"></i>{{ t('bibliographic.section_authors') }}
              </h6>

              <div class="row">
                <!-- Authors -->
                <div class="col-md-6 mb-3">
                  <label for="authors" class="form-label">
                    {{ t('bibliographic.authors') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="authors"
                    data-testid="input-authors"
                    v-model="authorsText"
                    :placeholder="t('bibliographic.placeholder_authors')"
                  />
                  <small class="form-text text-muted">{{ t('bibliographic.help_authors') }}</small>
                </div>

                <!-- Illustrators -->
                <div class="col-md-6 mb-3">
                  <label for="illustrators" class="form-label">
                    {{ t('bibliographic.illustrators') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="illustrators"
                    data-testid="input-illustrators"
                    v-model="illustratorsText"
                    :placeholder="t('bibliographic.placeholder_illustrators')"
                  />
                  <small class="form-text text-muted">{{ t('bibliographic.help_illustrators') }}</small>
                </div>
              </div>

              <!-- Publication Information Section -->
              <h6 class="border-bottom pb-2 mb-3 mt-4">
                <i class="bi bi-building me-2"></i>{{ t('bibliographic.section_publication') }}
              </h6>

              <div class="row">
                <!-- Publisher -->
                <div class="col-md-6 mb-3">
                  <label for="publisher" class="form-label">
                    {{ t('bibliographic.publisher') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="publisher"
                    data-testid="input-publisher"
                    v-model="formData.publisher"
                  />
                </div>

                <!-- Publication Year -->
                <div class="col-md-6 mb-3">
                  <label for="publication-year" class="form-label">
                    {{ t('bibliographic.publication_year') }}
                  </label>
                  <input
                    type="number"
                    class="form-control"
                    :class="{ 'is-invalid': errors.publication_year }"
                    id="publication-year"
                    data-testid="input-publication-year"
                    v-model="formData.publication_year"
                    min="1000"
                    max="2100"
                  />
                  <div v-if="errors.publication_year" class="invalid-feedback" data-testid="error-publication-year">
                    {{ errors.publication_year }}
                  </div>
                </div>
              </div>

              <div class="row">
                <!-- Collection/Series -->
                <div class="col-md-8 mb-3">
                  <label for="collection" class="form-label">
                    {{ t('bibliographic.collection') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="collection"
                    data-testid="input-collection"
                    v-model="formData.collection"
                  />
                </div>

                <!-- Series Number -->
                <div class="col-md-4 mb-3">
                  <label for="series-number" class="form-label">
                    {{ t('bibliographic.series_number') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="series-number"
                    data-testid="input-series-number"
                    v-model="formData.series_number"
                    :placeholder="t('bibliographic.placeholder_series_number')"
                  />
                </div>
              </div>

              <!-- Classification Section -->
              <h6 class="border-bottom pb-2 mb-3 mt-4">
                <i class="bi bi-tags me-2"></i>{{ t('bibliographic.section_classification') }}
              </h6>

              <div class="row">
                <!-- Medium Type -->
                <div class="col-md-6 mb-3">
                  <label for="medium-type" class="form-label">
                    {{ t('bibliographic.medium_type') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="medium-type"
                    data-testid="input-medium-type"
                    v-model="formData.medium_type"
                    list="medium-type-suggestions"
                    :placeholder="t('bibliographic.placeholder_medium_type')"
                  />
                  <datalist id="medium-type-suggestions">
                    <option v-for="medium in mediumTypeSuggestions" :key="medium" :value="medium">
                      {{ medium }}
                    </option>
                  </datalist>
                  <small class="form-text text-muted">{{ t('bibliographic.medium_type_hint') || 'Type any value or select from suggestions' }}</small>
                </div>

                <!-- Genre -->
                <div class="col-md-6 mb-3">
                  <label for="genre" class="form-label">
                    {{ t('bibliographic.genre') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="genre"
                    data-testid="input-genre"
                    v-model="formData.genre"
                    list="genre-suggestions"
                    :placeholder="t('bibliographic.placeholder_genre')"
                  />
                  <datalist id="genre-suggestions">
                    <option v-for="genre in genreSuggestions" :key="genre" :value="genre">
                      {{ genre }}
                    </option>
                  </datalist>
                  <small class="form-text text-muted">{{ t('bibliographic.genre_hint') || 'Type any value or select from suggestions' }}</small>
                </div>
              </div>

              <div class="row">
                <!-- Target Audience -->
                <div class="col-md-4 mb-3">
                  <label for="target-audience" class="form-label">
                    {{ t('bibliographic.target_audience') }}
                  </label>
                  <select
                    class="form-select"
                    id="target-audience"
                    data-testid="select-target-audience"
                    v-model="formData.target_audience"
                  >
                    <option value="">— {{ t('common.select') }} —</option>
                    <option v-for="audience in audienceOptions" :key="audience.value" :value="audience.value">
                      {{ audience.label }}
                    </option>
                  </select>
                </div>

                <!-- Reading Level -->
                <div class="col-md-4 mb-3">
                  <label for="level" class="form-label">
                    {{ t('bibliographic.level') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="level"
                    data-testid="input-level"
                    v-model="formData.level"
                    :placeholder="t('bibliographic.placeholder_level')"
                  />
                </div>
              </div>

              <div class="row">
                <!-- Language -->
                <div class="col-md-6 mb-3">
                  <label for="language" class="form-label">
                    {{ t('bibliographic.language') }}
                  </label>
                  <select
                    class="form-select"
                    id="language"
                    data-testid="select-language"
                    v-model="formData.language"
                  >
                    <option value="">— {{ t('common.select') }} —</option>
                    <option v-for="lang in languageOptions" :key="lang.value" :value="lang.value">
                      {{ lang.label }}
                    </option>
                  </select>
                </div>

                <!-- Country Code -->
                <div class="col-md-6 mb-3">
                  <label for="country-code" class="form-label">
                    {{ t('bibliographic.country_code') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="country-code"
                    data-testid="input-country-code"
                    v-model="formData.country_code"
                    maxlength="5"
                    :placeholder="t('bibliographic.placeholder_country_code')"
                  />
                </div>
              </div>

              <!-- Physical Description Section -->
              <h6 class="border-bottom pb-2 mb-3 mt-4">
                <i class="bi bi-book me-2"></i>{{ t('bibliographic.section_physical') }}
              </h6>

              <div class="row">
                <!-- Binding Type -->
                <div class="col-md-4 mb-3">
                  <label for="binding-type" class="form-label">
                    {{ t('bibliographic.binding_type') }}
                  </label>
                  <select
                    class="form-select"
                    id="binding-type"
                    data-testid="select-binding-type"
                    v-model="formData.binding_type"
                  >
                    <option value="">— {{ t('common.select') }} —</option>
                    <option v-for="binding in bindingTypeOptions" :key="binding.value" :value="binding.value">
                      {{ binding.label }}
                    </option>
                  </select>
                </div>

                <!-- Page Count -->
                <div class="col-md-4 mb-3">
                  <label for="page-count" class="form-label">
                    {{ t('bibliographic.page_count') }}
                  </label>
                  <input
                    type="number"
                    class="form-control"
                    :class="{ 'is-invalid': errors.page_count }"
                    id="page-count"
                    data-testid="input-page-count"
                    v-model="formData.page_count"
                    min="0"
                  />
                  <div v-if="errors.page_count" class="invalid-feedback" data-testid="error-page-count">
                    {{ errors.page_count }}
                  </div>
                </div>

                <!-- Has Illustrations -->
                <div class="col-md-4 mb-3">
                  <label class="form-label d-block">
                    {{ t('bibliographic.has_illustrations') }}
                  </label>
                  <div class="form-check form-check-inline mt-2">
                    <input
                      type="checkbox"
                      class="form-check-input"
                      id="has-illustrations"
                      data-testid="checkbox-has-illustrations"
                      v-model="formData.has_illustrations"
                    />
                    <label class="form-check-label" for="has-illustrations">
                      {{ t('common.yes') }}
                    </label>
                  </div>
                </div>
              </div>

              <div class="row">
                <!-- Dimensions -->
                <div class="col-md-6 mb-3">
                  <label for="dimensions" class="form-label">
                    {{ t('bibliographic.dimensions') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="dimensions"
                    data-testid="input-dimensions"
                    v-model="formData.dimensions"
                    :placeholder="t('bibliographic.placeholder_dimensions')"
                  />
                </div>

                <!-- Physical Size -->
                <div class="col-md-6 mb-3">
                  <label for="physical-size" class="form-label">
                    {{ t('bibliographic.physical_size') }}
                  </label>
                  <input
                    type="text"
                    class="form-control"
                    id="physical-size"
                    data-testid="input-physical-size"
                    v-model="formData.physical_size"
                    :placeholder="t('bibliographic.placeholder_physical_description')"
                  />
                </div>
              </div>

              <!-- Content Description Section -->
              <h6 class="border-bottom pb-2 mb-3 mt-4">
                <i class="bi bi-card-text me-2"></i>{{ t('bibliographic.section_content') }}
              </h6>

              <!-- Keywords -->
              <div class="mb-3">
                <label for="keywords" class="form-label">
                  {{ t('bibliographic.keywords') }}
                </label>
                <input
                  type="text"
                  class="form-control"
                  id="keywords"
                  data-testid="input-keywords"
                  v-model="keywordsText"
                  :placeholder="t('bibliographic.placeholder_keywords')"
                />
                <small class="form-text text-muted">{{ t('bibliographic.help_keywords') }}</small>
              </div>

              <!-- Description -->
              <div class="mb-3">
                <label for="description" class="form-label">
                  {{ t('bibliographic.description') }}
                </label>
                <textarea
                  class="form-control"
                  id="description"
                  data-testid="textarea-description"
                  v-model="formData.description"
                  rows="4"
                  :placeholder="t('bibliographic.placeholder_description')"
                ></textarea>
              </div>

              <!-- Items (Exemplaires) Section -->
              <h6 class="border-bottom pb-2 mb-3 mt-4">
                <i class="bi bi-layers me-2"></i>{{ t('catalog.copies') }} ({{ items.length }})
              </h6>

              <div v-if="loadingItems" class="text-center py-3">
                <div class="spinner-border spinner-border-sm me-2"></div>
                {{ t('common.loading') }}...
              </div>

              <div v-else-if="items.length === 0" class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                {{ t('catalog.no_items') || 'No physical items found for this record' }}
              </div>

              <div v-else class="table-responsive">
                <table class="table table-sm table-hover">
                  <thead>
                    <tr>
                      <th>{{ t('catalog.item_id') }}</th>
                      <th>{{ t('catalog.shelf_location') }}</th>
                      <th>{{ t('catalog.call_number') }}</th>
                      <th>{{ t('catalog.status') }}</th>
                      <th>{{ t('catalog.condition') }}</th>
                      <th>{{ t('common.actions') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in items" :key="item.id">
                      <td><code class="small">{{ item.item_id }}</code></td>
                      <td>{{ item.shelf_location || '—' }}</td>
                      <td class="text-muted">{{ item.call_number || '—' }}</td>
                      <td>
                        <span class="badge" :class="{
                          'bg-success': item.status === 'available',
                          'bg-warning': item.status === 'on_loan',
                          'bg-info': item.status === 'on_hold',
                          'bg-primary': item.status === 'in_repair',
                          'bg-danger': item.status === 'lost',
                          'bg-dark': item.status === 'withdrawn',
                          'bg-secondary': !['available', 'on_loan', 'on_hold', 'in_repair', 'lost', 'withdrawn'].includes(item.status)
                        }">
                          {{ getStatusLabel(item.status) }}
                        </span>
                      </td>
                      <td>{{ getConditionLabel(item.condition) }}</td>
                      <td>
                        <button
                          type="button"
                          class="btn btn-sm btn-outline-primary me-1"
                          @click.stop="handleEditItem(item)"
                          :title="t('common.edit')"
                        >
                          <i class="bi bi-pencil"></i>
                        </button>
                        <button
                          type="button"
                          class="btn btn-sm btn-outline-danger"
                          @click.stop="handleDeleteItem(item)"
                          :title="t('common.delete')"
                        >
                          <i class="bi bi-trash"></i>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </form>
          </div>

          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-danger me-auto"
              data-testid="button-delete"
              @click="handleDeleteClick"
              :disabled="isSubmitting"
            >
              <i class="bi bi-trash me-1"></i>
              {{ t('common.delete') }}
            </button>
            <button
              type="button"
              class="btn btn-secondary"
              data-testid="button-cancel"
              @click="handleCancel"
              :disabled="isSubmitting"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              type="button"
              class="btn btn-primary"
              data-testid="button-save"
              @click="handleSubmit"
              :disabled="isSubmitting"
            >
              <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" data-testid="saving-spinner"></span>
              {{ isSubmitting ? t('common.saving') : t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Item Edit Modal -->
    <item-edit-form
      v-if="editingItem"
      :show="showItemEditModal"
      :item="editingItem"
      @update:show="showItemEditModal = $event"
      @saved="handleItemSaved"
    />

    <!-- Record Delete Dialog -->
    <record-delete-dialog
      v-if="record"
      :show="showDeleteDialog"
      :record-data="{ id: record.id, title: record.title, authors: record.authors, isbn: record.isbn, items: items }"
      @close="showDeleteDialog = false"
      @confirm="handleDeleteConfirm"
    />
  `
};
