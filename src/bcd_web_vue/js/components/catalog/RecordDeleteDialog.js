/**
 * Record Delete Dialog Component
 *
 * Confirmation dialog for deleting a bibliographic record with item loan warning.
 * Shows warning that all items and circulation history will be permanently deleted.
 */

const { ref, computed } = Vue;
const { useI18n } = VueI18n;

export default {
    name: 'RecordDeleteDialog',

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
            deleting,
            hasActiveLoans,
            itemCount,
            handleConfirm,
            handleClose
        };
    },

    template: `
        <div
            v-if="show"
            class="modal fade show"
            style="display: block;"
            tabindex="-1"
            aria-labelledby="recordDeleteDialogLabel"
            aria-modal="true"
            role="dialog"
            @click.self="handleClose"
        >
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <!-- Modal Header -->
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title" id="recordDeleteDialogLabel">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            {{ t('admin.delete_record') }}
                        </h5>
                        <button
                            type="button"
                            class="btn-close btn-close-white"
                            @click="handleClose"
                            :aria-label="t('common.close')"
                        ></button>
                    </div>

                    <!-- Modal Body -->
                    <div class="modal-body">
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
                                        {{ Array.isArray(recordData.authors) ? recordData.authors.join(', ') : recordData.authors }}
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
                    </div>

                    <!-- Modal Footer -->
                    <div class="modal-footer">
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
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal Backdrop -->
        <div class="modal-backdrop fade show"></div>
    `
};
