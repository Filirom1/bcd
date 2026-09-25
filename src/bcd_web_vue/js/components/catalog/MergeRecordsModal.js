const { defineComponent, ref, computed, watch } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';
import DeweyPicker from '../ui/DeweyPicker.js';
import ShelfLocationPicker from '../ui/ShelfLocationPicker.js';
import { apiClient } from '../../api/client.js';
import { useAppState } from '../../composables/useAppState.js';
import { formatAuthors, parseJsonSetting } from '../../utils/domain.js';
import { computeCallNumber } from '../../utils/callNumber.js';

export default defineComponent({
    name: 'MergeRecordsModal',

    components: { Modal, DeweyPicker, ShelfLocationPicker },

    props: {
        show: {
            type: Boolean,
            default: false
        },
        selectedRecords: {
            type: Array,
            default: () => []
        },
        loading: {
            type: Boolean,
            default: false
        },
        settings: {
            type: Object,
            default: null
        }
    },

    emits: ['close', 'confirm'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { settings: globalSettings } = useAppState();
        const effectiveSettings = computed(() => props.settings || globalSettings.value || {});
        const shelfLocationOptions = computed(() => parseJsonSetting(
            effectiveSettings.value?.catalog_shelf_locations, []
        ));
        const deweyColors = computed(() => parseJsonSetting(
            effectiveSettings.value?.dewey_colors, undefined
        ));
        const deweyEnabled = computed(() => effectiveSettings.value?.dewey_colors_enabled !== false);
        const callNumberRules = computed(() => parseJsonSetting(
            effectiveSettings.value?.catalog_call_number_rules, []
        ));
        const targetId = ref(null);
        const items = ref([]);
        const itemsLoading = ref(false);
        const itemLoadError = ref(null);

        const totalCopies = computed(() => props.selectedRecords.reduce(
            (total, record) => total + (record.total_items || record.total_copies || 0),
            0
        ));

        const targetRecord = computed(() => props.selectedRecords.find(
            record => record.id === targetId.value
        ) || null);

        const sourceRecords = computed(() => props.selectedRecords.filter(
            record => record.id !== targetId.value
        ));

        const chooseDefaultTarget = () => {
            if (props.selectedRecords.length === 0) {
                targetId.value = null;
                return;
            }

            const defaultTarget = [...props.selectedRecords].sort((left, right) => {
                const leftCopies = left.total_items || left.total_copies || 0;
                const rightCopies = right.total_items || right.total_copies || 0;
                return rightCopies - leftCopies || left.id - right.id;
            })[0];
            targetId.value = defaultTarget.id;
        };

        const reset = () => {
            chooseDefaultTarget();
            items.value = [];
            itemLoadError.value = null;
        };

        const loadItems = async () => {
            if (!props.selectedRecords.length) {
                items.value = [];
                return;
            }

            itemsLoading.value = true;
            itemLoadError.value = null;
            try {
                const recordsToMigrate = sourceRecords.value;
                const responses = await Promise.all(recordsToMigrate.map(async record => {
                    const [recordResponse, itemsResponse] = await Promise.all([
                        apiClient.get(`/catalog/bibliographic/${record.id}`),
                        apiClient.get(`/catalog/bibliographic/${record.id}/items`)
                    ]);
                    const fullRecord = recordResponse && !Array.isArray(recordResponse)
                        ? recordResponse
                        : record;
                    return {
                        record: fullRecord,
                        items: Array.isArray(itemsResponse) ? itemsResponse : []
                    };
                }));
                items.value = responses.flatMap(({ record, items: recordItems }) =>
                    recordItems.map(item => ({
                        ...item,
                        record_id: record.id,
                        record_title: record.title,
                        record_data: record,
                        _lastGeneratedCallNumber: item.call_number || null,
                        _callNumberManuallyEdited: false
                    }))
                );
            } catch (error) {
                itemLoadError.value = error.message || t('admin.merge_records_items_load_error');
            } finally {
                itemsLoading.value = false;
            }
        };

        const getCallNumberRecord = (item) => {
            const record = item.record_data || {};
            return {
                title: record.title,
                authors: record.authors,
                collection: record.collection || record.collection_name,
                deweyNumber: record.dewey_number || record.deweyNumber,
                mediumType: record.medium_type || record.mediumType,
                illustrators: record.illustrators
            };
        };

        const handleShelfLocationChange = (item, shelfLocation) => {
            const shelf = shelfLocation === '__clear__' ? '' : (shelfLocation || '');
            item.shelf_location = shelf;
            if (!shelf || item._callNumberManuallyEdited) return;

            const generated = computeCallNumber(
                getCallNumberRecord(item),
                shelf,
                callNumberRules.value
            );
            if (generated) {
                item.call_number = generated;
                item._lastGeneratedCallNumber = generated;
            }
        };

        const handleCallNumberChange = (item, callNumber) => {
            item.call_number = callNumber || '';
            item._callNumberManuallyEdited = item.call_number !== (item._lastGeneratedCallNumber || '');
        };

        const handleClose = () => {
            if (!props.loading) {
                emit('close');
            }
        };

        const handleConfirm = () => {
            if (
                props.loading || itemsLoading.value || itemLoadError.value
                || !targetRecord.value || sourceRecords.value.length === 0
            ) {
                return;
            }

            const payload = {
                targetId: targetRecord.value.id,
                sourceIds: sourceRecords.value.map(record => record.id)
            };
            if (items.value.length) {
                payload.itemUpdates = items.value.map(item => ({
                    itemId: item.id,
                    shelfLocation: item.shelf_location?.trim() || null,
                    callNumber: item.call_number?.trim() || null
                }));
            }
            emit('confirm', payload);
        };

        const recordIdentifier = (record) => record.isbn_value || record.isbn || '';

        watch(() => targetId.value, () => {
            if (props.show) {
                loadItems();
            }
        });

        watch(() => props.show, (show) => {
            if (show) {
                reset();
                loadItems();
            }
        }, { immediate: true });

        watch(() => props.selectedRecords, () => {
            if (props.show) {
                reset();
                loadItems();
            }
        });

        return {
            t,
            formatAuthors,
            targetId,
            targetRecord,
            sourceRecords,
            totalCopies,
            shelfLocationOptions,
            deweyColors,
            deweyEnabled,
            items,
            handleShelfLocationChange,
            handleCallNumberChange,
            itemsLoading,
            itemLoadError,
            recordIdentifier,
            handleClose,
            handleConfirm
        };
    },

    template: `
        <modal
            :show="show"
            :static="true"
            :centered="true"
            :scrollable="true"
            size="lg"
            @close="handleClose"
        >
            <template #header>
                <i class="bi bi-intersect me-2"></i>
                {{ t('admin.merge_records_title', { count: selectedRecords.length }) }}
            </template>

            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle me-2"></i>
                {{ t('admin.merge_records_warning') }}
            </div>

            <div class="card mb-4">
                <div class="card-header">
                    <strong>{{ t('admin.merge_records_keep') }}</strong>
                </div>
                <div class="list-group">
                    <label
                        v-for="record in selectedRecords"
                        :key="record.id"
                        class="list-group-item list-group-item-action d-flex align-items-start"
                        :class="{ active: targetId === record.id }"
                    >
                        <input
                            v-model="targetId"
                            class="form-check-input me-3 mt-1"
                            type="radio"
                            name="merge-target-record"
                            :value="record.id"
                        >
                        <span class="flex-grow-1">
                            <strong>{{ record.title }}</strong>
                            <span class="badge ms-2" :class="targetId === record.id ? 'bg-light text-dark' : 'bg-secondary'">
                                #{{ record.id }}
                            </span>
                            <div class="small" :class="targetId === record.id ? 'text-white-50' : 'text-muted'">
                                <span>{{ record.total_items || record.total_copies || 0 }} {{ t('catalog.copies').toLowerCase() }}</span>
                                <span v-if="recordIdentifier(record)" class="ms-2">{{ recordIdentifier(record) }}</span>
                                <span v-if="record.authors" class="ms-2">{{ formatAuthors(record.authors) }}</span>
                            </div>
                        </span>
                    </label>
                </div>
            </div>

            <div class="card mb-4">
                <div class="card-header">
                    <strong>{{ t('admin.merge_records_sources') }}</strong>
                </div>
                <ul class="list-group list-group-flush" style="max-height: 220px; overflow-y: auto;">
                    <li v-for="record in sourceRecords" :key="record.id" class="list-group-item d-flex justify-content-between align-items-center">
                        <span>
                            <strong>{{ record.title }}</strong>
                            <span class="small text-muted ms-2">#{{ record.id }}</span>
                        </span>
                        <span class="badge bg-secondary">
                            {{ record.total_items || record.total_copies || 0 }}
                        </span>
                    </li>
                </ul>

                <div class="card-body border-top">
                    <p class="small text-muted mb-3">
                        {{ t('admin.merge_records_location_help') }}
                    </p>
                    <div v-if="itemsLoading" class="text-center text-muted py-3">
                        <span class="spinner-border spinner-border-sm me-2"></span>
                        {{ t('common.loading') }}
                    </div>
                    <div v-else-if="itemLoadError" class="alert alert-danger mb-0">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        {{ itemLoadError }}
                    </div>
                    <div v-else-if="items.length === 0" class="text-muted">
                        {{ t('admin.merge_records_no_copies') }}
                    </div>
                    <div v-else class="table-responsive">
                        <table class="table table-sm align-middle mb-0">
                            <thead>
                                <tr>
                                    <th>{{ t('catalog.item_id') }}</th>
                                    <th>{{ t('catalog.shelf_location') }}</th>
                                    <th>{{ t('catalog.call_number') }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="item in items" :key="item.id">
                                    <td>
                                        <code>{{ item.item_id || item.barcode }}</code>
                                        <div class="small text-muted">{{ item.record_title }}</div>
                                    </td>
                                    <td>
                                        <shelf-location-picker
                                            :model-value="item.shelf_location || ''"
                                            :locations="shelfLocationOptions"
                                            input-class="form-control-sm"
                                            :placeholder="t('catalog.shelf_location_placeholder')"
                                            @update:model-value="handleShelfLocationChange(item, $event)"
                                        />
                                    </td>
                                    <td>
                                        <dewey-picker
                                            :model-value="item.call_number || ''"
                                            :colors="deweyColors"
                                            :enabled="deweyEnabled"
                                            input-class="form-control-sm"
                                            :placeholder="t('catalog.call_number')"
                                            @update:model-value="handleCallNumberChange(item, $event)"
                                        />
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="alert alert-info mb-0" v-if="targetRecord">
                <strong>{{ t('admin.merge_records_summary') }}</strong>
                <div class="small mt-1">
                    {{ t('admin.merge_records_result', {
                        target: targetRecord.title,
                        copies: totalCopies,
                        sources: sourceRecords.length
                    }) }}
                </div>
            </div>

            <template #footer>
                <button type="button" class="btn btn-secondary" @click="handleClose" :disabled="loading">
                    {{ t('common.cancel') }}
                </button>
                <button
                    type="button"
                    class="btn btn-warning"
                    @click="handleConfirm"
                    :disabled="loading || itemsLoading || itemLoadError || !targetRecord || sourceRecords.length === 0"
                >
                    <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
                    <i v-else class="bi bi-intersect me-1"></i>
                    {{ loading ? t('common.loading') : t('admin.merge_records_confirm') }}
                </button>
            </template>
        </modal>
    `
});
