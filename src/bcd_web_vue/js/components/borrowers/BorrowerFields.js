/**
 * BorrowerFields.js
 * 
 * Reusable borrower fields component for BorrowerDetail and BorrowerAddForm.
 * Displays label on the left (col-sm-3) and control/input on the right (col-sm-9).
 */

const { ref, watch, computed } = Vue;

export default {
    name: 'BorrowerFields',

    props: {
        modelValue: {
            type: Object,
            required: true
        },
        errors: {
            type: Object,
            default: () => ({})
        },
        classes: {
            type: Array,
            default: () => []
        },
        isLoadingClasses: {
            type: Boolean,
            default: false
        }
    },

    emits: ['update:modelValue'],

    setup(props, { emit }) {
        const { t } = VueI18n.useI18n();

        const localData = computed({
            get: () => props.modelValue,
            set: (val) => emit('update:modelValue', val)
        });

        const getRoleDisplayName = (role) => {
            const roleMap = {
                'student': t('borrower.role_student'),
                'teacher': t('borrower.role_teacher'),
                'staff': t('borrower.role_staff')
            };
            return roleMap[role] || role;
        };

        return {
            t,
            localData,
            getRoleDisplayName
        };
    },

    template: `
        <div class="container-fluid px-0">
            <!-- Borrower ID -->
            <div class="row mb-3 align-items-center">
                <label for="borrower-id" class="col-sm-3 col-form-label fw-bold">
                    {{ t('admin.borrower.edit.borrower_id') }} *
                </label>
                <div class="col-sm-9">
                    <input
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.borrower_id }"
                        id="borrower-id"
                        data-testid="input-borrower-id"
                        v-model="localData.borrower_id"
                        :placeholder="t('admin.borrower.edit.borrower_id_placeholder')"
                        required
                    />
                    <div v-if="errors.borrower_id" class="invalid-feedback" data-testid="error-borrower-id">
                        {{ errors.borrower_id }}
                    </div>
                </div>
            </div>

            <!-- First Name -->
            <div class="row mb-3 align-items-center">
                <label for="first-name" class="col-sm-3 col-form-label fw-bold">
                    {{ t('admin.borrower.edit.first_name') }} *
                </label>
                <div class="col-sm-9">
                    <input
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.first_name }"
                        id="first-name"
                        data-testid="input-first-name"
                        v-model="localData.first_name"
                        :placeholder="t('admin.borrower.edit.first_name_placeholder')"
                        required
                    />
                    <div v-if="errors.first_name" class="invalid-feedback" data-testid="error-first-name">
                        {{ errors.first_name }}
                    </div>
                </div>
            </div>

            <!-- Last Name -->
            <div class="row mb-3 align-items-center">
                <label for="last-name" class="col-sm-3 col-form-label fw-bold">
                    {{ t('admin.borrower.edit.last_name') }} *
                </label>
                <div class="col-sm-9">
                    <input
                        type="text"
                        class="form-control"
                        :class="{ 'is-invalid': errors.last_name }"
                        id="last-name"
                        data-testid="input-last-name"
                        v-model="localData.last_name"
                        :placeholder="t('admin.borrower.edit.last_name_placeholder')"
                        required
                    />
                    <div v-if="errors.last_name" class="invalid-feedback" data-testid="error-last-name">
                        {{ errors.last_name }}
                    </div>
                </div>
            </div>

            <!-- Role -->
            <div class="row mb-3 align-items-center">
                <label for="role" class="col-sm-3 col-form-label fw-bold">
                    {{ t('admin.borrower.edit.role') }} *
                </label>
                <div class="col-sm-9">
                    <select
                        class="form-select"
                        :class="{ 'is-invalid': errors.role }"
                        id="role"
                        data-testid="select-role"
                        v-model="localData.role"
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
            </div>

            <!-- Class -->
            <div class="row mb-3 align-items-center">
                <label for="class" class="col-sm-3 col-form-label fw-bold">
                    {{ t('admin.borrower.edit.class') }}
                </label>
                <div class="col-sm-9">
                    <select
                        class="form-select"
                        :class="{ 'is-invalid': errors.class_id }"
                        id="class"
                        data-testid="select-class"
                        v-model="localData.class_id"
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
                </div>
            </div>

            <!-- Email -->
            <div class="row mb-3 align-items-center">
                <label for="email" class="col-sm-3 col-form-label fw-bold">
                    {{ t('admin.borrower.edit.email') }}
                </label>
                <div class="col-sm-9">
                    <input
                        type="email"
                        class="form-control"
                        :class="{ 'is-invalid': errors.email }"
                        id="email"
                        data-testid="input-email"
                        v-model="localData.email"
                        :placeholder="t('admin.borrower.edit.email_placeholder')"
                    />
                    <div v-if="errors.email" class="invalid-feedback" data-testid="error-email">
                        {{ errors.email }}
                    </div>
                </div>
            </div>

            <!-- Phone -->
            <div class="row mb-3 align-items-center">
                <label for="phone" class="col-sm-3 col-form-label fw-bold">
                    {{ t('admin.borrower.edit.phone') }}
                </label>
                <div class="col-sm-9">
                    <input
                        type="tel"
                        class="form-control"
                        :class="{ 'is-invalid': errors.phone }"
                        id="phone"
                        data-testid="input-phone"
                        v-model="localData.phone"
                        :placeholder="t('admin.borrower.edit.phone_placeholder')"
                    />
                    <div v-if="errors.phone" class="invalid-feedback" data-testid="error-phone">
                        {{ errors.phone }}
                    </div>
                </div>
            </div>

            <!-- Notes -->
            <div class="row mb-3 align-items-start">
                <label for="notes" class="col-sm-3 col-form-label fw-bold pt-2">
                    {{ t('admin.borrower.edit.notes') }}
                </label>
                <div class="col-sm-9">
                    <textarea
                        class="form-control"
                        :class="{ 'is-invalid': errors.notes }"
                        id="notes"
                        data-testid="input-notes"
                        v-model="localData.notes"
                        rows="3"
                        :placeholder="t('admin.borrower.edit.notes_placeholder')"
                    ></textarea>
                    <div v-if="errors.notes" class="invalid-feedback" data-testid="error-notes">
                        {{ errors.notes }}
                    </div>
                </div>
            </div>
        </div>
    `
};
