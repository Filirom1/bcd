/**
 * Column Selector Component
 * Dropdown to select which columns to display in table view
 */

const { defineComponent, ref } = Vue;
const { useI18n } = VueI18n;
import { AVAILABLE_COLUMNS } from '../../composables/useColumnSettings.js';

export default defineComponent({
    name: 'ColumnSelector',

    props: {
        visibleColumns: {
            type: Array,
            required: true
        }
    },

    emits: ['toggle-column', 'reset'],

    setup(props, { emit }) {
        const { t, locale } = useI18n();
        const showDropdown = ref(false);

        const toggleDropdown = () => {
            showDropdown.value = !showDropdown.value;
        };

        const closeDropdown = () => {
            showDropdown.value = false;
        };

        const isColumnVisible = (columnId) => {
            return props.visibleColumns.includes(columnId);
        };

        const toggleColumn = (columnId) => {
            emit('toggle-column', columnId);
        };

        const resetToDefaults = () => {
            emit('reset');
            closeDropdown();
        };

        const getColumnLabel = (column) => {
            return locale.value === 'fr' ? column.label_fr : column.label_en;
        };

        return {
            showDropdown,
            toggleDropdown,
            closeDropdown,
            isColumnVisible,
            toggleColumn,
            resetToDefaults,
            getColumnLabel,
            AVAILABLE_COLUMNS,
            t
        };
    },

    template: `
        <div class="dropdown position-relative">
            <button
                type="button"
                class="btn btn-outline-secondary btn-sm"
                @click="toggleDropdown"
                :title="t('catalog.select_columns') || 'Select columns'"
            >
                <i class="bi bi-sliders"></i>
            </button>

            <div
                v-if="showDropdown"
                class="dropdown-menu show"
                style="position: absolute; right: 0; top: 100%; margin-top: 0.25rem; min-width: 200px; z-index: 1000;"
                @click.stop
            >
                <h6 class="dropdown-header">
                    {{ t('catalog.select_columns') || 'Select columns' }}
                </h6>
                <div class="dropdown-divider"></div>

                <div
                    v-for="column in AVAILABLE_COLUMNS"
                    :key="column.id"
                    class="form-check px-3 py-1"
                >
                    <input
                        type="checkbox"
                        class="form-check-input"
                        :id="'col-' + column.id"
                        :checked="isColumnVisible(column.id)"
                        @change="toggleColumn(column.id)"
                    />
                    <label
                        class="form-check-label"
                        :for="'col-' + column.id"
                        style="cursor: pointer;"
                    >
                        {{ getColumnLabel(column) }}
                    </label>
                </div>

                <div class="dropdown-divider"></div>
                <button
                    type="button"
                    class="dropdown-item text-primary"
                    @click="resetToDefaults"
                >
                    <i class="bi bi-arrow-counterclockwise me-1"></i>
                    {{ t('catalog.reset_columns') || 'Reset to defaults' }}
                </button>
            </div>

            <!-- Backdrop to close dropdown -->
            <div
                v-if="showDropdown"
                @click="closeDropdown"
                style="position: fixed; inset: 0; z-index: 999;"
            ></div>
        </div>
    `
});
