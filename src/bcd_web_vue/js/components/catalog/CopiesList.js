/**
 * Reusable list of the physical copies attached to a bibliographic notice.
 *
 * The list is deliberately presentation-only.  Parent components decide what
 * editing/deletion means and receive item events, so it can be used by both
 * the catalog detail screen and the cataloging workflow.
 */

const { defineComponent, computed, watch } = Vue;
const { useI18n } = VueI18n;
import { useItemBadge } from '../../composables/useItemBadge.js';
import { usePagination } from '../../composables/usePagination.js';
import Pagination from '../ui/Pagination.js';
import { getItemStatusBadge, getItemConditionLabel } from '../../utils/itemPresentation.js';

export default defineComponent({
    name: 'CopiesList',
    components: { Pagination },

    props: {
        items: {
            type: Array,
            default: () => []
        },
        settings: {
            type: Object,
            default: null
        },
        periodical: {
            type: Boolean,
            default: false
        },
        editable: {
            type: Boolean,
            default: false
        },
        allowDelete: {
            type: Boolean,
            default: false
        },
        showCurrentLoan: {
            type: Boolean,
            default: false
        },
        showCondition: {
            type: Boolean,
            default: false
        },
        showQuickReturn: {
            type: Boolean,
            default: false
        },
        emptyMessage: {
            type: String,
            default: ''
        },
        dense: {
            type: Boolean,
            default: false
        },
        formatDate: {
            type: Function,
            default: value => value || '—'
        }
    },

    emits: ['edit', 'delete', 'quick-return', 'view-borrower'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const settingsRef = computed(() => props.settings);
        const { getShelfBadge, getCoteBadge } = useItemBadge(settingsRef);
        const {
            currentPage,
            pageSize,
            totalItems,
            totalPages,
            offset,
            goToPage,
            setPageSize,
            setTotalItems
        } = usePagination({ pageSize: 25 });

        const pagedItems = computed(() => props.items.slice(
            offset.value,
            offset.value + pageSize.value
        ));

        watch(() => props.items.length, (count) => {
            setTotalItems(count);
        }, { immediate: true });


        const displayIssue = (item) => {
            if (!item.call_number) return '—';
            return String(item.call_number);
        };

        return {
            t,
            getShelfBadge,
            getCoteBadge,
            getStatusBadge: status => getItemStatusBadge(t, status),
            getConditionLabel: condition => getItemConditionLabel(t, condition),
            displayIssue,
            pagedItems,
            currentPage,
            pageSize,
            totalItems,
            totalPages,
            goToPage,
            setPageSize,
            emitEdit: item => emit('edit', item),
            emitDelete: item => emit('delete', item),
            emitQuickReturn: item => emit('quick-return', item),
            emitViewBorrower: borrowerId => emit('view-borrower', borrowerId)
        };
    },

    template: `
        <div class="copies-list">
            <div v-if="items.length === 0" class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                {{ emptyMessage || t('catalog.no_items') }}
            </div>

            <div v-else class="table-responsive">
                <table :class="['table', dense ? 'table-sm' : '', 'table-hover']">
                    <thead>
                        <tr>
                            <th>{{ t('catalog.item_id') }}</th>
                            <th v-if="periodical">{{ t('periodical.issue_number') }}</th>
                            <th>{{ t('catalog.shelf_location_call_number') }}</th>
                            <th>{{ t('catalog.status') }}</th>
                            <th v-if="showCurrentLoan">{{ t('catalog.due_date_borrower') }}</th>
                            <th v-else-if="showCondition">{{ t('catalog.condition') }}</th>
                            <th v-if="editable || showQuickReturn">{{ t('common.actions') }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="item in pagedItems" :key="item.id || item.item_id">
                            <td class="font-monospace">{{ item.item_id || item.barcode }}</td>
                            <td v-if="periodical" class="text-muted">{{ displayIssue(item) }}</td>
                            <td>
                                <div class="d-flex flex-wrap align-items-center gap-1">
                                    <span
                                        v-if="item.shelf_location && getShelfBadge(item.shelf_location)"
                                        :style="getShelfBadge(item.shelf_location)"
                                    >{{ item.shelf_location }}</span>
                                    <span
                                        v-if="!periodical && item.call_number && getCoteBadge(item.call_number)"
                                        :style="getCoteBadge(item.call_number)"
                                    >{{ item.call_number }}</span>
                                    <span v-if="!item.shelf_location && (periodical || !item.call_number)" class="text-muted">&mdash;</span>
                                </div>
                            </td>
                            <td>
                                <div class="d-flex flex-wrap gap-1">
                                    <span :class="['badge', getStatusBadge(item.status).class]">
                                        <i :class="getStatusBadge(item.status).icon"></i>
                                        {{ getStatusBadge(item.status).text }}
                                    </span>
                                    <span v-if="item.condition === 'damaged'" class="badge bg-warning text-dark">
                                        <i class="bi bi-exclamation-triangle"></i>
                                        {{ t('item.condition_damaged') }}
                                    </span>
                                    <span v-if="item.loanable === false" class="badge bg-secondary">
                                        <i class="bi bi-lock"></i>
                                        {{ t('item.status_not_loanable') || t('catalog.loanable') }}
                                    </span>
                                </div>
                            </td>
                            <td v-if="showCurrentLoan">
                                <div v-if="item.current_loan">
                                    <div class="mb-1">
                                        {{ formatDate(item.current_loan.due_date) }}
                                        <span v-if="item.current_loan.is_overdue" class="badge bg-danger ms-1">
                                            <i class="bi bi-exclamation-circle"></i>
                                            {{ t('catalog.overdue') }}
                                        </span>
                                    </div>
                                    <a
                                        href="#"
                                        class="link-entity fw-bold"
                                        @click.prevent="emitViewBorrower(item.current_loan.borrower_id)"
                                    >{{ item.current_loan.borrower_name || item.current_loan.borrower_id }}</a>
                                </div>
                                <span v-else class="text-muted">—</span>
                            </td>
                            <td v-else-if="showCondition">{{ getConditionLabel(item.condition) }}</td>
                            <td v-if="editable || showQuickReturn">
                                <button
                                    v-if="showQuickReturn && (item.status === 'on_loan' || item.status === 'overdue')"
                                    type="button"
                                    class="btn btn-sm btn-outline-primary me-1"
                                    @click="emitQuickReturn(item.item_id)"
                                >
                                    <i class="bi bi-arrow-return-left"></i>
                                    {{ t('catalog.quick_return') }}
                                </button>
                                <button
                                    v-if="editable"
                                    type="button"
                                    class="btn btn-sm btn-outline-primary me-1"
                                    :title="t('common.edit')"
                                    :aria-label="t('common.edit')"
                                    @click="emitEdit(item)"
                                >
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button
                                    v-if="allowDelete"
                                    type="button"
                                    class="btn btn-sm btn-outline-danger"
                                    :title="t('common.delete')"
                                    :aria-label="t('common.delete')"
                                    @click="emitDelete(item)"
                                >
                                    <i class="bi bi-trash"></i>
                                </button>
                                <span v-if="!editable && !(showQuickReturn && (item.status === 'on_loan' || item.status === 'overdue'))" class="text-muted">—</span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <pagination
                v-if="totalItems > pageSize"
                class="mt-3"
                :current-page="currentPage"
                :total-pages="totalPages"
                :page-size="pageSize"
                :total-items="totalItems"
                @page-change="goToPage"
                @page-size-change="setPageSize"
            />
        </div>
    `
});
