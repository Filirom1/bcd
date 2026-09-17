/**
 * BorrowerImport Component
 *
 * Modal for importing borrowers from CSV file.
 * Based on mockup: borrowers-import.png
 *
 * API Endpoint: POST /api/v1/borrowers/import
 * Expected CSV format: borrower_id, external_id, first_name, last_name, class_name, role, active
 */

import { apiClient } from '../../api/client.js';
import Modal from '../ui/Modal.js';

export default {
  name: 'BorrowerImport',

  components: { Modal },

  template: `
    <modal :show="show" size="lg" @close="handleClose">
      <template #header>
        <i class="bi bi-upload"></i> {{ $t('borrowers.import.title') }}
      </template>
            <!-- Format selector -->
            <div v-if="!importing && !importResult" class="mb-3">
              <label class="form-label fw-bold">
                <i class="bi bi-file-earmark-spreadsheet"></i>
                {{ $t('borrowers.import.format') }}
              </label>
              <div v-if="importersLoading" class="text-muted small">
                <span class="spinner-border spinner-border-sm me-1" role="status"></span>
                {{ $t('common.loading') }}
              </div>
              <select v-else class="form-select" v-model="selectedFormat">
                <option v-for="importer in importers" :key="importer.name" :value="importer.name">
                  {{ $t('borrowers.import.format_' + importer.name, importer.name) }}
                  — {{ $t('borrowers.import.format_' + importer.name + '_desc', importer.description) }}
                </option>
              </select>
            </div>

            <!-- File Upload Section -->
            <div v-if="!importing && !importResult" class="mb-4">
              <label for="csv-file" class="form-label fw-bold">
                {{ $t('borrowers.import.select_file') }}
              </label>
              <input
                id="csv-file"
                type="file"
                class="form-control"
                accept=".csv"
                @change="onFileSelected"
                ref="fileInput"
              >
              <div class="form-text">
                <i class="bi bi-info-circle"></i>
                {{ $t('borrowers.import.format_info') }}
              </div>
            </div>

            <!-- CSV Format Documentation -->
            <div v-if="!importing && !importResult" class="alert alert-info">
              <template v-if="selectedFormat === 'onde'">
                <h6 class="alert-heading">
                  <i class="bi bi-file-earmark-spreadsheet"></i>
                  {{ $t('borrowers.import.format_onde_doc_title') }}
                </h6>
                <p class="mb-2">{{ $t('borrowers.import.format_onde_help') }}</p>
                <code>Nom élève;Nom d'usage élève;Prénom élève;INE;Libellé classe</code>
              </template>
              <template v-else>
                <h6 class="alert-heading">
                  <i class="bi bi-file-earmark-spreadsheet"></i>
                  {{ $t('borrowers.import.csv_format') }}
                </h6>
                <p class="mb-2">
                <strong>{{ $t('borrowers.import.required_columns') }}:</strong>
                <code>first_name, last_name</code><br>
                <small>{{ $t('borrowers.import.optional_columns') }}: <code>borrower_id, external_id, class_name, role, active</code></small>
              </p>
              <p class="mb-0">
                <strong>{{ $t('borrowers.import.example') }}:</strong><br>
                <code>101,Amira,BENALI,CP-A,student,true</code><br>
                <code>305,Samir,BOUTALEB,CE1-B,student,true</code>
              </p>
                <div class="mt-3 pt-2 border-top border-info border-opacity-25">
                  <a href="/api/v1/borrowers/template" class="btn btn-sm btn-info text-white fw-bold" download>
                    <i class="bi bi-download"></i> {{ $t('borrowers.import.download_template') }}
                  </a>
                </div>
              </template>
            </div>

            <!-- Import Progress -->
            <div v-if="importing" class="text-center py-4">
              <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">{{ $t('common.loading') }}</span>
              </div>
              <p class="text-muted">{{ $t('borrowers.import.importing') }}...</p>
            </div>

            <!-- Import Results -->
            <div v-if="importResult && !importing" class="mb-3">
              <!-- Success Message -->
              <div class="alert alert-success" v-if="importResult.successful_rows > 0">
                <h6 class="alert-heading">
                  <i class="bi bi-check-circle"></i>
                  {{ $t('borrowers.import.success') }}
                </h6>
                <p class="mb-2">
                  Successfully imported <strong>{{ importResult.successful_rows }}</strong> of <strong>{{ importResult.total_rows }}</strong> rows.
                  <span v-if="importResult.failed_rows > 0">{{ importResult.failed_rows }} rows failed.</span>
                </p>
                <ul class="mb-0">
                  <li v-if="importResult.borrowers_created > 0">
                    <strong>{{ $t('borrowers.import.created') || 'Created' }}:</strong> {{ importResult.borrowers_created }}
                  </li>
                  <li v-if="importResult.borrowers_updated > 0">
                    <strong>{{ $t('borrowers.updated_count') || 'Updated' }}:</strong> {{ importResult.borrowers_updated }}
                  </li>
                </ul>
              </div>

              <!-- Info Message - All Failed -->
              <div class="alert alert-warning" v-if="importResult.successful_rows === 0 && importResult.failed_rows > 0">
                <h6 class="alert-heading">
                  <i class="bi bi-exclamation-triangle"></i>
                  Import failed
                </h6>
                <p class="mb-0">
                  All <strong>{{ importResult.failed_rows }}</strong> rows failed validation. See errors below.
                </p>
              </div>

              <!-- Error Display -->
              <div class="alert alert-danger" v-if="importResult.errors && importResult.errors.length > 0">
                <h6 class="alert-heading d-flex justify-content-between align-items-center">
                  <span>
                    <i class="bi bi-exclamation-circle"></i>
                    {{ $t('borrowers.import_errors') || 'Import Errors' }}
                  </span>
                  <small class="text-muted">{{ importResult.errors.length }} {{ $t('borrowers.import_rows_failed') || 'rows failed' }}</small>
                </h6>
                <details>
                  <summary class="text-primary" style="cursor: pointer;">
                    {{ $t('borrowers.import.show_details') || 'Show details' }}
                  </summary>
                  <ul class="mb-0 small mt-2" style="max-height: 200px; overflow-y: auto;">
                    <li v-for="(error, index) in importResult.errors" :key="index">
                      <strong>Row {{ error.row_number }}:</strong> {{ error.error }}
                    </li>
                  </ul>
                </details>
              </div>

              <!-- Summary Stats -->
              <div class="row text-center mb-3">
                <div class="col-4">
                  <div class="card border-success">
                    <div class="card-body">
                      <h3 class="text-success mb-0">{{ importResult.borrowers_created || 0 }}</h3>
                      <small class="text-muted">{{ $t('borrowers.import.created') || 'Created' }}</small>
                    </div>
                  </div>
                </div>
                <div class="col-4">
                  <div class="card border-info">
                    <div class="card-body">
                      <h3 class="text-info mb-0">{{ importResult.borrowers_updated || 0 }}</h3>
                      <small class="text-muted">{{ $t('borrowers.updated_count') || 'Updated' }}</small>
                    </div>
                  </div>
                </div>
                <div class="col-4">
                  <div class="card border-danger">
                    <div class="card-body">
                      <h3 class="text-danger mb-0">{{ importResult.failed_rows || 0 }}</h3>
                      <small class="text-muted">{{ $t('borrowers.import_rows_failed') || 'Failed' }}</small>
                    </div>
                  </div>
                </div>
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
          {{ $t('borrowers.import.import_button') }}
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
    const importers = Vue.ref([]);
    const importersLoading = Vue.ref(false);
    const selectedFormat = Vue.ref('bcd');
    const importing = Vue.ref(false);
    const importResult = Vue.ref(null);
    const fileInput = Vue.ref(null);

    async function loadImporters() {
      importersLoading.value = true;
      try {
        const response = await apiClient.get('/borrowers/importers');
        importers.value = response.importers || [];
        if (importers.value.length && !importers.value.some(item => item.name === selectedFormat.value)) {
          selectedFormat.value = importers.value[0].name;
        }
      } catch (error) {
        console.error('Failed to load borrower importers:', error);
        importers.value = [{ name: 'bcd', description: 'BCD CSV' }];
      } finally {
        importersLoading.value = false;
      }
    }

    Vue.onMounted(loadImporters);

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
        const response = await apiClient.post(`/borrowers/import?format=${encodeURIComponent(selectedFormat.value)}`, formData);

        importResult.value = response;

        // The API returns successful_rows, not imported/skipped counters.
        // The result panel is the notification summary for this modal.
      } catch (error) {
        console.error('Import failed:', error);
        importResult.value = {
          total_rows: 0,
          successful_rows: 0,
          failed_rows: 1,
          borrowers_created: 0,
          borrowers_updated: 0,
          errors: [{ row_number: 0, error: error.message || t('borrowers.import.import_failed') }]
        };
      } finally {
        importing.value = false;
      }
    }

    function resetImport() {
      selectedFile.value = null;
      importResult.value = null;
      selectedFormat.value = 'bcd';
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
      if (importResult.value && importResult.value.successful_rows > 0) {
        emit('import-complete', importResult.value);
      }
      resetImport();
      emit('close');
    }

    return {
      selectedFile,
      importers,
      importersLoading,
      selectedFormat,
      importing,
      importResult,
      fileInput,
      onFileSelected,
      startImport,
      resetImport,
      handleClose,
      onImportComplete
    };
  }
};
