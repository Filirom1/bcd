/**
 * Circulation Page Component
 * Checkout and Return workflows with <200ms scanner feedback
 */

const { defineComponent, ref, computed, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../api/client.js';
import { useNotification } from '../composables/useNotification.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { useBarcodeUtils } from '../composables/useBarcodeUtils.js';
import { useBlockReasonTranslation } from '../composables/useBlockReasonTranslation.js';
import { useGlobalModal } from '../composables/useGlobalModal.js';
import { useAppState } from '../composables/useAppState.js';
import { useItemBadge } from '../composables/useItemBadge.js';
import BorrowerCard from '../components/circulation/BorrowerCard.js';
import ItemScanner from '../components/circulation/ItemScanner.js';
import ClassRosterPanel from '../components/circulation/ClassRosterPanel.js';
import HelpPanel from '../components/ui/HelpPanel.js';

export default defineComponent({
    name: 'CirculationPage',

    components: {
        BorrowerCard,
        ItemScanner,
        ClassRosterPanel,
        HelpPanel
    },

    props: {
        mode: {
            type: String,
            default: 'checkout',
            validator: (value) => ['checkout', 'return'].includes(value)
        }
    },

    setup(props) {
        const { t, d } = useI18n();
        const { openRecord } = useGlobalModal();
        const { settings: appSettings } = useAppState();
        const { getShelfBadge, getCoteBadge } = useItemBadge(appSettings);
        const { success, error: showError, warning } = useNotification();
        const { handleError } = useErrorHandler(t);
        const { stripBarcodePrefix, fetchSettings } = useBarcodeUtils();
        const { translateBlockReason } = useBlockReasonTranslation();

        // Settings state (for barcode prefixes)
        const settings = ref(null);
        const settingsLoading = ref(true);

        // Borrower state
        const borrower = ref(null);
        const borrowerLoading = ref(false);
        const borrowerHolds = ref([]);

        // Scanned items state
        const scannedItems = ref([]);

        // Incremented after each checkout/return so ClassRosterPanel reloads its roster
        const rosterRefreshTick = ref(0);

        // Load settings on mount (must complete before scanning)
        onMounted(async () => {
            try {
                settings.value = await fetchSettings();
            } catch (error) {
                console.error('Failed to load settings:', error);
                // Use defaults if settings fail to load
                settings.value = {
                    borrower_barcode_prefix: '%',
                    item_barcode_prefix: '.'
                };
            } finally {
                settingsLoading.value = false;
            }
        });

        // Computed
        const borrowerLoaded = computed(() => borrower.value !== null);
        const borrowerInitials = computed(() => {
            if (!borrower.value) return '';
            return (borrower.value.first_name?.[0] || '').toUpperCase() +
                   (borrower.value.last_name?.[0] || '').toUpperCase();
        });
        const scannerDisabled = computed(() => {
            // Disable if settings are still loading
            if (settingsLoading.value) return true;
            // In checkout mode, also disable if borrower not loaded
            return props.mode === 'checkout' && !borrowerLoaded.value;
        });
        const borrowerAtLimit = computed(() => {
            if (!borrower.value) return false;
            return borrower.value.current_loans_count >= borrower.value.loan_limit;
        });

        /**
         * Load borrower information
         */
        const loadBorrower = async (borrowerId) => {
            try {
                borrowerLoading.value = true;

                // Strip barcode prefix if present (e.g., "%101" -> "101")
                const prefix = settings.value?.borrower_barcode_prefix || '';
                const normalizedId = prefix
                    ? stripBarcodePrefix(borrowerId, prefix)
                    : borrowerId;


                const data = await apiClient.get(`/borrowers/${normalizedId}`);

                // Fetch current loans from dedicated endpoint
                const loansData = await apiClient.get(`/circulation/borrower/${normalizedId}/items`);
                data.current_loans = loansData.loans || [];

                borrower.value = data;

                // Fetch active holds for this borrower (using numeric id)
                try {
                    const holdsData = await apiClient.get(`/holds/borrower/${data.id}`);
                    borrowerHolds.value = holdsData || [];
                } catch {
                    borrowerHolds.value = [];
                }

                // Check if blocked (only in checkout mode)
                if (props.mode === 'checkout' && data.status === 'blocked') {
                    showError(t('circulation.borrower_blocked_error'));
                    return;
                }

            } catch (err) {
                if (err.status === 404) {
                    showError(t('circulation.error_borrower_not_found', {
                        borrower_id: borrowerId
                    }));
                } else {
                    handleError(err);
                }
                borrower.value = null;
            } finally {
                borrowerLoading.value = false;
            }
        };

        /**
         * Handle item scan - IMMEDIATE checkout/return with <200ms target
         */
        const handleItemScanned = async (barcode) => {
            try {
                if (props.mode === 'checkout') {
                    await performCheckout(barcode);
                } else {
                    await performReturn(barcode);
                }
            } catch (err) {
                console.error('Error processing item:', err);
                // Error already handled in performCheckout/performReturn
            }
        };

        /**
         * Perform immediate checkout for single item
         */
        const performCheckout = async (barcode) => {
            try {
                // Strip item barcode prefix if present (e.g., ".785" -> "785")
                const itemId = settings.value?.item_barcode_prefix
                    ? stripBarcodePrefix(barcode, settings.value.item_barcode_prefix)
                    : barcode;

                const result = await apiClient.post('/circulation/checkout', {
                    borrower_id: borrower.value.borrower_id,
                    item_ids: [itemId],
                    checked_out_by: 'web-ui'
                });

                const transaction = result.transactions[0];

                // Add to scanned items list
                scannedItems.value.push({
                    item_id: transaction.item_id,
                    barcode: barcode,
                    title: transaction.display_title || transaction.title || 'Unknown',
                    author: transaction.author,
                    due_date: transaction.due_date,
                    cover_image: transaction.cover_image,
                    checked_out: true
                });

                // Reload borrower to update loan count and current loans table
                await loadBorrower(borrower.value.borrower_id);

                // Refresh the class roster to reflect the new loan status
                rosterRefreshTick.value++;

            } catch (err) {
                // Handle error using error codes and context (no regex!)
                // Note: error codes are lowercase (normalized by ApiError)
                const errorCode = err.code || 'unknown_error';
                const context = err.details || {};
                let friendlyMessage;

                // Use error code to get translated message with context
                // Note: error codes are lowercase (normalized by ApiError)
                switch (errorCode) {
                    case 'loan_limit_exceeded':
                        friendlyMessage = t('errors.loan_limit_exceeded', {
                            current: context.current,
                            limit: context.limit,
                            additional: context.additional
                        });
                        break;

                    case 'item_already_on_loan':
                        friendlyMessage = t('errors.item_already_on_loan', {
                            item_id: context.item_id,
                            borrower_name: context.borrower_name,
                            due_date: d(new Date(context.due_date), 'short')
                        });
                        break;

                    case 'borrower_blocked':
                        friendlyMessage = t('errors.borrower_blocked', {
                            borrower_id: context.borrower_id,
                            reason: translateBlockReason(context.reason)
                        });
                        break;

                    case 'borrower_has_overdue':
                        friendlyMessage = t('errors.borrower_has_overdue', {
                            count: context.overdue_count
                        });
                        break;

                    case 'item_not_found':
                        friendlyMessage = t('errors.item_not_found', {
                            item_id: context.item_id || barcode
                        });
                        break;

                    case 'item_not_available':
                        friendlyMessage = t('errors.item_not_available', {
                            item_id: context.item_id || barcode,
                            status: context.status
                        });
                        break;

                    case 'item_not_loanable':
                        friendlyMessage = t('errors.item_not_loanable', {
                            item_id: context.item_id || barcode
                        });
                        break;

                    case 'item_reserved_for_other':
                        friendlyMessage = t('errors.item_reserved_for_other', {
                            reserved_for_name: context.reserved_for_name
                        });
                        break;

                    case 'borrower_not_found':
                        friendlyMessage = t('errors.borrower_not_found', {
                            borrower_id: context.borrower_id
                        });
                        break;

                    default:
                        // Fallback to raw error message or generic error
                        friendlyMessage = err.message || t('circulation.error_checkout_failed');
                }

                showError(friendlyMessage);

                // Don't add failed items to list - just show error notification
            }
        };

        /**
         * Perform immediate return for single item
         */
        const performReturn = async (barcode) => {
            try {
                // Strip item barcode prefix if present (e.g., ".785" -> "785")
                const itemId = settings.value?.item_barcode_prefix
                    ? stripBarcodePrefix(barcode, settings.value.item_barcode_prefix)
                    : barcode;

                const result = await apiClient.post('/circulation/return', {
                    item_ids: [itemId],
                    returned_by: 'web-ui'
                });

                const transaction = result.items[0];

                // Add to scanned items list
                scannedItems.value.push({
                    item_id: transaction.item_id,
                    barcode: barcode,
                    title: transaction.display_title || transaction.title || 'Unknown',
                    author: transaction.author,
                    call_number: transaction.call_number,
                    shelf_location: transaction.shelf_location,
                    returned_date: transaction.return_date,
                    returned: true,
                    was_overdue: transaction.was_overdue,
                    days_overdue: transaction.days_overdue,
                    hold_ready: transaction.hold_ready
                });

                // Show warning if item was overdue
                if (transaction.was_overdue) {
                    warning(t('circulation.item_returned_overdue', {
                        item_id: barcode,
                        borrower: transaction.borrower_name,
                        days: transaction.days_overdue
                    }));
                }

                // Show hold_ready notification so librarian knows to set the book aside
                if (transaction.hold_ready) {
                    const hr = transaction.hold_ready;
                    warning(t('circulation.hold_ready_message', {
                        name: hr.borrower_name,
                        class: hr.class_name || hr.borrower_id
                    }));
                }

            } catch (err) {
                // Handle error using error codes like checkout
                // Note: error codes are lowercase (normalized by ApiError)
                const errorCode = err.code || 'unknown_error';
                const context = err.details || {};
                let friendlyMessage;

                switch (errorCode) {
                    case 'item_not_found':
                        friendlyMessage = t('errors.item_not_found', {
                            item_id: context.item_id || barcode
                        });
                        break;

                    case 'item_not_on_loan':
                        friendlyMessage = t('errors.item_not_on_loan', {
                            item_id: context.item_id || barcode
                        });
                        break;

                    default:
                        friendlyMessage = err.message || t('circulation.error_return_failed');
                }

                showError(friendlyMessage);

                // Don't add failed items to list - just show error notification
            }
        };

        /**
         * Renew all items for borrower
         */
        const renewAll = async () => {
            if (!borrower.value) return;

            try {
                const result = await apiClient.post('/circulation/renew', {
                    borrower_id: borrower.value.borrower_id,
                    item_ids: null  // null = renew all eligible items
                });

                // Show success/failure summary
                if (result.renewed.length > 0) {
                    success(t('circulation.renewed_successfully', {
                        count: result.renewed.length
                    }));
                }

                if (result.failed.length > 0) {
                    warning(t('circulation.renewal_failed', {
                        count: result.failed.length
                    }));
                }

                // Reload borrower to get updated loan info
                await loadBorrower(borrower.value.borrower_id);

            } catch (err) {
                handleError(err);
            }
        };

        /**
         * Remove item from scanned list
         */
        const removeItem = (itemId) => {
            scannedItems.value = scannedItems.value.filter(
                item => item.item_id !== itemId && item.barcode !== itemId
            );
        };

        /**
         * Format return time as HH:MM for session list
         */
        const formatReturnTime = (dateStr) => {
            if (!dateStr) return '';
            try {
                return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            } catch {
                return '';
            }
        };

        /**
         * Format date for hold expiration
         */
        const formatDate = (dateStr) => {
            if (!dateStr) return '';
            try {
                return new Date(dateStr).toLocaleDateString();
            } catch {
                return '';
            }
        };

        /**
         * Cancel a hold for the current borrower
         */
        const cancelHold = async (holdId) => {
            try {
                await apiClient.delete(`/holds/${holdId}`);
                success(t('holds.hold_cancelled'));
                // Reload holds
                if (borrower.value) {
                    const holdsData = await apiClient.get(`/holds/borrower/${borrower.value.id}`);
                    borrowerHolds.value = holdsData || [];
                }
            } catch (err) {
                handleError(err);
            }
        };

        /**
         * Check out a reserved item directly from the hold shortcut
         */
        const checkoutHold = async (hold) => {
            try {
                const itemsData = await apiClient.get(`/catalog/bibliographic/${hold.bibliographic_record_id}/items`);
                const items = Array.isArray(itemsData) ? itemsData : (itemsData.items || []);
                const availableItem = items.find(i => i.status === 'available');
                if (!availableItem) {
                    showError(t('holds.no_available_item'));
                    return;
                }
                await apiClient.post('/circulation/checkout', {
                    borrower_id: borrower.value.borrower_id,
                    item_ids: [availableItem.item_id],
                    checked_out_by: 'web-ui'
                });
                success(`${hold.title} — ${t('circulation.checkout_success', { count: 1 })}`);
                await loadBorrower(borrower.value.borrower_id);
            } catch (err) {
                handleError(err);
            }
        };

        /**
         * View item detail (navigate to catalog)
         */
        const viewItem = (recordId) => {
            openRecord(recordId);
        };

        /**
         * Quick return single item from borrower card
         */
        const quickReturn = async (itemId) => {
            try {
                const result = await apiClient.post('/circulation/return', {
                    item_ids: [itemId],
                    returned_by: 'web-ui'
                });

                const returned = result.items?.[0];
                const titleDisplay = returned?.display_title || returned?.title || itemId;
                
                let locationParts = [];
                if (returned?.shelf_location) locationParts.push(returned.shelf_location);
                if (returned?.call_number) locationParts.push(returned.call_number);
                
                const locationText = locationParts.length > 0 ? locationParts.join(' / ') : '-';
                const shelfInfo = ` — ${t('circulation.ranger')} : ${locationText}`;
                success(`✓ ${titleDisplay}${shelfInfo}`);

                // Show hold_ready notification so librarian knows to set the book aside
                if (returned?.hold_ready) {
                    const hr = returned.hold_ready;
                    warning(t('circulation.hold_ready_message', {
                        name: hr.borrower_name,
                        class: hr.class_name || hr.borrower_id
                    }));
                }

                // Reload borrower to get updated loan info
                await loadBorrower(borrower.value.borrower_id);

                // Refresh the class roster to reflect the updated loan status
                rosterRefreshTick.value++;

            } catch (err) {
                handleError(err);
            }
        };

        const helpSection = computed(() => props.mode === 'return' ? 'return' : 'checkout');

        return {
            borrower,
            borrowerLoading,
            helpSection,
            getShelfBadge,
            getCoteBadge,
            borrowerLoaded,
            borrowerInitials,
            borrowerHolds,
            scannedItems,
            rosterRefreshTick,
            scannerDisabled,
            borrowerAtLimit,
            settings,
            loadBorrower,
            handleItemScanned,
            renewAll,
            quickReturn,
            cancelHold,
            checkoutHold,
            viewItem,
            removeItem,
            formatReturnTime,
            formatDate,
            t,
            mode: props.mode
        };
    },

    template: `
        <div>

            <!-- ══════════════════════════════════════════════════════
                 CHECKOUT MODE — three-panel workspace
                 Left: class roster (ClassRosterPanel)
                 Right: borrower strip + item scanner + loans table
            ══════════════════════════════════════════════════════ -->
            <template v-if="mode === 'checkout'">
                <div class="page-header">
                    <h1 class="page-title">
                        <i class="bi bi-box-arrow-right me-2"></i>
                        {{ t('navigation.checkout') }}
                    </h1>
                    <div class="d-flex gap-2">
                        <help-panel :section="helpSection" />
                    </div>
                </div>

                <div class="checkout-page">
                    <div class="checkout-workspace">

                        <!-- Left: unified borrower identification panel -->
                        <class-roster-panel
                            :settings="settings"
                            :selected-borrower-id="borrower ? borrower.borrower_id : null"
                            :refresh-tick="rosterRefreshTick"
                            @borrower-selected="loadBorrower"
                        />

                        <!-- Right: action panel -->
                        <div class="action-panel">

                            <!-- ① Compact borrower strip -->
                            <div v-if="borrowerLoaded" class="borrower-strip">
                                <div class="b-avatar">{{ borrowerInitials }}</div>
                                <div class="b-info">
                                    <div class="b-name">{{ borrower.first_name }} {{ borrower.last_name }}</div>
                                    <div class="b-meta">
                                        ID {{ borrower.borrower_id }}
                                        <template v-if="borrower.class_name"> · {{ borrower.class_name }}</template>
                                        · {{ t('borrowers.role_' + borrower.role) }}
                                    </div>
                                </div>
                                <div class="b-badges">
                                    <span
                                        class="badge"
                                        :class="borrower.current_loans_count >= borrower.loan_limit ? 'bg-danger' : (borrower.loan_limit_warning && borrower.current_loans_count >= borrower.loan_limit_warning ? 'bg-warning text-dark' : 'bg-info text-dark')"
                                    >
                                        {{ borrower.current_loans_count }}/{{ borrower.loan_limit }}
                                    </span>
                                    <span
                                        class="badge ms-1"
                                        :class="borrower.overdue_count > 0 ? 'bg-danger' : 'bg-success'"
                                    >
                                        {{ borrower.overdue_count }} {{ t('circulation.overdue') }}
                                    </span>
                                </div>
                            </div>
                            <div v-else class="no-borrower-placeholder">
                                <i class="bi bi-person-plus fs-4 d-block mb-2"></i>
                                {{ t('circulation.no_borrower_selected') }}
                            </div>

                            <!-- ② Item scanner -->
                            <item-scanner
                                :mode="mode"
                                :borrower="borrower"
                                :disabled="scannerDisabled"
                                @item-scanned="handleItemScanned"
                                class="mb-3"
                            />

                            <!-- ③ BorrowerCard — compact mode (loans table + alerts only, no header/stats) -->
                            <borrower-card
                                v-if="borrowerLoaded"
                                :borrower="borrower"
                                :compact="true"
                                :holds="borrowerHolds"
                                :can-checkout-holds="true"
                                @renew-all="renewAll"
                                @quick-return="quickReturn"
                                @view-item="viewItem"
                                @cancel-hold="cancelHold"
                                @checkout-hold="checkoutHold"
                            />

                        </div><!-- /action-panel -->
                    </div><!-- /checkout-workspace -->
                </div><!-- /checkout-page -->
            </template>

            <!-- ══════════════════════════════════════════════════════
                 RETURN MODE — existing two-column layout (unchanged)
            ══════════════════════════════════════════════════════ -->
            <template v-else>
                <div class="page-header">
                    <h1 class="page-title">
                        <i class="bi bi-box-arrow-in-left me-2"></i>
                        {{ t('navigation.return') }}
                    </h1>
                    <div class="d-flex gap-2">
                        <help-panel :section="helpSection" />
                    </div>
                </div>

                <div class="return-page">
                <div class="return-workspace">
                    <!-- Left panel: Scanner + Borrower Card -->
                    <div class="return-scanner-panel">
                        <!-- Item Scanner -->
                        <item-scanner
                            :mode="mode"
                            :borrower="borrower"
                            :disabled="scannerDisabled"
                            @item-scanned="handleItemScanned"
                        />

                        <!-- Borrower Card (if loaded) -->
                        <borrower-card
                            v-if="borrowerLoaded"
                            :borrower="borrower"
                            :holds="borrowerHolds"
                            class="mt-3"
                            @renew-all="renewAll"
                            @quick-return="quickReturn"
                            @view-item="viewItem"
                            @cancel-hold="cancelHold"
                        />
                    </div>

                    <!-- Right panel: Session Returns List (always visible) -->
                    <div class="return-list-panel">
                        <div class="card shadow-sm">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <h6 class="mb-0">
                                    <i class="bi bi-box-arrow-in-left me-1"></i>
                                    {{ t('circulation.returned_items') }}
                                </h6>
                                <span class="badge bg-primary ms-1">{{ scannedItems.length }}</span>
                            </div>

                            <!-- Empty state -->
                            <div v-if="scannedItems.length === 0" class="card-body text-center py-5">
                                <i class="bi bi-arrow-return-left display-1 text-muted mb-3 d-block"></i>
                                <p class="text-muted mb-0">{{ t('circulation.return_help_message') }}</p>
                            </div>

                            <!-- Items table -->
                            <div v-else class="table-responsive">
                                <table class="table table-sm table-hover mb-0">
                                    <thead class="table-light">
                                        <tr>
                                            <th class="text-muted fw-normal" style="width: 2rem;">#</th>
                                            <th class="text-muted fw-normal">{{ t('catalog.inventory_number') }}</th>
                                            <th class="text-muted fw-normal">{{ t('catalog.title') }}</th>
                                            <th class="text-muted fw-normal">{{ t('catalog.shelf_location_call_number') }}</th>
                                            <th class="text-muted fw-normal">{{ t('circulation.returned_at') }}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr
                                            v-for="(item, index) in scannedItems.slice().reverse()"
                                            :key="item.item_id || index"
                                        >
                                            <td class="text-muted small align-middle">{{ scannedItems.length - index }}</td>
                                            <td class="align-middle"><code>{{ item.barcode || item.item_id }}</code></td>
                                            <td class="align-middle">
                                                <div class="fw-bold">{{ item.title }}</div>
                                                <small v-if="item.author" class="text-muted">{{ item.author }}</small>
                                                <span v-if="item.was_overdue" class="badge bg-danger ms-1">
                                                    {{ t('circulation.overdue_label') }}
                                                </span>
                                                <div v-if="item.hold_ready" class="alert alert-warning mt-2 mb-0 py-2 px-3">
                                                    <div class="d-flex align-items-center">
                                                        <i class="bi bi-bookmark-star-fill fs-5 me-2"></i>
                                                        <div>
                                                            <strong class="d-block">{{ t('circulation.hold_ready_title') }}</strong>
                                                            <span class="small">
                                                                {{ t('circulation.hold_ready_message', {
                                                                    name: item.hold_ready.borrower_name,
                                                                    class: item.hold_ready.class_name || item.hold_ready.borrower_id
                                                                }) }}
                                                            </span>
                                                            <div v-if="item.hold_ready.expiration_date" class="small text-muted">
                                                                {{ t('circulation.hold_expires') }}: {{ formatDate(item.hold_ready.expiration_date) }}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td class="align-middle">
                                                <div v-if="item.shelf_location || item.call_number" class="d-flex flex-wrap align-items-center gap-1">
                                                    <span v-if="item.shelf_location && getShelfBadge(item.shelf_location)" :style="getShelfBadge(item.shelf_location)">{{ item.shelf_location }}</span>
                                                    <span v-if="item.call_number && getCoteBadge(item.call_number)" :style="getCoteBadge(item.call_number)">{{ item.call_number }}</span>
                                                </div>
                                                <span v-else class="text-muted small">-</span>
                                            </td>
                                            <td class="small text-muted align-middle">{{ formatReturnTime(item.returned_date) }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div><!-- /return-workspace -->
                </div><!-- /return-page -->
            </template>

        </div>
    `
});
