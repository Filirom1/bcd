/**
 * Catalog-specific settings: suggestions, Dewey colors, locations and call numbers.
 */

const { defineComponent } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'CatalogSettingsForm',

    props: {
        settings: { type: Object, required: true },
        deweyColorsList: { type: Array, required: true },
        shelfLocationsList: { type: Array, required: true },
        localRules: { type: Array, required: true },
        mediumTypesOptions: { type: Array, required: true },
        shelfLocationLabels: { type: Array, required: true }
    },

    emits: [
        'update-dewey-color', 'toggle-dewey-color', 'update-shelf-location-label',
        'update-shelf-location-color', 'toggle-shelf-location-color',
        'add-shelf-location', 'remove-shelf-location', 'add-call-number-rule',
        'remove-call-number-rule', 'move-call-number-rule-up', 'move-call-number-rule-down'
    ],

    setup() {
        const { t } = useI18n();
        return { t };
    },

    template: `
        <div class="row g-3">
            <div class="col-12">
                <h4 class="border-bottom pb-2 mb-3"><i class="bi bi-tags me-1"></i>{{ t('settings.catalog_lists') }}</h4>
                <p class="text-muted small">{{ t('settings.catalog_lists_help') }}</p>
            </div>
            <div class="col-md-6">
                <label for="catalog_medium_types" class="form-label">{{ t('settings.catalog_medium_types') }}</label>
                <textarea id="catalog_medium_types" v-model="settings.catalog_medium_types" class="form-control" rows="3" :placeholder="t('settings.catalog_medium_types_placeholder')"></textarea>
            </div>
            <div class="col-md-6">
                <label for="catalog_languages" class="form-label">{{ t('settings.catalog_languages') }}</label>
                <textarea id="catalog_languages" v-model="settings.catalog_languages" class="form-control" rows="2" :placeholder="t('settings.catalog_languages_placeholder')"></textarea>
            </div>
            <div class="col-md-6">
                <label for="catalog_levels" class="form-label">{{ t('settings.catalog_levels') }}</label>
                <textarea id="catalog_levels" v-model="settings.catalog_levels" class="form-control" rows="2" :placeholder="t('settings.catalog_levels_placeholder')"></textarea>
            </div>

            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3"><i class="bi bi-palette me-1"></i>{{ t('settings.dewey_colors') }}</h4>
                <p class="text-muted small">{{ t('settings.dewey_colors_help') }}</p>
            </div>
            <div class="col-12">
                <div class="form-check form-switch mb-2">
                    <input id="dewey_colors_enabled" v-model="settings.dewey_colors_enabled" type="checkbox" class="form-check-input" />
                    <label for="dewey_colors_enabled" class="form-check-label">{{ t('settings.dewey_colors_enable') }}</label>
                </div>
                <div v-if="settings.dewey_colors_enabled !== false" class="d-flex flex-column gap-2">
                    <div v-for="(color, n) in deweyColorsList" :key="n" class="d-flex align-items-center gap-2">
                        <input type="checkbox" class="form-check-input flex-shrink-0" :checked="!!color" @change="$emit('toggle-dewey-color', n)" />
                        <input v-if="color" type="color" class="form-control form-control-color flex-shrink-0" style="width:2.5rem;height:2rem;padding:2px" :value="color" @input="$emit('update-dewey-color', n, $event.target.value)" />
                        <span class="small text-muted">{{ n }} · {{ t('dewey.class_full.' + n) }}</span>
                    </div>
                </div>
            </div>

            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3"><i class="bi bi-geo-alt me-1"></i>{{ t('settings.shelf_locations') }}</h4>
                <p class="text-muted small">{{ t('settings.shelf_locations_help') }}</p>
            </div>
            <div class="col-12">
                <div class="d-flex flex-column gap-2">
                    <div v-for="(loc, idx) in shelfLocationsList" :key="idx" class="d-flex align-items-center gap-2">
                        <input type="text" class="form-control" style="max-width:240px" :value="loc.label" :placeholder="t('settings.shelf_location_label_placeholder')" @input="$emit('update-shelf-location-label', idx, $event.target.value)" />
                        <input type="checkbox" class="form-check-input flex-shrink-0" :checked="!!loc.color" @change="$emit('toggle-shelf-location-color', idx)" />
                        <input v-if="loc.color" type="color" class="form-control form-control-color flex-shrink-0" style="width:2.5rem;height:2rem;padding:2px" :value="loc.color" @input="$emit('update-shelf-location-color', idx, $event.target.value)" />
                        <button type="button" class="btn btn-sm btn-outline-danger flex-shrink-0" @click="$emit('remove-shelf-location', idx)"><i class="bi bi-trash"></i></button>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary mt-2" @click="$emit('add-shelf-location')"><i class="bi bi-plus-circle me-1"></i>{{ t('settings.shelf_location_add') }}</button>
            </div>

            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3"><i class="bi bi-tag me-1"></i>{{ t('settings.call_number_rules') }}</h4>
                <p class="text-muted small">{{ t('settings.call_number_rules_help') }}</p>
            </div>
            <div class="col-12">
                <div class="table-responsive">
                    <table class="table table-sm table-borderless align-middle">
                        <thead><tr><th style="width:100px">{{ t('settings.rule_order') }}</th><th>{{ t('settings.rule_if_medium') }}</th><th>{{ t('catalog.shelf_location') }}</th><th>{{ t('settings.rule_then_pattern') }}</th><th style="width:50px"></th></tr></thead>
                        <tbody>
                            <tr v-for="(rule, idx) in localRules" :key="idx">
                                <td><div class="btn-group btn-group-sm"><button type="button" class="btn btn-outline-secondary" :disabled="idx === 0" @click="$emit('move-call-number-rule-up', idx)"><i class="bi bi-arrow-up"></i></button><button type="button" class="btn btn-outline-secondary" :disabled="idx === localRules.length - 1" @click="$emit('move-call-number-rule-down', idx)"><i class="bi bi-arrow-down"></i></button></div></td>
                                <td><input v-model="rule.medium_type" type="text" class="form-control form-control-sm" list="settings-medium-suggestions" :placeholder="t('settings.all_any')" /></td>
                                <td><input v-model="rule.shelf_location" type="text" class="form-control form-control-sm" list="settings-shelf-suggestions" :placeholder="t('settings.all_any')" /></td>
                                <td><input v-model="rule.pattern" type="text" class="form-control form-control-sm" :placeholder="t('settings.manual_entry_placeholder')" /></td>
                                <td><button type="button" class="btn btn-sm btn-outline-danger" @click="$emit('remove-call-number-rule', idx)"><i class="bi bi-trash"></i></button></td>
                            </tr>
                        </tbody>
                    </table>
                    <datalist id="settings-shelf-suggestions"><option v-for="s in shelfLocationLabels" :key="s" :value="s">{{ s }}</option></datalist>
                    <datalist id="settings-medium-suggestions"><option v-for="m in mediumTypesOptions" :key="m" :value="m">{{ m }}</option></datalist>
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary mt-2" @click="$emit('add-call-number-rule')"><i class="bi bi-plus-circle me-1"></i>{{ t('settings.rule_add') }}</button>
                <div class="card bg-light mt-3"><div class="card-body py-2">
                    <span class="small fw-bold text-muted d-block mb-1">{{ t('settings.rule_guide') }}</span>
                    <span v-for="key in ['aut1','aut3','ser1','ser3','ill1','ill3','tit1','tit3','dewey']" :key="key" class="small text-muted d-block">{{ t('settings.rule_guide_' + key, { [key.toUpperCase()]: '{' + key.toUpperCase() + '}' }) }}</span>
                </div></div>
            </div>
        </div>
    `
});
