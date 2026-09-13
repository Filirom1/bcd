/**
 * Settings form coordinator.
 *
 * The two large setting groups are rendered by dedicated components. Keeping the
 * shared draft here means switching sections never loses unsaved changes.
 */

const { defineComponent, ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import { DEWEY_DEFAULT_COLORS, parseCsv } from '../../utils/domain.js';
import GeneralSettingsForm from './GeneralSettingsForm.js';
import CatalogSettingsForm from './CatalogSettingsForm.js';

export default defineComponent({
    name: 'SettingsForm',

    components: { GeneralSettingsForm, CatalogSettingsForm },

    props: {
        loading: Boolean,
        settings: { type: Object, required: true },
        // "all" is retained for consumers/tests that use SettingsForm directly.
        section: { type: String, default: 'all' }
    },

    emits: ['save', 'reset'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const localSettings = ref({});

        watch(() => props.settings, (value) => {
            if (value) localSettings.value = { ...value };
        }, { immediate: true, deep: true });

        // Keep the parent draft synchronized while editing either section.
        watch(localSettings, (value) => Object.assign(props.settings, value), { deep: true });

        const deweyColorsList = computed(() => {
            const colors = localSettings.value.dewey_colors;
            return Array.isArray(colors) && colors.length === 10 ? colors : DEWEY_DEFAULT_COLORS;
        });

        const updateDeweyColor = (index, color) => {
            const colors = [...deweyColorsList.value];
            colors[index] = color;
            localSettings.value.dewey_colors = colors;
        };

        const toggleDeweyColor = (index) => {
            const colors = [...deweyColorsList.value];
            colors[index] = colors[index] ? null : DEWEY_DEFAULT_COLORS[index];
            localSettings.value.dewey_colors = colors;
        };

        const shelfLocationsList = computed(() => Array.isArray(localSettings.value.catalog_shelf_locations)
            ? localSettings.value.catalog_shelf_locations : []);
        const updateShelfLocations = (locations) => {
            localSettings.value.catalog_shelf_locations = locations;
        };
        const addShelfLocation = () => updateShelfLocations([...shelfLocationsList.value, { label: '', color: null }]);
        const removeShelfLocation = (index) => updateShelfLocations(shelfLocationsList.value.filter((_, i) => i !== index));
        const updateShelfLocationLabel = (index, label) => updateShelfLocations(
            shelfLocationsList.value.map((location, i) => i === index ? { ...location, label } : location)
        );
        const updateShelfLocationColor = (index, color) => updateShelfLocations(
            shelfLocationsList.value.map((location, i) => i === index ? { ...location, color } : location)
        );
        const toggleShelfLocationColor = (index) => updateShelfLocations(
            shelfLocationsList.value.map((location, i) => i === index
                ? { ...location, color: location.color ? null : '#6c757d' } : location)
        );

        const localRules = ref([]);
        watch(() => localSettings.value.catalog_call_number_rules, (value) => {
            const rules = Array.isArray(value) ? value : [];
            if (JSON.stringify(rules) !== JSON.stringify(localRules.value)) localRules.value = rules;
        }, { immediate: true });
        watch(localRules, (value) => { localSettings.value.catalog_call_number_rules = value; }, { deep: true });

        const mediumTypesOptions = computed(() => parseCsv(localSettings.value.catalog_medium_types || ''));
        const shelfLocationLabels = computed(() => shelfLocationsList.value.map(({ label }) => label).filter(Boolean));
        const addCallNumberRule = () => localRules.value.push({ medium_type: null, shelf_location: null, pattern: '' });
        const removeCallNumberRule = (index) => localRules.value.splice(index, 1);
        const moveCallNumberRuleUp = (index) => {
            if (index > 0) [localRules.value[index - 1], localRules.value[index]] = [localRules.value[index], localRules.value[index - 1]];
        };
        const moveCallNumberRuleDown = (index) => {
            if (index < localRules.value.length - 1) [localRules.value[index], localRules.value[index + 1]] = [localRules.value[index + 1], localRules.value[index]];
        };

        const handleSubmit = () => {
            Object.assign(props.settings, localSettings.value);
            emit('save');
        };
        const handleReset = () => emit('reset');

        return {
            t, handleSubmit, handleReset, localSettings,
            deweyColorsList, updateDeweyColor, toggleDeweyColor,
            shelfLocationsList, addShelfLocation, removeShelfLocation,
            updateShelfLocationLabel, updateShelfLocationColor, toggleShelfLocationColor,
            localRules, mediumTypesOptions, shelfLocationLabels,
            addCallNumberRule, removeCallNumberRule, moveCallNumberRuleUp, moveCallNumberRuleDown
        };
    },

    template: `
        <form @submit.prevent="handleSubmit" class="settings-form">
            <general-settings-form
                v-if="section === 'all' || section === 'general'"
                :settings="localSettings"
            />
            <catalog-settings-form
                v-if="section === 'all' || section === 'catalog'"
                :settings="localSettings"
                :dewey-colors-list="deweyColorsList"
                :shelf-locations-list="shelfLocationsList"
                :local-rules="localRules"
                :medium-types-options="mediumTypesOptions"
                :shelf-location-labels="shelfLocationLabels"
                @update-dewey-color="updateDeweyColor"
                @toggle-dewey-color="toggleDeweyColor"
                @update-shelf-location-label="updateShelfLocationLabel"
                @update-shelf-location-color="updateShelfLocationColor"
                @toggle-shelf-location-color="toggleShelfLocationColor"
                @add-shelf-location="addShelfLocation"
                @remove-shelf-location="removeShelfLocation"
                @add-call-number-rule="addCallNumberRule"
                @remove-call-number-rule="removeCallNumberRule"
                @move-call-number-rule-up="moveCallNumberRuleUp"
                @move-call-number-rule-down="moveCallNumberRuleDown"
            />
            <div class="mt-4">
                <button type="submit" class="btn btn-primary" :disabled="loading"><i class="bi bi-save me-1"></i>{{ t('common.save') }}</button>
                <button type="button" class="btn btn-secondary ms-2" :disabled="loading" @click="handleReset"><i class="bi bi-x-circle me-1"></i>{{ t('common.cancel') }}</button>
            </div>
        </form>
    `
});
