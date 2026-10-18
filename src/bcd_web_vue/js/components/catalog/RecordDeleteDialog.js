/**
 * Record Delete Dialog Component
 *
 * Confirmation dialog for deleting a bibliographic record with item loan warning.
 * Shows warning that all items and circulation history will be permanently deleted.
 * Teleported to body for correct z-index layered display on top of other modals.
 */

const { ref, computed } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';
import { formatAuthors } from '../../utils/domain.js';

export default {
    name: 'RecordDeleteDialog',
    components: { Modal },

    props: {
        show: {
            type: Boolean,
            default: false
        },
        recordData: {
            type: Object,
            required: true
        }
    },

    emits: ['close', 'confirm'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const deleting = ref(false);

        // Check if any item is on loan
        const hasActiveLoans = computed(() => {
            if (!props.recordData.items || !Array.isArray(props.recordData.items)) {
                return false;
            }
            return props.recordData.items.some(item => item.status === 'on_loan');
        });

        const itemCount = computed(() => {
            return props.recordData.items?.length || 0;
        });

        // Handle confirm
        const handleConfirm = async () => {
            deleting.value = true;

            try {
                emit('confirm', props.recordData.id);
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
            formatAuthors,
            deleting,
            hasActiveLoans,
            itemCount,
            handleConfirm,
            handleClose
        };
    },

    template: `
        <modal :show="show" centered scrollable @close="handleClose">
            <template #header>
                <i class="bi bi-exclamation-triangle me-2"></i>
                {{ t('admin.delete_record') }}
            </template>

                                <!-- Warning about items and circulation history -->
                                <div class="alert alert-warning" role="alert">
                                    <i class="bi bi-exclamation-triangle me-2"></i>
                                    {{ t('admin.delete_record_warning', { count: itemCount }) }}
                                </div>

                                <!-- Delete confirmation message -->
                                <p class="mb-3">
                                    {{ t('admin.confirm_delete_record', {
                                        title: recordData.title
                                    }) }}
                                </p>

                                <!-- Record details -->
                                <div class="card mb-3">
                                    <div class="card-body">
                                        <h6 class="card-subtitle mb-2 text-muted">{{ t('admin.record_details') }}</h6>
                                        <ul class="list-unstyled mb-0">
                                            <li>
                                                <strong>{{ t('bibliographic.title') }}:</strong>
                                                {{ recordData.title }}
                                            </li>
                                            <li v-if="recordData.authors && recordData.authors.length">
                                                <strong>{{ t('bibliographic.authors') }}:</strong>
                                                {{ formatAuthors(recordData.authors) }}
                                            </li>
                                            <li v-if="recordData.isbn">
                                                <strong>{{ t('bibliographic.isbn') }}:</strong>
                                                {{ recordData.isbn_value }}
                                            </li>
                                            <li>
                                                <strong>{{ t('catalog.copies') }}:</strong>
                                                <span class="badge bg-info text-dark">
                                                    {{ itemCount }}
                                                </span>
                                            </li>
                                        </ul>
                                    </div>
                                </div>

                                <!-- Error alert if items are on loan -->
                                <div v-if="hasActiveLoans" class="alert alert-danger" role="alert">
                                    <i class="bi bi-x-circle me-2"></i>
                                    {{ t('admin.error_delete_record_has_loans') }}
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
                                    :disabled="deleting || hasActiveLoans"
                                >
                                    <span v-if="deleting" class="spinner-border spinner-border-sm me-1"></span>
                                    {{ deleting ? t('common.deleting') : t('common.delete') }}
                                </button>
            </template>
        </modal>
    `
};
