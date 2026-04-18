/**
 * BorrowerEditForm.js
 *
 * Modal form for editing a single borrower's information.
 * Supports updating: borrower ID, name, role, class assignment, and contact info.
 *
 * User Story 4 from specs/006-admin-features/spec.md:
 * - Edit individual borrower details (name, ID, role, class)
 * - Validate borrower ID uniqueness and format
 * - Update full_name automatically when first/last name changes
 */

const { ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import BorrowerDeleteDialog from './BorrowerDeleteDialog.js';

export default {
  name: 'BorrowerEditForm',
  components: {
    BorrowerDeleteDialog
  },
  props: {
    borrower: {
      type: Object,
      required: false,
      default: null
    },
    show: {
      type: Boolean,
      required: true
    }
  },
  emits: ['update:show', 'saved', 'deleted'],
  setup(props, { emit }) {
    const { t } = useI18n();

    // Form data
    const formData = ref({
      borrower_id: '',
      first_name: '',
      last_name: '',
      role: 'student',
      class_id: null,
      email: '',
      phone: '',
      notes: ''
    });

    const errors = ref({});
    const isSubmitting = ref(false);
    const classes = ref([]);
    const isLoadingClasses = ref(false);
    const showDeleteDialog = ref(false);

    // Load form data when borrower prop changes
    watch(() => props.borrower, (newBorrower) => {
      if (newBorrower) {
        formData.value = {
          borrower_id: newBorrower.borrower_id || '',
          first_name: newBorrower.first_name || '',
          last_name: newBorrower.last_name || '',
          role: newBorrower.role || 'student',
          class_id: newBorrower.class_id || null,
          email: newBorrower.email || '',
          phone: newBorrower.phone || '',
          notes: newBorrower.notes || ''
        };
        errors.value = {};
      }
    }, { immediate: true });

    // Load classes when modal opens
    watch(() => props.show, async (show) => {
      if (show) {
        await loadClasses();
      }
    }, { immediate: true });

    /**
     * Load available classes from API
     */
    const loadClasses = async () => {
      isLoadingClasses.value = true;
      try {
        const response = await fetch('/api/v1/classes?limit=500');
        if (!response.ok) {
          throw new Error('Failed to load classes');
        }
        const data = await response.json();
        classes.value = data;
      } catch (error) {
        console.error('Error loading classes:', error);
        classes.value = [];
      } finally {
        isLoadingClasses.value = false;
      }
    };

    /**
     * Validate form data
     */
    const validateForm = () => {
      const newErrors = {};

      if (!formData.value.first_name || formData.value.first_name.trim() === '') {
        newErrors.first_name = t('admin.borrower.validation.first_name_required');
      }

      if (!formData.value.last_name || formData.value.last_name.trim() === '') {
        newErrors.last_name = t('admin.borrower.validation.last_name_required');
      }

      if (!formData.value.borrower_id || formData.value.borrower_id.trim() === '') {
        newErrors.borrower_id = t('admin.borrower.validation.borrower_id_required');
      }

      if (!formData.value.role) {
        newErrors.role = t('admin.borrower.validation.role_required');
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
        const response = await fetch(`/api/v1/borrowers/${props.borrower.borrower_id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(formData.value)
        });

        if (!response.ok) {
          const errorData = await response.json();

          // Handle specific error cases
          if (response.status === 409) {
            // Duplicate borrower ID
            errors.value.borrower_id = t('errors.BORROWER_ID_NOT_AVAILABLE');
          } else if (response.status === 400) {
            // Validation error (invalid ID format or role)
            if (errorData.detail && errorData.detail.includes('borrower_id')) {
              errors.value.borrower_id = errorData.detail;
            } else if (errorData.detail && errorData.detail.includes('role')) {
              errors.value.role = errorData.detail;
            } else {
              errors.value.general = errorData.detail || t('admin.borrower.edit.error');
            }
          } else {
            errors.value.general = errorData.detail || t('admin.borrower.edit.error');
          }
          return;
        }

        const updatedBorrower = await response.json();
        emit('saved', updatedBorrower);
        closeModal();
      } catch (error) {
        console.error('Error updating borrower:', error);
        errors.value.general = t('admin.borrower.edit.error');
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
     * Get role display name
     */
    const getRoleDisplayName = (role) => {
      const roleMap = {
        'student': t('borrower.role_student'),
        'teacher': t('borrower.role_teacher'),
        'staff': t('borrower.role_staff')
      };
      return roleMap[role] || role;
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
    const handleDeleteConfirm = async (borrower_id) => {
      try {
        const response = await fetch(`/api/v1/borrowers/${borrower_id}`, {
          method: 'DELETE'
        });

        if (!response.ok) {
          const errorData = await response.json();
          if (response.status === 400) {
            errors.value.general = errorData.detail;
          } else {
            errors.value.general = t('admin.error_delete_borrower');
          }
          showDeleteDialog.value = false;
          return;
        }

        // Success - emit deleted event and close both modals
        showDeleteDialog.value = false;
        emit('deleted', borrower_id);
        closeModal();
      } catch (error) {
        console.error('Error deleting borrower:', error);
        errors.value.general = t('errors.network_error');
        showDeleteDialog.value = false;
      }
    };

    return {
      formData,
      errors,
      isSubmitting,
      classes,
      isLoadingClasses,
      showDeleteDialog,
      handleSubmit,
      handleCancel,
      handleDeleteClick,
      handleDeleteConfirm,
      getRoleDisplayName,
      t
    };
  },
  template: `
    <div v-if="show" class="modal fade show d-block" data-testid="borrower-edit-modal" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" data-testid="modal-title">
              <i class="bi bi-pencil-square me-2"></i>
              {{ t('admin.borrower.edit.title') }}
            </h5>
            <button type="button" class="btn-close" data-testid="modal-close-button" @click="handleCancel" :disabled="isSubmitting"></button>
          </div>

          <div class="modal-body">
            <!-- General Error -->
            <div v-if="errors.general" class="alert alert-danger" data-testid="general-error">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              {{ errors.general }}
            </div>

            <form @submit.prevent="handleSubmit">
              <!-- Borrower ID -->
              <div class="mb-3">
                <label for="borrower-id" class="form-label">
                  {{ t('admin.borrower.edit.borrower_id') }} *
                </label>
                <input
                  type="text"
                  class="form-control"
                  :class="{ 'is-invalid': errors.borrower_id }"
                  id="borrower-id"
                  data-testid="input-borrower-id"
                  v-model="formData.borrower_id"
                  :placeholder="t('admin.borrower.edit.borrower_id_placeholder')"
                  required
                />
                <div v-if="errors.borrower_id" class="invalid-feedback" data-testid="error-borrower-id">
                  {{ errors.borrower_id }}
                </div>
                <small class="form-text text-muted">
                  {{ t('admin.borrower.edit.borrower_id_help') }}
                </small>
              </div>

              <!-- First Name -->
              <div class="mb-3">
                <label for="first-name" class="form-label">
                  {{ t('admin.borrower.edit.first_name') }} *
                </label>
                <input
                  type="text"
                  class="form-control"
                  :class="{ 'is-invalid': errors.first_name }"
                  id="first-name"
                  data-testid="input-first-name"
                  v-model="formData.first_name"
                  :placeholder="t('admin.borrower.edit.first_name_placeholder')"
                  required
                />
                <div v-if="errors.first_name" class="invalid-feedback" data-testid="error-first-name">
                  {{ errors.first_name }}
                </div>
              </div>

              <!-- Last Name -->
              <div class="mb-3">
                <label for="last-name" class="form-label">
                  {{ t('admin.borrower.edit.last_name') }} *
                </label>
                <input
                  type="text"
                  class="form-control"
                  :class="{ 'is-invalid': errors.last_name }"
                  id="last-name"
                  data-testid="input-last-name"
                  v-model="formData.last_name"
                  :placeholder="t('admin.borrower.edit.last_name_placeholder')"
                  required
                />
                <div v-if="errors.last_name" class="invalid-feedback" data-testid="error-last-name">
                  {{ errors.last_name }}
                </div>
              </div>

              <!-- Role -->
              <div class="mb-3">
                <label for="role" class="form-label">
                  {{ t('admin.borrower.edit.role') }} *
                </label>
                <select
                  class="form-select"
                  :class="{ 'is-invalid': errors.role }"
                  id="role"
                  data-testid="select-role"
                  v-model="formData.role"
                  required
                >
                  <option value="student">{{ getRoleDisplayName('student') }}</option>
                  <option value="teacher">{{ getRoleDisplayName('teacher') }}</option>
                  <option value="staff">{{ getRoleDisplayName('staff') }}</option>
                </select>
                <div v-if="errors.role" class="invalid-feedback" data-testid="error-role">
                  {{ errors.role }}
                </div>
              </div>

              <!-- Class -->
              <div class="mb-3">
                <label for="class" class="form-label">
                  {{ t('admin.borrower.edit.class') }}
                </label>
                <select
                  class="form-select"
                  :class="{ 'is-invalid': errors.class_id }"
                  id="class"
                  data-testid="select-class"
                  v-model="formData.class_id"
                  :disabled="isLoadingClasses"
                >
                  <option :value="null">{{ t('admin.borrower.edit.no_class') }}</option>
                  <option v-for="cls in classes" :key="cls.id" :value="cls.id">
                    {{ cls.name }}{{ cls.homeroom_teacher ? ' (' + cls.homeroom_teacher + ')' : '' }}
                  </option>
                </select>
                <div v-if="errors.class_id" class="invalid-feedback" data-testid="error-class-id">
                  {{ errors.class_id }}
                </div>
                <small v-if="formData.role === 'student'" class="form-text text-muted">
                  {{ t('admin.borrower.edit.class_help_student') }}
                </small>
              </div>

              <!-- Email -->
              <div class="mb-3">
                <label for="email" class="form-label">
                  {{ t('admin.borrower.edit.email') }}
                </label>
                <input
                  type="email"
                  class="form-control"
                  :class="{ 'is-invalid': errors.email }"
                  id="email"
                  data-testid="input-email"
                  v-model="formData.email"
                  :placeholder="t('admin.borrower.edit.email_placeholder')"
                />
                <div v-if="errors.email" class="invalid-feedback" data-testid="error-email">
                  {{ errors.email }}
                </div>
              </div>

              <!-- Phone -->
              <div class="mb-3">
                <label for="phone" class="form-label">
                  {{ t('admin.borrower.edit.phone') }}
                </label>
                <input
                  type="tel"
                  class="form-control"
                  :class="{ 'is-invalid': errors.phone }"
                  id="phone"
                  data-testid="input-phone"
                  v-model="formData.phone"
                  :placeholder="t('admin.borrower.edit.phone_placeholder')"
                />
                <div v-if="errors.phone" class="invalid-feedback" data-testid="error-phone">
                  {{ errors.phone }}
                </div>
              </div>

              <!-- Notes -->
              <div class="mb-3">
                <label for="notes" class="form-label">
                  {{ t('admin.borrower.edit.notes') }}
                </label>
                <textarea
                  class="form-control"
                  :class="{ 'is-invalid': errors.notes }"
                  id="notes"
                  data-testid="input-notes"
                  v-model="formData.notes"
                  rows="3"
                  :placeholder="t('admin.borrower.edit.notes_placeholder')"
                ></textarea>
                <div v-if="errors.notes" class="invalid-feedback" data-testid="error-notes">
                  {{ errors.notes }}
                </div>
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

    <!-- Delete Confirmation Dialog -->
    <borrower-delete-dialog
      v-if="borrower"
      :show="showDeleteDialog"
      :borrower-data="borrower"
      @close="showDeleteDialog = false"
      @confirm="handleDeleteConfirm"
    />
  `
};
