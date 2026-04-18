/**
 * Class Form Component
 *
 * Create/Edit modal for class management with validation.
 * Follows Bootstrap 5 modal pattern.
 */

const { ref, watch, computed } = Vue;
const { useI18n } = VueI18n;

export default {
    name: 'ClassForm',

    props: {
        show: {
            type: Boolean,
            default: false
        },
        classData: {
            type: Object,
            default: null
        }
    },

    emits: ['close', 'save'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Form data
        const form = ref({
            name: '',
            homeroom_teacher: '',
            notes: '',
            average_age: null
        });

        const errors = ref({});
        const saving = ref(false);

        // Modal instance
        let modalInstance = null;

        // Is editing mode?
        const isEdit = computed(() => props.classData !== null);

        // Modal title
        const modalTitle = computed(() =>
            isEdit.value ? t('admin.edit_class') : t('admin.create_class')
        );

        // Grade level options (French elementary school system)
        const gradeLevelOptions = [
            'CP',    // Cours Préparatoire (1st year)
            'CE1',   // Cours Élémentaire 1 (2nd year)
            'CE2',   // Cours Élémentaire 2 (3rd year)
            'CM1',   // Cours Moyen 1 (4th year)
            'CM2'    // Cours Moyen 2 (5th year)
        ];

        // Current academic year (e.g., "2025-2026")
        const currentAcademicYear = computed(() => {
            const now = new Date();
            const year = now.getFullYear();
            const month = now.getMonth() + 1; // 1-12

            // Academic year starts in September
            if (month >= 9) {
                return `${year}-${year + 1}`;
            } else {
                return `${year - 1}-${year}`;
            }
        });

        // Initialize form when classData changes
        watch(() => props.classData, (newData) => {
            if (newData) {
                // Edit mode - populate form
                form.value = {
                    name: newData.name || '',
                    homeroom_teacher: newData.homeroom_teacher || '',
                    notes: newData.notes || '',
                    average_age: newData.average_age ?? null
                };
            } else {
                // Create mode - reset form
                form.value = {
                    name: '',
                    homeroom_teacher: '',
                    notes: '',
                    average_age: null
                };
            }
            errors.value = {};
        }, { immediate: true });

        // Validate form
        const validateForm = () => {
            errors.value = {};
            let isValid = true;

            // Only name is required
            if (!form.value.name || form.value.name.trim() === '') {
                errors.value.name = t('validation.required_field');
                isValid = false;
            }

            return isValid;
        };

        // Handle save
        const handleSave = async () => {
            if (!validateForm()) {
                return;
            }

            saving.value = true;

            try {
                emit('save', {
                    id: props.classData?.id,
                    ...form.value
                });
            } finally {
                saving.value = false;
            }
        };

        // Handle close
        const handleClose = () => {
            emit('close');
        };

        return {
            t,
            form,
            errors,
            saving,
            isEdit,
            modalTitle,
            gradeLevelOptions,
            currentAcademicYear,
            handleSave,
            handleClose
        };
    },

    template: `
        <div
            class="modal fade"
            :class="{ show: show }"
            :style="{ display: show ? 'block' : 'none' }"
            tabindex="-1"
            aria-labelledby="classFormModalLabel"
            :aria-hidden="!show"
            @click.self="handleClose"
        >
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <!-- Modal Header -->
                    <div class="modal-header">
                        <h5 class="modal-title" id="classFormModalLabel">
                            {{ modalTitle }}
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
                        <form @submit.prevent="handleSave">
                            <!-- Class Name -->
                            <div class="mb-3">
                                <label for="class-name" class="form-label">
                                    {{ t('admin.class_name') }}
                                    <span class="text-danger">*</span>
                                </label>
                                <input
                                    type="text"
                                    class="form-control"
                                    :class="{ 'is-invalid': errors.name }"
                                    id="class-name"
                                    v-model="form.name"
                                    :placeholder="t('admin.class_name_placeholder', 'e.g., CP-A')"
                                    maxlength="50"
                                    required
                                >
                                <div v-if="errors.name" class="invalid-feedback">
                                    {{ errors.name }}
                                </div>
                                <small class="form-text text-muted">
                                    {{ t('admin.class_name_help', 'Example: CP-A, CE1-B, CM2') }}
                                </small>
                            </div>

                            <!-- Homeroom Teacher -->
                            <div class="mb-3">
                                <label for="homeroom-teacher" class="form-label">
                                    {{ t('admin.homeroom_teacher') }}
                                </label>
                                <input
                                    type="text"
                                    class="form-control"
                                    id="homeroom-teacher"
                                    v-model="form.homeroom_teacher"
                                    maxlength="100"
                                >
                            </div>

                            <!-- Average Age -->
                            <div class="mb-3">
                                <label for="average-age" class="form-label">
                                    {{ t('admin.average_age') }}
                                </label>
                                <input
                                    type="number"
                                    class="form-control"
                                    id="average-age"
                                    v-model.number="form.average_age"
                                    min="3"
                                    max="18"
                                    :placeholder="t('admin.average_age_placeholder')"
                                >
                                <small class="form-text text-muted">
                                    {{ t('admin.average_age_help') }}
                                </small>
                            </div>

                            <!-- Notes -->
                            <div class="mb-3">
                                <label for="notes" class="form-label">
                                    {{ t('admin.notes') }}
                                </label>
                                <textarea
                                    class="form-control"
                                    id="notes"
                                    v-model="form.notes"
                                    rows="3"
                                ></textarea>
                            </div>
                        </form>
                    </div>

                    <!-- Modal Footer -->
                    <div class="modal-footer">
                        <button
                            type="button"
                            class="btn btn-secondary"
                            @click="handleClose"
                            :disabled="saving"
                        >
                            {{ t('common.cancel') }}
                        </button>
                        <button
                            type="button"
                            class="btn btn-primary"
                            @click="handleSave"
                            :disabled="saving"
                        >
                            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                            {{ saving ? t('common.saving') : t('common.save') }}
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
