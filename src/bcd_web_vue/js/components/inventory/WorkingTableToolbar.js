/**
 * WorkingTableToolbar Component
 * Toolbar for the inventory working table with selection count and actions
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import InventoryColumnSelector from './InventoryColumnSelector.js';

export default defineComponent({
    name: 'WorkingTableToolbar',

    components: {
        InventoryColumnSelector
    },

    props: {
        selectedCount: {
            type: Number,
            required: true
        },
        totalCount: {
            type: Number,
            required: true
        },
        visibleColumns: {
            type: Array,
            required: true
        }
    },

    emits: ['clear', 'toggle-column', 'reset-columns'],

    setup(props, { emit }) {
        const { t } = useI18n();

        const handleClear = () => {
            emit('clear');
        };

        const handleToggleColumn = (columnId) => {
            emit('toggle-column', columnId);
        };

        const handleResetColumns = () => {
            emit('reset-columns');
        };

        return {
            t,
            handleClear,
            handleToggleColumn,
            handleResetColumns
        };
    },

    template: `
        <div class="d-flex justify-content-between align-items-center px-3 py-2 border-bottom bg-light">
            <!-- Left: Selection count -->
            <div class="d-flex align-items-center gap-2">
                <span class="badge" :class="selectedCount > 0 ? 'bg-primary' : 'bg-secondary'">
                    {{ selectedCount }}/{{ totalCount }}
                </span>
            </div>

            <!-- Right: Action buttons -->
            <div class="d-flex gap-2">
                <inventory-column-selector
                    :visible-columns="visibleColumns"
                    @toggle-column="handleToggleColumn"
                    @reset="handleResetColumns"
                />
                <button
                    class="btn btn-sm btn-outline-danger"
                    @click="handleClear"
                    :disabled="selectedCount === 0"
                    :title="selectedCount === 0 ? t('inventory.working_table.clear_hint') : t('inventory.working_table.clear_selected')"
                >
                    <i class="bi bi-x-circle me-1"></i>
                    {{ t('inventory.working_table.clear') }}
                </button>
            </div>
        </div>
    `
});
