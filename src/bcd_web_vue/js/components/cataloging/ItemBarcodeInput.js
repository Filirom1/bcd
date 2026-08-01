/**
 * Item Barcode Input Component
 * Creates physical items (copies) for a bibliographic record
 */

const { defineComponent, ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';
import { useAppState } from '../../composables/useAppState.js';
import DeweyPicker from '../ui/DeweyPicker.js';
import ShelfLocationPicker from '../ui/ShelfLocationPicker.js';
import { computeCallNumber, suggestShelfLocation } from '../../utils/callNumber.js';

export default defineComponent({
    name: 'ItemBarcodeInput',

    components: { DeweyPicker, ShelfLocationPicker },

    props: {
        recordId: {
            type: Number,
            required: true
        },
        recordTitle: {
            type: String,
            required: true
        },
        recordMediumType: {
            type: String,
            default: ''
        },
        recordDeweyNumber: {
            type: String,
            default: null
        },
        recordAuthors: {
            type: Array,
            default: () => []
        },
        recordCollection: {
            type: String,
            default: null
        },
        recordIllustrators: {
            type: Array,
            default: () => []
        }
    },

    emits: ['item-created', 'done', 'edit-record'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { success, error: showError } = useNotification();
        const { handleError } = useErrorHandler(t);
        const { settings } = useAppState();

        const deweyColors = computed(() => {
            try { return JSON.parse(settings.value?.dewey_colors || 'null') || undefined; }
            catch { return undefined; }
        });

        const shelfLocationOptions = computed(() => {
            try { return JSON.parse(settings.value?.catalog_shelf_locations || '[]') || []; }
            catch { return []; }
        });

        // State
        const barcode = ref('');
        const barcodeInput = ref(null);
        const callNumber = ref('');
        const callNumberInput = ref(null);
        const shelfLocation = ref('');
        const loading = ref(false);
        const createdItems = ref([]);
        const showOptional = ref(false);
        const acquisitionDate = ref(new Date().toISOString().slice(0, 10));
        const fundingSource = ref('');
        const condition = ref('good');
        const loanable = ref(true);

        const isPeriodical = computed(() => props.recordMediumType === 'P\u00e9riodique');

        // Suggested call number based on dynamic settings rules:
        const suggestedCallNumber = computed(() => {
            const rules = (() => {
                try {
                    return JSON.parse(settings.value?.catalog_call_number_rules || '[]');
                } catch {
                    return [];
                }
            })();

            const record = {
                title: props.recordTitle,
                authors: props.recordAuthors,
                collection: props.recordCollection,
                deweyNumber: props.recordDeweyNumber,
                mediumType: props.recordMediumType,
                illustrators: props.recordIllustrators
            };

            return computeCallNumber(record, shelfLocation.value, rules);
        });

        const suggestedShelfLocation = computed(() => {
            return suggestShelfLocation(props.recordMediumType, shelfLocationOptions.value);
        });

        // Update call number when suggestedCallNumber changes
        watch(suggestedCallNumber, (val, oldVal) => {
            if (val && (!callNumber.value.trim() || callNumber.value === oldVal)) {
                callNumber.value = val;
            }
        }, { immediate: true });

        // Pre-fill shelf location only when it is still empty
        watch(suggestedShelfLocation, (val) => {
            if (val && !shelfLocation.value.trim()) {
                shelfLocation.value = val;
            }
        }, { immediate: true });

        /**
         * Create item with barcode
         */
        const createItem = async () => {
            const barcodeValue = barcode.value.trim();

            if (!barcodeValue) {
                showError(t('cataloging.error_no_barcode'));
                return;
            }

            try {
                loading.value = true;

                // Create item
                const itemData = {
                    item_id: barcodeValue,  // API expects 'item_id' not 'barcode'
                    bibliographic_record_id: props.recordId
                };

                if (isPeriodical.value) {
                    const cn = callNumber.value.trim();
                    if (!cn) {
                        showError(t('periodical.required'));
                        loading.value = false;
                        return;
                    }
                    itemData.call_number = cn;
                } else {
                    const cn = callNumber.value.trim();
                    if (cn) itemData.call_number = cn;
                }

                const sl = shelfLocation.value.trim();
                if (sl) itemData.shelf_location = sl;

                if (acquisitionDate.value) itemData.acquisition_date = acquisitionDate.value;
                if (fundingSource.value.trim()) itemData.funding_source = fundingSource.value.trim();
                itemData.condition = condition.value;
                itemData.loanable = loanable.value;

                const item = await apiClient.post('/catalog/items', itemData);

                // Add to created items list
                createdItems.value.push(item);

                success(t('cataloging.item_created', {
                    barcode: item.item_id || item.barcode
                }));

                // Emit event
                emit('item-created', item);

                // Clear barcode for next item (keep shelf_location + call_number for batch scanning)
                barcode.value = '';
                if (isPeriodical.value) callNumber.value = '';

                // Re-focus input for rapid scanning
                setTimeout(() => {
                    if (isPeriodical.value) {
                        callNumberInput.value?.focus();
                    } else {
                        barcodeInput.value?.focus();
                    }
                }, 100);

            } catch (err) {
                if (err.error_code === 'DUPLICATE_ITEM_ID') {
                    showError(t('cataloging.error_barcode_exists', {
                        barcode: barcodeValue
                    }));
                } else {
                    handleError(err);
                }
            } finally {
                loading.value = false;
            }
        };

        /**
         * Handle Enter key (scanner compatibility)
         */
        const handleKeypress = (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                createItem();
            }
        };

        /**
         * Finish creating items
         */
        const finish = () => {
            emit('done');
        };

        // Computed
        const itemCount = computed(() => createdItems.value.length);

        return {
            barcode,
            barcodeInput,
            callNumber,
            callNumberInput,
            shelfLocation,
            loading,
            createdItems,
            itemCount,
            isPeriodical,
            deweyColors,
            shelfLocationOptions,
            showOptional,
            acquisitionDate,
            fundingSource,
            condition,
            loanable,
            createItem,
            handleKeypress,
            finish
        };
    },

    template: `
        <div class="item-barcode-input">
            <h5 class="mb-3">
                <i class="bi bi-box-seam"></i>
                {{ $t('cataloging.create_items_title') }}
            </h5>

            <div class="alert alert-info mb-4 d-flex justify-content-between align-items-center">
                <div>
                    <p class="mb-2">
                        <strong>{{ $t('cataloging.record_created_title') }}:</strong> {{ recordTitle }}
                    </p>
                    <p class="mb-0 small">
                        {{ $t('cataloging.scan_barcodes_help') }}
                    </p>
                </div>
                <div>
                    <button
                        type="button"
                        class="btn btn-outline-primary btn-sm"
                        @click="$emit('edit-record')"
                    >
                        <i class="bi bi-pencil me-1"></i>
                        {{ $t('cataloging.edit_record_button') }}
                    </button>
                </div>
            </div>

            <form @submit.prevent="createItem">
                <!-- Issue number field (periodicals only) -->
                <div v-if="isPeriodical" class="mb-3">
                    <label class="form-label">
                        {{ $t('periodical.issue_number') }}
                        <span class="text-danger">*</span>
                    </label>
                    <input
                        ref="callNumberInput"
                        v-model="callNumber"
                        type="text"
                        class="form-control"
                        :placeholder="$t('periodical.issue_number_placeholder')"
                        :disabled="loading"
                        @keypress.enter.prevent="$refs.barcodeInput?.focus()"
                    />
                </div>

                <!-- Shelf location + call number (non-periodicals) -->
                <div v-if="!isPeriodical" class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">{{ $t('catalog.shelf_location') }}</label>
                        <shelf-location-picker
                            v-model="shelfLocation"
                            :locations="shelfLocationOptions"
                            :disabled="loading"
                        />
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">{{ $t('catalog.call_number') }}</label>
                        <dewey-picker
                            v-model="callNumber"
                            :colors="deweyColors"
                            :disabled="loading"
                        />
                    </div>
                </div>

                <div class="row g-3">
                    <div class="col-md-8">
                        <label for="item-barcode-input" class="form-label">
                            {{ $t('cataloging.item_barcode_label') }}
                        </label>
                        <div class="input-group input-group-lg">
                            <span class="input-group-text">
                                <i class="bi bi-upc"></i>
                            </span>
                            <input
                                id="item-barcode-input"
                                ref="barcodeInput"
                                v-model="barcode"
                                type="text"
                                class="form-control"
                                :placeholder="$t('cataloging.item_barcode_placeholder')"
                                :disabled="loading"
                                @keypress="handleKeypress"
                                autofocus
                            />
                        </div>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label">&nbsp;</label>
                        <button
                            type="submit"
                            class="btn btn-success btn-lg w-100"
                            :disabled="loading || !barcode.trim()"
                        >
                            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                            <i v-else class="bi bi-plus-circle me-2"></i>
                            {{ $t('cataloging.add_copy') }}
                        </button>
                    </div>
                </div>

                <!-- Optional fields toggle -->
                <div class="mt-3">
                    <button
                        type="button"
                        class="btn btn-link btn-sm p-0 text-muted"
                        @click="showOptional = !showOptional"
                    >
                        <i :class="showOptional ? 'bi-chevron-up' : 'bi-chevron-down'" class="me-1"></i>
                        {{ $t('cataloging.optional_fields') }}
                    </button>
                </div>

                <div v-if="showOptional" class="row g-3 mt-1">
                    <div class="col-md-4">
                        <label class="form-label">{{ $t('catalog.acquisition_date') }}</label>
                        <input
                            type="date"
                            class="form-control"
                            v-model="acquisitionDate"
                            :disabled="loading"
                        />
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">{{ $t('catalog.funding_source') }}</label>
                        <input
                            type="text"
                            class="form-control"
                            v-model="fundingSource"
                            :placeholder="$t('catalog.placeholder_funding_source')"
                            :disabled="loading"
                        />
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">{{ $t('catalog.condition') }}</label>
                        <select class="form-select" v-model="condition" :disabled="loading">
                            <option value="good">{{ $t('item.condition_good') }}</option>
                            <option value="damaged">{{ $t('item.condition_damaged') }}</option>
                        </select>
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <div class="form-check mb-2">
                            <input
                                type="checkbox"
                                class="form-check-input"
                                id="item-loanable"
                                v-model="loanable"
                                :disabled="loading"
                            />
                            <label class="form-check-label" for="item-loanable">
                                {{ $t('catalog.loanable') }}
                            </label>
                        </div>
                    </div>
                </div>
            </form>

            <!-- Created Items List -->
            <div v-if="createdItems.length > 0" class="mt-4">
                <h6>
                    {{ $t('cataloging.created_items') }} ({{ itemCount }})
                </h6>
                <ul class="list-group">
                    <li
                        v-for="item in createdItems"
                        :key="item.id"
                        class="list-group-item d-flex justify-content-between align-items-center"
                    >
                        <div>
                            <i class="bi bi-box-seam text-success me-2"></i>
                            <strong>{{ item.item_id || item.barcode }}</strong>
                            <span v-if="item.shelf_location" class="ms-2 text-muted small">
                                <i class="bi bi-geo-alt"></i> {{ item.shelf_location }}
                            </span>
                            <span v-if="item.call_number" class="ms-2 text-muted small">
                                {{ /^\\d+$/.test(item.call_number) ? 'n\u00b0 ' + item.call_number : item.call_number }}
                            </span>
                        </div>
                        <span class="badge bg-success">
                            {{ $t('item.status_available') }}
                        </span>
                    </li>
                </ul>
            </div>

            <!-- New Record Button -->
            <div class="mt-4 d-flex justify-content-end">
                <button
                    type="button"
                    class="btn btn-primary"
                    @click="finish"
                >
                    <i class="bi bi-plus-circle me-2"></i>
                    {{ $t('cataloging.catalog_another') }}
                </button>
            </div>
        </div>
    `
});
