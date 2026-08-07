/**
 * SearchTab Component
 *
 * Search and filter items for inventory operations.
 * - 15 optional filters (item, record, inventory, rotation)
 * - Results capped at 200 items
 * - Add selected items to working table
 * - Displays archive cutoff warning
 */

const { defineComponent, ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { normalizeCollection } from '../../models/pagination.js';
import { useNotification } from '../../composables/useNotification.js';
import { useAppState } from '../../composables/useAppState.js';
import InventorySearchResults from './InventorySearchResults.js';
import { parseCsv } from '../../utils/domain.js';

export default defineComponent({
    name: 'SearchTab',

    components: {
        InventorySearchResults
    },

    props: {
        inventoryTable: {
            type: Object,
            required: true
        }
    },

    emits: ['switch-to-working-table'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { success, error, warning } = useNotification();
        const { settings } = useAppState();

        // Search filters (15 optional parameters)
        const filters = ref({
            q: '',
            status: '',
            condition: '',
            shelf_location: '',
            never_inventoried: null,
            inventoried_before: null,
            medium_type: '',
            target_audience: '',
            level: '',
            language: '',
            publication_year_min: null,
            publication_year_max: null,
            max_borrows: null,
            since_date: null
        });

        // Search state
        const searching = ref(false);
        const searchResults = ref([]);
        const totalCount = ref(0);
        const displayedCount = ref(0);
        const capped = ref(false);
        const archiveCutoffDate = ref(null);
        const hasSearched = ref(false);

        // Selected items from results
        const selectedItemIds = ref(new Set());

        /**
         * Perform search with current filters
         */
        const performSearch = async () => {
            searching.value = true;
            hasSearched.value = true;
            searchResults.value = [];
            totalCount.value = 0;
            selectedItemIds.value.clear();

            try {
                // Build query params (exclude empty/null values)
                const params = {};
                for (const [key, value] of Object.entries(filters.value)) {
                    if (value !== '' && value !== null && value !== undefined) {
                        params[key] = value;
                    }
                }

                const response = await apiClient.get('/inventory/items/search', params);

                const normalized = normalizeCollection(response);
                searchResults.value = normalized.items;
                totalCount.value = normalized.pagination.total_items;
                displayedCount.value = response.displayed_count;
                capped.value = response.capped;
                archiveCutoffDate.value = response.archive_cutoff_date;

                // Show archive warning if rotation filter is active and date is before cutoff
                if (filters.value.since_date && archiveCutoffDate.value) {
                    const sinceDate = new Date(filters.value.since_date);
                    const cutoffDate = new Date(archiveCutoffDate.value);
                    if (sinceDate < cutoffDate) {
                        warning(t('inventory.search.archive_warning'));
                    }
                }

            } catch (err) {
                console.error('Search error:', err);
                error(t('inventory.search.error', { error: err.message || 'Unknown error' }));
            } finally {
                searching.value = false;
            }
        };

        /**
         * Clear all filters
         */
        const clearFilters = () => {
            filters.value = {
                q: '',
                status: '',
                condition: '',
                shelf_location: '',
                never_inventoried: null,
                inventoried_before: null,
                medium_type: '',
                target_audience: '',
                level: '',
                language: '',
                publication_year_min: null,
                publication_year_max: null,
                max_borrows: null,
                since_date: null
            };
            searchResults.value = [];
            hasSearched.value = false;
            selectedItemIds.value.clear();
        };

        /**
         * Toggle item selection
         */
        const toggleSelection = (itemId) => {
            if (selectedItemIds.value.has(itemId)) {
                selectedItemIds.value.delete(itemId);
            } else {
                selectedItemIds.value.add(itemId);
            }
        };

        /**
         * Toggle select all
         */
        const toggleSelectAll = () => {
            if (selectedItemIds.value.size === searchResults.value.length) {
                selectedItemIds.value.clear();
            } else {
                selectedItemIds.value = new Set(searchResults.value.map(item => item.item_id));
            }
        };

        /**
         * Add selected items to working table
         */
        const addSelectedToWorkingTable = async () => {
            if (selectedItemIds.value.size === 0) {
                warning(t('inventory.search.no_selection'));
                return;
            }

            try {
                // Call bulk-mark API
                const response = await apiClient.post('/inventory/items/bulk-mark', {
                    item_ids: Array.from(selectedItemIds.value)
                });

                // Add items to working table with all fields
                const itemsToAdd = searchResults.value.filter(item =>
                    selectedItemIds.value.has(item.item_id)
                );

                for (const item of itemsToAdd) {
                    props.inventoryTable.addItem({
                        // Item fields
                        item_id: item.item_id,
                        bibliographic_record_id: item.bibliographic_record_id,
                        status: item.status,
                        condition: item.condition,
                        loanable: item.loanable,
                        shelf_location: item.shelf_location,
                        call_number: item.call_number,
                        last_inventoried_at: new Date().toISOString(),
                        // Record fields (from search results JOIN)
                        title: item.title,
                        level: item.level,
                        target_audience: item.target_audience,
                        language: item.language,
                        medium_type: item.medium_type
                    });
                }

                success(t('inventory.search.added_to_table', {
                    count: response.items_updated
                }));

                // Switch to working table tab
                emit('switch-to-working-table');

            } catch (err) {
                console.error('Add to table error:', err);
                error(t('inventory.search.add_error', { error: err.message || 'Unknown error' }));
            }
        };

        /**
         * Computed: Selected count
         */
        const selectedCount = computed(() => selectedItemIds.value.size);

        /**
         * Computed: Is rotation filter active
         */
        const rotationFilterActive = computed(() => {
            return filters.value.max_borrows !== null && filters.value.since_date !== null;
        });

        /**
         * Computed: Parse vocabulary lists from settings
         */
        const levelOptions = computed(() => {
            return parseCsv(settings.value?.catalog_levels);
        });

        const mediumTypeOptions = computed(() => {
            return parseCsv(settings.value?.catalog_medium_types);
        });

        const languageOptions = computed(() => {
            return parseCsv(settings.value?.catalog_languages);
        });

        return {
            t,
            filters,
            searching,
            searchResults,
            totalCount,
            displayedCount,
            capped,
            hasSearched,
            selectedItemIds,
            selectedCount,
            rotationFilterActive,
            levelOptions,
            mediumTypeOptions,
            languageOptions,
            performSearch,
            clearFilters,
            toggleSelection,
            toggleSelectAll,
            addSelectedToWorkingTable
        };
    },

    template: `
        <div class="search-tab">
            <!-- Filters Section -->
            <div class="mb-3">
                <h6 class="text-uppercase small text-muted mb-3">{{ t('inventory.search.filters') }}</h6>

                <!-- Text search -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.text_search') }}</label>
                    <input
                        v-model="filters.q"
                        type="text"
                        class="form-control"
                        :placeholder="t('inventory.search.text_search_placeholder')"
                        @keyup.enter="performSearch"
                    />
                </div>

                <!-- Status -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.status') }}</label>
                    <select v-model="filters.status" class="form-select">
                        <option value="">{{ t('inventory.search.all') }}</option>
                        <option value="available">{{ t('item.status_available') }}</option>
                        <option value="on_loan">{{ t('item.status_on_loan') }}</option>
                        <option value="on_hold">{{ t('item.status_on_hold') }}</option>
                        <option value="in_repair">{{ t('item.status_in_repair') }}</option>
                        <option value="lost">{{ t('item.status_lost') }}</option>
                        <option value="withdrawn">{{ t('item.status_withdrawn') }}</option>
                    </select>
                </div>

                <!-- Condition -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.condition') }}</label>
                    <select v-model="filters.condition" class="form-select">
                        <option value="">{{ t('inventory.search.all') }}</option>
                        <option value="good">{{ t('item.condition_good') }}</option>
                        <option value="damaged">{{ t('item.condition_damaged') }}</option>
                    </select>
                </div>

                <!-- Location -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.location') }}</label>
                    <input
                        v-model="filters.shelf_location"
                        type="text"
                        class="form-control form-control-sm"
                        list="search-shelf-location-suggestions"
                        :placeholder="t('inventory.search.location_placeholder')"
                    />
                    <datalist id="search-shelf-location-suggestions">
                        <option value="__none__">{{ t('inventory.search.not_defined') }}</option>
                    </datalist>
                </div>

                <!-- Never inventoried checkbox -->
                <div class="mb-3">
                    <div class="form-check">
                        <input
                            v-model="filters.never_inventoried"
                            type="checkbox"
                            class="form-check-input"
                            id="neverInventoried"
                        />
                        <label class="form-check-label" for="neverInventoried">
                            {{ t('inventory.search.never_inventoried') }}
                        </label>
                    </div>
                </div>

                <!-- Inventoried before date -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.inventoried_before') }}</label>
                    <input
                        v-model="filters.inventoried_before"
                        type="date"
                        class="form-control form-control-sm"
                    />
                </div>

                <!-- Medium type -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.medium_type') }}</label>
                    <input
                        v-model="filters.medium_type"
                        type="text"
                        class="form-control form-control-sm"
                        list="search-medium-type-suggestions"
                        :placeholder="t('inventory.search.all')"
                    />
                    <datalist id="search-medium-type-suggestions">
                        <option value="__none__">{{ t('inventory.search.not_defined') }}</option>
                        <option v-for="option in mediumTypeOptions" :key="option" :value="option">{{ option }}</option>
                    </datalist>
                </div>

                <!-- Target audience -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.target_audience') }}</label>
                    <select v-model="filters.target_audience" class="form-select">
                        <option value="">{{ t('inventory.search.all') }}</option>
                        <option value="__none__">{{ t('inventory.search.not_defined') }}</option>
                        <option value="child">{{ t('bibliographic.audience_child') }}</option>
                        <option value="youth">{{ t('bibliographic.audience_youth') }}</option>
                        <option value="adult">{{ t('bibliographic.audience_adult') }}</option>
                    </select>
                </div>

                <!-- Level -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.level') }}</label>
                    <input
                        v-model="filters.level"
                        type="text"
                        class="form-control form-control-sm"
                        list="search-level-suggestions"
                        :placeholder="t('inventory.search.all')"
                    />
                    <datalist id="search-level-suggestions">
                        <option value="__none__">{{ t('inventory.search.not_defined') }}</option>
                        <option v-for="option in levelOptions" :key="option" :value="option">{{ option }}</option>
                    </datalist>
                </div>

                <!-- Language -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.language') }}</label>
                    <input
                        v-model="filters.language"
                        type="text"
                        class="form-control form-control-sm"
                        list="search-language-suggestions"
                        :placeholder="t('inventory.search.all')"
                    />
                    <datalist id="search-language-suggestions">
                        <option value="__none__">{{ t('inventory.search.not_defined') }}</option>
                        <option v-for="option in languageOptions" :key="option" :value="option">{{ option }}</option>
                    </datalist>
                </div>

                <!-- Publication year min -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.publication_year_min') }}</label>
                    <input
                        v-model.number="filters.publication_year_min"
                        type="number"
                        class="form-control form-control-sm"
                        :placeholder="t('inventory.search.year_placeholder')"
                    />
                </div>

                <!-- Publication year max -->
                <div class="mb-3">
                    <label class="form-label">{{ t('inventory.search.publication_year_max') }}</label>
                    <input
                        v-model.number="filters.publication_year_max"
                        type="number"
                        class="form-control form-control-sm"
                        :placeholder="t('inventory.search.year_placeholder')"
                    />
                </div>

                <!-- Rotation filter (CREW method) -->
                <div class="card bg-light mb-3">
                    <div class="card-body">
                        <h6 class="card-title">{{ t('inventory.search.rotation_filter') }}</h6>

                        <div class="mb-2">
                            <label class="form-label">{{ t('inventory.search.max_borrows') }}</label>
                            <input
                                v-model.number="filters.max_borrows"
                                type="number"
                                class="form-control form-control-sm"
                                :placeholder="t('inventory.search.max_borrows_placeholder')"
                                min="0"
                            />
                        </div>

                        <div class="mb-2">
                            <label class="form-label">{{ t('inventory.search.since_date') }}</label>
                            <input
                                v-model="filters.since_date"
                                type="date"
                                class="form-control form-control-sm"
                            />
                        </div>

                        <small class="text-muted">{{ t('inventory.search.rotation_help') }}</small>
                    </div>
                </div>

                <!-- Action buttons -->
                <div class="d-grid gap-2">
                    <button
                        @click="performSearch"
                        class="btn btn-primary btn-sm"
                        :disabled="searching"
                    >
                        <i class="bi bi-search"></i>
                        {{ searching ? t('inventory.search.searching') : t('inventory.search.search_button') }}
                    </button>
                    <button
                        @click="clearFilters"
                        class="btn btn-outline-secondary btn-sm"
                    >
                        <i class="bi bi-x-circle"></i>
                        {{ t('inventory.search.clear_filters') }}
                    </button>
                </div>
            </div>

            <!-- Results Section -->
            <div v-if="hasSearched">
                <h6 class="text-uppercase small text-muted mb-2">
                    {{ t('inventory.search.results_title') }}
                </h6>

                <div v-if="capped" class="alert alert-warning py-2 px-2 mb-2" style="font-size: 0.8rem;">
                    <i class="bi bi-exclamation-triangle"></i>
                    {{ t('inventory.search.results_capped', { displayed: displayedCount, total: totalCount }) }}
                </div>
                <div v-else class="text-muted mb-2" style="font-size: 0.8rem;">
                    {{ t('inventory.search.results_count', { count: displayedCount }) }}
                </div>

                <InventorySearchResults
                    :items="searchResults"
                    :selected-ids="selectedItemIds"
                    :show-period-loan-count="rotationFilterActive"
                    @toggle-selection="toggleSelection"
                    @toggle-select-all="toggleSelectAll"
                />

                <!-- Add to table button -->
                <div v-if="searchResults.length > 0" class="mt-2">
                    <button
                        @click="addSelectedToWorkingTable"
                        class="btn btn-success btn-sm w-100"
                        :disabled="selectedCount === 0"
                    >
                        <i class="bi bi-plus-circle"></i>
                        {{ t('inventory.search.add_to_table', { count: selectedCount }) }}
                    </button>
                </div>

                <div v-if="searchResults.length === 0" class="text-center text-muted py-4">
                    <i class="bi bi-inbox" style="font-size: 2rem;"></i>
                    <p class="mt-2 mb-0" style="font-size: 0.85rem;">{{ t('inventory.search.no_results') }}</p>
                </div>
            </div>
        </div>
    `
});
