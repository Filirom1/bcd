/**
 * AdvancedFilters Component
 * Availability, language, medium type filters for catalog
 */

const { defineComponent, ref, computed, onMounted } = Vue;
const { useI18n } = VueI18n;
import { parseCsv } from '../../utils/domain.js';
import FilterSelect from '../ui/FilterSelect.js';
import ColumnSelector from './ColumnSelector.js';

export default defineComponent({
    name: 'AdvancedFilters',

    components: {
        FilterSelect,
        ColumnSelector
    },

    props: {
        filters: {
            type: Object,
            required: true
        },
        settings: {
            type: Object,
            default: null
        },
        shelfLocations: {
            type: Array,
            default: () => []
        },
        viewMode: {
            type: String,
            default: 'table'
        },
        visibleColumns: {
            type: Array,
            default: () => []
        }
    },

    emits: ['update:filters', 'filter', 'update:view-mode', 'toggle-column', 'reset-columns'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const showAdvanced = ref(false);

        const availabilityOptions = [
            { value: 'all', label: t('catalog.all_items') },
            { value: 'available', label: t('catalog.available_only') },
            { value: 'borrowed', label: t('catalog.borrowed_only') },
            { value: 'reserved', label: t('catalog.reserved_only') }
        ];

        const locationOptions = computed(() =>
            props.shelfLocations.map(loc => ({ value: loc, label: loc }))
        );

        const levelSuggestions = computed(() => parseCsv(props.settings?.catalog_levels));
        const languageSuggestions = computed(() => parseCsv(props.settings?.catalog_languages));
        const mediumTypeSuggestions = computed(() => parseCsv(props.settings?.catalog_medium_types));

        const updateFilter = (key, value) => {
            const newFilters = { ...props.filters, [key]: value };
            emit('update:filters', newFilters);
            emit('filter', newFilters);
        };

        const clearFilters = () => {
            const clearedFilters = {
                availability: 'all',
                level: '',
                language: '',
                medium_type: '',
                shelf_location: ''
            };
            emit('update:filters', clearedFilters);
            emit('filter', clearedFilters);
        };

        const toggleAdvanced = () => {
            showAdvanced.value = !showAdvanced.value;
        };

        return {
            showAdvanced,
            availabilityOptions,
            locationOptions,
            levelSuggestions,
            languageSuggestions,
            mediumTypeSuggestions,
            updateFilter,
            clearFilters,
            toggleAdvanced,
            t
        };
    },

    template: `
        <div class="card mb-3">
            <div class="card-body">
                <div class="row g-3">
                    <!-- Availability Filter -->
                    <div class="col-md-4">
                        <label class="form-label">{{ t('catalog.filter_availability') }}</label>
                        <filter-select
                            :model-value="filters.availability"
                            :options="availabilityOptions"
                            :show-placeholder="false"
                            @update:model-value="updateFilter('availability', $event)"
                        />
                    </div>

                    <!-- Advanced Filters Toggle & View Mode -->
                    <div class="col-md-8 d-flex align-items-end justify-content-between">
                        <div>
                            <button
                                type="button"
                                class="btn btn-outline-primary me-2"
                                @click="toggleAdvanced"
                            >
                                <i class="bi bi-funnel"></i>
                                {{ t('catalog.advanced_filters') }}
                                <i :class="showAdvanced ? 'bi-chevron-up' : 'bi-chevron-down'" class="ms-1"></i>
                            </button>
                            <button
                                type="button"
                                class="btn btn-outline-secondary"
                                @click="clearFilters"
                            >
                                <i class="bi bi-x-circle"></i>
                                {{ t('catalog.clear_filters') }}
                            </button>
                        </div>
                        <div class="d-flex gap-2">
                            <div class="btn-group btn-group-sm" role="group">
                                <button
                                    type="button"
                                    :class="['btn', viewMode === 'table' ? 'btn-primary' : 'btn-outline-primary']"
                                    @click="$emit('update:view-mode', 'table')"
                                    :title="t('catalog.table_view') || 'Vue tableau'"
                                >
                                    <i class="bi bi-table"></i>
                                </button>
                                <button
                                    type="button"
                                    :class="['btn', viewMode === 'cards' ? 'btn-primary' : 'btn-outline-primary']"
                                    @click="$emit('update:view-mode', 'cards')"
                                    :title="t('catalog.card_view') || 'Vue cartes'"
                                >
                                    <i class="bi bi-grid-3x3-gap"></i>
                                </button>
                            </div>
                            <column-selector
                                v-if="viewMode === 'table'"
                                :visible-columns="visibleColumns"
                                @toggle-column="$emit('toggle-column', $event)"
                                @reset="$emit('reset-columns')"
                            />
                        </div>
                    </div>
                </div>

                <!-- Advanced Filters Section -->
                <div v-if="showAdvanced" class="row g-3 mt-2">
                    <!-- Medium Type -->
                    <div class="col-md-3">
                        <label class="form-label">{{ t('catalog.medium_type') || 'Support' }}</label>
                        <input
                            type="text"
                            class="form-control"
                            :value="filters.medium_type"
                            list="filter-medium-type-suggestions"
                            @input="updateFilter('medium_type', $event.target.value)"
                            :placeholder="t('catalog.medium_type') || 'Support'"
                        />
                        <datalist id="filter-medium-type-suggestions">
                            <option v-for="s in mediumTypeSuggestions" :key="s" :value="s" />
                        </datalist>
                    </div>

                    <!-- Level -->
                    <div class="col-md-3">
                        <label class="form-label">{{ t('bibliographic.level') }}</label>
                        <input
                            type="text"
                            class="form-control"
                            :value="filters.level"
                            list="filter-level-suggestions"
                            @input="updateFilter('level', $event.target.value)"
                            :placeholder="t('bibliographic.level')"
                        />
                        <datalist id="filter-level-suggestions">
                            <option v-for="s in levelSuggestions" :key="s" :value="s" />
                        </datalist>
                    </div>

                    <!-- Language -->
                    <div class="col-md-3">
                        <label class="form-label">{{ t('catalog.language') }}</label>
                        <input
                            type="text"
                            class="form-control"
                            :value="filters.language"
                            list="filter-language-suggestions"
                            @input="updateFilter('language', $event.target.value)"
                            :placeholder="t('catalog.language')"
                        />
                        <datalist id="filter-language-suggestions">
                            <option v-for="s in languageSuggestions" :key="s" :value="s" />
                        </datalist>
                    </div>

                </div>
            </div>
        </div>
    `
});
