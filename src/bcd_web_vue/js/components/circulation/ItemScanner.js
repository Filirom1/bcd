/**
 * ItemScanner Component
 * Scanner input for checkout/return with <200ms feedback and autocomplete
 */

const { defineComponent, ref, onMounted, nextTick, watch } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import AutocompleteInput from '../ui/AutocompleteInput.js';

export default defineComponent({
    name: 'ItemScanner',

    components: {
        AutocompleteInput
    },

    props: {
        mode: {
            type: String,
            required: true,
            validator: (value) => ['checkout', 'return'].includes(value)
        },
        borrower: {
            type: Object,
            default: null
        },
        disabled: {
            type: Boolean,
            default: false
        }
    },

    emits: ['item-scanned', 'focus'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const itemBarcode = ref('');
        const autocompleteRef = ref(null);
        const scanning = ref(false);

        // Fetch items from API for autocomplete
        const fetchItems = async (query, signal) => {
            try {
                const response = await apiClient.get('/catalog/bibliographic/search', {
                    q: query,
                    limit: 10
                }, { signal });

                // For each bibliographic record, fetch its items to get actual barcodes
                const recordsWithItems = await Promise.all(
                    (response.items || []).map(async (record) => {
                        try {
                            const items = await apiClient.get(`/catalog/bibliographic/${record.id}/items`, {}, { signal });
                            return {
                                ...record,
                                physical_items: items || []
                            };
                        } catch (err) {
                            console.warn(`Could not fetch items for record ${record.id}:`, err);
                            return {
                                ...record,
                                physical_items: []
                            };
                        }
                    })
                );

                // In return mode, only show records that have at least one item on loan
                if (props.mode === 'return') {
                    return recordsWithItems.filter(record =>
                        (record.physical_items || []).some(item => item.status === 'on_loan')
                    );
                }

                return recordsWithItems;
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Error fetching items:', error);
                }
                throw error;
            }
        };

        // Format item result for display
        const formatItemResult = (record) => {
            const physicalItems = record.physical_items || [];
            const authors = record.authors && record.authors.length > 0
                ? record.authors.join(', ')
                : t('catalog.unknown_author');

            if (props.mode === 'return') {
                const onLoanItems = physicalItems.filter(item => item.status === 'on_loan');
                const itemId = onLoanItems[0]?.item_id || 'N/A';
                const copyInfo = onLoanItems.length > 1 ? ` (${onLoanItems.length} ${t('catalog.copies_label')})` : '';
                return `
                    <div>
                        <div class="fw-bold">${itemId} - ${record.title || t('catalog.unknown_title')}${copyInfo}</div>
                        <small class="text-muted">${authors} · ${record.medium_type || t('catalog.medium_book')}</small>
                        <span class="badge bg-warning text-dark ms-2">${t('catalog.status_en_cours')}</span>
                    </div>
                `;
            }

            // Checkout mode
            const availableItems = physicalItems.filter(item => item.status === 'available');
            const firstAvailable = availableItems.length > 0 ? availableItems[0] : physicalItems[0];
            const itemId = firstAvailable ? firstAvailable.item_id : 'N/A';
            const totalItems = record.total_items || 0;
            const copyInfo = totalItems > 1 ? ` (${totalItems} ${t('catalog.copies_label')})` : '';
            const statusBadge = availableItems.length > 0
                ? `<span class="badge bg-success ms-2">${t('item.status_available')}</span>`
                : `<span class="badge bg-secondary ms-2">${t('item.status_on_loan')}</span>`;

            return `
                <div>
                    <div class="fw-bold">${itemId} - ${record.title || t('catalog.unknown_title')}${copyInfo}</div>
                    <small class="text-muted">${authors} · ${record.medium_type || t('catalog.medium_book')}</small>
                    ${statusBadge}
                </div>
            `;
        };

        // Handle item selection from autocomplete
        const handleItemSelect = (record) => {
            const physicalItems = record.physical_items || [];
            let itemToScan;

            if (props.mode === 'return') {
                itemToScan = physicalItems.find(item => item.status === 'on_loan') || physicalItems[0];
            } else {
                const availableItems = physicalItems.filter(item => item.status === 'available');
                itemToScan = availableItems.length > 0 ? availableItems[0] : physicalItems[0];
            }

            if (itemToScan && itemToScan.item_id) {
                scanItem(itemToScan.item_id);
            }
        };

        // Handle manual submit (Enter or button click)
        const handleSubmit = (value) => {
            const barcode = value.trim();
            if (barcode) {
                scanItem(barcode);
            }
        };

        const scanItem = async (barcode) => {
            if (!barcode || scanning.value) {
                return;
            }

            // In checkout mode, require borrower to be loaded
            if (props.mode === 'checkout' && !props.borrower) {
                return;
            }

            try {
                scanning.value = true;

                // Emit the scan event - parent will handle API call
                emit('item-scanned', barcode);

                // Clear input for next scan
                itemBarcode.value = '';

            } catch (error) {
                console.error('Error in item scanner:', error);
            } finally {
                // Re-enable input then re-focus so focus works on an enabled element
                setTimeout(() => {
                    scanning.value = false;
                    focusInput();
                }, 50);
            }
        };

        const focusInput = async () => {
            await nextTick();
            if (autocompleteRef.value) {
                autocompleteRef.value.focusInput();
            }
            emit('focus');
        };

        // Auto-focus when component mounts
        onMounted(() => {
            focusInput();
        });

        // Re-focus when mode changes, borrower loads, or input becomes enabled
        watch([() => props.mode, () => props.borrower, () => props.disabled], () => {
            if (!props.disabled) {
                focusInput();
            }
        });

        return {
            itemBarcode,
            autocompleteRef,
            scanning,
            fetchItems,
            formatItemResult,
            handleItemSelect,
            handleSubmit,
            scanItem,
            focusInput,
            t
        };
    },

    template: `
        <div class="card">
            <div class="card-body">
                <form @submit.prevent="handleSubmit(itemBarcode)">
                    <div class="input-group input-group-lg">
                        <span class="input-group-text">
                            <i class="bi bi-upc-scan"></i>
                        </span>
                        <autocomplete-input
                            ref="autocompleteRef"
                            v-model="itemBarcode"
                            :placeholder="t('circulation.scan_barcode_placeholder')"
                            :fetchResults="fetchItems"
                            :formatResult="formatItemResult"
                            :disabled="disabled || scanning"
                            inputmode="text"
                            :minChars="2"
                            :autoSelectFirst="true"
                            :otherInputAttrs="{ class: 'font-monospace' }"
                            @select="handleItemSelect"
                            @submit="handleSubmit"
                        />
                        <button
                            type="submit"
                            class="btn"
                            :class="mode === 'checkout' ? 'btn-success' : 'btn-info'"
                            :disabled="disabled || scanning || !itemBarcode.trim()"
                        >
                            <span v-if="scanning" class="spinner-border spinner-border-sm me-1"></span>
                            <i v-else class="bi bi-check-lg me-1"></i>
                            {{ mode === 'checkout' ? t('circulation.checkout') : t('circulation.return') }}
                        </button>
                    </div>
                </form>

                <div v-if="disabled && mode === 'checkout' && !borrower" class="alert alert-info mt-3 mb-0">
                    <i class="bi bi-info-circle me-2"></i>
                    {{ t('circulation.scan_borrower_first') }}
                </div>
            </div>
        </div>
    `
});
