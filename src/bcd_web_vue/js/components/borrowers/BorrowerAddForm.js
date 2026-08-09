/**
 * BorrowerAddForm.js
 *
 * Modal form for adding a new borrower.
 * Pre-fills the borrower ID with the smallest available ID so that IDs
 * freed when students leave (e.g., CM2 deletion at year-end) are reused.
 */

const { ref, watch } = Vue;
const { useI18n } = VueI18n;
import BorrowerFields from './BorrowerFields.js';
import { apiClient } from '../../api/client.js';
import { events } from '../../utils/events.js';

export default {
  name: 'BorrowerAddForm',
  components: {
    BorrowerFields
  },
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
        classes.value = await apiClient.get('/classes', { limit: 500 });
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
        const data = await apiClient.get('/borrowers/next-available-id');
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
        const newBorrower = await apiClient.post('/borrowers', formData.value);
        emit('created', newBorrower);
        events.emit('borrowers:refresh');
        closeModal();
      } catch (error) {
        console.error('Error creating borrower:', error);
        if (error.statusCode === 409) {
          errors.value.borrower_id = t('errors.BORROWER_ID_NOT_AVAILABLE');
        } else if (error.statusCode === 400) {
          if (error.message && error.message.includes('borrower_id')) {
            errors.value.borrower_id = error.message;
          } else if (error.message && error.message.includes('role')) {
            errors.value.role = error.message;
          } else {
            errors.value.general = error.message || t('admin.borrower.add.error');
          }
        } else {
          errors.value.general = error.message || t('admin.borrower.add.error');
        }
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
              <borrower-fields
                v-model="formData"
                :errors="errors"
                :classes="classes"
                :is-loading-classes="isLoadingClasses"
              />
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
