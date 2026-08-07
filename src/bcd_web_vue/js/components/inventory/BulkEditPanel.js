/**
 * BulkEditPanel Component
 * Bulk editing panel for inventory items and their bibliographic records
 */

const { defineComponent, ref, computed } = Vue;
const { useI18n } = VueI18n;
import { parseCsv, parseJsonSetting } from '../../utils/domain.js';
import FilterSelect from '../ui/FilterSelect.js';
import ShelfLocationPicker from '../ui/ShelfLocationPicker.js';

export default defineComponent({
    name: 'BulkEditPanel',

    components: {
        FilterSelect,
        ShelfLocationPicker
    },

    props: {
        selectedCount: {
            type: Number,
            required: true
        },
        settings: {
            type: Object,
            default: () => ({})
        }
    },

    emits: ['apply', 'delete'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Item fields
        const itemCondition = ref('unchanged');
        const itemStatus = ref('unchanged');
        const loanable = ref('unchanged');
        const shelfLocation = ref('');

        // Record fields
        const level = ref('');
        const targetAudience = ref('unchanged');
        const language = ref('');
        const mediumType = ref('');

        // Parse CSV suggestions from settings

        const shelfLocationOptions = computed(() => {
            return parseJsonSetting(props.settings?.catalog_shelf_locations, []);
        });

        const languageSuggestions = computed(() => parseCsv(props.settings?.catalog_languages));
        const mediumTypeSuggestions = computed(() => parseCsv(props.settings?.catalog_medium_types));
        const levelSuggestions = computed(() => parseCsv(props.settings?.catalog_levels));

        // FilterSelect options
        const conditionOptions = computed(() => [
            { value: 'unchanged', label: `— ${t('inventory.bulk_edit.unchanged')} —` },
            { value: 'good', label: t('item.condition_good') },
            { value: 'damaged', label: t('item.condition_damaged') }
        ]);

        const statusOptions = computed(() => [
            { value: 'unchanged', label: `— ${t('inventory.bulk_edit.unchanged')} —` },
            { value: 'available', label: t('item.status_available') },
            { value: 'in_repair', label: t('item.status_in_repair') },
            { value: 'withdrawn', label: t('item.status_withdrawn') },
            { value: 'lost', label: t('item.status_lost') }
        ]);

        const audienceOptions = computed(() => [
            { value: 'unchanged', label: `— ${t('inventory.bulk_edit.unchanged')} —` },
            { value: 'child', label: t('bibliographic.audience_child') },
            { value: 'youth', label: t('bibliographic.audience_youth') },
            { value: 'adult', label: t('bibliographic.audience_adult') }
        ]);

        const hasChanges = computed(() => {
            return itemCondition.value !== 'unchanged' ||
                   itemStatus.value !== 'unchanged' ||
                   loanable.value !== 'unchanged' ||
                   shelfLocation.value.trim() !== '' ||
                   level.value.trim() !== '' ||
                   targetAudience.value !== 'unchanged' ||
                   language.value.trim() !== '' ||
                   mediumType.value.trim() !== '';
        });

        // Convert field value to payload: '__clear__' -> '' (clear), '' -> skip, else use as-is
        const toPayload = (v) => {
            const trimmed = v.trim();
            if (trimmed === '__clear__') return '';
            if (trimmed === '') return null;  // null = skip
            return trimmed;
        };

        const handleApply = () => {
            if (props.selectedCount === 0) {
                return;
            }

            const payload = {
                item_updates: {},
                record_updates: {}
            };

            // Item updates
            if (itemCondition.value !== 'unchanged') {
                payload.item_updates.condition = itemCondition.value;
            }
            if (itemStatus.value !== 'unchanged') {
                payload.item_updates.status = itemStatus.value;
            }
            if (loanable.value !== 'unchanged') {
                payload.item_updates.loanable = loanable.value === 'yes';
            }
            const shelfVal = toPayload(shelfLocation.value);
            if (shelfVal !== null) payload.item_updates.shelf_location = shelfVal;

            // Record updates
            const levelVal = toPayload(level.value);
            if (levelVal !== null) payload.record_updates.level = levelVal;
            if (targetAudience.value !== 'unchanged') {
                payload.record_updates.target_audience = targetAudience.value;
            }
            const langVal = toPayload(language.value);
            if (langVal !== null) payload.record_updates.language = langVal;
            const mediumVal = toPayload(mediumType.value);
            if (mediumVal !== null) payload.record_updates.medium_type = mediumVal;

            emit('apply', payload);
        };

        const handleDelete = () => {
            if (props.selectedCount === 0) {
                return;
            }
            emit('delete');
        };

        return {
            t,
            itemCondition,
            itemStatus,
            loanable,
            shelfLocation,
            shelfLocationOptions,
            level,
            targetAudience,
            language,
            mediumType,
            levelSuggestions,
            languageSuggestions,
            mediumTypeSuggestions,
            conditionOptions,
            statusOptions,
            audienceOptions,
            hasChanges,
            handleApply,
            handleDelete
        };
    },

    template: `
        <div class="bulk-edit-panel">
            <div class="card-body">
                <h6 class="text-uppercase text-muted small mb-3">
                    {{ t('inventory.bulk_edit.title') }}
                    <span v-if="selectedCount > 0" class="badge bg-secondary ms-2">
                        {{ selectedCount }}
                    </span>
                </h6>

                <!-- Item fields -->
                <div class="mb-3">
                    <label class="form-label small fw-bold">{{ t('inventory.bulk_edit.item_section') }}</label>

                    <div class="mb-2">
                        <filter-select
                            v-model="itemCondition"
                            :options="conditionOptions"
                            :label="t('inventory.bulk_edit.condition')"
                            :show-placeholder="false"
                        />
                    </div>

                    <div class="mb-2">
                        <filter-select
                            v-model="itemStatus"
                            :options="statusOptions"
                            :label="t('inventory.bulk_edit.status')"
                            :show-placeholder="false"
                        />
                    </div>

                    <div class="mb-2">
                        <label class="form-label small">{{ t('inventory.bulk_edit.loanable') }}</label>
                        <div class="btn-group btn-group-sm w-100" role="group">
                            <input type="radio" class="btn-check" id="loanable-unchanged" value="unchanged" v-model="loanable">
                            <label class="btn btn-outline-secondary" for="loanable-unchanged">
                                {{ t('inventory.bulk_edit.unchanged') }}
                            </label>

                            <input type="radio" class="btn-check" id="loanable-yes" value="yes" v-model="loanable">
                            <label class="btn btn-outline-secondary" for="loanable-yes">
                                {{ t('common.yes') }}
                            </label>

                            <input type="radio" class="btn-check" id="loanable-no" value="no" v-model="loanable">
                            <label class="btn btn-outline-secondary" for="loanable-no">
                                {{ t('common.no') }}
                            </label>
                        </div>
                    </div>

                    <div class="mb-2">
                        <label class="form-label small">{{ t('inventory.bulk_edit.location') }}</label>
                        <shelf-location-picker
                            v-model="shelfLocation"
                            :locations="shelfLocationOptions"
                            :placeholder="t('inventory.bulk_edit.location_placeholder')"
                            :extra-options="[{ label: '__clear__', display: t('inventory.bulk_edit.clear_value') }]"
                            input-class="form-control-sm"
                        />
                    </div>
                </div>

                <!-- Record fields -->
                <div class="mb-3">
                    <label class="form-label small fw-bold">{{ t('inventory.bulk_edit.record_section') }}</label>

                    <div class="mb-2">
                        <label class="form-label small">{{ t('bibliographic.level') }}</label>
                        <input
                            type="text"
                            class="form-control form-control-sm"
                            v-model="level"
                            list="bulk-level-suggestions"
                            :placeholder="t('inventory.bulk_edit.unchanged')"
                        />
                        <datalist id="bulk-level-suggestions">
                            <option value="__clear__">{{ t('inventory.bulk_edit.clear_value') }}</option>
                            <option v-for="lv in levelSuggestions" :key="lv" :value="lv">{{ lv }}</option>
                        </datalist>
                    </div>

                    <div class="mb-2">
                        <filter-select
                            v-model="targetAudience"
                            :options="audienceOptions"
                            :label="t('bibliographic.target_audience')"
                            :show-placeholder="false"
                        />
                    </div>

                    <div class="mb-2">
                        <label class="form-label small">{{ t('bibliographic.language') }}</label>
                        <input
                            type="text"
                            class="form-control form-control-sm"
                            v-model="language"
                            list="bulk-language-suggestions"
                            :placeholder="t('inventory.bulk_edit.unchanged')"
                        />
                        <datalist id="bulk-language-suggestions">
                            <option value="__clear__">{{ t('inventory.bulk_edit.clear_value') }}</option>
                            <option v-for="lang in languageSuggestions" :key="lang" :value="lang">{{ lang }}</option>
                        </datalist>
                    </div>

                    <div class="mb-2">
                        <label class="form-label small">{{ t('bibliographic.medium_type') }}</label>
                        <input
                            type="text"
                            class="form-control form-control-sm"
                            v-model="mediumType"
                            list="bulk-medium-type-suggestions"
                            :placeholder="t('inventory.bulk_edit.unchanged')"
                        />
                        <datalist id="bulk-medium-type-suggestions">
                            <option value="__clear__">{{ t('inventory.bulk_edit.clear_value') }}</option>
                            <option v-for="medium in mediumTypeSuggestions" :key="medium" :value="medium">{{ medium }}</option>
                        </datalist>
                    </div>
                </div>

                <!-- Action buttons -->
                <div class="d-grid gap-2">
                    <button
                        class="btn btn-primary btn-sm"
                        @click="handleApply"
                        :disabled="selectedCount === 0"
                    >
                        <i class="bi bi-check-circle me-1"></i>
                        {{ t('inventory.bulk_edit.apply') }}
                        <span v-if="selectedCount > 0">({{ selectedCount }})</span>
                    </button>

                    <button
                        class="btn btn-danger btn-sm"
                        @click="handleDelete"
                        :disabled="selectedCount === 0"
                    >
                        <i class="bi bi-trash me-1"></i>
                        {{ t('inventory.bulk_edit.delete') }}
                        <span v-if="selectedCount > 0">({{ selectedCount }})</span>
                    </button>
                </div>
            </div>
        </div>
    `
});
