/**
 * Borrower Delete Dialog Component
 *
 * Confirmation dialog for deleting a borrower with active loan warning.
 * Shows warning that circulation history will be permanently deleted.
 * Teleported to body for correct z-index layered display on top of other modals.
 */

const { ref } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';

export default {
    name: 'BorrowerDeleteDialog',
    components: { Modal },

    props: {
        show: {
            type: Boolean,
            default: false
        },
        borrowerData: {
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
                emit('confirm', props.borrowerData.borrower_id);
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
                {{ t('admin.delete_borrower') }}
            </template>

                                <!-- Warning about circulation history -->
                                <div class="alert alert-warning" role="alert">
                                    <i class="bi bi-exclamation-triangle me-2"></i>
                                    {{ t('admin.delete_borrower_warning_history') }}
                                </div>

                                <!-- Delete confirmation message -->
                                <p class="mb-3">
                                    {{ t('admin.confirm_delete_borrower', {
                                        name: borrowerData.full_name || borrowerData.borrower_id
                                    }) }}
                                </p>

                                <!-- Borrower details -->
                                <div class="card mb-3">
                                    <div class="card-body">
                                        <h6 class="card-subtitle mb-2 text-muted">{{ t('admin.borrower_details') }}</h6>
                                        <ul class="list-unstyled mb-0">
                                            <li>
                                                <strong>{{ t('borrower.borrower_id') }}:</strong>
                                                {{ borrowerData.borrower_id }}
                                            </li>
                                            <li>
                                                <strong>{{ t('borrower.name') }}:</strong>
                                                {{ borrowerData.full_name }}
                                            </li>
                                            <li v-if="borrowerData.role">
                                                <strong>{{ t('borrower.role') }}:</strong>
                                                {{ borrowerData.role }}
                                            </li>
                                        </ul>
                                    </div>
                                </div>

                                <!-- Error alert if has active loans -->
                                <div v-if="borrowerData.current_loans_count > 0" class="alert alert-danger" role="alert">
                                    <i class="bi bi-x-circle me-2"></i>
                                    {{ t('admin.error_delete_borrower_has_loans_detail', {
                                        name: borrowerData.full_name || borrowerData.borrower_id,
                                        count: borrowerData.current_loans_count
                                    }) }}
                                </div>

                                <!-- Cannot be undone warning -->
                                <p class="text-danger mb-0">
                                    <i class="bi bi-exclamation-circle me-1"></i>
                                    <strong>{{ t('admin.delete_warning_irreversible') }}</strong>
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
                                    :disabled="deleting || borrowerData.current_loans_count > 0"
                                >
                                    <span v-if="deleting" class="spinner-border spinner-border-sm me-1"></span>
                                    {{ deleting ? t('common.deleting') : t('common.delete') }}
                                </button>
            </template>
        </modal>
    `
};
