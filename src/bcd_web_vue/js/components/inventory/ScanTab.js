/**
 * ScanTab Component
 *
 * Barcode scanning input for inventory operations.
 * - Auto-focus input field
 * - Submit on enter (no button needed)
 * - Clear and refocus after each scan
 * - Calls API to mark item as inventoried
 * - Adds item to working table via useInventoryTable
 */

const { defineComponent, ref, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useAppState } from '../../composables/useAppState.js';
import { useBarcodeUtils } from '../../composables/useBarcodeUtils.js';

export default defineComponent({
    name: 'ScanTab',

    props: {
        inventoryTable: {
            type: Object,
            required: true
        }
    },

    setup(props) {
        const { t } = useI18n();
        const { success, error } = useNotification();
        const { settings } = useAppState();
        const { stripBarcodePrefix } = useBarcodeUtils();

        const barcodeInput = ref('');
        const scanInputEl = ref(null);
        const scanning = ref(false);

        /**
         * Focus the input field
         */
        const focusInput = () => {
            nextTick(() => {
                if (scanInputEl.value) {
                    scanInputEl.value.focus();
                }
            });
        };

        /**
         * Handle barcode scan submission
         */
        const handleScan = async () => {
            const barcode = barcodeInput.value.trim();

            if (!barcode) {
                return;
            }

            // Strip barcode prefix before sending to API
            const prefix = settings.value?.item_barcode_prefix || '.';
            const itemId = stripBarcodePrefix(barcode, prefix);

            scanning.value = true;

            try {
                // Call API to mark item as inventoried
                const response = await apiClient.patch(`/inventory/items/${itemId}`);

                // Add to working table with all fields (deduplicate + move to top if exists)
                props.inventoryTable.addItem({
                    // Item fields
                    item_id: response.item_id,
                    bibliographic_record_id: response.bibliographic_record_id,
                    status: response.status,
                    condition: response.condition,
                    loanable: response.loanable,
                    shelf_location: response.shelf_location,
                    last_inventoried_at: response.last_inventoried_at,
                    // Record fields
                    title: response.title,
                    genre: response.genre,
                    level: response.level,
                    target_audience: response.target_audience,
                    language: response.language,
                    medium_type: response.medium_type
                });

                // Show success notification (use itemId for consistency)
                success(t('inventory.scan.item_scanned', { barcode: itemId }));

            } catch (err) {
                if (err.response && err.response.status === 404) {
                    error(t('inventory.scan.item_not_found', { barcode: itemId }));
                } else {
                    error(t('inventory.scan.error', { barcode: itemId }));
                    console.error('Scan error:', err);
                }
            } finally {
                // Clear input and refocus
                barcodeInput.value = '';
                scanning.value = false;
                focusInput();
            }
        };

        // Auto-focus on mount
        onMounted(() => {
            focusInput();
        });

        return {
            t,
            barcodeInput,
            scanInputEl,
            scanning,
            handleScan,
            focusInput
        };
    },

    template: `
        <div class="scan-tab">
            <form @submit.prevent="handleScan">
                <div class="mb-3">
                    <label for="barcode-input" class="form-label">
                        {{ t('inventory.scan.barcode_label') }}
                    </label>
                    <input
                        id="barcode-input"
                        ref="scanInputEl"
                        v-model="barcodeInput"
                        type="text"
                        class="form-control form-control-lg"
                        :placeholder="t('inventory.scan.barcode_placeholder')"
                        :disabled="scanning"
                        autofocus
                    />
                    <div class="form-text">
                        {{ t('inventory.scan.help_text') }}
                    </div>
                </div>
            </form>
        </div>
    `
});
