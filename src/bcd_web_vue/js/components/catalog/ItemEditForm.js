/**
 * ItemEditForm.js
 *
 * Modal form for editing a single physical item.
 * Supports updating: barcode, call_number, shelf_location, condition, status, loanable, acquisition_date, funding_source
 *
 * User Story 6 from specs/006-admin-features/spec.md:
 * - Edit individual item details
 * - Validate barcode uniqueness
 * - Client-side duplicate barcode detection
 */

const { ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import DeweyPicker from '../ui/DeweyPicker.js';
import ShelfLocationPicker from '../ui/ShelfLocationPicker.js';
import Modal from '../ui/Modal.js';
import { useAppState } from '../../composables/useAppState.js';
import { apiClient } from '../../api/client.js';

export default {
  name: 'ItemEditForm',
  components: { DeweyPicker, ShelfLocationPicker, Modal },
  props: {
    item: {
      type: Object,
      required: true
    },
    show: {
      type: Boolean,
      required: true
    }
  },
  emits: ['update:show', 'saved'],
  setup(props, { emit }) {
    const { t } = useI18n();
    const { settings } = useAppState();

    const deweyColors = computed(() => {
      try { return JSON.parse(settings.value?.dewey_colors || 'null') || undefined; }
      catch { return undefined; }
    });

    const shelfLocationOptions = computed(() => {
      try { return JSON.parse(settings.value?.catalog_shelf_locations || '[]') || []; }
      catch { return []; }
    });

    // Form data
    const formData = ref({
      barcode: '',
      call_number: '',
      shelf_location: '',
      condition: 'good',
      status: 'available',
      loanable: true,
      acquisition_date: '',
      funding_source: ''
    });

    const errors = ref({});
    const isSubmitting = ref(false);

    // Status options (from ItemStatus enum)
    const statusOptions = [
      { value: 'available', label: t('item.status_available') },
      { value: 'on_loan', label: t('item.status_on_loan') },
      { value: 'on_hold', label: t('item.status_on_hold') },
      { value: 'in_repair', label: t('item.status_in_repair') },
      { value: 'lost', label: t('item.status_lost') },
      { value: 'withdrawn', label: t('item.status_withdrawn') }
    ];

    // Condition options - physical state only (lost/withdrawn are status, not condition)
    const conditionOptions = [
      { value: 'good', label: t('item.condition_good') || 'Good' },
      { value: 'damaged', label: t('item.condition_damaged') || 'Damaged' }
    ];

    // Load form data when item prop changes
    watch(() => props.item, (newItem) => {
      if (newItem) {
        console.log('ItemEditForm: Loading item data:', newItem);
        formData.value = {
          barcode: newItem.item_id,
          call_number: newItem.call_number || '',
          shelf_location: newItem.shelf_location || '',
          condition: newItem.condition || 'good',
          status: newItem.status || 'available',
          loanable: newItem.loanable !== undefined ? newItem.loanable : true,
          acquisition_date: newItem.acquisition_date || '',
          funding_source: newItem.funding_source || ''
        };
        errors.value = {};
      }
    }, { immediate: true });

    /**
     * Validate form data
     */
    const validateForm = () => {
      const newErrors = {};

      // Barcode is required
      if (!formData.value.barcode || formData.value.barcode.trim() === '') {
        newErrors.barcode = t('errors.required_field');
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
        // Prepare payload - exclude barcode (item_id is immutable)
        const payload = {
          call_number: formData.value.call_number || null,
          shelf_location: formData.value.shelf_location || null,
          condition: formData.value.condition,
          status: formData.value.status,
          loanable: formData.value.loanable,
          acquisition_date: formData.value.acquisition_date || null,
          funding_source: formData.value.funding_source || null
        };

        // Use item_id (barcode) in URL, not database id
        const updatedItem = await apiClient.patch(`/catalog/items/${props.item.item_id}`, payload);

        emit('saved', updatedItem);
        closeModal();
      } catch (error) {
        console.error('Error updating item:', error);
        if (error.statusCode === 409) {
          // Duplicate barcode
          errors.value.barcode = t('errors.DUPLICATE_BARCODE', {
            barcode: formData.value.barcode,
            existing_item_id: error.details?.existing_item_id || '?'
          });
        } else if (error.statusCode === 400) {
          // Validation error
          errors.value.general = error.message || t('errors.validation_failed');
        } else {
          errors.value.general = error.message || t('errors.unknown_error');
        }
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
    };

    /**
     * Cancel editing
     */
    const handleCancel = () => {
      closeModal();
    };

    return {
      formData,
      errors,
      isSubmitting,
      statusOptions,
      conditionOptions,
      deweyColors,
      shelfLocationOptions,
      handleSubmit,
      handleCancel,
      t
    };
  },
  template: `
    <modal :show="show" size="lg" @close="handleCancel">
      <template #header>
        <i class="bi bi-pencil-square me-2"></i>
        {{ t('admin.edit_item') }}
      </template>
            <!-- Item Info -->
            <div class="alert alert-info mb-3">
              <p class="mb-0">
                <strong>{{ t('cataloging.item_barcode_label') }}:</strong> <code>{{ item.item_id }}</code>
              </p>
            </div>

            <!-- General Error -->
            <div v-if="errors.general" class="alert alert-danger" data-testid="general-error">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              {{ errors.general }}
            </div>

            <form @submit.prevent="handleSubmit">
              <!-- Barcode (Read-only - cannot be changed) -->
              <div class="mb-3">
                <label for="barcode" class="form-label">
                  {{ t('cataloging.item_barcode_label') }}
                </label>
                <input
                  type="text"
                  class="form-control"
                  id="barcode"
                  data-testid="input-barcode"
                  v-model="formData.barcode"
                  disabled
                  readonly
                />
                <small class="form-text text-muted">
                  {{ t('catalog.barcode_immutable') || 'Barcode cannot be changed after creation' }}
                </small>
              </div>

              <!-- Call Number -->
              <div class="mb-3">
                <label class="form-label">{{ t('catalog.call_number') }}</label>
                <dewey-picker
                  v-model="formData.call_number"
                  :colors="deweyColors"
                  data-testid="input-call-number"
                />
                <div v-if="errors.call_number" class="text-danger small mt-1" data-testid="error-call-number">
                  {{ errors.call_number }}
                </div>
              </div>

              <!-- Shelf Location -->
              <div class="mb-3">
                <label class="form-label">{{ t('catalog.shelf_location') }}</label>
                <shelf-location-picker
                  v-model="formData.shelf_location"
                  :locations="shelfLocationOptions"
                  data-testid="input-shelf-location"
                />
                <div v-if="errors.shelf_location" class="text-danger small mt-1" data-testid="error-shelf-location">
                  {{ errors.shelf_location }}
                </div>
              </div>

              <!-- Condition -->
              <div class="mb-3">
                <label for="condition" class="form-label">
                  {{ t('catalog.condition') }}
                </label>
                <select
                  class="form-select"
                  :class="{ 'is-invalid': errors.condition }"
                  id="condition"
                  data-testid="select-condition"
                  v-model="formData.condition"
                >
                  <option v-for="cond in conditionOptions" :key="cond.value" :value="cond.value">
                    {{ cond.label }}
                  </option>
                </select>
                <div v-if="errors.condition" class="invalid-feedback" data-testid="error-condition">
                  {{ errors.condition }}
                </div>
              </div>

              <!-- Status -->
              <div class="mb-3">
                <label for="status" class="form-label">
                  {{ t('catalog.status') }}
                </label>
                <select
                  class="form-select"
                  :class="{ 'is-invalid': errors.status }"
                  id="status"
                  data-testid="select-status"
                  v-model="formData.status"
                >
                  <option v-for="stat in statusOptions" :key="stat.value" :value="stat.value">
                    {{ stat.label }}
                  </option>
                </select>
                <div v-if="errors.status" class="invalid-feedback" data-testid="error-status">
                  {{ errors.status }}
                </div>
              </div>

              <!-- Loanable -->
              <div class="mb-3">
                <div class="form-check">
                  <input
                    type="checkbox"
                    class="form-check-input"
                    id="loanable"
                    data-testid="checkbox-loanable"
                    v-model="formData.loanable"
                  />
                  <label class="form-check-label" for="loanable">
                    {{ t('catalog.loanable') || 'Can be borrowed' }}
                  </label>
                </div>
                <small class="form-text text-muted">
                  {{ t('catalog.loanable_help') || 'Uncheck for reference-only items that cannot be borrowed (e.g., encyclopedias, rare books)' }}
                </small>
              </div>

              <!-- Acquisition Date -->
              <div class="mb-3">
                <label for="acquisition-date" class="form-label">
                  {{ t('catalog.acquisition_date') }}
                </label>
                <input
                  type="date"
                  class="form-control"
                  :class="{ 'is-invalid': errors.acquisition_date }"
                  id="acquisition-date"
                  data-testid="input-acquisition-date"
                  v-model="formData.acquisition_date"
                />
                <div v-if="errors.acquisition_date" class="invalid-feedback" data-testid="error-acquisition-date">
                  {{ errors.acquisition_date }}
                </div>
              </div>

              <!-- Funding Source -->
              <div class="mb-3">
                <label for="funding-source" class="form-label">
                  {{ t('catalog.funding_source') }}
                </label>
                <input
                  type="text"
                  class="form-control"
                  :class="{ 'is-invalid': errors.funding_source }"
                  id="funding-source"
                  data-testid="input-funding-source"
                  v-model="formData.funding_source"
                  :placeholder="t('catalog.placeholder_funding_source')"
                />
                <div v-if="errors.funding_source" class="invalid-feedback" data-testid="error-funding-source">
                  {{ errors.funding_source }}
                </div>
              </div>
            </form>

      <template #footer>
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
      </template>
    </modal>
  `
};
