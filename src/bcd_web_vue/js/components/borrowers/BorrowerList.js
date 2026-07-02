/**
 * Borrower List Component
 *
 * Table displaying borrowers with status badges and overdue warnings.
 * Replaces HTMX template swapping with Vue reactive rendering.
 *
 * COMPARISON WITH OLD SOLUTION:
 * - OLD: Jinja2 template (borrower_list.html) rendered server-side
 * - NEW: Vue template with v-for loop, client-side rendering
 * - OLD: HTMX hx-get attributes to load modal
 * - NEW: Click events emit to parent
 * - OLD: Manual i18n.updateDOM() after htmx:afterSwap
 * - NEW: Vue I18n reactive {{ t() }} in template
 */

const { computed } = Vue;
const { useI18n } = VueI18n;
import DataTable from '../ui/DataTable.js';

export default {
    name: 'BorrowerList',

    components: {
        DataTable
    },

    props: {
        borrowers: {
            type: Array,
            required: true
        },
        loading: {
            type: Boolean,
            default: false
        }
    },

    emits: ['view-borrower', 'selection-changed'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Selection state
        const selectedBorrowerIds = Vue.ref([]);
        const selectAll = Vue.ref(false);

        // Define table columns (with checkbox column)
        const columns = computed(() => [
            { key: 'select', label: '', width: '40px' },
            { key: 'borrower_id', label: t('borrowers.borrower_id') },
            { key: 'full_name', label: t('borrowers.name') },
            { key: 'class_name', label: t('borrowers.class') },
            { key: 'role', label: t('borrowers.role') },
            { key: 'current_loans', label: t('borrower.current_loans') },
            { key: 'status', label: t('catalog.status') }
        ]);

        // Get badge class for loan count
        const getLoanBadgeClass = (borrower) => {
            const count = borrower.current_loans_count || 0;
            const limit = borrower.loan_limit || 0;
            const warningLimit = borrower.loan_limit_warning || 0;

            if (count >= limit) {
                return 'bg-danger';
            }
            if (warningLimit && count >= warningLimit) {
                return 'bg-warning text-dark';
            }
            return 'bg-secondary';
        };

        // View borrower detail
        const viewBorrower = (borrower) => {
            emit('view-borrower', borrower.borrower_id);
        };

        // Toggle individual borrower selection
        const toggleBorrowerSelection = (borrowerId) => {
            const index = selectedBorrowerIds.value.indexOf(borrowerId);
            if (index > -1) {
                selectedBorrowerIds.value.splice(index, 1);
            } else {
                selectedBorrowerIds.value.push(borrowerId);
            }
            emitSelectionChange();
            updateSelectAllState();
        };

        // Toggle select all
        const toggleSelectAll = () => {
            if (selectAll.value) {
                // Unselect all
                selectedBorrowerIds.value = [];
                selectAll.value = false;
            } else {
                // Select all
                selectedBorrowerIds.value = props.borrowers.map(b => b.borrower_id);
                selectAll.value = true;
            }
            emitSelectionChange();
        };

        // Update select all state based on individual selections
        const updateSelectAllState = () => {
            if (props.borrowers.length === 0) {
                selectAll.value = false;
            } else {
                selectAll.value = selectedBorrowerIds.value.length === props.borrowers.length;
            }
        };

        // Emit selection change
        const emitSelectionChange = () => {
            emit('selection-changed', selectedBorrowerIds.value);
        };

        // Check if borrower is selected
        const isSelected = (borrowerId) => {
            return selectedBorrowerIds.value.includes(borrowerId);
        };

        // Watch for borrowers prop changes to update select all state
        Vue.watch(() => props.borrowers, () => {
            updateSelectAllState();
        });

        return {
            t,
            columns,
            getLoanBadgeClass,
            viewBorrower,
            selectedBorrowerIds,
            selectAll,
            toggleBorrowerSelection,
            toggleSelectAll,
            isSelected
        };
    },

    template: `
        <data-table
            :columns="columns"
            :rows="borrowers"
            :loading="loading"
            :empty-message="t('borrowers.no_borrowers')"
            clickable
            row-key="borrower_id"
            @row-click="viewBorrower"
        >
            <!-- Custom header for checkbox column -->
            <template #header-select>
                <input
                    type="checkbox"
                    class="form-check-input"
                    :checked="selectAll"
                    @change="toggleSelectAll"
                    @click.stop
                >
            </template>

            <template #row="{ row: borrower }">
                <!-- Checkbox -->
                <td @click.stop>
                    <input
                        type="checkbox"
                        class="form-check-input"
                        :checked="isSelected(borrower.borrower_id)"
                        @change="toggleBorrowerSelection(borrower.borrower_id)"
                    >
                </td>

                <!-- Borrower ID -->
                <td>
                    <code class="text-primary">{{ borrower.borrower_id }}</code>
                </td>

                <!-- Name & Email -->
                <td>
                    <span class="link-entity fw-bold">{{ borrower.full_name }}</span>
                    <br v-if="borrower.email">
                    <small v-if="borrower.email" class="text-muted">
                        <i class="bi bi-envelope"></i> {{ borrower.email }}
                    </small>
                </td>

                <!-- Class -->
                <td>
                    <span v-if="borrower.class_name">{{ borrower.class_name }}</span>
                    <span v-else class="text-muted">—</span>
                </td>

                <!-- Role -->
                <td>
                    <span class="badge bg-secondary">
                        {{ t('borrower.role_' + borrower.role) }}
                    </span>
                </td>

                <!-- Current Loans Count -->
                <td>
                    <span
                        class="badge"
                        :class="getLoanBadgeClass(borrower)"
                    >
                        {{ borrower.current_loans_count || 0 }}/{{ borrower.loan_limit }}
                    </span>
                </td>

                <!-- Status -->
                <td>
                    <!-- Blocked Status -->
                    <div v-if="!borrower.active">
                        <span class="badge bg-danger">
                            <i class="bi bi-x-circle"></i>
                            {{ t('borrowers.blocked') }}
                        </span>
                        <br v-if="borrower.overdue_count > 0">
                        <small v-if="borrower.overdue_count > 0" class="text-danger">
                            <i class="bi bi-exclamation-triangle"></i>
                            {{ borrower.overdue_count }} {{ t('borrower.overdue') }}
                        </small>
                    </div>

                    <!-- Overdue (but Active) -->
                    <span
                        v-else-if="borrower.overdue_count > 0"
                        class="badge bg-warning text-dark"
                    >
                        <i class="bi bi-exclamation-triangle"></i>
                        {{ t('borrowers.late') }}
                    </span>

                    <!-- Active (no issues) -->
                    <span v-else class="badge bg-success">
                        <i class="bi bi-check-circle"></i>
                        {{ t('borrowers.active') }}
                    </span>
                </td>
            </template>
        </data-table>
    `
};
