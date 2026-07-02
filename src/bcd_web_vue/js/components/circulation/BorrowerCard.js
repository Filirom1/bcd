/**
 * BorrowerCard Component
 * Displays borrower information and current loans
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import { useBlockReasonTranslation } from '../../composables/useBlockReasonTranslation.js';

export default defineComponent({
    name: 'BorrowerCard',

    props: {
        borrower: {
            type: Object,
            required: true
        },
        showEditButton: {
            type: Boolean,
            default: false
        },
        compact: {
            type: Boolean,
            default: false
        },
        holds: {
            type: Array,
            default: () => []
        },
        canCheckoutHolds: {
            type: Boolean,
            default: false
        }
    },

    emits: ['renew-all', 'edit', 'quick-return', 'view-item', 'cancel-hold', 'checkout-hold'],

    setup(props, { emit }) {
        const { t, d } = useI18n();
        const { translateBlockReason } = useBlockReasonTranslation();

        const statusClass = computed(() => {
            if (props.borrower.status === 'blocked') {
                return 'danger';
            }
            if (props.borrower.overdue_count > 0) {
                return 'warning';
            }
            return 'success';
        });

        const statusIcon = computed(() => {
            if (props.borrower.status === 'blocked') {
                return 'bi-x-circle-fill';
            }
            if (props.borrower.overdue_count > 0) {
                return 'bi-exclamation-triangle-fill';
            }
            return 'bi-check-circle-fill';
        });

        const statusText = computed(() => {
            if (props.borrower.status === 'blocked') {
                return t('borrowers.status_blocked');
            }
            return t('borrowers.status_active');
        });

        const hasCurrentLoans = computed(() => {
            return props.borrower.current_loans && props.borrower.current_loans.length > 0;
        });

        const hasActiveHolds = computed(() => {
            return props.holds && props.holds.length > 0;
        });

        const hasAnythingToShow = computed(() => {
            return hasCurrentLoans.value ||
                   hasActiveHolds.value ||
                   props.borrower.status === 'blocked' ||
                   props.borrower.current_loans_count >= props.borrower.loan_limit ||
                   props.borrower.overdue_count > 0;
        });

        const renewAll = () => {
            emit('renew-all');
        };

        const edit = () => {
            emit('edit');
        };

        const formatDate = (dateStr) => {
            if (!dateStr) return '';
            return d(new Date(dateStr), 'short');
        };

        const isOverdue = (dueDate) => {
            if (!dueDate) return false;
            return new Date(dueDate) < new Date();
        };

        const daysOverdue = (dueDate) => {
            if (!isOverdue(dueDate)) return 0;
            const today = new Date();
            const due = new Date(dueDate);
            const diffTime = Math.abs(today - due);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            return diffDays;
        };

        return {
            statusClass,
            statusIcon,
            statusText,
            hasCurrentLoans,
            hasActiveHolds,
            hasAnythingToShow,
            renewAll,
            edit,
            formatDate,
            isOverdue,
            daysOverdue,
            translateBlockReason,
            t
        };
    },

    template: `
        <div class="card shadow-sm">
            <div v-if="!compact" class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">{{ borrower.first_name }} {{ borrower.last_name }}</h5>
                <button
                    v-if="showEditButton"
                    @click="edit"
                    class="btn btn-sm btn-light"
                >
                    <i class="bi bi-pencil"></i>
                    {{ t('common.edit') }}
                </button>
            </div>
            <div class="card-body">
                <!-- Borrower Info (hidden in compact mode — shown in borrower strip above) -->
                <div v-if="!compact" class="row mb-3">
                    <div class="col-md-6">
                        <div class="mb-2">
                            <small class="text-muted">{{ t('borrowers.borrower_id') }}</small>
                            <div class="fw-bold">{{ borrower.borrower_id }}</div>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">{{ t('borrowers.role') }}</small>
                            <div>
                                <span class="badge bg-secondary">{{ t('borrowers.role_' + borrower.role) }}</span>
                            </div>
                        </div>
                        <div v-if="borrower.class_name" class="mb-2">
                            <small class="text-muted">{{ t('borrowers.class') }}</small>
                            <div>{{ borrower.class_name }}</div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-muted mb-2">{{ t('borrowers.circulation_status') }}</h6>
                        <div class="mb-2">
                            <small class="text-muted">{{ t('circulation.current_loans') }}</small>
                            <div>
                                <span class="badge"
                                      :class="borrower.current_loans_count >= borrower.loan_limit ? 'bg-danger' : (borrower.loan_limit_warning && borrower.current_loans_count >= borrower.loan_limit_warning ? 'bg-warning text-dark' : 'bg-info')">
                                    {{ borrower.current_loans_count || 0 }}/{{ borrower.loan_limit }}
                                </span>
                            </div>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">{{ t('circulation.overdue') }}</small>
                            <div>
                                <span class="badge" :class="borrower.overdue_count > 0 ? 'bg-danger' : 'bg-success'">
                                    <i v-if="borrower.overdue_count > 0" class="bi bi-exclamation-triangle"></i>
                                    <i v-else class="bi bi-check"></i>
                                    {{ borrower.overdue_count || 0 }}
                                </span>
                            </div>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">{{ t('borrowers.total_checkouts') }}</small>
                            <div>{{ borrower.total_checkouts || 0 }}</div>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">{{ t('circulation.status') }}</small>
                            <div>
                                <span :class="'badge bg-' + statusClass">
                                    <i :class="statusIcon"></i>
                                    {{ statusText }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Current Loans Table -->
                <div v-if="hasCurrentLoans" class="mt-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="mb-0">
                            <i class="bi bi-book"></i>
                            {{ t('circulation.currently_borrowed') }}
                            <span class="badge bg-primary ms-1">{{ borrower.current_loans.length }}</span>
                        </h6>
                        <button
                            @click="renewAll"
                            class="btn btn-sm btn-primary"
                            v-if="borrower.current_loans.length > 0"
                        >
                            {{ t('circulation.renew_all') }}
                        </button>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>{{ t('catalog.inventory_number') }}</th>
                                    <th>{{ t('catalog.title') }}</th>
                                    <th>{{ t('circulation.due_date') }}</th>
                                    <th>{{ t('circulation.status') }}</th>
                                    <th>{{ t('common.actions') }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="loan in borrower.current_loans" :key="loan.item_id">
                                    <td>
                                        <code>{{ loan.item_id }}</code>
                                    </td>
                                    <td>
                                        <div class="d-flex align-items-center gap-2">
                                            <img
                                                v-if="loan.cover_image"
                                                :src="'/covers/' + loan.cover_image"
                                                style="width:28px; height:40px; object-fit:contain; flex-shrink:0;"
                                                @error="$event.target.style.display='none'"
                                            />
                                            <div>
                                                <a
                                                    href="#"
                                                    @click.prevent="$emit('view-item', loan.bibliographic_record_id)"
                                                    class="link-entity fw-bold"
                                                >
                                                    {{ loan.display_title || loan.title }}
                                                </a>
                                                <div v-if="loan.author" class="text-muted small">{{ loan.author }}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <div>{{ formatDate(loan.due_date) }}</div>
                                        <small v-if="isOverdue(loan.due_date)" class="text-danger">
                                            <i class="bi bi-exclamation-triangle"></i>
                                            {{ t('circulation.overdue_by_days', { days: daysOverdue(loan.due_date) }) }}
                                        </small>
                                    </td>
                                    <td>
                                        <span v-if="isOverdue(loan.due_date)" class="badge bg-danger">
                                            {{ t('circulation.overdue_label') }}
                                        </span>
                                        <span v-else class="badge bg-success">
                                            {{ t('circulation.on_loan') }}
                                        </span>
                                    </td>
                                    <td>
                                        <button
                                            class="btn btn-sm btn-outline-primary"
                                            @click="$emit('quick-return', loan.item_id)"
                                            :title="t('circulation.return')">
                                            <i class="bi bi-arrow-return-left"></i>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Reservations (Holds) Section -->
                <div v-if="hasActiveHolds" class="mt-3">
                    <h6 class="mb-2">
                        <i class="bi bi-bookmark-fill me-1"></i>
                        {{ t('holds.title') }}
                        <span class="badge bg-secondary ms-1">{{ holds.length }}</span>
                    </h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <tbody>
                                <tr v-for="hold in holds" :key="hold.id">
                                    <td>
                                        <a
                                            href="#"
                                            @click.prevent="$emit('view-item', hold.bibliographic_record_id)"
                                            class="link-entity fw-bold"
                                        >{{ hold.title || hold.bibliographic_record_title }}</a>
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
                                            v-if="canCheckoutHolds"
                                            :class="hold.status === 'ready' ? 'btn btn-sm btn-success me-1' : 'btn btn-sm btn-outline-success me-1'"
                                            @click="$emit('checkout-hold', hold)"
                                            :title="t('holds.checkout_hold')"
                                        >
                                            <i class="bi bi-box-arrow-in-right me-1"></i>{{ t('holds.checkout_hold') }}
                                        </button>
                                        <button
                                            class="btn btn-sm btn-outline-danger"
                                            @click="$emit('cancel-hold', hold.id)"
                                            :title="t('holds.cancel')"
                                        >
                                            <i class="bi bi-x-lg"></i>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Warning if blocked -->
                <div v-if="borrower.status === 'blocked'" class="alert alert-danger mt-3 mb-0">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    {{ t('circulation.borrower_blocked_warning') }}
                    <div v-if="borrower.blocked_reason" class="mt-1 small">
                        <strong>{{ t('borrowers.block_reason') }}:</strong> {{ translateBlockReason(borrower.blocked_reason) }}
                    </div>
                </div>

                <!-- Warning if at limit -->
                <div v-if="borrower.current_loans_count >= borrower.loan_limit" class="alert alert-warning mt-3 mb-0">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    {{ t('circulation.at_loan_limit') }}
                </div>

                <!-- Warning if at/above warning limit (soft limit) -->
                <div v-else-if="borrower.loan_limit_warning && borrower.current_loans_count >= borrower.loan_limit_warning" class="alert alert-warning mt-3 mb-0">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    {{ t('circulation.near_loan_limit', { count: borrower.current_loans_count, limit: borrower.loan_limit }) }}
                </div>

                <!-- Warning if has overdue items -->
                <div v-if="borrower.overdue_count > 0 && borrower.status !== 'blocked'"
                     class="alert alert-warning mt-3 mb-0">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    {{ t('circulation.has_overdue_items', { count: borrower.overdue_count }) }}
                </div>

                <!-- Empty state: compact mode, nothing to show -->
                <div v-if="compact && !hasAnythingToShow" class="text-center text-muted py-3">
                    {{ t('circulation.no_current_loans') }}
                </div>
            </div>
        </div>
    `
});
