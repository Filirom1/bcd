/**
 * Settings Form Component
 * Form with 14 fields matching HTMX version exactly
 */

const { defineComponent, ref, computed, watch } = Vue;
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

        const DEFAULT_DEWEY_COLORS = [
            '#000000','#9e6633','#f20000','#ff9813','#ffee00',
            '#409d42','#0fafe9','#98238b','#d3d5d4','#ffffff'
        ];

        const deweyColorsList = computed(() => {
            try {
                const parsed = JSON.parse(props.settings.dewey_colors || 'null');
                if (Array.isArray(parsed) && parsed.length === 10) return parsed;
            } catch {}
            return DEFAULT_DEWEY_COLORS;
        });

        const updateDeweyColor = (n, hex) => {
            const colors = [...deweyColorsList.value];
            colors[n] = hex;
            props.settings.dewey_colors = JSON.stringify(colors);
        };

        const toggleDeweyColor = (n) => {
            const colors = [...deweyColorsList.value];
            colors[n] = colors[n] ? null : DEFAULT_DEWEY_COLORS[n];
            props.settings.dewey_colors = JSON.stringify(colors);
        };

        const shelfLocationsList = computed(() => {
            try {
                const parsed = JSON.parse(props.settings.catalog_shelf_locations || 'null');
                if (Array.isArray(parsed)) return parsed;
            } catch {}
            return [];
        });

        const updateShelfLocations = (list) => {
            props.settings.catalog_shelf_locations = JSON.stringify(list);
        };

        const addShelfLocation = () => {
            updateShelfLocations([...shelfLocationsList.value, { label: '', color: null }]);
        };

        const removeShelfLocation = (idx) => {
            updateShelfLocations(shelfLocationsList.value.filter((_, i) => i !== idx));
        };

        const updateShelfLocationLabel = (idx, label) => {
            updateShelfLocations(shelfLocationsList.value.map((e, i) => i === idx ? { ...e, label } : e));
        };

        const updateShelfLocationColor = (idx, color) => {
            updateShelfLocations(shelfLocationsList.value.map((e, i) => i === idx ? { ...e, color } : e));
        };

        const toggleShelfLocationColor = (idx) => {
            updateShelfLocations(shelfLocationsList.value.map((e, i) =>
                i === idx ? { ...e, color: e.color ? null : '#6c757d' } : e
            ));
        };

        const localRules = ref([]);

        watch(() => props.settings.catalog_call_number_rules, (newVal) => {
            try {
                const parsed = JSON.parse(newVal || '[]');
                if (JSON.stringify(parsed) !== JSON.stringify(localRules.value)) {
                    localRules.value = parsed;
                }
            } catch {
                localRules.value = [];
            }
        }, { immediate: true });

        watch(localRules, (newVal) => {
            props.settings.catalog_call_number_rules = JSON.stringify(newVal);
        }, { deep: true });

        const mediumTypesOptions = computed(() => {
            if (!props.settings.catalog_medium_types) return [];
            return props.settings.catalog_medium_types.split(',').map(s => s.trim()).filter(s => s);
        });

        const shelfLocationLabels = computed(() => {
            return shelfLocationsList.value.map(s => s.label).filter(Boolean);
        });

        const addCallNumberRule = () => {
            localRules.value.push({ medium_type: null, shelf_location: null, pattern: '' });
        };

        const removeCallNumberRule = (idx) => {
            localRules.value.splice(idx, 1);
        };

        const moveCallNumberRuleUp = (idx) => {
            if (idx === 0) return;
            const temp = localRules.value[idx];
            localRules.value[idx] = localRules.value[idx - 1];
            localRules.value[idx - 1] = temp;
        };

        const moveCallNumberRuleDown = (idx) => {
            if (idx === localRules.value.length - 1) return;
            const temp = localRules.value[idx];
            localRules.value[idx] = localRules.value[idx + 1];
            localRules.value[idx + 1] = temp;
        };

        return {
            t,
            handleSubmit,
            handleReset,
            deweyColorsList,
            updateDeweyColor,
            toggleDeweyColor,
            shelfLocationsList,
            addShelfLocation,
            removeShelfLocation,
            updateShelfLocationLabel,
            updateShelfLocationColor,
            toggleShelfLocationColor,
            localRules,
            mediumTypesOptions,
            shelfLocationLabels,
            addCallNumberRule,
            removeCallNumberRule,
            moveCallNumberRuleUp,
            moveCallNumberRuleDown
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

                <!-- Dewey Colors -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-palette"></i>
                        {{ t('settings.dewey_colors') }}
                    </h4>
                    <p class="text-muted small">{{ t('settings.dewey_colors_help') }}</p>
                </div>

                <div class="col-12">
                    <div class="d-flex flex-column gap-2">
                        <div
                            v-for="(color, n) in deweyColorsList"
                            :key="n"
                            class="d-flex align-items-center gap-2"
                        >
                            <input
                                type="checkbox"
                                class="form-check-input flex-shrink-0"
                                :checked="!!color"
                                @change="toggleDeweyColor(n)"
                            />
                            <input
                                v-if="color"
                                type="color"
                                :value="color"
                                class="form-control form-control-color flex-shrink-0"
                                style="width:2.5rem; height:2rem; padding:2px;"
                                @input="updateDeweyColor(n, $event.target.value)"
                            />
                            <span class="small text-muted">{{ n }} · {{ t('dewey.class_full.' + n) }}</span>
                        </div>
                    </div>
                </div>

                <!-- Shelf Locations (Emplacements) -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-geo-alt"></i>
                        {{ t('settings.shelf_locations') }}
                    </h4>
                    <p class="text-muted small">{{ t('settings.shelf_locations_help') }}</p>
                </div>

                <div class="col-12">
                    <div class="d-flex flex-column gap-2">
                        <div
                            v-for="(loc, idx) in shelfLocationsList"
                            :key="idx"
                            class="d-flex align-items-center gap-2"
                        >
                            <input
                                type="text"
                                class="form-control"
                                style="max-width: 240px;"
                                :value="loc.label"
                                :placeholder="t('settings.shelf_location_label_placeholder')"
                                @input="updateShelfLocationLabel(idx, $event.target.value)"
                            />
                            <input
                                type="checkbox"
                                class="form-check-input flex-shrink-0"
                                :checked="!!loc.color"
                                @change="toggleShelfLocationColor(idx)"
                            />
                            <input
                                v-if="loc.color"
                                type="color"
                                :value="loc.color"
                                class="form-control form-control-color flex-shrink-0"
                                style="width:2.5rem; height:2rem; padding:2px;"
                                @input="updateShelfLocationColor(idx, $event.target.value)"
                            />
                            <button
                                type="button"
                                class="btn btn-sm btn-outline-danger flex-shrink-0"
                                @click="removeShelfLocation(idx)"
                            >
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary mt-2"
                        @click="addShelfLocation"
                    >
                        <i class="bi bi-plus-circle me-1"></i>
                        {{ t('settings.shelf_location_add') }}
                    </button>
                </div>

                <!-- Automatic Call Number Rules -->
                <div class="col-12 mt-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="bi bi-tag"></i>
                        {{ t('settings.call_number_rules') }}
                    </h4>
                    <p class="text-muted small">{{ t('settings.call_number_rules_help') }}</p>
                </div>

                <div class="col-12">
                    <div class="table-responsive">
                        <table class="table table-sm table-borderless align-middle">
                            <thead>
                                <tr>
                                    <th style="width: 100px;">Ordre</th>
                                    <th>{{ t('settings.rule_if_medium') }}</th>
                                    <th>{{ t('catalog.shelf_location') }}</th>
                                    <th>{{ t('settings.rule_then_pattern') }}</th>
                                    <th style="width: 50px;"></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(rule, idx) in localRules" :key="idx">
                                    <td>
                                        <div class="btn-group btn-group-sm">
                                            <button
                                                type="button"
                                                class="btn btn-outline-secondary"
                                                :disabled="idx === 0"
                                                @click="moveCallNumberRuleUp(idx)"
                                            >
                                                <i class="bi bi-arrow-up"></i>
                                            </button>
                                            <button
                                                type="button"
                                                class="btn btn-outline-secondary"
                                                :disabled="idx === localRules.length - 1"
                                                @click="moveCallNumberRuleDown(idx)"
                                            >
                                                <i class="bi bi-arrow-down"></i>
                                            </button>
                                        </div>
                                    </td>
                                    <td>
                                        <select
                                            class="form-select form-select-sm"
                                            v-model="rule.medium_type"
                                        >
                                            <option :value="null">{{ t('settings.all_any') }}</option>
                                            <option v-for="m in mediumTypesOptions" :key="m" :value="m">{{ m }}</option>
                                        </select>
                                    </td>
                                    <td>
                                        <select
                                            class="form-select form-select-sm"
                                            v-model="rule.shelf_location"
                                        >
                                            <option :value="null">{{ t('settings.all_any') }}</option>
                                            <option v-for="s in shelfLocationLabels" :key="s" :value="s">{{ s }}</option>
                                        </select>
                                    </td>
                                    <td>
                                        <input
                                            type="text"
                                            class="form-control form-control-sm"
                                            v-model="rule.pattern"
                                            :placeholder="t('settings.manual_entry_placeholder')"
                                        />
                                    </td>
                                    <td>
                                        <button
                                            type="button"
                                            class="btn btn-sm btn-outline-danger"
                                            @click="removeCallNumberRule(idx)"
                                        >
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary mt-2"
                        @click="addCallNumberRule"
                    >
                        <i class="bi bi-plus-circle me-1"></i>
                        {{ t('settings.rule_add') }}
                    </button>

                    <div class="card bg-light mt-3">
                        <div class="card-body py-2">
                            <span class="small fw-bold text-muted d-block mb-1">{{ t('settings.rule_guide') }}</span>
                            <span class="small text-muted d-block">{{ t('settings.rule_guide_aut1', { AUT1: '{AUT1}' }) }}</span>
                            <span class="small text-muted d-block">{{ t('settings.rule_guide_aut3', { AUT3: '{AUT3}' }) }}</span>
                            <span class="small text-muted d-block">{{ t('settings.rule_guide_dewey', { DEWEY: '{DEWEY}' }) }}</span>
                        </div>
                    </div>
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
