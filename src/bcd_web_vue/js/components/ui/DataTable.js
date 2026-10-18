/**
 * DataTable Component
 * Reusable table component with consistent styling across the application
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import LoadingSpinner from './LoadingSpinner.js';

export default defineComponent({
    name: 'DataTable',

    components: {
        LoadingSpinner
    },

    props: {
        // Column definitions: [{ key: 'id', label: 'ID', width: '60px' }]
        columns: {
            type: Array,
            required: true
        },
        // Row data array
        rows: {
            type: Array,
            default: () => []
        },
        // Loading state
        loading: {
            type: Boolean,
            default: false
        },
        // Empty state message
        emptyMessage: {
            type: String,
            default: null
        },
        // Make rows clickable
        clickable: {
            type: Boolean,
            default: false
        },
        // Use card wrapper (for reports)
        card: {
            type: Boolean,
            default: false
        },
        // Bare mode: no card wrapper; the table can still have its shared frame.
        bare: {
            type: Boolean,
            default: false
        },
        // Draw the shared outer border. Disable when a parent card already provides it.
        framed: {
            type: Boolean,
            default: true
        },
        // Row key property (for v-for key)
        rowKey: {
            type: [String, Function],
            default: 'id'
        },
        // Additional table classes for contextual sizing or specialized layouts
        tableClass: {
            type: [String, Array, Object],
            default: ''
        },
        // Optional row-class string or (row, index) callback
        rowClass: {
            type: [String, Function],
            default: ''
        },
        // Sort indicator state for sortable columns
        sortColumn: {
            type: String,
            default: ''
        },
        sortDirection: {
            type: String,
            default: 'asc'
        }
    },

    emits: ['row-click', 'sort'],

    setup(props, { emit }) {
        const { t } = useI18n();

        const hasRows = computed(() => props.rows.length > 0);

        const handleRowClick = (row) => {
            if (props.clickable) {
                emit('row-click', row);
            }
        };

        const handleSort = (column) => {
            if (column.sortable) {
                emit('sort', column.key);
            }
        };

        const getRowKey = (row, index) => typeof props.rowKey === 'function'
            ? props.rowKey(row, index)
            : (row[props.rowKey] ?? index);
        const getRowClass = (row, index) => typeof props.rowClass === 'function'
            ? props.rowClass(row, index)
            : props.rowClass;

        return {
            t,
            hasRows,
            handleRowClick,
            handleSort,
            getRowKey,
            getRowClass
        };
    },

    template: `
        <div>
            <!-- Loading State -->
            <div v-if="loading" class="text-center py-5">
                <loading-spinner />
                <p class="text-muted mt-3">{{ t('common.loading') }}</p>
            </div>

            <!-- Empty State -->
            <div v-else-if="!hasRows" class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                {{ emptyMessage || t('common.no_data') }}
            </div>

            <!-- Bare Table (no card wrapper) -->
            <div v-else-if="bare" :class="['data-table-frame', { 'data-table-frame--bordered': framed }]">
                <table :class="['table table-hover table-striped mb-0', tableClass]">
                <thead>
                    <tr>
                        <th
                            v-for="column in columns"
                            :key="column.key"
                            :class="[column.headerClass, { 'data-table-sortable': column.sortable }]"
                            :style="column.width ? { width: column.width } : {}"
                            :aria-sort="column.sortable && sortColumn === column.key ? (sortDirection === 'asc' ? 'ascending' : 'descending') : null"
                            @click="handleSort(column)"
                        >
                            <slot :name="'header-' + column.key">{{ column.label }}</slot>
                            <i
                                v-if="column.sortable && sortColumn === column.key"
                                class="bi ms-1"
                                :class="sortDirection === 'asc' ? 'bi-arrow-up' : 'bi-arrow-down'"
                                aria-hidden="true"
                            ></i>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="(row, index) in rows"
                        :key="getRowKey(row, index)"
                        @click="handleRowClick(row)"
                        :class="getRowClass(row, index)"
                        :style="clickable ? { cursor: 'pointer' } : {}"
                    >
                        <slot name="row" :row="row" :columns="columns" :index="index">
                            <td v-for="column in columns" :key="column.key">
                                {{ row[column.key] }}
                            </td>
                        </slot>
                    </tr>
                </tbody>
                </table>
            </div>

            <!-- Table with Card Wrapper -->
            <div v-else-if="card" :class="['card', { 'data-table-frame--bordered': framed }]">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table :class="['table table-hover table-striped mb-0', tableClass]">
                            <thead>
                                <tr>
                                    <th
                                        v-for="column in columns"
                                        :key="column.key"
                                        :class="[column.headerClass, { 'data-table-sortable': column.sortable }]"
                                        :style="column.width ? { width: column.width } : {}"
                                        :aria-sort="column.sortable && sortColumn === column.key ? (sortDirection === 'asc' ? 'ascending' : 'descending') : null"
                                        @click="handleSort(column)"
                                    >
                                        <slot :name="'header-' + column.key">{{ column.label }}</slot>
                                        <i
                                            v-if="column.sortable && sortColumn === column.key"
                                            class="bi ms-1"
                                            :class="sortDirection === 'asc' ? 'bi-arrow-up' : 'bi-arrow-down'"
                                            aria-hidden="true"
                                        ></i>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="(row, index) in rows"
                                    :key="getRowKey(row, index)"
                                    @click="handleRowClick(row)"
                                    :class="getRowClass(row, index)"
                                    :style="clickable ? { cursor: 'pointer' } : {}"
                                >
                                    <slot name="row" :row="row" :columns="columns" :index="index">
                                        <td v-for="column in columns" :key="column.key">
                                            {{ row[column.key] }}
                                        </td>
                                    </slot>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Table without Card -->
            <div v-else :class="['table-responsive', 'data-table-frame', { 'data-table-frame--bordered': framed }]">
                <table :class="['table table-hover table-striped mb-0', tableClass]">
                    <thead>
                        <tr>
                            <th
                                v-for="column in columns"
                                :key="column.key"
                                :class="[column.headerClass, { 'data-table-sortable': column.sortable }]"
                                :style="column.width ? { width: column.width } : {}"
                                :aria-sort="column.sortable && sortColumn === column.key ? (sortDirection === 'asc' ? 'ascending' : 'descending') : null"
                                @click="handleSort(column)"
                            >
                                <slot :name="'header-' + column.key">{{ column.label }}</slot>
                                <i
                                    v-if="column.sortable && sortColumn === column.key"
                                    class="bi ms-1"
                                    :class="sortDirection === 'asc' ? 'bi-arrow-up' : 'bi-arrow-down'"
                                    aria-hidden="true"
                                ></i>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="(row, index) in rows"
                            :key="getRowKey(row, index)"
                            @click="handleRowClick(row)"
                            :class="getRowClass(row, index)"
                            :style="clickable ? { cursor: 'pointer' } : {}"
                        >
                            <slot name="row" :row="row" :columns="columns" :index="index">
                                <td v-for="column in columns" :key="column.key">
                                    {{ row[column.key] }}
                                </td>
                            </slot>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    `
});
