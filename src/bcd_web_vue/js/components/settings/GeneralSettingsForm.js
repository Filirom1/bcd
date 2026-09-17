/**
 * General library settings.
 * Kept separate from catalog configuration so the settings page stays compact.
 */

const { defineComponent } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'GeneralSettingsForm',

    props: {
        settings: {
            type: Object,
            required: true
        }
    },

    setup() {
        const { t } = useI18n();
        return { t };
    },

    template: `
        <div class="row g-3">
            <div class="col-12">
                <h4 class="border-bottom pb-2 mb-3">
                    <i class="bi bi-building me-1"></i>
                    {{ t('settings.library_information') }}
                </h4>
            </div>
            <div class="col-md-6">
                <label for="library_name" class="form-label">{{ t('settings.library_name') }}</label>
                <input id="library_name" v-model="settings.library_name" type="text" class="form-control" required />
            </div>
            <div class="col-md-6">
                <label for="library_code" class="form-label">{{ t('settings.library_code') }}</label>
                <input id="library_code" v-model="settings.library_code" type="text" class="form-control" />
                <small class="form-text text-muted">{{ t('settings.library_code_help') }}</small>
            </div>

            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3">
                    <i class="bi bi-arrow-repeat me-1"></i>
                    {{ t('settings.circulation_settings') }}
                </h4>
            </div>
            <div class="col-md-4">
                <label for="loan_duration_days" class="form-label">{{ t('settings.loan_duration') }}</label>
                <input id="loan_duration_days" v-model.number="settings.loan_duration_days" type="number" class="form-control" min="1" max="365" required />
            </div>
            <div class="col-md-4">
                <label for="loan_limit_default" class="form-label">{{ t('settings.loan_limit_default') }}</label>
                <input id="loan_limit_default" v-model.number="settings.loan_limit_default" type="number" class="form-control" min="1" max="10" required />
            </div>
            <div class="col-md-4">
                <label for="loan_limit_warning" class="form-label">{{ t('settings.loan_limit_warning') }}</label>
                <input id="loan_limit_warning" v-model.number="settings.loan_limit_warning" type="number" class="form-control" min="0" max="10" required />
            </div>
            <div class="col-md-4">
                <label for="loan_limit_teacher" class="form-label">{{ t('settings.loan_limit_teacher') }}</label>
                <input id="loan_limit_teacher" v-model.number="settings.loan_limit_teacher" type="number" class="form-control" min="1" max="20" required />
            </div>
            <div class="col-md-4">
                <label for="renewal_limit" class="form-label">{{ t('settings.renewal_limit') }}</label>
                <input id="renewal_limit" v-model.number="settings.renewal_limit" type="number" class="form-control" min="0" max="10" required />
            </div>
            <div class="col-md-4">
                <label for="hold_expiration_days" class="form-label">{{ t('settings.hold_expiration_days') }}</label>
                <input id="hold_expiration_days" v-model.number="settings.hold_expiration_days" type="number" class="form-control" min="1" max="30" required />
            </div>
            <div class="col-md-4">
                <label for="max_holds_per_borrower" class="form-label">{{ t('settings.max_holds_per_borrower') }}</label>
                <input id="max_holds_per_borrower" v-model.number="settings.max_holds_per_borrower" type="number" class="form-control" min="1" max="10" required />
            </div>

            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3">
                    <i class="bi bi-calendar me-1"></i>
                    {{ t('settings.academic_year_settings') }}
                </h4>
            </div>
            <div class="col-md-6">
                <label for="academic_year_start_month" class="form-label">{{ t('settings.academic_year_start_month') }}</label>
                <select id="academic_year_start_month" v-model.number="settings.academic_year_start_month" class="form-select" required>
                    <option v-for="month in 12" :key="month" :value="month">{{ month }}</option>
                </select>
                <small class="form-text text-muted">{{ t('settings.academic_year_start_month_help') }}</small>
            </div>
            <div class="col-md-6">
                <label for="academic_year_current" class="form-label">{{ t('settings.academic_year_current') }}</label>
                <input id="academic_year_current" v-model="settings.academic_year_current" type="text" class="form-control" pattern="\\d{4}-\\d{4}" placeholder="2024-2025" required />
                <small class="form-text text-muted">{{ t('settings.academic_year_format') }}</small>
            </div>

            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3">
                    <i class="bi bi-gear me-1"></i>
                    {{ t('settings.system_settings') }}
                </h4>
            </div>
            <div class="col-md-4">
                <label for="language" class="form-label">{{ t('settings.language') }}</label>
                <select id="language" v-model="settings.language" class="form-select" required>
                    <option value="fr">{{ t('settings.language_french') }}</option>
                    <option value="en">{{ t('settings.language_english') }}</option>
                </select>
            </div>
            <div class="col-md-4">
                <label for="date_format" class="form-label">{{ t('settings.date_format') }}</label>
                <select id="date_format" v-model="settings.date_format" class="form-select" required>
                    <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                    <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                    <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                </select>
            </div>
            <div class="col-md-4">
                <label for="barcode_type" class="form-label">{{ t('settings.barcode_type') }}</label>
                <select id="barcode_type" v-model="settings.barcode_type" class="form-select" required>
                    <option value="code39">Code 39</option>
                    <option value="code128">Code 128</option>
                    <option value="ean13">EAN-13</option>
                </select>
            </div>

            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3">
                    <i class="bi bi-upc-scan me-1"></i>
                    {{ t('settings.barcode_settings') }}
                </h4>
            </div>
            <div class="col-md-4">
                <label for="borrower_barcode_prefix" class="form-label">{{ t('settings.borrower_barcode_prefix') }}</label>
                <input id="borrower_barcode_prefix" v-model="settings.borrower_barcode_prefix" type="text" class="form-control" maxlength="10" />
                <small class="form-text text-muted">{{ t('settings.borrower_barcode_prefix_help') }}</small>
            </div>
            <div class="col-md-4">
                <label for="item_barcode_prefix" class="form-label">{{ t('settings.item_barcode_prefix') }}</label>
                <input id="item_barcode_prefix" v-model="settings.item_barcode_prefix" type="text" class="form-control" maxlength="10" />
                <small class="form-text text-muted">{{ t('settings.item_barcode_prefix_help') }}</small>
            </div>
        </div>
    `
});
