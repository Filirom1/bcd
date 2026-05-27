/**
 * InventoryResults Component
 * Displays the working table of inventoried items using DataTable
 * Follows the same pattern as catalog SearchResults for consistency
 */

const { defineComponent, computed, ref, watch } = Vue;
const { useI18n } = VueI18n;
import DataTable from '../ui/DataTable.js';
import { useAppState } from '../../composables/useAppState.js';
import { useItemBadge } from '../../composables/useItemBadge.js';

export default defineComponent({
    name: 'InventoryResults',

    components: {
        DataTable
    },

    props: {
        items: {
            type: Array,
            required: true
        },
        selectedIds: {
            type: Set,
            required: true
        },
        selectAllChecked: {
            type: Boolean,
            default: false
        },
        visibleColumns: {
            type: Array,
            default: () => ['item_id', 'title', 'condition', 'status']
        }
    },

    emits: ['toggle-selection', 'toggle-select-all', 'edit-item', 'edit-record'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { settings } = useAppState();
        const { getShelfBadge, getCoteBadge } = useItemBadge(settings);

        const recentlyAddedId = ref(null);

        // Check if column should be visible
        const isColumnVisible = (columnId) => {
            return props.visibleColumns.includes(columnId);
        };

        // Define all available columns
        const tableColumns = computed(() => {
            const allColumns = [
                { key: 'select', label: '', width: '40px' },
                // Item identification
                { key: 'item_id', label: t('inventory.working_table.barcode'), width: '120px' },
                { key: 'title', label: t('inventory.working_table.title_column') },
                // Item fields
                { key: 'condition', label: t('inventory.working_table.condition'), width: '100px' },
                { key: 'status', label: t('inventory.working_table.status'), width: '120px' },
                { key: 'call_number', label: t('catalog.call_number'), width: '120px' },
                { key: 'loanable', label: t('item.loanable'), width: '100px' },
                { key: 'shelf_location', label: t('item.shelf_location'), width: '150px' },
                // Record fields
                { key: 'genre', label: t('bibliographic.genre'), width: '150px' },
                { key: 'level', label: t('bibliographic.level'), width: '100px' },
                { key: 'target_audience', label: t('bibliographic.target_audience'), width: '120px' },
                { key: 'language', label: t('bibliographic.language'), width: '100px' },
                { key: 'medium_type', label: t('bibliographic.medium_type'), width: '150px' },
                // Inventory tracking
                { key: 'last_inventoried', label: t('inventory.working_table.last_inventoried'), width: '150px' }
            ];
            // Always include checkbox, filter rest based on visibility
            return [
                allColumns[0],
                ...allColumns.slice(1).filter(col => isColumnVisible(col.key))
            ];
        });

        // Toggle individual item selection
        const toggleItemSelection = (itemId) => {
            emit('toggle-selection', itemId);
        };

        // Toggle select all
        const toggleSelectAll = () => {
            emit('toggle-select-all');
        };

        // Check if item is selected
        const isSelected = (itemId) => {
            return props.selectedIds.has(itemId);
        };

        // Ref for header checkbox to handle indeterminate state
        const headerCheckboxRef = ref(null);

        // Watch for indeterminate state (some but not all selected)
        watch(
            () => [props.selectedIds.size, props.items.length, props.selectAllChecked],
            ([selectedSize, totalItems, allChecked]) => {
                if (headerCheckboxRef.value) {
                    const someSelected = selectedSize > 0 && selectedSize < totalItems;
                    headerCheckboxRef.value.indeterminate = someSelected;
                }
            },
            { immediate: true }
        );

        /**
         * Truncate title if too long
         */
        const truncateTitle = (title, maxLength = 40) => {
            if (!title) return '';
            if (title.length <= maxLength) return title;
            return title.substring(0, maxLength) + '…';
        };

        /**
         * Highlight row briefly when duplicate item scanned
         */
        const highlightRow = (item_id) => {
            recentlyAddedId.value = item_id;
            setTimeout(() => {
                recentlyAddedId.value = null;
            }, 1000);
        };

        /**
         * Watch for items changing at top (duplicate scan)
         */
        watch(
            () => props.items[0],
            (newFirst, oldFirst) => {
                if (newFirst && oldFirst && newFirst.item_id !== oldFirst.item_id) {
                    highlightRow(newFirst.item_id);
                }
            }
        );

        /**
         * Get row class for highlighting
         */
        const getRowClass = (item) => {
            return recentlyAddedId.value === item.item_id ? 'table-success' : '';
        };

        /**
         * Format date for display
         */
        const formatDate = (dateStr) => {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            return date.toLocaleDateString();
        };

        /**
         * Handle edit item click
         */
        const handleEditItem = (item) => {
            emit('edit-item', item);
        };

        /**
         * Handle edit record click (navigate to catalog page)
         */
        const handleEditRecord = (item) => {
            emit('edit-record', item);
        };

        return {
            t,
            isColumnVisible,
            tableColumns,
            toggleItemSelection,
            toggleSelectAll,
            handleEditItem,
            handleEditRecord,
            truncateTitle,
            recentlyAddedId,
            isSelected,
            getRowClass,
            formatDate,
            headerCheckboxRef,
            getShelfBadge,
            getCoteBadge
        };
    },

    template: `
        <data-table
            :columns="tableColumns"
            :rows="items"
            :loading="false"
            :empty-message="t('inventory.working_table.empty')"
            bare
            row-key="item_id"
        >
            <!-- Custom header for checkbox column -->
            <template #header-select>
                <input
                    ref="headerCheckboxRef"
                    type="checkbox"
                    class="form-check-input"
                    :checked="selectAllChecked"
                    @change="toggleSelectAll"
                    @click.stop
                    :title="t('inventory.working_table.select_all')"
                >
            </template>

            <template #row="{ row: item }">
                <!-- Checkbox -->
                <td @click.stop :class="getRowClass(item)">
                    <input
                        type="checkbox"
                        class="form-check-input"
                        :checked="isSelected(item.item_id)"
                        @change="toggleItemSelection(item.item_id)"
                    >
                </td>

                <!-- Item ID (barcode) - clickable to edit -->
                <td v-if="isColumnVisible('item_id')" class="font-monospace" :class="getRowClass(item)">
                    <a
                        href="#"
                        @click.prevent="handleEditItem(item)"
                        class="link-entity"
                        :title="t('admin.edit_item')"
                    >
                        {{ item.item_id }}
                    </a>
                </td>

                <!-- Title (truncated) - clickable to edit record -->
                <td v-if="isColumnVisible('title')" :class="getRowClass(item)">
                    <a
                        href="#"
                        @click.prevent="handleEditRecord(item)"
                        class="link-entity fw-bold"
                        :title="item.title"
                    >
                        {{ truncateTitle(item.title) }}
                    </a>
                </td>

                <!-- Condition badge -->
                <td v-if="isColumnVisible('condition')" :class="getRowClass(item)">
                    <span
                        class="badge"
                        :class="{
                            'bg-success': item.condition === 'good',
                            'bg-warning text-dark': item.condition === 'damaged'
                        }"
                    >
                        {{ t(\`item.condition_\${item.condition}\`) }}
                    </span>
                </td>

                <!-- Status badge -->
                <td v-if="isColumnVisible('status')" :class="getRowClass(item)">
                    <span
                        class="badge"
                        :class="{
                            'bg-success': item.status === 'available',
                            'bg-primary': item.status === 'on_loan',
                            'bg-warning text-dark': item.status === 'on_hold',
                            'bg-secondary': item.status === 'in_repair',
                            'bg-danger': item.status === 'lost',
                            'bg-dark': item.status === 'withdrawn'
                        }"
                    >
                        {{ t(\`item.status_\${item.status}\`) }}
                    </span>
                </td>

                <!-- Call Number -->
                <td v-if="isColumnVisible('call_number')" :class="getRowClass(item)">
                    <span v-if="item.call_number && getCoteBadge(item.call_number)" :style="getCoteBadge(item.call_number)">{{ item.call_number }}</span>
                    <span v-else class="text-muted">—</span>
                </td>

                <!-- Loanable -->
                <td v-if="isColumnVisible('loanable')" :class="getRowClass(item)">
                    <i class="bi" :class="item.loanable ? 'bi-check-circle text-success' : 'bi-x-circle text-muted'"></i>
                </td>

                <!-- Shelf Location -->
                <td v-if="isColumnVisible('shelf_location')" :class="getRowClass(item)">
                    <span v-if="item.shelf_location && getShelfBadge(item.shelf_location)" :style="getShelfBadge(item.shelf_location)">{{ item.shelf_location }}</span>
                    <span v-else class="text-muted">—</span>
                </td>

                <!-- Genre -->
                <td v-if="isColumnVisible('genre')" :class="getRowClass(item)">
                    <small>{{ item.genre || '—' }}</small>
                </td>

                <!-- Level -->
                <td v-if="isColumnVisible('level')" :class="getRowClass(item)">
                    <small>{{ item.level || '—' }}</small>
                </td>

                <!-- Target Audience -->
                <td v-if="isColumnVisible('target_audience')" :class="getRowClass(item)">
                    <small v-if="item.target_audience">{{ t(\`bibliographic.audience_\${item.target_audience}\`) }}</small>
                    <small v-else class="text-muted">—</small>
                </td>

                <!-- Language -->
                <td v-if="isColumnVisible('language')" :class="getRowClass(item)">
                    <small>{{ item.language || '—' }}</small>
                </td>

                <!-- Medium Type -->
                <td v-if="isColumnVisible('medium_type')" :class="getRowClass(item)">
                    <small>{{ item.medium_type || '—' }}</small>
                </td>

                <!-- Last inventoried date -->
                <td v-if="isColumnVisible('last_inventoried')" :class="getRowClass(item)">
                    <small class="text-muted">{{ formatDate(item.last_inventoried_at) }}</small>
                </td>
            </template>
        </data-table>
    `
});
