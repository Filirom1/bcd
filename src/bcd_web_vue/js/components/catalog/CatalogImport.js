/**
 * CatalogImport Component
 *
 * Modal for importing catalog records from Dublin Core CSV file.
 * Based on mockup: inport-dc.png
 *
 * API Endpoint: POST /api/v1/catalog/import?format=<format>
 * Supported formats listed by GET /api/v1/catalog/importers
 */

import { apiClient } from '../../api/client.js';
import Modal from '../ui/Modal.js';
import { events } from '../../utils/events.js';

export default {
  name: 'CatalogImport',

  components: { Modal },

  template: `
    <modal :show="show" size="lg" @close="handleClose">
      <template #header>
        <i class="bi bi-upload"></i> {{ $t('catalog.import_dc') }}
      </template>
            <!-- Format selector -->
            <div v-if="!importing && !importResult" class="mb-3">
              <label class="form-label fw-bold">
                <i class="bi bi-file-earmark-spreadsheet"></i>
                {{ $t('catalog.import_format') }}
              </label>
              <div v-if="importersLoading" class="text-muted small">
                <span class="spinner-border spinner-border-sm me-1" role="status"></span>
                {{ $t('common.loading') }}
              </div>
              <select
                v-else
                class="form-select"
                v-model="selectedFormat"
              >
                <option
                  v-for="importer in importers"
                  :key="importer.name"
                  :value="importer.name"
                >
                  {{ $t('catalog.format_' + importer.name, importer.name) }}
                  — {{ $t('catalog.format_' + importer.name + '_desc', importer.description) }}
                </option>
              </select>
            </div>

            <!-- Dublin Core Format Documentation -->
            <div v-if="!importing && !importResult && selectedFormat === 'dublin_core'" class="alert alert-info mb-3">
              <h6 class="alert-heading">
                <i class="bi bi-file-earmark-spreadsheet"></i>
                {{ $t('catalog.format_dc_doc_title') }}
              </h6>
              <p class="mb-2">
                <strong>{{ $t('catalog.format_dc_standard_cols') }}</strong>
              </p>
              <p class="mb-2 small">
                <code>dc.title, dc.identifier, dc.creator, dc.subject, dc.description, dc.publisher, dc.contributor, dc.date, dc.type, dc.format, dc.language</code>
              </p>
              <p class="mb-2 small">
                <strong>{{ $t('catalog.format_dc_item_extensions') }}</strong><br>
                <code>item.id, item.callNumber, item.acquisitionDate, item.fundingSource</code>
              </p>
              <div class="mt-3 pt-2 border-top border-info border-opacity-25">
                <a href="/api/v1/catalog/template" class="btn btn-sm btn-info text-white fw-bold" download>
                  <i class="bi bi-download"></i> {{ $t('catalog.download_template') }}
                </a>
              </div>
            </div>

            <!-- File Upload Section -->
            <div v-if="!importing && !importResult" class="mb-4">
              <label for="csv-file-catalog" class="form-label fw-bold">
                {{ $t('common.select_file') }}
              </label>
              <input
                id="csv-file-catalog"
                type="file"
                class="form-control"
                accept=".csv"
                @change="onFileSelected"
                ref="fileInput"
              >
              <div class="form-text">
                <i class="bi bi-info-circle"></i>
                {{ $t('catalog.import_dc_help') }}
              </div>
            </div>

            <!-- Import Progress -->
            <div v-if="importing" class="text-center py-4">
              <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">{{ $t('common.loading') }}</span>
              </div>
              <p class="text-muted">{{ $t('common.importing') }}...</p>
              <p class="small text-muted">{{ $t('cataloging.import_instructions') }}</p>
            </div>

            <!-- Import Results -->
            <div v-if="importResult && !importing" class="mb-3">
              <!-- Success Message -->
              <div class="alert alert-success" v-if="importResult.records_created > 0 || importResult.items_created > 0">
                <h6 class="alert-heading">
                  <i class="bi bi-check-circle"></i>
                  {{ $t('catalog.import_success') }}
                </h6>
                <ul class="mb-0">
                  <li v-if="importResult.records_created">
                    <strong>{{ $t('catalog.records_imported') }}:</strong> {{ importResult.records_created }}
                  </li>
                  <li v-if="importResult.items_created">
                    <strong>{{ $t('catalog.items_imported') }}:</strong> {{ importResult.items_created }}
                  </li>
                  <li v-if="importResult.records_skipped" class="text-muted">
                    <strong>{{ $t('catalog.records_skipped') }}:</strong> {{ importResult.records_skipped }}
                    ({{ $t('borrowers.import.duplicates') }})
                  </li>
                  <li v-if="importResult.items_skipped" class="text-muted">
                    <strong>{{ $t('catalog.items_skipped') }}:</strong> {{ importResult.items_skipped }}
                    ({{ $t('borrowers.import.duplicates') }})
                  </li>
                </ul>
              </div>

              <!-- Info Message - Only Skipped -->
              <div class="alert alert-info" v-if="importResult.records_created === 0 && importResult.items_created === 0 && (importResult.records_skipped > 0 || importResult.items_skipped > 0) && (!importResult.errors || importResult.errors.length === 0)">
                <h6 class="alert-heading">
                  <i class="bi bi-info-circle"></i>
                  {{ $t('catalog.all_records_exist') }}
                </h6>
                <p class="mb-0">
                  {{ $t('catalog.skipped_exist_message', { records: importResult.records_skipped || 0, items: importResult.items_skipped || 0 }) }}
                </p>
              </div>

              <!-- Details Display (warnings/info, not errors) -->
              <div class="alert alert-secondary" v-if="importResult.errors && importResult.errors.length > 0">
                <h6 class="alert-heading d-flex justify-content-between align-items-center">
                  <span>
                    <i class="bi bi-info-circle"></i>
                    {{ $t('borrowers.import.details') }}
                  </span>
                  <small class="text-muted">{{ importResult.errors.length }} {{ $t('borrowers.import.items') }}</small>
                </h6>
                <details>
                  <summary class="text-primary" style="cursor: pointer;">
                    {{ $t('borrowers.import.show_details') }}
                  </summary>
                  <ul class="mb-0 small mt-2" style="max-height: 200px; overflow-y: auto;">
                    <li v-for="(error, index) in importResult.errors" :key="index">
                      {{ error }}
                    </li>
                  </ul>
                </details>
              </div>

              <!-- Summary Stats -->
              <div class="row text-center mb-3">
                <div class="col-3">
                  <div class="card border-success">
                    <div class="card-body">
                      <h3 class="text-success mb-0">{{ importResult.records_created || 0 }}</h3>
                      <small class="text-muted">{{ $t('cataloging.records_created') }}</small>
                    </div>
                  </div>
                </div>
                <div class="col-3">
                  <div class="card border-success">
                    <div class="card-body">
                      <h3 class="text-success mb-0">{{ importResult.items_created || 0 }}</h3>
                      <small class="text-muted">{{ $t('cataloging.items_created') }}</small>
                    </div>
                  </div>
                </div>
                <div class="col-3">
                  <div class="card border-warning">
                    <div class="card-body">
                      <h3 class="text-warning mb-0">{{ (importResult.records_skipped || 0) + (importResult.items_skipped || 0) }}</h3>
                      <small class="text-muted">{{ $t('borrowers.import.skipped') }}</small>
                    </div>
                  </div>
                </div>
                <div class="col-3">
                  <div class="card border-secondary">
                    <div class="card-body">
                      <h3 class="text-secondary mb-0">{{ (importResult.errors && importResult.errors.length) || 0 }}</h3>
                      <small class="text-muted">{{ $t('borrowers.import.details_count') }}</small>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Total Rows Processed -->
              <div v-if="importResult.total_rows" class="text-center text-muted small">
                {{ $t('catalog.total_rows_processed') }}: {{ importResult.total_rows }}
              </div>
            </div>

      <template #footer>
        <button
          v-if="!importing && !importResult"
          type="button"
          class="btn btn-secondary"
          @click="handleClose"
        >
          {{ $t('common.cancel') }}
        </button>

        <button
          v-if="!importing && !importResult"
          type="button"
          class="btn btn-primary"
          :disabled="!selectedFile"
          @click="startImport"
        >
          <i class="bi bi-upload"></i>
          {{ $t('common.import') }}
        </button>

        <button
          v-if="importResult && !importing"
          type="button"
          class="btn btn-primary"
          @click="resetImport"
        >
          <i class="bi bi-arrow-clockwise"></i>
          {{ $t('borrowers.import.import_another') }}
        </button>

        <button
          v-if="importResult && !importing"
          type="button"
          class="btn btn-success"
          @click="onImportComplete"
        >
          <i class="bi bi-check-lg"></i>
          {{ $t('common.close') }}
        </button>
      </template>
    </modal>
  `,

  props: {
    show: {
      type: Boolean,
      default: false
    }
  },

  emits: ['import-complete', 'close'],

  setup(props, { emit }) {
    const { t } = VueI18n.useI18n();
    const selectedFile = Vue.ref(null);
    const importing = Vue.ref(false);
    const importResult = Vue.ref(null);
    const fileInput = Vue.ref(null);
    const importers = Vue.ref([]);
    const importersLoading = Vue.ref(false);
    const selectedFormat = Vue.ref('dublin_core');

    async function loadImporters() {
      importersLoading.value = true;
      try {
        const result = await apiClient.get('/catalog/importers');
        importers.value = result.importers || [];
        // Default to first format (dublin_core)
        if (importers.value.length > 0) {
          selectedFormat.value = importers.value[0].name;
        }
      } catch (error) {
        console.error('Failed to load importers:', error);
        importers.value = [];
      } finally {
        importersLoading.value = false;
      }
    }

    Vue.onMounted(() => {
      loadImporters();
    });

    function onFileSelected(event) {
      const file = event.target.files[0];
      if (file && file.name.endsWith('.csv')) {
        selectedFile.value = file;
      } else {
        selectedFile.value = null;
        alert(t('borrowers.import.invalid_file'));
      }
    }

    async function startImport() {
      if (!selectedFile.value) return;

      importing.value = true;
      importResult.value = null;

      try {
        const formData = new FormData();
        formData.append('file', selectedFile.value);

        // Don't set Content-Type header - browser will set it with boundary
        const response = await apiClient.post(`/catalog/import?format=${encodeURIComponent(selectedFormat.value)}`, formData);

        importResult.value = response;

        // Success notification handled in modal display
      } catch (error) {
        console.error('Import failed:', error);
        importResult.value = {
          records_created: 0,
          items_created: 0,
          records_skipped: 0,
          items_skipped: 0,
          errors: [error.message || t('catalog.import_failed')],
          total_rows: 0
        };
      } finally {
        importing.value = false;
      }
    }

    function resetImport() {
      selectedFile.value = null;
      importResult.value = null;
      importing.value = false;
      if (fileInput.value) {
        fileInput.value.value = '';
      }
    }

    function handleClose() {
      resetImport();
      emit('close');
    }

    function onImportComplete() {
      if (importResult.value && (importResult.value.records_created > 0 || importResult.value.items_created > 0)) {
        events.emit('catalog:refresh');
        emit('import-complete', importResult.value);
      }
      resetImport();
      emit('close');
    }

    return {
      selectedFile,
      importing,
      importResult,
      fileInput,
      importers,
      importersLoading,
      selectedFormat,
      onFileSelected,
      startImport,
      resetImport,
      handleClose,
      onImportComplete
    };
  }
};
