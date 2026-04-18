/**
 * Borrower Detail Modal Component
 *
 * Full borrower information modal with current loans, history, and actions.
 * Replaces HTMX template loading with Vue component composition.
 *
 * COMPARISON WITH OLD SOLUTION:
 * - OLD: HTMX loads borrower_detail.html template into modal div
 * - NEW: Vue modal component with reactive data
 * - OLD: borrower_display.html included via Jinja2 {% include %}
 * - NEW: Component imports and uses BorrowerCard component
 * - OLD: Manual Bootstrap modal show/hide via JavaScript
 * - NEW: Vue-managed modal visibility with v-if and teleport
 */

import BorrowerCard from '../circulation/BorrowerCard.js';
import BorrowerActions from './BorrowerActions.js';
import Pagination from '../ui/Pagination.js';
import { useBlockReasonTranslation } from '../../composables/useBlockReasonTranslation.js';

export default {
    name: 'BorrowerDetail',

    components: {
        BorrowerCard,
        BorrowerActions,
        Pagination
    },

    props: {
        borrowerId: {
            type: String,
            required: true
        },
        show: {
            type: Boolean,
            default: false
        }
    },

    template: `
        <teleport to="body">
            <div
                v-if="show"
                class="modal fade show d-block"
                tabindex="-1"
                @click.self="close"
            >
                <div class="modal-dialog modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <!-- Modal Header -->
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-person-circle"></i>
                                {{ borrower?.full_name || t('borrowers.loading') }}
                            </h5>
                            <button
                                type="button"
                                class="btn-close btn-close-white"
                                @click="close"
                            ></button>
                        </div>

                        <!-- Modal Body -->
                        <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                            <!-- Loading State -->
                            <div v-if="loading" class="text-center py-5">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">{{ t('common.loading') }}</span>
                                </div>
                            </div>

                            <!-- Error State -->
                            <div v-else-if="error" class="alert alert-danger">
                                <i class="bi bi-exclamation-triangle"></i>
                                {{ error }}
                            </div>

                            <!-- Borrower Data -->
                            <div v-else-if="borrower">
                                <!-- Borrower Information Section -->
                                <div class="row mb-4">
                                    <div class="col-md-6">
                                        <h6 class="text-muted">{{ t('borrowers.information') }}</h6>
                                        <dl class="row">
                                            <dt class="col-sm-5">{{ t('borrower.id') }}</dt>
                                            <dd class="col-sm-7"><code>{{ borrower.borrower_id }}</code></dd>

                                            <dt class="col-sm-5">{{ t('borrower.role') }}</dt>
                                            <dd class="col-sm-7">
                                                <span class="badge bg-secondary">
                                                    {{ t('borrower.role_' + borrower.role) }}
                                                </span>
                                            </dd>

                                            <dt class="col-sm-5">{{ t('borrower.class') }}</dt>
                                            <dd class="col-sm-7">
                                                <span v-if="borrower.class_name">{{ borrower.class_name }}</span>
                                                <span v-else class="text-muted">—</span>
                                            </dd>

                                            <dt v-if="borrower.email" class="col-sm-5">{{ t('borrower.email') }}</dt>
                                            <dd v-if="borrower.email" class="col-sm-7">
                                                <a :href="'mailto:' + borrower.email">
                                                    <i class="bi bi-envelope"></i> {{ borrower.email }}
                                                </a>
                                            </dd>

                                            <dt v-if="borrower.phone" class="col-sm-5">{{ t('borrower.phone') }}</dt>
                                            <dd v-if="borrower.phone" class="col-sm-7">
                                                <i class="bi bi-telephone"></i> {{ borrower.phone }}
                                            </dd>
                                        </dl>
                                    </div>

                                    <div class="col-md-6">
                                        <h6 class="text-muted">{{ t('borrowers.circulation_status') }}</h6>
                                        <dl class="row">
                                            <dt class="col-sm-6">{{ t('borrower.current_loans') }}</dt>
                                            <dd class="col-sm-6">
                                                <span
                                                    class="badge"
                                                    :class="getLoanBadgeClass(borrower)"
                                                >
                                                    {{ borrower.current_loans_count }}/{{ borrower.loan_limit }}
                                                </span>
                                            </dd>

                                            <dt class="col-sm-6">{{ t('borrower.overdue') }}</dt>
                                            <dd class="col-sm-6">
                                                <span
                                                    v-if="borrower.overdue_count > 0"
                                                    class="badge bg-danger"
                                                >
                                                    <i class="bi bi-exclamation-triangle"></i>
                                                    {{ borrower.overdue_count }}
                                                </span>
                                                <span v-else class="badge bg-success">
                                                    <i class="bi bi-check-circle"></i> 0
                                                </span>
                                            </dd>

                                            <dt class="col-sm-6">{{ t('borrower.total_checkouts') }}</dt>
                                            <dd class="col-sm-6">{{ borrower.total_checkouts }}</dd>

                                            <dt class="col-sm-6">{{ t('borrower.status') }}</dt>
                                            <dd class="col-sm-6">
                                                <div v-if="!borrower.active">
                                                    <span class="badge bg-danger">
                                                        <i class="bi bi-x-circle"></i>
                                                        {{ t('borrowers.blocked') }}
                                                    </span>
                                                    <br v-if="borrower.blocked_reason">
                                                    <small v-if="borrower.blocked_reason" class="text-muted">
                                                        {{ translateBlockReason(borrower.blocked_reason) }}
                                                    </small>
                                                </div>
                                                <span v-else class="badge bg-success">
                                                    <i class="bi bi-check-circle"></i>
                                                    {{ t('borrowers.active') }}
                                                </span>
                                            </dd>
                                        </dl>
                                    </div>
                                </div>

                                <!-- Warning Alerts (always visible) -->
                                <div v-if="borrower.overdue_count > 0" class="alert alert-danger mb-3">
                                    <i class="bi bi-exclamation-triangle"></i>
                                    <strong>{{ t('circulation.overdue_warning') }}</strong>:
                                    {{ t('borrower.has_overdue_items') }}
                                </div>
                                <div
                                    v-if="borrower.current_loans_count >= borrower.loan_limit"
                                    class="alert alert-warning mb-3"
                                >
                                    <i class="bi bi-x-circle"></i>
                                    <strong>{{ t('circulation.loan_limit_reached') }}</strong>:
                                    {{ t('borrower.cannot_checkout') }}
                                </div>

                                <!-- Tabs -->
                                <ul class="nav nav-tabs mb-3">
                                    <li class="nav-item">
                                        <a class="nav-link" :class="{ active: activeTab === 'loans' }"
                                           @click.prevent="activeTab = 'loans'" href="#">
                                            <i class="bi bi-book"></i>
                                            {{ t('borrower.current_loans') }}
                                            <span v-if="currentLoans.length > 0" class="badge bg-primary ms-1">{{ currentLoans.length }}</span>
                                        </a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link" :class="{ active: activeTab === 'holds' }"
                                           @click.prevent="activeTab = 'holds'" href="#">
                                            <i class="bi bi-bookmark-fill"></i>
                                            {{ t('holds.title') }}
                                            <span v-if="holds.length > 0" class="badge bg-secondary ms-1">{{ holds.length }}</span>
                                        </a>
                                    </li>
                                    <li class="nav-item">
                                        <a class="nav-link" :class="{ active: activeTab === 'history' }"
                                           @click.prevent="activeTab = 'history'" href="#">
                                            <i class="bi bi-clock-history"></i>
                                            {{ t('borrower.circulation_history') }}
                                        </a>
                                    </li>
                                </ul>

                                <!-- Loans Tab -->
                                <div v-if="activeTab === 'loans'">
                                    <div v-if="!currentLoans.length" class="text-muted small">
                                        {{ t('circulation.no_current_loans') }}
                                    </div>
                                    <div v-else class="table-responsive">
                                        <table class="table table-sm">
                                            <thead>
                                                <tr>
                                                    <th>{{ t('catalog.title') }}</th>
                                                    <th>{{ t('circulation.due_date') }}</th>
                                                    <th>{{ t('circulation.renewals') }}</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr
                                                    v-for="loan in currentLoans"
                                                    :key="loan.item_id"
                                                    :class="{ 'table-danger': loan.is_overdue }"
                                                >
                                                    <td>
                                                        <a
                                                            href="#"
                                                            @click.prevent="viewItem(loan.bibliographic_record_id)"
                                                            class="link-entity fw-bold"
                                                        >{{ loan.title }}</a>
                                                        <br><small class="text-muted"><code>{{ loan.item_id }}</code></small>
                                                    </td>
                                                    <td>
                                                        {{ loan.due_date }}
                                                        <span v-if="loan.is_overdue" class="badge bg-danger ms-1">
                                                            {{ t('borrower.overdue') }}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <span class="badge bg-secondary">{{ loan.renewal_count }}</span>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                <!-- Holds Tab -->
                                <div v-if="activeTab === 'holds'">
                                    <!-- Search to reserve -->
                                    <input
                                        type="text"
                                        class="form-control mb-2"
                                        :placeholder="t('holds.search_to_reserve_placeholder')"
                                        v-model="holdSearch"
                                        @input="searchBooksForHold"
                                    >
                                    <div v-if="holdFormMessage" :class="['alert', 'alert-' + holdFormMessage.type, 'py-1', 'mb-2', 'small']">
                                        {{ holdFormMessage.text }}
                                    </div>
                                    <div v-if="holdResults.length > 0" class="list-group list-group-flush mb-2" style="max-height:200px;overflow-y:auto">
                                        <div
                                            v-for="rec in holdResults"
                                            :key="rec.id"
                                            class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-1 px-2"
                                        >
                                            <div>
                                                <div class="fw-bold small">{{ rec.title }}</div>
                                                <small class="text-muted">{{ rec.authors ? (Array.isArray(rec.authors) ? rec.authors.join(', ') : rec.authors) : '' }}</small>
                                            </div>
                                            <button class="btn btn-success btn-sm ms-2" @click="createHold(rec.id)">
                                                <i class="bi bi-bookmark-plus"></i>
                                            </button>
                                        </div>
                                    </div>
                                    <div v-else-if="holdSearch && !holdSearchLoading" class="text-muted small mb-2">{{ t('holds.search_no_results') }}</div>

                                    <!-- Active holds list -->
                                    <div v-if="holds.length > 0" class="table-responsive">
                                        <table class="table table-sm">
                                            <tbody>
                                                <tr v-for="hold in holds" :key="hold.id">
                                                    <td>
                                                        <a
                                                            href="#"
                                                            @click.prevent="viewItem(hold.bibliographic_record_id)"
                                                            class="link-entity fw-bold"
                                                        >{{ hold.title }}</a>
                                                    </td>
                                                    <td>
                                                        <span v-if="hold.status === 'ready'" class="badge bg-success">
                                                            <i class="bi bi-check-circle me-1"></i>{{ t('holds.status.ready') }}
                                                        </span>
                                                        <span v-else class="badge bg-secondary">
                                                            #{{ hold.queue_position }} {{ t('holds.status.waiting') }}
                                                        </span>
                                                    </td>
                                                    <td class="text-end">
                                                        <button
                                                            class="btn btn-sm btn-outline-danger"
                                                            @click="cancelHold(hold.id)"
                                                            :title="t('holds.cancel')"
                                                        >
                                                            <i class="bi bi-x-lg"></i>
                                                        </button>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                    <div v-if="!holds.length" class="text-muted small">{{ t('holds.no_holds') }}</div>
                                </div>

                                <!-- History Tab -->
                                <div v-if="activeTab === 'history'">
                                    <!-- Date filter row -->
                                    <div class="d-flex align-items-center gap-2 mb-3 flex-wrap">
                                        <label class="form-label mb-0 small text-muted">{{ t('circulation.date_from') }}</label>
                                        <input type="date" class="form-control form-control-sm w-auto" v-model="historyDateFrom" />
                                        <label class="form-label mb-0 small text-muted">{{ t('circulation.date_to') }}</label>
                                        <input type="date" class="form-control form-control-sm w-auto" v-model="historyDateTo" />
                                        <button class="btn btn-sm btn-primary" @click="applyHistoryFilter">{{ t('circulation.apply_date_filter') }}</button>
                                        <button class="btn btn-sm btn-outline-secondary" @click="clearHistoryFilter">{{ t('circulation.clear_date_filter') }}</button>
                                    </div>

                                    <!-- Loading -->
                                    <div v-if="historyLoading" class="text-center py-3">
                                        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                                    </div>

                                    <!-- No results -->
                                    <div v-else-if="historyItems.length === 0" class="text-muted small">
                                        <span v-if="historyDateFrom || historyDateTo">{{ t('circulation.no_history_for_period') }}</span>
                                        <span v-else>{{ t('circulation.no_history') }}</span>
                                    </div>

                                    <!-- History table -->
                                    <div v-else class="table-responsive">
                                        <table class="table table-sm table-striped">
                                            <thead>
                                                <tr>
                                                    <th>{{ t('catalog.title') }}</th>
                                                    <th>{{ t('circulation.checkout_date') }}</th>
                                                    <th>{{ t('circulation.return_date') }}</th>
                                                    <th>{{ t('catalog.status') }}</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr v-for="item in historyItems" :key="item.item_id + item.checkout_date">
                                                    <td>
                                                        <a
                                                            href="#"
                                                            @click.prevent="viewItem(item.bibliographic_record_id)"
                                                            class="link-entity fw-bold"
                                                        >{{ item.title }}</a>
                                                        <br><small class="text-muted"><code>{{ item.item_id }}</code></small>
                                                    </td>
                                                    <td>{{ new Date(item.checkout_date).toLocaleDateString() }}</td>
                                                    <td>{{ new Date(item.return_date).toLocaleDateString() }}</td>
                                                    <td>
                                                        <span v-if="item.was_overdue" class="badge bg-warning text-dark">
                                                            <i class="bi bi-exclamation-circle"></i>
                                                            {{ t('circulation.history_returned_late') }}
                                                        </span>
                                                        <span v-else class="badge bg-success">
                                                            <i class="bi bi-check"></i>
                                                            {{ t('circulation.history_returned_on_time') }}
                                                        </span>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>

                                    <!-- Pagination -->
                                    <pagination
                                        v-if="historyPagination && historyPagination.total_pages > 1"
                                        :current-page="historyPagination.page"
                                        :total-pages="historyPagination.total_pages"
                                        :page-size="historyPagination.page_size"
                                        :total-items="historyPagination.total_items"
                                        @page-change="onHistoryPageChange"
                                    ></pagination>
                                </div>

                                <!-- Notes (always visible) -->
                                <div v-if="borrower.notes" class="alert alert-info mt-3 mb-0">
                                    <h6 class="alert-heading">
                                        <i class="bi bi-sticky"></i>
                                        {{ t('borrower.notes') }}
                                    </h6>
                                    <p class="mb-0">{{ borrower.notes }}</p>
                                </div>
                            </div>
                        </div>

                        <!-- Modal Footer with Actions -->
                        <div v-if="borrower" class="modal-footer">
                            <borrower-actions
                                :borrower="borrower"
                                @action-completed="handleActionCompleted"
                                class="me-auto"
                            ></borrower-actions>

                            <button
                                type="button"
                                class="btn btn-secondary rounded-pill"
                                @click="close"
                            >
                                {{ t('common.close') }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <div v-if="show" class="modal-backdrop fade show"></div>
        </teleport>
    `,

    emits: ['close', 'updated', 'view-item'],

    setup(props, { emit }) {
        const { t } = VueI18n.useI18n();
        const { translateBlockReason } = useBlockReasonTranslation();
        const borrower = Vue.ref(null);
        const currentLoans = Vue.ref([]);
        const loading = Vue.ref(false);
        const error = Vue.ref('');

        // Holds state
        const activeTab = Vue.ref('loans');

        // History tab state
        const historyItems = Vue.ref([]);
        const historyPagination = Vue.ref(null);
        const historyPage = Vue.ref(1);
        const historyLoading = Vue.ref(false);
        const historyDateFrom = Vue.ref('');
        const historyDateTo = Vue.ref('');
        const historyLoaded = Vue.ref(false);

        // Holds state
        const holds = Vue.ref([]);
        const holdSearch = Vue.ref('');
        const holdResults = Vue.ref([]);
        const holdSearchLoading = Vue.ref(false);
        const holdFormMessage = Vue.ref(null); // { type: 'success'|'error', text: '' }

        // Get badge class for loan count
        const getLoanBadgeClass = (borrower) => {
            const count = borrower.current_loans_count || 0;
            const limit = borrower.loan_limit || 0;
            return count >= limit ? 'bg-warning text-dark' : 'bg-secondary';
        };

        // Load borrower data
        const loadBorrowerData = async () => {
            if (!props.borrowerId) return;

            loading.value = true;
            error.value = '';

            try {
                const response = await fetch(`/api/v1/borrowers/${props.borrowerId}?detail=true`);

                if (!response.ok) {
                    throw new Error(t('borrowers.error_load_failed'));
                }

                const data = await response.json();
                borrower.value = data;
                currentLoans.value = data.current_loans || [];
                historyLoaded.value = false;

                // Load active holds for this borrower
                try {
                    const holdsResp = await fetch(`/api/v1/holds/borrower/${data.id}`);
                    holds.value = holdsResp.ok ? await holdsResp.json() : [];
                } catch {
                    holds.value = [];
                }

            } catch (err) {
                error.value = err.message;
                console.error('Error loading borrower:', err);
            } finally {
                loading.value = false;
            }
        };

        // Handle action completed (block, unblock, renew)
        const handleActionCompleted = (action) => {
            // Reload borrower data to show updated state
            loadBorrowerData();
            emit('updated', action);
        };

        // Search books to reserve
        const searchBooksForHold = async () => {
            const q = holdSearch.value.trim();
            if (!q) { holdResults.value = []; holdFormMessage.value = null; return; }
            holdSearchLoading.value = true;
            try {
                const resp = await fetch(`/api/v1/catalog/bibliographic/search?q=${encodeURIComponent(q)}&limit=6`);
                const data = await resp.json();
                holdResults.value = data.records || data.items || [];
            } catch {
                holdResults.value = [];
            } finally {
                holdSearchLoading.value = false;
            }
        };

        // Create a hold for this borrower on a bibliographic record
        const createHold = async (biblioId) => {
            holdFormMessage.value = null;
            try {
                const resp = await fetch('/api/v1/holds', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        borrower_id: borrower.value.id,
                        bibliographic_record_id: biblioId,
                        created_by: 'web-ui'
                    })
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    const msg = err.error_code === 'HOLD_LIMIT_EXCEEDED'
                        ? t('holds.hold_limit_exceeded', { limit: err.context?.limit ?? '' })
                        : (err.error || t('errors.generic'));
                    holdFormMessage.value = { type: 'error', text: msg };
                    return;
                }
                holdSearch.value = '';
                holdResults.value = [];
                holdFormMessage.value = null;
                // Reload holds
                const holdsResp = await fetch(`/api/v1/holds/borrower/${borrower.value.id}`);
                holds.value = holdsResp.ok ? await holdsResp.json() : [];
            } catch {
                holdFormMessage.value = { type: 'error', text: t('errors.generic') };
            }
        };

        // Cancel a hold
        const cancelHold = async (holdId) => {
            try {
                await fetch(`/api/v1/holds/${holdId}`, { method: 'DELETE' });
                const holdsResp = await fetch(`/api/v1/holds/borrower/${borrower.value.id}`);
                holds.value = holdsResp.ok ? await holdsResp.json() : [];
            } catch {
                // ignore
            }
        };

        // Load history from dedicated endpoint
        const loadHistory = async () => {
            if (!borrower.value) return;
            historyLoading.value = true;
            try {
                const params = new URLSearchParams({
                    page: historyPage.value,
                    page_size: 20,
                });
                if (historyDateFrom.value) params.set('date_from', historyDateFrom.value);
                if (historyDateTo.value) params.set('date_to', historyDateTo.value);
                const resp = await fetch(`/api/v1/circulation/borrower/${borrower.value.borrower_id}/history?${params}`);
                if (!resp.ok) throw new Error('Failed to load history');
                const data = await resp.json();
                historyItems.value = data.history || [];
                historyPagination.value = data.pagination || null;
                historyLoaded.value = true;
            } catch {
                historyItems.value = [];
                historyPagination.value = null;
            } finally {
                historyLoading.value = false;
            }
        };

        const applyHistoryFilter = () => {
            historyPage.value = 1;
            loadHistory();
        };

        const clearHistoryFilter = () => {
            historyDateFrom.value = '';
            historyDateTo.value = '';
            historyPage.value = 1;
            loadHistory();
        };

        const onHistoryPageChange = (page) => {
            historyPage.value = page;
            loadHistory();
        };

        // View item detail (navigate to catalog)
        const viewItem = (recordId) => {
            emit('view-item', recordId);
        };

        // Close modal
        const close = () => {
            emit('close');
        };

        // Watch for show prop changes
        // Watch for both show and borrowerId changes
        // Combined into single watcher to prevent duplicate requests
        Vue.watch(
            () => [props.show, props.borrowerId],
            ([newShow, newId]) => {
                if (newShow && newId) {
                    loadBorrowerData();
                }
            },
            { immediate: true }
        );

        // Lazy-load history when tab is first activated
        Vue.watch(activeTab, (tab) => {
            if (tab === 'history' && !historyLoaded.value) {
                historyPage.value = 1;
                loadHistory();
            }
        });

        return {
            t,
            borrower,
            currentLoans,
            loading,
            error,
            activeTab,
            holds,
            holdSearch,
            holdResults,
            holdSearchLoading,
            holdFormMessage,
            historyItems,
            historyPagination,
            historyLoading,
            historyDateFrom,
            historyDateTo,
            getLoanBadgeClass,
            handleActionCompleted,
            searchBooksForHold,
            createHold,
            cancelHold,
            applyHistoryFilter,
            clearHistoryFilter,
            onHistoryPageChange,
            viewItem,
            translateBlockReason,
            close
        };
    }
};
