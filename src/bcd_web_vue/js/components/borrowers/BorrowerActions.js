/**
 * Borrower Actions Component
 *
 * Block/Unblock/Renew All action buttons and modal dialogs.
 * Replaces global JavaScript functions with scoped Vue component logic.
 *
 * COMPARISON WITH OLD SOLUTION:
 * - OLD: Global functions (openBlockBorrowerModal, confirmBlockBorrower, etc.)
 * - NEW: Component methods with reactive state
 * - OLD: Manual Bootstrap modal creation (new bootstrap.Modal())
 * - NEW: Vue-managed modal visibility with v-if
 * - OLD: Manual DOM queries (getElementById) to get form values
 * - NEW: Vue v-model for form binding
 * - OLD: Manual notification (showNotification global function)
 * - NEW: useNotification composable
 */

import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';
import { apiClient } from '../../api/client.js';

export default {
    name: 'BorrowerActions',

    props: {
        borrower: {
            type: Object,
            required: true
        }
    },

    template: `
        <div class="borrower-actions">
            <!-- Block/Unblock Button -->
            <button
                v-if="borrower.active"
                type="button"
                class="btn btn-danger rounded-pill me-2"
                @click="openBlockModal"
            >
                <i class="bi bi-lock"></i>
                {{ t('borrowers.block_borrower') }}
            </button>
            <button
                v-else
                type="button"
                class="btn btn-success rounded-pill me-2"
                @click="openUnblockModal"
            >
                <i class="bi bi-unlock"></i>
                {{ t('borrowers.unblock_borrower') }}
            </button>

            <!-- Renew All Button (only if has current loans) -->
            <button
                v-if="borrower.current_loans_count > 0"
                type="button"
                class="btn btn-primary rounded-pill me-2"
                @click="renewAll"
                :disabled="renewLoading"
            >
                <span v-if="renewLoading" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-arrow-repeat"></i>
                {{ t('circulation.renew_all') }}
            </button>

            <!-- Block Modal -->
            <teleport to="body">
                <div
                    v-if="showBlockModal"
                    class="modal fade show d-block"
                    tabindex="-1"
                    @click.self="closeBlockModal"
                >
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="bi bi-lock"></i>
                                    {{ t('borrowers.block_borrower') }}
                                </h5>
                                <button
                                    type="button"
                                    class="btn-close"
                                    @click="closeBlockModal"
                                ></button>
                            </div>
                            <div class="modal-body">
                                <p>
                                    {{ t('borrowers.confirm_block') }}:
                                    <strong>{{ borrower.full_name }}</strong>
                                </p>

                                <!-- Reason Dropdown -->
                                <div class="mb-3">
                                    <label class="form-label">
                                        {{ t('borrowers.blocking_reason') }} *
                                    </label>
                                    <select
                                        class="form-select"
                                        v-model="blockReason"
                                        :class="{ 'is-invalid': blockReasonError }"
                                    >
                                        <option value="">{{ t('borrowers.select_reason') }}</option>
                                        <option value="Lost Book">{{ t('borrowers.reason_lost_book') }}</option>
                                        <option value="Damaged Materials">{{ t('borrowers.reason_damaged') }}</option>
                                        <option value="Repeated Overdue Items">{{ t('borrowers.reason_overdue') }}</option>
                                        <option value="Policy Violation">{{ t('borrowers.reason_policy') }}</option>
                                        <option value="Other">{{ t('borrowers.reason_other') }}</option>
                                    </select>
                                    <div v-if="blockReasonError" class="invalid-feedback">
                                        {{ blockReasonError }}
                                    </div>
                                </div>

                                <!-- Optional Notes -->
                                <div class="mb-3">
                                    <label class="form-label">
                                        {{ t('borrowers.notes') }}
                                        <small class="text-muted">({{ t('common.optional') }})</small>
                                    </label>
                                    <textarea
                                        class="form-control"
                                        v-model="blockNotes"
                                        rows="3"
                                        :placeholder="t('borrowers.notes_placeholder')"
                                        maxlength="150"
                                    ></textarea>
                                    <small class="text-muted">
                                        {{ blockNotes.length }}/150
                                    </small>
                                </div>

                                <div class="alert alert-warning">
                                    <i class="bi bi-exclamation-triangle"></i>
                                    {{ t('borrowers.block_warning') }}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button
                                    type="button"
                                    class="btn btn-secondary"
                                    @click="closeBlockModal"
                                >
                                    {{ t('common.cancel') }}
                                </button>
                                <button
                                    type="button"
                                    class="btn btn-danger"
                                    @click="confirmBlock"
                                    :disabled="blockLoading"
                                >
                                    <span v-if="blockLoading" class="spinner-border spinner-border-sm me-1"></span>
                                    <i v-else class="bi bi-lock"></i>
                                    {{ t('borrowers.block_borrower') }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div v-if="showBlockModal" class="modal-backdrop fade show"></div>
            </teleport>

            <!-- Unblock Modal -->
            <teleport to="body">
                <div
                    v-if="showUnblockModal"
                    class="modal fade show d-block"
                    tabindex="-1"
                    @click.self="closeUnblockModal"
                >
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="bi bi-unlock"></i>
                                    {{ t('borrowers.unblock_borrower') }}
                                </h5>
                                <button
                                    type="button"
                                    class="btn-close"
                                    @click="closeUnblockModal"
                                ></button>
                            </div>
                            <div class="modal-body">
                                <p>
                                    {{ t('borrowers.confirm_unblock') }}:
                                    <strong>{{ borrower.full_name }}</strong>
                                </p>
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle"></i>
                                    {{ t('borrowers.unblock_info') }}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button
                                    type="button"
                                    class="btn btn-secondary"
                                    @click="closeUnblockModal"
                                >
                                    {{ t('common.cancel') }}
                                </button>
                                <button
                                    type="button"
                                    class="btn btn-success"
                                    @click="confirmUnblock"
                                    :disabled="unblockLoading"
                                >
                                    <span v-if="unblockLoading" class="spinner-border spinner-border-sm me-1"></span>
                                    <i v-else class="bi bi-unlock"></i>
                                    {{ t('borrowers.unblock_borrower') }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div v-if="showUnblockModal" class="modal-backdrop fade show"></div>
            </teleport>
        </div>
    `,

    emits: ['action-completed'],

    setup(props, { emit }) {
        const { t } = VueI18n.useI18n();
        const { success: showSuccess, error: showError, warning: showWarning, info: showInfo } = useNotification();
        const { handleError } = useErrorHandler(t);

        // Block Modal State
        const showBlockModal = Vue.ref(false);
        const blockReason = Vue.ref('');
        const blockNotes = Vue.ref('');
        const blockReasonError = Vue.ref('');
        const blockLoading = Vue.ref(false);

        // Unblock Modal State
        const showUnblockModal = Vue.ref(false);
        const unblockLoading = Vue.ref(false);

        // Renew All State
        const renewLoading = Vue.ref(false);

        // Open Block Modal
        const openBlockModal = () => {
            blockReason.value = '';
            blockNotes.value = '';
            blockReasonError.value = '';
            showBlockModal.value = true;
        };

        // Close Block Modal
        const closeBlockModal = () => {
            showBlockModal.value = false;
        };

        // Confirm Block Action
        const confirmBlock = async () => {
            // Validation
            if (!blockReason.value) {
                blockReasonError.value = t('borrowers.error_select_reason');
                return;
            }

            blockReasonError.value = '';
            blockLoading.value = true;

            try {
                // Combine reason + notes (max 200 chars)
                let combinedReason = blockReason.value;
                if (blockNotes.value.trim()) {
                    combinedReason += ' - ' + blockNotes.value.trim();
                }
                if (combinedReason.length > 200) {
                    combinedReason = combinedReason.substring(0, 200);
                }

                await apiClient.post(
                    `/borrowers/${props.borrower.borrower_id}/block`,
                    null,
                    { reason: combinedReason }
                );

                showSuccess(t('borrowers.borrower_blocked_success'));

                // Close modal first
                closeBlockModal();

                // Wait for Vue to update DOM, then emit to parent
                Vue.nextTick(() => {
                    emit('action-completed', 'block');
                });

            } catch (error) {
                handleError(error);
            } finally {
                blockLoading.value = false;
            }
        };

        // Open Unblock Modal
        const openUnblockModal = () => {
            showUnblockModal.value = true;
        };

        // Close Unblock Modal
        const closeUnblockModal = () => {
            showUnblockModal.value = false;
        };

        // Confirm Unblock Action
        const confirmUnblock = async () => {
            unblockLoading.value = true;

            try {
                await apiClient.post(
                    `/borrowers/${props.borrower.borrower_id}/unblock`,
                    null
                );

                showSuccess(t('borrowers.borrower_unblocked_success'));

                // Close modal first
                closeUnblockModal();

                // Wait for Vue to update DOM, then emit to parent
                Vue.nextTick(() => {
                    emit('action-completed', 'unblock');
                });

            } catch (error) {
                handleError(error);
            } finally {
                unblockLoading.value = false;
            }
        };

        // Renew All Items
        const renewAll = async () => {
            renewLoading.value = true;

            try {
                showInfo(t('circulation.renewing'));

                const data = await apiClient.post('/circulation/renew', {
                    borrower_id: props.borrower.borrower_id,
                    item_ids: null  // null = renew all eligible
                });

                // Build message based on results
                let message, type;
                if (data.failed_count === 0) {
                    message = t('circulation.renewed_successfully', { count: data.renewed_count });
                    type = 'success';
                } else if (data.renewed_count === 0) {
                    message = t('circulation.renewal_failed', { count: data.failed_count });
                    type = 'error';
                } else {
                    message = t('circulation.renewed_successfully', { count: data.renewed_count }) +
                              ', ' + t('circulation.renewal_failed', { count: data.failed_count });
                    type = 'warning';
                }

                // Show appropriate notification based on type
                if (type === 'success') {
                    showSuccess(message);
                } else if (type === 'error') {
                    showError(message);
                } else if (type === 'warning') {
                    showWarning(message);
                }

                emit('action-completed', 'renew');

            } catch (error) {
                // Check for specific error codes
                if (error.code === 'no_renewable_items') {
                    showWarning(t('circulation.no_renewable_items') || error.message || 'No items can be renewed at this time');
                    return; // Exit gracefully without throwing
                }
                handleError(error);
            } finally {
                renewLoading.value = false;
            }
        };

        return {
            t,
            showBlockModal,
            blockReason,
            blockNotes,
            blockReasonError,
            blockLoading,
            showUnblockModal,
            unblockLoading,
            renewLoading,
            openBlockModal,
            closeBlockModal,
            confirmBlock,
            openUnblockModal,
            closeUnblockModal,
            confirmUnblock,
            renewAll
        };
    }
};
