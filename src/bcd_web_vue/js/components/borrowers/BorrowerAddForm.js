/**
 * BorrowerAddForm.js
 *
 * Modal form for adding a new borrower.
 * Pre-fills the borrower ID with the smallest available ID so that IDs
 * freed when students leave (e.g., CM2 deletion at year-end) are reused.
 */

const { ref, watch } = Vue;
const { useI18n } = VueI18n;

export default {
  name: 'BorrowerAddForm',
  props: {
    show: {
      type: Boolean,
      required: true
    }
  },
  emits: ['update:show', 'created'],
  setup(props, { emit }) {
    const { t } = useI18n();

    const defaultForm = () => ({
      borrower_id: '',
      first_name: '',
      last_name: '',
      role: 'student',
      class_id: null,
      email: '',
      phone: '',
      notes: ''
    });

    const formData = ref(defaultForm());
    const errors = ref({});
    const isSubmitting = ref(false);
    const classes = ref([]);
    const isLoadingClasses = ref(false);
    const isLoadingNextId = ref(false);

    /**
     * Load available classes from API
     */
    const loadClasses = async () => {
      isLoadingClasses.value = true;
      try {
        const response = await fetch('/api/v1/classes?limit=500');
        if (!response.ok) throw new Error('Failed to load classes');
        classes.value = await response.json();
      } catch (error) {
        console.error('Error loading classes:', error);
        classes.value = [];
      } finally {
        isLoadingClasses.value = false;
      }
    };

    /**
     * Fetch the smallest available borrower ID and pre-fill the field
     */
    const loadNextAvailableId = async () => {
      isLoadingNextId.value = true;
      try {
        const response = await fetch('/api/v1/borrowers/next-available-id');
        if (!response.ok) throw new Error('Failed to load next ID');
        const data = await response.json();
        formData.value.borrower_id = data.next_id;
      } catch (error) {
        console.error('Error loading next available ID:', error);
      } finally {
        isLoadingNextId.value = false;
      }
    };

    // When modal opens: reset form, load classes and next available ID
    watch(() => props.show, async (show) => {
      if (show) {
        formData.value = defaultForm();
        errors.value = {};
        await Promise.all([loadClasses(), loadNextAvailableId()]);
      }
    });

    /**
     * Validate form data client-side
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
     * Submit the form to create a new borrower
     */
    const handleSubmit = async () => {
      if (!validateForm()) return;

      isSubmitting.value = true;
      errors.value = {};

      try {
        const response = await fetch('/api/v1/borrowers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData.value)
        });

        if (!response.ok) {
          const errorData = await response.json();
          if (response.status === 409) {
            errors.value.borrower_id = t('errors.BORROWER_ID_NOT_AVAILABLE');
          } else if (response.status === 400) {
            if (errorData.detail && errorData.detail.includes('borrower_id')) {
              errors.value.borrower_id = errorData.detail;
            } else if (errorData.detail && errorData.detail.includes('role')) {
              errors.value.role = errorData.detail;
            } else {
              errors.value.general = errorData.detail || t('admin.borrower.add.error');
            }
          } else {
            errors.value.general = errorData.detail || t('admin.borrower.add.error');
          }
          return;
        }

        const newBorrower = await response.json();
        emit('created', newBorrower);
        closeModal();
      } catch (error) {
        console.error('Error creating borrower:', error);
        errors.value.general = t('admin.borrower.add.error');
      } finally {
        isSubmitting.value = false;
      }
    };

    const closeModal = () => {
      emit('update:show', false);
      errors.value = {};
      // Clean up any Bootstrap backdrop that may have been added
      const backdrop = document.querySelector('.modal-backdrop');
      if (backdrop) {
        backdrop.remove();
      }
    };

    const getRoleDisplayName = (role) => {
      const roleMap = {
        'student': t('borrower.role_student'),
        'teacher': t('borrower.role_teacher'),
        'staff': t('borrower.role_staff')
      };
      return roleMap[role] || role;
    };

    return {
      formData,
      errors,
      isSubmitting,
      classes,
      isLoadingClasses,
      isLoadingNextId,
      handleSubmit,
      closeModal,
      getRoleDisplayName,
      t
    };
  },
  template: `
    <div v-if="show" class="modal fade show d-block" data-testid="borrower-add-modal" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" data-testid="modal-title">
              <i class="bi bi-person-plus me-2"></i>
              {{ t('admin.borrower.add.title') }}
            </h5>
            <button type="button" class="btn-close" data-testid="modal-close-button" @click="closeModal" :disabled="isSubmitting"></button>
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
                <label for="add-borrower-id" class="form-label">
                  {{ t('admin.borrower.edit.borrower_id') }} *
                </label>
                <div class="input-group">
                  <input
                    type="text"
                    class="form-control"
                    :class="{ 'is-invalid': errors.borrower_id }"
                    id="add-borrower-id"
                    data-testid="input-borrower-id"
                    v-model="formData.borrower_id"
                    :placeholder="isLoadingNextId ? t('admin.borrower.add.next_id_loading') : t('admin.borrower.edit.borrower_id_placeholder')"
                    :disabled="isLoadingNextId"
                    required
                  />
                  <span v-if="isLoadingNextId" class="input-group-text">
                    <span class="spinner-border spinner-border-sm"></span>
                  </span>
                </div>
                <div v-if="errors.borrower_id" class="invalid-feedback d-block" data-testid="error-borrower-id">
                  {{ errors.borrower_id }}
                </div>
                <small class="form-text text-muted">
                  {{ t('admin.borrower.add.next_id_help') }}
                </small>
              </div>

              <!-- First Name -->
              <div class="mb-3">
                <label for="add-first-name" class="form-label">
                  {{ t('admin.borrower.edit.first_name') }} *
                </label>
                <input
                  type="text"
                  class="form-control"
                  :class="{ 'is-invalid': errors.first_name }"
                  id="add-first-name"
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
                <label for="add-last-name" class="form-label">
                  {{ t('admin.borrower.edit.last_name') }} *
                </label>
                <input
                  type="text"
                  class="form-control"
                  :class="{ 'is-invalid': errors.last_name }"
                  id="add-last-name"
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
                <label for="add-role" class="form-label">
                  {{ t('admin.borrower.edit.role') }} *
                </label>
                <select
                  class="form-select"
                  :class="{ 'is-invalid': errors.role }"
                  id="add-role"
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
                <label for="add-class" class="form-label">
                  {{ t('admin.borrower.edit.class') }}
                </label>
                <select
                  class="form-select"
                  id="add-class"
                  data-testid="select-class"
                  v-model="formData.class_id"
                  :disabled="isLoadingClasses"
                >
                  <option :value="null">{{ t('admin.borrower.edit.no_class') }}</option>
                  <option v-for="cls in classes" :key="cls.id" :value="cls.id">
                    {{ cls.name }}{{ cls.homeroom_teacher ? ' (' + cls.homeroom_teacher + ')' : '' }}
                  </option>
                </select>
                <small v-if="formData.role === 'student'" class="form-text text-muted">
                  {{ t('admin.borrower.edit.class_help_student') }}
                </small>
              </div>

              <!-- Email -->
              <div class="mb-3">
                <label for="add-email" class="form-label">
                  {{ t('admin.borrower.edit.email') }}
                </label>
                <input
                  type="email"
                  class="form-control"
                  id="add-email"
                  data-testid="input-email"
                  v-model="formData.email"
                  :placeholder="t('admin.borrower.edit.email_placeholder')"
                />
              </div>

              <!-- Phone -->
              <div class="mb-3">
                <label for="add-phone" class="form-label">
                  {{ t('admin.borrower.edit.phone') }}
                </label>
                <input
                  type="tel"
                  class="form-control"
                  id="add-phone"
                  data-testid="input-phone"
                  v-model="formData.phone"
                  :placeholder="t('admin.borrower.edit.phone_placeholder')"
                />
              </div>

              <!-- Notes -->
              <div class="mb-3">
                <label for="add-notes" class="form-label">
                  {{ t('admin.borrower.edit.notes') }}
                </label>
                <textarea
                  class="form-control"
                  id="add-notes"
                  data-testid="input-notes"
                  v-model="formData.notes"
                  rows="3"
                  :placeholder="t('admin.borrower.edit.notes_placeholder')"
                ></textarea>
              </div>
            </form>
          </div>

          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-testid="button-cancel"
              @click="closeModal"
              :disabled="isSubmitting"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              type="button"
              class="btn btn-primary"
              data-testid="button-save"
              @click="handleSubmit"
              :disabled="isSubmitting || isLoadingNextId"
            >
              <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" data-testid="saving-spinner"></span>
              {{ isSubmitting ? t('common.saving') : t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `
};
