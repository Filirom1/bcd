/**
 * BulkEditModal Component
 *
 * 3-step wizard modal for bulk borrower operations:
 * - Step 1: Select operation (Change Class, Delete)
 * - Step 2: Configure operation (select target class, or confirm delete)
 * - Step 3: Confirm operation (show summary with selected count)
 *
 * Props:
 * - show (Boolean): Show/hide modal
 * - selectedBorrowers (Array): Array of selected borrower objects
 *
 * Emits:
 * - close: User closed modal
 * - execute: User confirmed operation { operation, targetClassId? }
 */

const { ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';

export default {
    name: 'BulkEditModal',

    props: {
        show: {
            type: Boolean,
            default: false
        },
        selectedBorrowers: {
            type: Array,
            default: () => []
        }
    },

    emits: ['close', 'execute'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Wizard state
        const currentStep = ref(1);
        const selectedOperation = ref(null);
        const targetClassId = ref(null);

        // Available classes (loaded from API)
        const classes = ref([]);
        const loadingClasses = ref(false);

        // Operation types
        const OPERATIONS = {
            CHANGE_CLASS: 'change_class',
            DELETE: 'delete'
        };

        // Selected count
        const selectedCount = computed(() => props.selectedBorrowers.length);

        // Can proceed to next step?
        const canProceedStep1 = computed(() => selectedOperation.value !== null);
        const canProceedStep2 = computed(() => {
            if (selectedOperation.value === OPERATIONS.CHANGE_CLASS) {
                return targetClassId.value !== null;
            } else if (selectedOperation.value === OPERATIONS.DELETE) {
                return true; // No config needed for delete
            }
            return false;
        });

        // Target class name (for confirmation message)
        const targetClassName = computed(() => {
            if (!targetClassId.value) return '';
            const cls = classes.value.find(c => c.id === targetClassId.value);
            return cls ? cls.name : '';
        });

        // Confirmation message
        const confirmationMessage = computed(() => {
            if (selectedOperation.value === OPERATIONS.CHANGE_CLASS) {
                return t('admin.confirm_bulk_change_class', {
                    count: selectedCount.value,
                    target_class: targetClassName.value
                });
            } else if (selectedOperation.value === OPERATIONS.DELETE) {
                return t('admin.confirm_bulk_delete_borrowers', {
                    count: selectedCount.value
                });
            }
            return '';
        });

        // Load classes from API
        const loadClasses = async () => {
            loadingClasses.value = true;
            try {
                classes.value = await apiClient.get('/classes', { limit: 500 });
            } catch (error) {
                console.error('Error loading classes:', error);
                classes.value = [];
            } finally {
                loadingClasses.value = false;
            }
        };

        // Reset wizard state
        const resetWizard = () => {
            currentStep.value = 1;
            selectedOperation.value = null;
            targetClassId.value = null;
        };

        // Handle operation selection
        const selectOperation = (operation) => {
            selectedOperation.value = operation;
        };

        // Navigate between steps
        const goToStep = (step) => {
            currentStep.value = step;
        };

        const nextStep = () => {
            if (currentStep.value < 3) {
                currentStep.value++;
            }
        };

        const previousStep = () => {
            if (currentStep.value > 1) {
                currentStep.value--;
            }
        };

        // Handle close
        const handleClose = () => {
            resetWizard();
            emit('close');
        };

        // Handle execute operation
        const handleExecute = () => {
            const payload = {
                operation: selectedOperation.value
            };

            if (selectedOperation.value === OPERATIONS.CHANGE_CLASS) {
                payload.targetClassId = targetClassId.value;
            }

            emit('execute', payload);
            resetWizard();
        };

        // Watch show prop to reset wizard and load classes
        watch(() => props.show, (newValue) => {
            if (newValue) {
                resetWizard();
                loadClasses();
            }
        });

        return {
            t,
            currentStep,
            selectedOperation,
            targetClassId,
            classes,
            loadingClasses,
            selectedCount,
            canProceedStep1,
            canProceedStep2,
            targetClassName,
            confirmationMessage,
            OPERATIONS,
            selectOperation,
            goToStep,
            nextStep,
            previousStep,
            handleClose,
            handleExecute
        };
    },

    template: `
        <div
            class="modal fade"
            :class="{ show: show }"
            :style="{ display: show ? 'block' : 'none' }"
            tabindex="-1"
            aria-labelledby="bulkEditModalLabel"
            :aria-hidden="!show"
            @click.self="handleClose"
        >
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content">
                    <!-- Modal Header -->
                    <div class="modal-header">
                        <h5 class="modal-title" id="bulkEditModalLabel">
                            <i class="bi bi-pencil"></i>
                            {{ t('admin.bulk_edit_title') }}
                            <span class="badge bg-secondary ms-2">{{ selectedCount }} {{ t('borrowers.selected') }}</span>
                        </h5>
                        <button
                            type="button"
                            class="btn-close"
                            @click="handleClose"
                            :aria-label="t('common.close')"
                        ></button>
                    </div>

                    <!-- Modal Body -->
                    <div class="modal-body">
                        <!-- Progress Indicator -->
                        <div class="mb-4">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <div class="d-flex align-items-center">
                                    <div
                                        class="rounded-circle d-flex align-items-center justify-content-center me-2"
                                        :class="currentStep >= 1 ? 'bg-primary text-white' : 'bg-secondary text-white'"
                                        style="width: 32px; height: 32px; font-size: 14px;"
                                    >
                                        1
                                    </div>
                                    <span :class="currentStep === 1 ? 'fw-bold' : ''">
                                        {{ t('admin.select_operation') }}
                                    </span>
                                </div>
                                <div class="flex-grow-1 mx-2" style="height: 2px; background-color: #dee2e6;"></div>
                                <div class="d-flex align-items-center">
                                    <div
                                        class="rounded-circle d-flex align-items-center justify-content-center me-2"
                                        :class="currentStep >= 2 ? 'bg-primary text-white' : 'bg-secondary text-white'"
                                        style="width: 32px; height: 32px; font-size: 14px;"
                                    >
                                        2
                                    </div>
                                    <span :class="currentStep === 2 ? 'fw-bold' : ''">
                                        {{ t('admin.configure_operation') }}
                                    </span>
                                </div>
                                <div class="flex-grow-1 mx-2" style="height: 2px; background-color: #dee2e6;"></div>
                                <div class="d-flex align-items-center">
                                    <div
                                        class="rounded-circle d-flex align-items-center justify-content-center me-2"
                                        :class="currentStep >= 3 ? 'bg-primary text-white' : 'bg-secondary text-white'"
                                        style="width: 32px; height: 32px; font-size: 14px;"
                                    >
                                        3
                                    </div>
                                    <span :class="currentStep === 3 ? 'fw-bold' : ''">
                                        {{ t('admin.confirm_operation') }}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Step 1: Select Operation -->
                        <div v-if="currentStep === 1">
                            <p class="text-muted mb-3">
                                {{ t('admin.select_operation') }}
                            </p>
                            <div class="list-group">
                                <button
                                    type="button"
                                    class="list-group-item list-group-item-action"
                                    :class="{ active: selectedOperation === OPERATIONS.CHANGE_CLASS }"
                                    @click="selectOperation(OPERATIONS.CHANGE_CLASS)"
                                >
                                    <div class="d-flex w-100 justify-content-between">
                                        <h6 class="mb-1">
                                            <i class="bi bi-house-door"></i>
                                            {{ t('admin.change_class') }}
                                        </h6>
                                    </div>
                                    <p class="mb-0 small">
                                        {{ t('admin.change_class_description', 'Change the class assignment for selected borrowers') }}
                                    </p>
                                </button>

                                <button
                                    type="button"
                                    class="list-group-item list-group-item-action list-group-item-danger"
                                    :class="{ active: selectedOperation === OPERATIONS.DELETE }"
                                    @click="selectOperation(OPERATIONS.DELETE)"
                                >
                                    <div class="d-flex w-100 justify-content-between">
                                        <h6 class="mb-1">
                                            <i class="bi bi-trash"></i>
                                            {{ t('admin.delete') }}
                                        </h6>
                                    </div>
                                    <p class="mb-0 small">
                                        {{ t('admin.delete_description', 'Permanently delete selected borrowers and their circulation history') }}
                                    </p>
                                </button>
                            </div>
                        </div>

                        <!-- Step 2: Configure Operation -->
                        <div v-if="currentStep === 2">
                            <!-- Change Class Configuration -->
                            <div v-if="selectedOperation === OPERATIONS.CHANGE_CLASS">
                                <p class="text-muted mb-3">
                                    {{ t('admin.select_target_class') }}
                                </p>
                                <div v-if="loadingClasses" class="text-center py-4">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">{{ t('common.loading') }}</span>
                                    </div>
                                </div>
                                <div v-else>
                                    <div v-if="classes.length === 0" class="alert alert-warning">
                                        <i class="bi bi-exclamation-triangle"></i>
                                        {{ t('admin.no_classes_available', 'No classes available. Please create a class first.') }}
                                    </div>
                                    <select v-else class="form-select" v-model="targetClassId">
                                        <option :value="null">{{ t('admin.select_class', 'Select a class...') }}</option>
                                        <option v-for="cls in classes" :key="cls.id" :value="cls.id">
                                            {{ cls.name }}
                                            <span v-if="cls.homeroom_teacher">- {{ cls.homeroom_teacher }}</span>
                                        </option>
                                    </select>
                                </div>
                            </div>

                            <!-- Delete Confirmation (no config needed) -->
                            <div v-if="selectedOperation === OPERATIONS.DELETE">
                                <div class="alert alert-danger">
                                    <h6 class="alert-heading">
                                        <i class="bi bi-exclamation-triangle"></i>
                                        {{ t('admin.warning') }}
                                    </h6>
                                    <p class="mb-0">
                                        {{ t('admin.delete_warning_message') }}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <!-- Step 3: Confirm Operation -->
                        <div v-if="currentStep === 3">
                            <div class="alert alert-info">
                                <h6 class="alert-heading">
                                    <i class="bi bi-info-circle"></i>
                                    {{ t('admin.confirm_operation') }}
                                </h6>
                                <p class="mb-0">
                                    {{ confirmationMessage }}
                                </p>
                            </div>

                            <!-- List of selected borrowers (first 5) -->
                            <div class="card">
                                <div class="card-header">
                                    <strong>{{ t('borrowers.selected') }} ({{ selectedCount }})</strong>
                                </div>
                                <ul class="list-group list-group-flush">
                                    <li
                                        v-for="(borrower, index) in selectedBorrowers.slice(0, 5)"
                                        :key="borrower.borrower_id"
                                        class="list-group-item"
                                    >
                                        <code>{{ borrower.borrower_id }}</code> - {{ borrower.full_name }}
                                        <span v-if="borrower.class_name" class="text-muted ms-2">
                                            ({{ borrower.class_name }})
                                        </span>
                                    </li>
                                    <li v-if="selectedCount > 5" class="list-group-item text-muted">
                                        {{ t('admin.and_n_more', { count: selectedCount - 5 }) }}
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <!-- Modal Footer -->
                    <div class="modal-footer">
                        <button
                            v-if="currentStep > 1"
                            type="button"
                            class="btn btn-secondary"
                            @click="previousStep"
                        >
                            <i class="bi bi-arrow-left"></i>
                            {{ t('common.back') }}
                        </button>
                        <button
                            type="button"
                            class="btn btn-secondary"
                            @click="handleClose"
                        >
                            {{ t('common.cancel') }}
                        </button>
                        <button
                            v-if="currentStep < 3"
                            type="button"
                            class="btn btn-primary"
                            :disabled="currentStep === 1 ? !canProceedStep1 : !canProceedStep2"
                            @click="nextStep"
                        >
                            {{ t('common.next') }}
                            <i class="bi bi-arrow-right"></i>
                        </button>
                        <button
                            v-if="currentStep === 3"
                            type="button"
                            class="btn btn-danger"
                            @click="handleExecute"
                        >
                            <i class="bi bi-check-lg"></i>
                            {{ t('common.confirm') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal Backdrop -->
        <div
            v-if="show"
            class="modal-backdrop fade show"
        ></div>
    `
};
