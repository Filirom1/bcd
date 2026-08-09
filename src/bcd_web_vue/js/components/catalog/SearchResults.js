/**
 * SearchResults Component
 * Displays catalog search results with availability badges
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import { formatAuthors, parseJsonSetting } from '../../utils/domain.js';
import DataTable from '../ui/DataTable.js';
import { useAppState } from '../../composables/useAppState.js';
import { useItemBadge } from '../../composables/useItemBadge.js';

export default defineComponent({
    name: 'SearchResults',

    components: {
        DataTable
    },

    props: {
        results: {
            type: Array,
            default: () => []
        },
        loading: {
            type: Boolean,
            default: false
        },
        query: {
            type: String,
            default: ''
        },
        viewMode: {
            type: String,
            default: 'cards',
            validator: (value) => ['cards', 'table'].includes(value)
        },
        visibleColumns: {
            type: Array,
            default: () => ['title', 'author', 'publisher', 'year', 'copies', 'availability']
        },
        selectedIds: {
            type: Set,
            default: () => new Set()
        },
        selectAllChecked: {
            type: Boolean,
            default: false
        }
    },

    emits: ['record-click', 'toggle-selection', 'toggle-select-all'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { settings } = useAppState();
        const { getShelfBadge, getCoteBadge } = useItemBadge(settings);

        const hasResults = computed(() => props.results.length > 0);
        const hasQuery = computed(() => props.query.trim().length > 0);

        const isColumnVisible = (columnId) => {
            return props.visibleColumns.includes(columnId);
        };

        // Define table columns based on visible columns (with checkbox column)
        const tableColumns = computed(() => {
            const allColumns = [
                { key: 'select', label: '', width: '40px' },
                // Basic information
                { key: 'title', label: t('catalog.title') },
                { key: 'author', label: t('catalog.author') },
                { key: 'isbn', label: t('catalog.isbn') },
                // Publication information
                { key: 'publisher', label: t('catalog.publisher') },
                { key: 'year', label: t('catalog.year') },
                { key: 'collection', label: t('bibliographic.collection') },
                { key: 'series_number', label: t('bibliographic.series_number') },
                // Classification
                { key: 'medium_type', label: t('bibliographic.medium_type') },
                { key: 'target_audience', label: t('bibliographic.target_audience') },
                { key: 'level', label: t('bibliographic.level') },
                { key: 'language', label: t('catalog.language') },
                // Physical description
                { key: 'binding_type', label: t('bibliographic.binding_type') },
                { key: 'page_count', label: t('bibliographic.page_count') },
                { key: 'has_illustrations', label: t('bibliographic.has_illustrations') },
                // Availability
                { key: 'copies', label: t('catalog.copies') },
                { key: 'availability', label: t('catalog.availability') }
            ];
            // Always include checkbox column, filter the rest
            return [
                allColumns[0],
                ...allColumns.slice(1).filter(col => isColumnVisible(col.key))
            ];
        });

        const getAvailabilityBadge = (record) => {
            // API returns available_copies, not available_items_count
            const availableCount = record.available_copies || 0;
            const totalCount = record.total_items || record.total_copies || 0;

            if (totalCount === 0) {
                return { class: 'bg-secondary', text: t('catalog.no_copies'), icon: 'bi-x-circle' };
            }

            if (availableCount === 0) {
                // All copies unavailable - could be on loan, withdrawn, lost, etc.
                return { class: 'bg-danger', text: t('catalog.unavailable') || 'Unavailable', icon: 'bi-x-circle' };
            }

            if (availableCount === totalCount) {
                return { class: 'bg-success', text: t('catalog.available'), icon: 'bi-check-circle' };
            }

            // Partially available
            return {
                class: 'bg-warning',
                text: `${availableCount}/${totalCount}`,
                icon: 'bi-dash-circle'
            };
        };

        const getAuthors = (record) => {
            if (!record.authors) return record.publisher || '';
            const authors = parseJsonSetting(record.authors, record.authors);
            const joined = formatAuthors(authors);
            if (joined) return joined;
            return record.publisher || '';
        };

        const getAudienceLabel = (audience) => {
            const map = {
                'child': t('bibliographic.audience_child'),
                'youth': t('bibliographic.audience_youth'),
                'adult': t('bibliographic.audience_adult')
            };
            return map[audience] || audience;
        };

        const handleRecordClick = (record) => {
            emit('record-click', record);
        };

        // Toggle individual record selection
        const toggleRecordSelection = (recordId) => {
            emit('toggle-selection', recordId);
        };

        // Toggle select all
        const toggleSelectAll = () => {
            emit('toggle-select-all');
        };

        // Check if record is selected
        const isSelected = (recordId) => {
            return props.selectedIds.has(recordId);
        };

        return {
            hasResults,
            hasQuery,
            isColumnVisible,
            tableColumns,
            getAvailabilityBadge,
            getAuthors,
            getAudienceLabel,
            getShelfBadge,
            getCoteBadge,
            handleRecordClick,
            toggleRecordSelection,
            toggleSelectAll,
            isSelected,
            t
        };
    },

    template: `
        <div>
            <!-- No Query State -->
            <div v-if="!hasQuery && !hasResults" class="text-center py-5">
                <i class="bi bi-search display-1 text-muted mb-3"></i>
                <h5>{{ t('catalog.search_prompt') }}</h5>
            </div>

            <!-- No Results State -->
            <div v-else-if="!loading && hasQuery && !hasResults" class="text-center py-5">
                <i class="bi bi-inbox display-1 text-muted mb-3"></i>
                <h5>{{ t('catalog.no_results') }}</h5>
                <p class="text-muted">{{ t('catalog.no_results_for') }} "{{ query }}"</p>
            </div>

            <!-- Table View -->
            <data-table
                v-else-if="viewMode === 'table'"
                :columns="tableColumns"
                :rows="results"
                :loading="loading"
                clickable
                row-key="id"
                @row-click="handleRecordClick"
            >
                <!-- Custom header for checkbox column -->
                <template #header-select>
                    <input
                        type="checkbox"
                        class="form-check-input"
                        :checked="selectAllChecked"
                        @change="toggleSelectAll"
                        @click.stop
                    >
                </template>

                <template #row="{ row: record }">
                    <!-- Checkbox -->
                    <td @click.stop>
                        <input
                            type="checkbox"
                            class="form-check-input"
                            :checked="isSelected(record.id)"
                            @change="toggleRecordSelection(record.id)"
                        >
                    </td>

                    <!-- Basic Information -->
                    <td v-if="isColumnVisible('title')">
                        <span class="link-entity fw-bold">{{ record.title }}</span>
                        <div v-if="record.subtitle" class="small text-muted">
                            {{ record.subtitle }}
                        </div>
                        <div v-if="record.first_item_id || record.shelf_location || record.call_number" class="mt-1 d-flex flex-wrap align-items-center gap-1">
                            <span v-if="record.first_item_id" class="small text-muted me-1">
                                <i class="bi bi-upc"></i> {{ record.first_item_id }}
                            </span>
                            <span v-if="record.shelf_location && getShelfBadge(record.shelf_location)" :style="getShelfBadge(record.shelf_location)">{{ record.shelf_location }}</span>
                            <span v-if="record.call_number && getCoteBadge(record.call_number)" :style="getCoteBadge(record.call_number)">{{ record.call_number }}</span>
                        </div>
                    </td>
                    <td v-if="isColumnVisible('author')">{{ getAuthors(record) }}</td>
                    <td v-if="isColumnVisible('isbn')">
                        <code v-if="record.isbn" class="small">{{ record.isbn_value }}</code>
                    </td>

                    <!-- Publication Information -->
                    <td v-if="isColumnVisible('publisher')">{{ record.publisher }}</td>
                    <td v-if="isColumnVisible('year')">{{ record.publication_year }}</td>
                    <td v-if="isColumnVisible('collection')">{{ record.collection }}</td>
                    <td v-if="isColumnVisible('series_number')">{{ record.series_number }}</td>

                    <!-- Classification -->
                    <td v-if="isColumnVisible('medium_type')">{{ record.medium_type }}</td>
                    <td v-if="isColumnVisible('target_audience')">
                        <span v-if="record.target_audience" class="badge bg-info">{{ getAudienceLabel(record.target_audience) }}</span>
                    </td>
                    <td v-if="isColumnVisible('level')">{{ record.level }}</td>
                    <td v-if="isColumnVisible('language')">
                        <span v-if="record.language">{{ record.language.toUpperCase() }}</span>
                    </td>

                    <!-- Physical Description -->
                    <td v-if="isColumnVisible('binding_type')">{{ record.binding_type }}</td>
                    <td v-if="isColumnVisible('page_count')">{{ record.page_count }}</td>
                    <td v-if="isColumnVisible('has_illustrations')">
                        <i v-if="record.has_illustrations" class="bi bi-check-circle text-success"></i>
                    </td>

                    <!-- Availability -->
                    <td v-if="isColumnVisible('copies')">{{ record.total_items }}</td>
                    <td v-if="isColumnVisible('availability')">
                        <span :class="['badge', getAvailabilityBadge(record).class]">
                            <i :class="getAvailabilityBadge(record).icon"></i>
                            {{ getAvailabilityBadge(record).text }}
                        </span>
                        <span v-if="record.active_holds_count > 0" class="badge bg-primary ms-1">
                            <i class="bi bi-bookmark-fill"></i>
                            {{ record.active_holds_count }}
                        </span>
                    </td>
                </template>
            </data-table>

            <!-- Card View (Grid) -->
            <div v-else class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
                <div
                    v-for="record in results"
                    :key="record.id"
                    class="col"
                >
                    <div
                        class="card h-100 catalog-result-card"
                        @click="handleRecordClick(record)"
                        style="cursor: pointer;"
                    >
                        <img
                            v-if="record.cover_image"
                            :src="'/covers/' + record.cover_image"
                            :alt="record.title"
                            class="card-img-top"
                            style="height: 160px; object-fit: contain; background: #f8f9fa; padding: 8px;"
                            @error="$event.target.style.display = 'none'"
                        />
                        <div v-else class="text-center py-3 bg-light" style="height: 100px;">
                            <i class="bi bi-book display-6 text-muted"></i>
                        </div>
                        <div class="card-body">
                            <!-- Title -->
                            <h5 class="card-title mb-2">
                                {{ record.title }}
                                <span v-if="record.subtitle" class="d-block small text-muted mt-1">
                                    {{ record.subtitle }}
                                </span>
                            </h5>

                            <!-- Authors -->
                            <p v-if="record.authors" class="card-text text-muted small mb-2">
                                <i class="bi bi-person"></i>
                                {{ getAuthors(record) }}
                            </p>

                            <!-- Publisher, Year & Collection -->
                            <p class="card-text text-muted small mb-2">
                                <span v-if="record.publisher">
                                    <i class="bi bi-building"></i>
                                    {{ record.publisher }}
                                </span>
                                <span v-if="record.publication_year" class="ms-2">
                                    ({{ record.publication_year }})
                                </span>
                            </p>
                            <p v-if="record.collection" class="card-text text-muted small mb-2">
                                <i class="bi bi-collection"></i>
                                {{ record.collection }}
                                <span v-if="record.series_number"> #{{ record.series_number }}</span>
                            </p>

                            <!-- ISBN (if available) -->
                            <p v-if="record.isbn" class="card-text small mb-2">
                                <code class="small">{{ record.isbn_value }}</code>
                            </p>

                            <!-- Code-barre · Emplacement · Cote -->
                            <div v-if="record.first_item_id || record.shelf_location || record.call_number" class="mb-2 d-flex flex-wrap align-items-center gap-1">
                                <span v-if="record.first_item_id" class="small text-muted me-1">
                                    <i class="bi bi-upc"></i> {{ record.first_item_id }}
                                </span>
                                <span v-if="record.shelf_location && getShelfBadge(record.shelf_location)" :style="getShelfBadge(record.shelf_location)">{{ record.shelf_location }}</span>
                                <span v-if="record.call_number && getCoteBadge(record.call_number)" :style="getCoteBadge(record.call_number)">{{ record.call_number }}</span>
                            </div>

                            <!-- Badges: Medium Type, Audience, Language -->
                            <div class="mb-3 d-flex flex-wrap gap-1">
                                <span v-if="record.medium_type" class="badge bg-secondary">
                                    {{ record.medium_type }}
                                </span>
                                <span v-if="record.target_audience" class="badge bg-info">
                                    {{ getAudienceLabel(record.target_audience) }}
                                </span>
                                <span v-if="record.language" class="badge bg-light text-dark">
                                    <i class="bi bi-translate"></i> {{ record.language.toUpperCase() }}
                                </span>
                                <span v-if="record.page_count" class="badge bg-light text-dark">
                                    <i class="bi bi-file-earmark-text"></i> {{ record.page_count }}p
                                </span>
                            </div>

                            <!-- Availability Badge -->
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">
                                    {{ record.total_items }} {{ t('catalog.copies').toLowerCase() }}
                                    <span v-if="record.active_holds_count > 0" class="badge bg-primary ms-1">
                                        <i class="bi bi-bookmark-fill"></i>
                                        {{ record.active_holds_count }}
                                    </span>
                                </small>
                                <span
                                    :class="['badge', getAvailabilityBadge(record).class]"
                                >
                                    <i :class="getAvailabilityBadge(record).icon"></i>
                                    {{ getAvailabilityBadge(record).text }}
                                </span>
                            </div>
                        </div>

                        <div class="card-footer bg-transparent">
                            <small class="text-primary">
                                <i class="bi bi-info-circle"></i>
                                {{ t('catalog.view_details') || 'View details' }}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});
