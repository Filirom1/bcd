/**
 * Item Barcode Input Component
 * Creates physical items (copies) for a bibliographic record
 */

const { defineComponent, ref, computed, watch, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';
import { useAppState } from '../../composables/useAppState.js';
import DeweyPicker from '../ui/DeweyPicker.js';
import ShelfLocationPicker from '../ui/ShelfLocationPicker.js';
import ItemEditForm from '../catalog/ItemEditForm.js';
import CopiesList from '../catalog/CopiesList.js';
import { computeCallNumber, suggestShelfLocation } from '../../utils/callNumber.js';
import { parseJsonSetting } from '../../utils/domain.js';
import { isPeriodicalRecord } from '../../utils/domain.js';

export default defineComponent({
    name: 'ItemBarcodeInput',

    components: { DeweyPicker, ShelfLocationPicker, ItemEditForm, CopiesList },

    props: {
        recordId: {
            type: Number,
            required: true
        },
        recordTitle: {
            type: String,
            required: true
        },
        recordSubtitle: {
            type: String,
            default: null
        },
        recordMediumType: {
            type: String,
            default: ''
        },
        recordIdentifierType: {
            type: String,
            default: null
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

        const deweyColors = computed(() => parseJsonSetting(settings.value?.dewey_colors, undefined));
        const deweyEnabled = computed(() => settings.value?.dewey_colors_enabled !== false);

        const shelfLocationOptions = computed(() => parseJsonSetting(settings.value?.catalog_shelf_locations, []));

        // State
        const barcode = ref('');
        const barcodeInput = ref(null);
        const callNumber = ref('');
        const callNumberInput = ref(null);
        const shelfLocation = ref('');
        const lastSuggestedShelfLocation = ref('');
        // Keep track of the value last generated automatically so changing the
        // shelf can replace it without overwriting a manually edited call number.
        const lastSuggestedCallNumber = ref('');
        const loading = ref(false);
        const createdItems = ref([]);
        const existingItems = ref([]);
        const loadingExistingItems = ref(false);
        const showOptional = ref(false);
        const acquisitionDate = ref(new Date().toISOString().slice(0, 10));
        const fundingSource = ref('');
        const condition = ref('good');
        const loanable = ref(true);
        const showItemEditModal = ref(false);
        const editingItem = ref(null);

        const isPeriodical = computed(() => isPeriodicalRecord({
            identifier_type: props.recordIdentifierType,
            medium_type: props.recordMediumType
        }));

        // Suggested call number based on dynamic settings rules:
        const suggestedCallNumber = computed(() => {
            const rules = (() => {
                try {
                    return parseJsonSetting(settings.value?.catalog_call_number_rules, []);
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

        // Update call number when the selected shelf changes the suggestion.
        // Comparing with the previous computed value is fragile when several
        // reactive updates are batched; the last value applied by this watcher
        // is the reliable indication that the field is still automatic.
        watch(suggestedCallNumber, (val) => {
            const current = callNumber.value.trim();
            if (val && (!current || current === lastSuggestedCallNumber.value)) {
                callNumber.value = val;
            }
            lastSuggestedCallNumber.value = val || '';
        }, { immediate: true });

        // Pre-fill shelf location only when it is still empty
        watch(suggestedShelfLocation, (val) => {
            if (val && (!shelfLocation.value.trim() || shelfLocation.value === lastSuggestedShelfLocation.value)) {
                shelfLocation.value = val;
            }
            lastSuggestedShelfLocation.value = val || '';
        }, { immediate: true });

        // Keep the scanner workflow keyboard-friendly.  The input is disabled
        // while the request is running, which makes the browser drop focus;
        // autofocus alone cannot restore it after that happens.
        const focusNextInput = () => {
            nextTick(() => {
                if (loading.value) return;
                const input = isPeriodical.value
                    ? callNumberInput.value
                    : barcodeInput.value;
                input?.focus();
            });
        };

        // The model suggestion is asynchronous.  It may replace the static
        // medium-type default, but never overwrites a librarian's edit.
        onMounted(async () => {
            focusNextInput();
            await loadExistingItems();
            try {
                const result = await apiClient.post('/catalog/shelf-suggestion', {
                    title: props.recordTitle,
                    subtitle: props.recordSubtitle,
                    collection: props.recordCollection,
                    authors: props.recordAuthors
                }, {}, { skipGlobalLoading: true });
                const suggested = result?.suggested_shelf?.trim();
                const current = shelfLocation.value.trim();
                if (suggested && (!current || current === lastSuggestedShelfLocation.value)) {
                    shelfLocation.value = suggested;
                    lastSuggestedShelfLocation.value = suggested;
                }
            } catch (error) {
                // A missing/untrained model is an expected fallback case.
                console.debug('Shelf suggestion unavailable:', error);
            }
        });

        /**
         * Load copies already attached to this notice.  This is intentionally
         * kept separate from createdItems: a librarian may edit existing
         * copies here, but deletion remains limited to copies created in the
         * current cataloging session.
         */
        const loadExistingItems = async () => {
            loadingExistingItems.value = true;
            try {
                const result = await apiClient.get(
                    `/catalog/bibliographic/${props.recordId}/items`,
                    {},
                    { skipGlobalLoading: true }
                );
                existingItems.value = Array.isArray(result)
                    ? result
                    : (Array.isArray(result?.items) ? result.items : []);
            } catch (error) {
                // The copy form remains usable when the recap cannot be loaded.
                console.error('Error loading existing copies:', error);
                existingItems.value = [];
            } finally {
                loadingExistingItems.value = false;
            }
        };

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
                    const issue = callNumber.value.trim();
                    if (!issue) {
                        showError(t('periodical.required'));
                        loading.value = false;
                        return;
                    }
                    // The API stores the explicit periodical numbering in the
                    // existing call_number column for schema compatibility.
                    itemData.call_number = issue;
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

            } catch (err) {
                if (err.code === 'duplicate_item_id') {
                    showError(t('cataloging.error_barcode_exists', {
                        barcode: barcodeValue
                    }));
                } else {
                    handleError(err);
                }
            } finally {
                loading.value = false;
                // Restore focus on both success and error so the next scan can
                // be entered immediately without requiring a mouse click.
                focusNextInput();
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

        const editItem = (item) => {
            editingItem.value = item;
            showItemEditModal.value = true;
        };

        const handleItemSaved = (updatedItem) => {
            const itemId = updatedItem.item_id || editingItem.value?.item_id;
            const updateCollection = (collection) => {
                const index = collection.value.findIndex(item => item.item_id === itemId);
                if (index !== -1) {
                    collection.value[index] = { ...collection.value[index], ...updatedItem };
                }
            };
            updateCollection(existingItems);
            updateCollection(createdItems);
            editingItem.value = null;
        };

        const deleteItem = async (item) => {
            const itemId = item.item_id || item.barcode;
            if (!itemId || !confirm(t('admin.confirm_delete_item', { item_id: itemId }))) return;

            try {
                await apiClient.delete(`/catalog/items/${itemId}`);
                createdItems.value = createdItems.value.filter(createdItem => {
                    return (createdItem.item_id || createdItem.barcode) !== itemId;
                });
            } catch (error) {
                console.error('Error deleting item:', error);
                handleError(error);
            }
        };

        const record = computed(() => ({
            id: props.recordId,
            title: props.recordTitle,
            medium_type: props.recordMediumType,
            identifier_type: props.recordIdentifierType,
            dewey_number: props.recordDeweyNumber,
            authors: props.recordAuthors,
            collection: props.recordCollection,
            illustrators: props.recordIllustrators
        }));

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
            existingItems,
            loadingExistingItems,
            itemCount,
            isPeriodical,
            deweyColors,
            deweyEnabled,
            shelfLocationOptions,
            // Expose global settings to CopiesList and ItemEditForm so their
            // shelf-location badges use the configured database colours.
            settings,
            showOptional,
            acquisitionDate,
            fundingSource,
            condition,
            loanable,
            showItemEditModal,
            editingItem,
            createItem,
            handleKeypress,
            finish,
            editItem,
            handleItemSaved,
            deleteItem,
            loadExistingItems,
            record
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

                <!-- Shelf location is used for all media; call number is also used for non-periodicals. -->
                <div class="row g-3 mb-3">
                    <div :class="isPeriodical ? 'col-md-12' : 'col-md-6'">
                        <label class="form-label">{{ $t('catalog.shelf_location') }}</label>
                        <shelf-location-picker
                            v-model="shelfLocation"
                            :locations="shelfLocationOptions"
                            :disabled="loading"
                        />
                    </div>
                    <div v-if="!isPeriodical" class="col-md-6">
                        <label class="form-label">{{ $t('catalog.call_number') }}</label>
                        <dewey-picker
                            v-model="callNumber"
                            :colors="deweyColors"
                            :enabled="deweyEnabled"
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

            <!-- Copies already attached to this notice.  The same reusable
                 list is also used by the record detail page. -->
            <div v-if="loadingExistingItems" class="text-center text-muted mt-4">
                <span class="spinner-border spinner-border-sm me-2"></span>
                {{ $t('common.loading') }}
            </div>
            <div v-else-if="existingItems.length > 0" class="mt-4">
                <h6>
                    {{ $t('cataloging.other_copies') }} ({{ existingItems.length }})
                </h6>
                <p class="small text-muted mb-2">{{ $t('cataloging.other_copies_help') }}</p>
                <copies-list
                    :items="existingItems"
                    :settings="settings"
                    :periodical="isPeriodical"
                    :editable="true"
                    :dense="true"
                    @edit="editItem"
                />
            </div>

            <!-- Copies created during this session -->
            <div v-if="createdItems.length > 0" class="mt-4">
                <h6>
                    {{ $t('cataloging.created_items') }} ({{ itemCount }})
                </h6>
                <copies-list
                    :items="createdItems"
                    :settings="settings"
                    :periodical="isPeriodical"
                    :editable="true"
                    :allow-delete="true"
                    :dense="true"
                    @edit="editItem"
                    @delete="deleteItem"
                />
            </div>

            <item-edit-form
                v-if="editingItem"
                :show="showItemEditModal"
                :item="editingItem"
                :record="record"
                :settings="settings"
                @update:show="showItemEditModal = $event"
                @saved="handleItemSaved"
            />

        </div>
    `
});
