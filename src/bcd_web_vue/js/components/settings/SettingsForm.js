/**
 * Settings Form Component
 * Form with 14 fields matching HTMX version exactly
 */

const { defineComponent, ref } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'SettingsForm',

    props: {
        loading: Boolean,
        settings: {
            type: Object,
            required: true
        }
    },

    emits: ['save', 'reset'],

    setup(props, { emit }) {
        const { t } = useI18n();

        const handleSubmit = () => {
            emit('save');
        };

        const handleReset = () => {
            emit('reset');
        };

        return {
            t,
            handleSubmit,
            handleReset
        };
    },

    template: `
        <form @submit.prevent="handleSubmit" class="settings-form">
            <div class="row g-3">
                <!-- Library Information -->
                <div class="col-12">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-building"></i>
                        {{ t('settings.library_information') }}
                    </h4>
                </div>

                <div class="col-md-6">
                    <label for="library_name" class="form-label">
                        {{ t('settings.library_name') }}
                    </label>
                    <input
                        type="text"
                        class="form-control"
                        id="library_name"
                        v-model="settings.library_name"
                        required
                    />
                </div>

                <div class="col-md-6">
                    <label for="library_code" class="form-label">
                        {{ t('settings.library_code') }}
                    </label>
                    <input
                        type="text"
                        class="form-control"
                        id="library_code"
                        v-model="settings.library_code"
                    />
                    <small class="form-text text-muted">
                        {{ t('settings.library_code_help') }}
                    </small>
                </div>

                <!-- Circulation Settings -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-arrow-repeat"></i>
                        {{ t('settings.circulation_settings') }}
                    </h4>
                </div>

                <div class="col-md-4">
                    <label for="loan_duration_days" class="form-label">
                        {{ t('settings.loan_duration') }}
                    </label>
                    <input
                        type="number"
                        class="form-control"
                        id="loan_duration_days"
                        v-model.number="settings.loan_duration_days"
                        min="1"
                        max="365"
                        required
                    />
                </div>

                <div class="col-md-4">
                    <label for="loan_limit_default" class="form-label">
                        {{ t('settings.loan_limit_default') }}
                    </label>
                    <input
                        type="number"
                        class="form-control"
                        id="loan_limit_default"
                        v-model.number="settings.loan_limit_default"
                        min="1"
                        max="10"
                        required
                    />
                </div>

                <div class="col-md-4">
                    <label for="loan_limit_teacher" class="form-label">
                        {{ t('settings.loan_limit_teacher') }}
                    </label>
                    <input
                        type="number"
                        class="form-control"
                        id="loan_limit_teacher"
                        v-model.number="settings.loan_limit_teacher"
                        min="1"
                        max="20"
                        required
                    />
                </div>

                <div class="col-md-4">
                    <label for="renewal_limit" class="form-label">
                        {{ t('settings.renewal_limit') }}
                    </label>
                    <input
                        type="number"
                        class="form-control"
                        id="renewal_limit"
                        v-model.number="settings.renewal_limit"
                        min="0"
                        max="10"
                        required
                    />
                </div>

                <div class="col-md-4">
                    <label for="hold_expiration_days" class="form-label">
                        {{ t('settings.hold_expiration_days') }}
                    </label>
                    <input
                        type="number"
                        class="form-control"
                        id="hold_expiration_days"
                        v-model.number="settings.hold_expiration_days"
                        min="1"
                        max="30"
                        required
                    />
                </div>

                <div class="col-md-4">
                    <label for="max_holds_per_borrower" class="form-label">
                        {{ t('settings.max_holds_per_borrower') }}
                    </label>
                    <input
                        type="number"
                        class="form-control"
                        id="max_holds_per_borrower"
                        v-model.number="settings.max_holds_per_borrower"
                        min="1"
                        max="10"
                        required
                    />
                </div>

                <!-- Academic Year Settings -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-calendar"></i>
                        {{ t('settings.academic_year_settings') }}
                    </h4>
                </div>

                <div class="col-md-6">
                    <label for="academic_year_start_month" class="form-label">
                        {{ t('settings.academic_year_start_month') }}
                    </label>
                    <select
                        class="form-select"
                        id="academic_year_start_month"
                        v-model.number="settings.academic_year_start_month"
                        required
                    >
                        <option v-for="month in 12" :key="month" :value="month">
                            {{ month }}
                        </option>
                    </select>
                    <small class="form-text text-muted">
                        {{ t('settings.academic_year_start_month_help') }}
                    </small>
                </div>

                <div class="col-md-6">
                    <label for="academic_year_current" class="form-label">
                        {{ t('settings.academic_year_current') }}
                    </label>
                    <input
                        type="text"
                        class="form-control"
                        id="academic_year_current"
                        v-model="settings.academic_year_current"
                        pattern="\\d{4}-\\d{4}"
                        placeholder="2024-2025"
                        required
                    />
                    <small class="form-text text-muted">
                        {{ t('settings.academic_year_format') }}
                    </small>
                </div>

                <!-- System Settings -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-gear"></i>
                        {{ t('settings.system_settings') }}
                    </h4>
                </div>

                <div class="col-md-4">
                    <label for="language" class="form-label">
                        {{ t('settings.language') }}
                    </label>
                    <select
                        class="form-select"
                        id="language"
                        v-model="settings.language"
                        required
                    >
                        <option value="fr">Français</option>
                        <option value="en">English</option>
                    </select>
                </div>

                <div class="col-md-4">
                    <label for="date_format" class="form-label">
                        {{ t('settings.date_format') }}
                    </label>
                    <select
                        class="form-select"
                        id="date_format"
                        v-model="settings.date_format"
                        required
                    >
                        <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                        <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                        <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                    </select>
                </div>

                <div class="col-md-4">
                    <label for="barcode_type" class="form-label">
                        {{ t('settings.barcode_type') }}
                    </label>
                    <select
                        class="form-select"
                        id="barcode_type"
                        v-model="settings.barcode_type"
                        required
                    >
                        <option value="code39">Code 39</option>
                        <option value="code128">Code 128</option>
                        <option value="ean13">EAN-13</option>
                    </select>
                </div>

                <!-- Barcode Settings -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-upc-scan"></i>
                        {{ t('settings.barcode_settings') }}
                    </h4>
                </div>

                <div class="col-md-4">
                    <label for="borrower_barcode_prefix" class="form-label">
                        {{ t('settings.borrower_barcode_prefix') }}
                    </label>
                    <input
                        type="text"
                        class="form-control"
                        id="borrower_barcode_prefix"
                        v-model="settings.borrower_barcode_prefix"
                        maxlength="10"
                        required
                    />
                    <small class="form-text text-muted">
                        {{ t('settings.borrower_barcode_prefix_help') }}
                    </small>
                </div>

                <div class="col-md-4">
                    <label for="item_barcode_prefix" class="form-label">
                        {{ t('settings.item_barcode_prefix') }}
                    </label>
                    <input
                        type="text"
                        class="form-control"
                        id="item_barcode_prefix"
                        v-model="settings.item_barcode_prefix"
                        maxlength="10"
                        required
                    />
                    <small class="form-text text-muted">
                        {{ t('settings.item_barcode_prefix_help') }}
                    </small>
                </div>

                <!-- Catalog Lists -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-tags"></i>
                        {{ t('settings.catalog_lists') }}
                    </h4>
                    <p class="text-muted small">{{ t('settings.catalog_lists_help') }}</p>
                </div>

                <div class="col-md-6">
                    <label for="catalog_medium_types" class="form-label">{{ t('settings.catalog_medium_types') }}</label>
                    <textarea
                        class="form-control"
                        id="catalog_medium_types"
                        v-model="settings.catalog_medium_types"
                        rows="3"
                        :placeholder="t('settings.catalog_medium_types_placeholder')"
                    ></textarea>
                </div>

                <div class="col-md-6">
                    <label for="catalog_genres" class="form-label">{{ t('settings.catalog_genres') }}</label>
                    <textarea
                        class="form-control"
                        id="catalog_genres"
                        v-model="settings.catalog_genres"
                        rows="3"
                        :placeholder="t('settings.catalog_genres_placeholder')"
                    ></textarea>
                </div>

                <div class="col-md-6">
                    <label for="catalog_languages" class="form-label">{{ t('settings.catalog_languages') }}</label>
                    <textarea
                        class="form-control"
                        id="catalog_languages"
                        v-model="settings.catalog_languages"
                        rows="2"
                        :placeholder="t('settings.catalog_languages_placeholder')"
                    ></textarea>
                </div>

                <div class="col-md-6">
                    <label for="catalog_levels" class="form-label">{{ t('settings.catalog_levels') }}</label>
                    <textarea
                        class="form-control"
                        id="catalog_levels"
                        v-model="settings.catalog_levels"
                        rows="2"
                        :placeholder="t('settings.catalog_levels_placeholder')"
                    ></textarea>
                </div>

                <!-- Save Button -->
                <div class="col-12 mt-4">
                    <button type="submit" class="btn btn-primary" :disabled="loading">
                        <i class="bi bi-save"></i>
                        {{ t('common.save') }}
                    </button>
                    <button
                        type="button"
                        class="btn btn-secondary ms-2"
                        @click="handleReset"
                        :disabled="loading"
                    >
                        <i class="bi bi-x-circle"></i>
                        {{ t('common.cancel') }}
                    </button>
                </div>
            </div>
        </form>
    `
});
