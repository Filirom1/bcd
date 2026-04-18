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
        // Bare mode: just table, no wrappers (for use inside existing cards)
        bare: {
            type: Boolean,
            default: false
        },
        // Row key property (for v-for key)
        rowKey: {
            type: String,
            default: 'id'
        }
    },

    emits: ['row-click'],

    setup(props, { emit }) {
        const { t } = useI18n();

        const hasRows = computed(() => props.rows.length > 0);

        const handleRowClick = (row) => {
            if (props.clickable) {
                emit('row-click', row);
            }
        };

        return {
            t,
            hasRows,
            handleRowClick
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

            <!-- Bare Table (no wrapper, for use inside cards) -->
            <table v-else-if="bare" class="table table-hover table-striped mb-0">
                <thead>
                    <tr>
                        <th
                            v-for="column in columns"
                            :key="column.key"
                            :style="column.width ? { width: column.width } : {}"
                        >
                            <slot :name="'header-' + column.key">{{ column.label }}</slot>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="row in rows"
                        :key="row[rowKey]"
                        @click="handleRowClick(row)"
                        :style="clickable ? { cursor: 'pointer' } : {}"
                    >
                        <slot name="row" :row="row" :columns="columns">
                            <td v-for="column in columns" :key="column.key">
                                {{ row[column.key] }}
                            </td>
                        </slot>
                    </tr>
                </tbody>
            </table>

            <!-- Table with Card Wrapper -->
            <div v-else-if="card" class="card">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover table-striped mb-0">
                            <thead>
                                <tr>
                                    <th
                                        v-for="column in columns"
                                        :key="column.key"
                                        :style="column.width ? { width: column.width } : {}"
                                    >
                                        <slot :name="'header-' + column.key">{{ column.label }}</slot>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="row in rows"
                                    :key="row[rowKey]"
                                    @click="handleRowClick(row)"
                                    :style="clickable ? { cursor: 'pointer' } : {}"
                                >
                                    <slot name="row" :row="row" :columns="columns">
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
            <div v-else class="table-responsive">
                <table class="table table-hover table-striped">
                    <thead>
                        <tr>
                            <th
                                v-for="column in columns"
                                :key="column.key"
                                :style="column.width ? { width: column.width } : {}"
                            >
                                <slot :name="'header-' + column.key">{{ column.label }}</slot>
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="row in rows"
                            :key="row[rowKey]"
                            @click="handleRowClick(row)"
                            :style="clickable ? { cursor: 'pointer' } : {}"
                        >
                            <slot name="row" :row="row" :columns="columns">
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
