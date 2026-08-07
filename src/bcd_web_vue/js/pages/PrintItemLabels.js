const { defineComponent, ref, computed, watch, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { useBarcodeRenderer } from '../composables/useBarcodeRenderer.js';
import { useAppState } from '../composables/useAppState.js';
import { LABEL_FORMATS, DEFAULT_FORMAT_ID } from '../config/labelFormats.js';
import { apiClient } from '../api/client.js';
import { useDebouncedAction } from '../composables/useDebouncedAction.js';

export default defineComponent({
    name: 'PrintItemLabels',

    setup() {
        const { t } = useI18n();
        const { renderBarcodes } = useBarcodeRenderer();
        const { settings, loadSettings } = useAppState();

        // --- Generation params ---
        const startId = ref('');
        const labelCount = ref(21);
        const generatedIds = ref([]);
        const loading = ref(false);
        const error = ref(null);

        // --- Format state ---
        const selectedFormatId = ref(DEFAULT_FORMAT_ID);
        const advancedOpen = ref(false);

        function deepCopyFormat(fmt) {
            return {
                label: { ...fmt.label },
                layout: { ...fmt.layout },
            };
        }

        const customParams = ref(deepCopyFormat(LABEL_FORMATS.find(f => f.id === DEFAULT_FORMAT_ID)));

        // --- Computed ---
        const totalCount = computed(() => generatedIds.value.length);
        const libraryName = computed(() => settings.value?.library_name || '');
        const barcodePrefix = computed(() => settings.value?.item_barcode_prefix ?? '');

        const labelsPerSheet = computed(() =>
            customParams.value.layout.cols * customParams.value.layout.rows
        );

        // Split generated IDs into per-sheet chunks for page-break rendering
        const labelSheets = computed(() => {
            const perSheet = labelsPerSheet.value;
            const ids = generatedIds.value;
            const sheets = [];
            for (let i = 0; i < ids.length; i += perSheet) {
                sheets.push(ids.slice(i, i + perSheet));
            }
            return sheets;
        });

        const sheetsCount = computed(() => labelSheets.value.length);

        const isModified = computed(() => {
            const preset = LABEL_FORMATS.find(f => f.id === selectedFormatId.value);
            if (!preset) return false;
            return JSON.stringify(customParams.value) !== JSON.stringify(deepCopyFormat(preset));
        });

        // CSS custom properties injected as inline style on each .label-sheet div
        const labelSheetStyle = computed(() => {
            const p = customParams.value;
            return {
                '--label-width':  p.label.width_mm  + 'mm',
                '--label-height': p.label.height_mm + 'mm',
                '--cols':         p.layout.cols,
                '--top-margin':   p.layout.top_margin_mm  + 'mm',
                '--left-margin':  p.layout.left_margin_mm + 'mm',
                '--col-gap':      p.layout.col_gap_mm + 'mm',
                '--row-gap':      p.layout.row_gap_mm + 'mm',
            };
        });

        // JsBarcode bar height scaled to label height (px, clamped 18–72)
        const barcodeHeight = computed(() =>
            Math.max(18, Math.min(72, Math.round(customParams.value.label.height_mm * 1.3)))
        );

        // Display toggles (controllable in advanced settings)
        const showLibraryName = ref(true);
        const showItemId = ref(true);
        const libraryFontSize = ref(6);  // pt
        const idFontSize = ref(7);       // pt
        const contiguous = ref(true);    // contiguous block vs scatter

        // --- Watchers ---

        // When user picks a different preset, reset custom params and fill one sheet by default
        watch(selectedFormatId, (newId) => {
            const preset = LABEL_FORMATS.find(f => f.id === newId);
            if (preset) {
                customParams.value = deepCopyFormat(preset);
                labelCount.value = preset.layout.cols * preset.layout.rows;
            }
        });

        // Auto-regenerate when count or starting ID changes (debounced)
        const regenDelay = ref(400);
        const debouncedRegen = useDebouncedAction(() => { generateIds(); }, regenDelay);

        const scheduleRegen = (delay = 400) => {
            regenDelay.value = delay;
            debouncedRegen();
        };
        watch(labelCount, () => scheduleRegen(400));
        watch(startId, () => scheduleRegen(1200));
        watch(contiguous, () => scheduleRegen(400));

        // Re-render barcodes when computed height changes (label height edited)
        watch(barcodeHeight, async () => {
            if (generatedIds.value.length > 0) {
                await nextTick();
                renderBarcodesCurrentFormat();
            }
        });

        // --- Methods ---

        const renderBarcodesCurrentFormat = () => {
            const format = (settings.value?.barcode_type || 'code39').toUpperCase();
            renderBarcodes({ format, width: 1.5, height: barcodeHeight.value });
        };

        onMounted(async () => {
            await loadSettings();
            generateIds();
        });

        const generateIds = async () => {
            loading.value = true;
            error.value = null;
            try {
                const params = { count: labelCount.value };
                if (startId.value && startId.value.trim() !== '') {
                    params.start_from = startId.value.trim();
                }
                if (!contiguous.value) {
                    params.contiguous = 'false';
                }
                const data = await apiClient.get('/catalog/items/available-ids', params);
                generatedIds.value = data.ids;
                loading.value = false;
                await nextTick();
                renderBarcodesCurrentFormat();
            } catch (err) {
                error.value = err.message;
                loading.value = false;
            }
        };

        const resetToPreset = () => {
            const preset = LABEL_FORMATS.find(f => f.id === selectedFormatId.value);
            if (preset) customParams.value = deepCopyFormat(preset);
        };

        const fillOneSheet = () => {
            labelCount.value = labelsPerSheet.value;
        };

        const printPage = () => window.print();

        // Display helper: "63,5 \u00d7 38,1\u00a0mm"
        const formatDims = (fmt) => {
            const w = fmt.label.width_mm.toFixed(1).replace('.', ',');
            const h = fmt.label.height_mm.toFixed(1).replace('.', ',');
            return w + '\u00a0\u00d7\u00a0' + h + '\u00a0mm';
        };

        return {
            t,
            labelFormats: LABEL_FORMATS,
            startId,
            labelCount,
            generatedIds,
            loading,
            error,
            totalCount,
            libraryName,
            barcodePrefix,
            selectedFormatId,
            customParams,
            advancedOpen,
            labelsPerSheet,
            labelSheets,
            sheetsCount,
            isModified,
            labelSheetStyle,
            showLibraryName,
            showItemId,
            libraryFontSize,
            idFontSize,
            contiguous,
            generateIds,
            resetToPreset,
            fillOneSheet,
            printPage,
            formatDims,
        };
    },

    template: `
        <div class="container-fluid">

            <!-- Print button toolbar (hidden when printing) -->
            <div class="d-flex justify-content-end mb-3 no-print">
                <button
                    class="btn btn-primary"
                    @click="printPage"
                    :disabled="loading || totalCount === 0"
                >
                    <i class="bi bi-printer-fill me-2"></i>
                    {{ t('reports.print') }}
                </button>
            </div>

            <!-- Settings Card (hidden when printing) -->
            <div class="card mb-4 no-print">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-gear me-2"></i>
                        {{ t('print_labels.configuration') }}
                    </h5>
                </div>
                <div class="card-body">

                    <!-- Format selector -->
                    <div class="mb-3">
                        <label class="form-label fw-semibold">
                            {{ t('print_labels.label_format') }}
                        </label>
                        <select class="form-select" v-model="selectedFormatId">
                            <option v-for="fmt in labelFormats" :key="fmt.id" :value="fmt.id">
                                {{ fmt.labelsPerSheet }}
                                {{ t('print_labels.labels_per_sheet_unit') }}
                                \u2014 {{ formatDims(fmt) }}{{ fmt.recommended ? ' \u2605' : '' }}
                            </option>
                        </select>
                    </div>

                    <!-- Advanced settings (collapsible) -->
                    <div class="border rounded mb-3">
                        <div
                            class="d-flex align-items-center justify-content-between p-2 bg-light rounded"
                            style="cursor:pointer"
                            @click="advancedOpen = !advancedOpen"
                        >
                            <span class="small text-muted">
                                <i class="bi bi-sliders me-1"></i>
                                {{ t('print_labels.advanced_settings') }}
                                <span
                                    v-if="isModified"
                                    class="badge bg-warning text-dark ms-2"
                                >{{ t('print_labels.modified') }}</span>
                            </span>
                            <i class="bi" :class="advancedOpen ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                        </div>

                        <div v-show="advancedOpen" class="p-3 border-top">
                            <div class="row g-2">
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.label_width') }}
                                    </label>
                                    <div class="input-group input-group-sm">
                                        <input type="number" class="form-control"
                                            v-model.number="customParams.label.width_mm"
                                            step="0.1" min="10" max="210">
                                        <span class="input-group-text">mm</span>
                                    </div>
                                </div>
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.label_height') }}
                                    </label>
                                    <div class="input-group input-group-sm">
                                        <input type="number" class="form-control"
                                            v-model.number="customParams.label.height_mm"
                                            step="0.1" min="5" max="297">
                                        <span class="input-group-text">mm</span>
                                    </div>
                                </div>
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.columns') }}
                                    </label>
                                    <input type="number" class="form-control form-control-sm"
                                        v-model.number="customParams.layout.cols"
                                        min="1" max="10">
                                </div>
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.rows_count') }}
                                    </label>
                                    <input type="number" class="form-control form-control-sm"
                                        v-model.number="customParams.layout.rows"
                                        min="1" max="30">
                                </div>
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.top_margin') }}
                                    </label>
                                    <div class="input-group input-group-sm">
                                        <input type="number" class="form-control"
                                            v-model.number="customParams.layout.top_margin_mm"
                                            step="0.01" min="0" max="50">
                                        <span class="input-group-text">mm</span>
                                    </div>
                                </div>
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.left_margin') }}
                                    </label>
                                    <div class="input-group input-group-sm">
                                        <input type="number" class="form-control"
                                            v-model.number="customParams.layout.left_margin_mm"
                                            step="0.01" min="0" max="50">
                                        <span class="input-group-text">mm</span>
                                    </div>
                                </div>
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.col_gap') }}
                                    </label>
                                    <div class="input-group input-group-sm">
                                        <input type="number" class="form-control"
                                            v-model.number="customParams.layout.col_gap_mm"
                                            step="0.01" min="0" max="20">
                                        <span class="input-group-text">mm</span>
                                    </div>
                                </div>
                                <div class="col-6 col-md-3">
                                    <label class="form-label form-label-sm">
                                        {{ t('print_labels.row_gap') }}
                                    </label>
                                    <div class="input-group input-group-sm">
                                        <input type="number" class="form-control"
                                            v-model.number="customParams.layout.row_gap_mm"
                                            step="0.01" min="0" max="20">
                                        <span class="input-group-text">mm</span>
                                    </div>
                                </div>
                                <!-- Library name: toggle + font size -->
                                <div class="col-6 col-md-3">
                                    <div class="form-check mb-1">
                                        <input class="form-check-input" type="checkbox"
                                            id="showLibraryName" v-model="showLibraryName">
                                        <label class="form-check-label small" for="showLibraryName">
                                            {{ t('print_labels.show_library_name') }}
                                        </label>
                                    </div>
                                    <div class="input-group input-group-sm" v-if="showLibraryName">
                                        <input type="number" class="form-control"
                                            v-model.number="libraryFontSize"
                                            step="0.5" min="4" max="14"
                                            :title="t('print_labels.font_size')">
                                        <span class="input-group-text">pt</span>
                                    </div>
                                </div>
                                <!-- Item ID: toggle + font size -->
                                <div class="col-6 col-md-3">
                                    <div class="form-check mb-1">
                                        <input class="form-check-input" type="checkbox"
                                            id="showItemId" v-model="showItemId">
                                        <label class="form-check-label small" for="showItemId">
                                            {{ t('print_labels.show_item_id') }}
                                        </label>
                                    </div>
                                    <div class="input-group input-group-sm" v-if="showItemId">
                                        <input type="number" class="form-control"
                                            v-model.number="idFontSize"
                                            step="0.5" min="4" max="14"
                                            :title="t('print_labels.font_size')">
                                        <span class="input-group-text">pt</span>
                                    </div>
                                </div>
                            </div>

                            <div class="d-flex justify-content-between align-items-center mt-3">
                                <span class="text-muted small">
                                    {{ t('print_labels.labels_per_sheet_computed') }}:
                                    <strong>{{ labelsPerSheet }}</strong>
                                </span>
                                <button
                                    v-if="isModified"
                                    class="btn btn-sm btn-outline-secondary"
                                    @click="resetToPreset"
                                >
                                    <i class="bi bi-arrow-counterclockwise me-1"></i>
                                    {{ t('print_labels.reset_to_preset') }}
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- ID generation params -->
                    <div class="row g-3 align-items-end">
                        <div class="col-md-4">
                            <label for="startId" class="form-label">
                                {{ t('print_labels.starting_id') }}
                            </label>
                            <input
                                id="startId"
                                v-model="startId"
                                type="text"
                                class="form-control"
                                :placeholder="t('print_labels.auto_detect_placeholder')"
                                :disabled="loading"
                            />
                        </div>
                        <div class="col-md-4">
                            <label for="labelCount" class="form-label">
                                {{ t('print_labels.number_of_labels') }}
                            </label>
                            <div class="input-group">
                                <input
                                    id="labelCount"
                                    v-model.number="labelCount"
                                    type="number"
                                    class="form-control"
                                    min="1"
                                    max="1000"
                                    :disabled="loading"
                                />
                                <button
                                    class="btn btn-outline-secondary"
                                    type="button"
                                    @click="fillOneSheet"
                                    :title="t('print_labels.fill_one_sheet')"
                                >
                                    <i class="bi bi-journals"></i>
                                </button>
                            </div>
                        </div>
                        <div class="col-md-4 d-flex align-items-end">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox"
                                    id="contiguous" v-model="contiguous">
                                <label class="form-check-label small" for="contiguous">
                                    {{ t('print_labels.contiguous') }}
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Print hint -->
                    <div class="alert alert-light border mt-3 mb-0 small">
                        <i class="bi bi-lightbulb me-2 text-warning"></i>
                        {{ t('print_labels.print_hint') }}
                    </div>

                </div>
            </div>

            <!-- Status Summary (hidden when printing) -->
            <div v-if="!loading && totalCount > 0" class="alert alert-info no-print">
                <i class="bi bi-info-circle me-2"></i>
                <strong>{{ totalCount }} {{ t('print_labels.labels_ready') }}</strong>
                <span class="ms-3">
                    {{ t('print_labels.range') }}: {{ generatedIds[0] }} \u2013 {{ generatedIds[generatedIds.length - 1] }}
                </span>
                <span class="ms-3">
                    {{ t('print_labels.sheets_count', { n: sheetsCount }) }}
                </span>
            </div>

            <!-- Loading State -->
            <div v-if="loading" class="text-center py-5">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">{{ t('common.loading') }}</span>
                </div>
                <p class="mt-3 text-muted">{{ t('print_labels.generating') }}</p>
            </div>

            <!-- Error State -->
            <div v-else-if="error" class="alert alert-danger no-print">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>{{ t('common.error') }}:</strong> {{ error }}
            </div>

            <!-- Empty State -->
            <div v-else-if="totalCount === 0" class="text-center py-5 no-print">
                <i class="bi bi-printer" style="font-size: 4rem; color: #ccc;"></i>
                <h4 class="mt-3">{{ t('print_labels.no_labels') }}</h4>
                <p class="text-muted">{{ t('print_labels.no_labels_message') }}</p>
            </div>

            <!-- Label Sheets (one div per physical page, page-break handled by CSS) -->
            <div v-else>
                <div
                    v-for="(sheetIds, sheetIdx) in labelSheets"
                    :key="sheetIdx"
                    class="label-sheet"
                    :style="labelSheetStyle"
                >
                    <div
                        v-for="id in sheetIds"
                        :key="id"
                        class="item-label"
                    >
                        <div v-if="showLibraryName" class="label-library"
                            :style="{ fontSize: libraryFontSize + 'pt' }">{{ libraryName }}</div>
                        <div class="label-barcode">
                            <svg class="barcode" :data-code="barcodePrefix + id"></svg>
                        </div>
                        <div v-if="showItemId" class="label-id"
                            :style="{ fontSize: idFontSize + 'pt' }">{{ id }}</div>
                    </div>
                </div>
            </div>

        </div>
    `
});
