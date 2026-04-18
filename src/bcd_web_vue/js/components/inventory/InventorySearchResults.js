/**
 * InventorySearchResults Component
 * Displays search results for inventory operations with selection
 */

const { defineComponent, computed, ref, watch } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'InventorySearchResults',

    props: {
        items: {
            type: Array,
            required: true
        },
        selectedIds: {
            type: Set,
            required: true
        },
        showPeriodLoanCount: {
            type: Boolean,
            default: false
        }
    },

    emits: ['toggle-selection', 'toggle-select-all'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Ref for header checkbox
        const headerCheckboxRef = ref(null);

        /**
         * Header checkbox state
         */
        const allSelected = computed(() => {
            return props.items.length > 0 && props.selectedIds.size === props.items.length;
        });

        const someSelected = computed(() => {
            return props.selectedIds.size > 0 && props.selectedIds.size < props.items.length;
        });

        /**
         * Update header checkbox indeterminate state
         */
        watch(
            () => someSelected.value,
            (newVal) => {
                if (headerCheckboxRef.value) {
                    headerCheckboxRef.value.indeterminate = newVal;
                }
            },
            { immediate: true }
        );

        /**
         * Handle header checkbox click
         */
        const handleHeaderCheckbox = () => {
            emit('toggle-select-all');
        };

        /**
         * Handle row checkbox click
         */
        const handleRowCheckbox = (itemId) => {
            emit('toggle-selection', itemId);
        };

        /**
         * Check if item is selected
         */
        const isSelected = (itemId) => {
            return props.selectedIds.has(itemId);
        };

        /**
         * Truncate title if too long
         */
        const truncateTitle = (title, maxLength = 50) => {
            if (!title) return '';
            if (title.length <= maxLength) return title;
            return title.substring(0, maxLength) + '…';
        };

        return {
            t,
            headerCheckboxRef,
            allSelected,
            someSelected,
            handleHeaderCheckbox,
            handleRowCheckbox,
            isSelected,
            truncateTitle
        };
    },

    template: `
        <div class="search-results-compact">
            <!-- Header with select all -->
            <div class="d-flex align-items-center mb-2 px-2 py-1 bg-light" style="border-radius: 4px;">
                <input
                    ref="headerCheckboxRef"
                    type="checkbox"
                    class="form-check-input me-2"
                    :checked="allSelected"
                    @change="handleHeaderCheckbox"
                    :title="t('inventory.working_table.select_all')"
                    style="margin-top: 0;"
                >
                <small class="text-muted">{{ t('inventory.working_table.select_all') }}</small>
            </div>

            <!-- Results list -->
            <div v-if="items.length === 0" class="text-center text-muted py-3">
                <small>{{ t('inventory.search.no_results') }}</small>
            </div>

            <div v-else class="search-results-list" style="max-height: 400px; overflow-y: auto;">
                <div
                    v-for="item in items"
                    :key="item.item_id"
                    class="search-result-item mb-2 p-2"
                    :class="{ 'selected': isSelected(item.item_id) }"
                    style="border: 1px solid var(--bcd-border); border-radius: 4px; cursor: pointer;"
                    @click="handleRowCheckbox(item.item_id)"
                >
                    <div class="d-flex align-items-start gap-2">
                        <input
                            type="checkbox"
                            class="form-check-input mt-1"
                            :checked="isSelected(item.item_id)"
                            @click.stop="handleRowCheckbox(item.item_id)"
                        >
                        <div class="flex-grow-1" style="min-width: 0;">
                            <div class="font-monospace text-primary mb-1" style="font-size: 0.8rem;">
                                {{ item.item_id }}
                            </div>
                            <div class="mb-1" style="font-size: 0.85rem;" :title="item.title">
                                {{ truncateTitle(item.title, 35) }}
                            </div>
                            <div class="d-flex gap-2 align-items-center">
                                <span
                                    class="badge"
                                    style="font-size: 0.7rem;"
                                    :class="{
                                        'bg-success': item.condition === 'good',
                                        'bg-warning text-dark': item.condition === 'damaged'
                                    }"
                                >
                                    {{ t(\`item.condition_\${item.condition}\`) }}
                                </span>
                                <small v-if="showPeriodLoanCount" class="text-muted">
                                    {{ item.period_loan_count || 0 }} {{ t('inventory.search.period_loans').toLowerCase() }}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});
