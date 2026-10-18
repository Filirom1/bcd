/**
 * Class Delete Dialog Component
 *
 * Confirmation dialog for deleting a class with student count warning.
 * Shows warning that students will be unassigned from the class.
 */

const { ref } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';

export default {
    name: 'ClassDeleteDialog',
    components: { Modal },

    props: {
        show: {
            type: Boolean,
            default: false
        },
        classData: {
            type: Object,
            required: true
        }
    },

    emits: ['close', 'confirm'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const deleting = ref(false);

        // Handle confirm
        const handleConfirm = async () => {
            deleting.value = true;

            try {
                emit('confirm', props.classData.id);
            } finally {
                deleting.value = false;
            }
        };

        // Handle close
        const handleClose = () => {
            emit('close');
        };

        return {
            t,
            deleting,
            handleConfirm,
            handleClose
        };
    },

    template: `
        <modal :show="show" centered scrollable @close="handleClose">
            <template #header>
                <i class="bi bi-exclamation-triangle me-2"></i>
                {{ t('admin.delete_class') }}
            </template>

                        <!-- Warning -->
                        <div class="alert alert-warning" role="alert">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            <strong>{{ t('admin.warning') }}</strong>
                        </div>

                        <!-- Delete confirmation message -->
                        <p class="mb-3">
                            {{ t('admin.confirm_delete_class', { name: classData.name }) }}
                        </p>

                        <!-- Class details -->
                        <div class="card mb-3">
                            <div class="card-body">
                                <h6 class="card-subtitle mb-2 text-muted">{{ t('admin.class_details') }}</h6>
                                <ul class="list-unstyled mb-0">
                                    <li>
                                        <strong>{{ t('admin.class_name') }}:</strong>
                                        {{ classData.name }}
                                    </li>
                                </ul>
                            </div>
                        </div>

                        <!-- Warning about student unassignment -->
                        <div class="alert alert-info" role="alert">
                            <i class="bi bi-info-circle me-2"></i>
                            {{ t('admin.delete_class_warning_students') }}
                        </div>

                        <!-- Cannot be undone warning -->
                        <p class="text-danger mb-0">
                            <i class="bi bi-exclamation-circle me-1"></i>
                            <strong>{{ t('admin.delete_warning_irreversible', 'This action cannot be undone.') }}</strong>
                        </p>

            <template #footer>
                        <button
                            type="button"
                            class="btn btn-secondary"
                            @click="handleClose"
                            :disabled="deleting"
                        >
                            {{ t('common.cancel') }}
                        </button>
                        <button
                            type="button"
                            class="btn btn-danger"
                            @click="handleConfirm"
                            :disabled="deleting"
                        >
                            <span v-if="deleting" class="spinner-border spinner-border-sm me-1"></span>
                            {{ deleting ? t('common.deleting') : t('common.delete') }}
                        </button>
            </template>
        </modal>
    `
};
