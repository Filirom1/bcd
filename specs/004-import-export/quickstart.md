# Quick Start Guide: Import/Export Implementation

**Feature**: Library Data Import/Export with Standards Compatibility
**Date**: 2026-02-06
**For**: Developers implementing the Vue 3 UI and FastAPI backend

## Overview

This guide provides code examples and implementation patterns for the import/export feature. It follows the existing BCD architecture:

- **Backend**: FastAPI services + SQLAlchemy models
- **Frontend**: Vue 3 via CDN (no build tools)
- **i18n**: Database-driven localization for medium types, JSON files for UI strings
- **Testing**: Service-layer integration tests with pytest

## Table of Contents

1. [Vue 3 Component Examples](#vue-3-component-examples)
2. [API Service Integration](#api-service-integration)
3. [Database Model Examples](#database-model-examples)
4. [Testing Patterns](#testing-patterns)
5. [Deployment Checklist](#deployment-checklist)

---

## Vue 3 Component Examples

### 1. Export Dialog Component

**File**: `src/bcd_web_vue/js/components/catalog/CatalogExport.js`

```javascript
// CatalogExport.js - Export catalog to CSV
const { ref, reactive, computed } = Vue;

export default {
  name: 'CatalogExport',
  props: {
    visible: Boolean,
  },
  emits: ['close', 'export-complete'],
  setup(props, { emit }) {
    const loading = ref(false);
    const exportFormat = ref('standard');
    const filters = reactive({
      mediumTypes: [],
      deweyRange: { min: '', max: '' },
      availableOnly: false,
    });

    const availableMediumTypes = ref([
      { code: 'book', display: 'Livre' },
      { code: 'cd', display: 'CD' },
      { code: 'dvd', display: 'DVD' },
      { code: 'periodical', display: 'Périodique' },
    ]);

    const formatOptions = [
      { value: 'standard', label: 'Standard (BCD)' },
      { value: 'bcdi', label: 'BCDI (French)' },
      { value: 'dublin_core', label: 'Dublin Core (International)' },
    ];

    const exportButtonText = computed(() => {
      return loading.value ? 'Export en cours...' : 'Télécharger CSV';
    });

    const handleExport = async () => {
      loading.value = true;
      try {
        const response = await fetch('/api/v1/export/catalog', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            format: exportFormat.value,
            filters: {
              medium_types: filters.mediumTypes,
              dewey_range: filters.deweyRange.min
                ? { min: filters.deweyRange.min, max: filters.deweyRange.max }
                : null,
              available_only: filters.availableOnly,
            },
          }),
        });

        if (!response.ok) {
          throw new Error('Export failed');
        }

        // Trigger file download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `catalog_export_${exportFormat.value}_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        emit('export-complete');
        emit('close');
      } catch (error) {
        console.error('Export error:', error);
        alert('Erreur lors de l\'export. Veuillez réessayer.');
      } finally {
        loading.value = false;
      }
    };

    return {
      loading,
      exportFormat,
      filters,
      availableMediumTypes,
      formatOptions,
      exportButtonText,
      handleExport,
    };
  },
  template: `
    <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Exporter le catalogue</h2>
          <button @click="$emit('close')" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <!-- Format Selection -->
          <div class="form-group">
            <label>Format d'export</label>
            <select v-model="exportFormat" class="form-control">
              <option v-for="opt in formatOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <!-- Medium Type Filter -->
          <div class="form-group">
            <label>Types de support (optionnel)</label>
            <div class="checkbox-group">
              <label v-for="type in availableMediumTypes" :key="type.code">
                <input
                  type="checkbox"
                  :value="type.code"
                  v-model="filters.mediumTypes"
                />
                {{ type.display }}
              </label>
            </div>
          </div>

          <!-- Dewey Decimal Range Filter -->
          <div class="form-group">
            <label>Plage Dewey (optionnel)</label>
            <div class="range-inputs">
              <input
                v-model="filters.deweyRange.min"
                type="text"
                placeholder="Min (ex: 500)"
                class="form-control"
                pattern="\\d{3}(\\.\\d+)?"
              />
              <span>à</span>
              <input
                v-model="filters.deweyRange.max"
                type="text"
                placeholder="Max (ex: 599)"
                class="form-control"
                pattern="\\d{3}(\\.\\d+)?"
              />
            </div>
          </div>

          <!-- Available Only Filter -->
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="filters.availableOnly" />
              Uniquement les documents disponibles
            </label>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="$emit('close')" class="btn btn-secondary" :disabled="loading">
            Annuler
          </button>
          <button @click="handleExport" class="btn btn-primary" :disabled="loading">
            {{ exportButtonText }}
          </button>
        </div>
      </div>
    </div>
  `,
};
```

**Usage in CatalogPage.js**:

```javascript
import CatalogExport from './components/catalog/CatalogExport.js';

export default {
  components: { CatalogExport },
  setup() {
    const showExportDialog = ref(false);

    return {
      showExportDialog,
    };
  },
  template: `
    <div class="catalog-page">
      <div class="page-header">
        <h1>Catalogue</h1>
        <button @click="showExportDialog = true" class="btn btn-primary">
          Exporter
        </button>
      </div>

      <catalog-export
        :visible="showExportDialog"
        @close="showExportDialog = false"
        @export-complete="handleExportComplete"
      />
    </div>
  `,
};
```

---

### 2. Import Wizard Component (Multi-Step)

**File**: `src/bcd_web_vue/js/components/catalog/CatalogImport.js`

```javascript
// CatalogImport.js - Multi-step import wizard
const { ref, reactive, computed } = Vue;

export default {
  name: 'CatalogImport',
  props: {
    visible: Boolean,
  },
  emits: ['close', 'import-complete'],
  setup(props, { emit }) {
    const currentStep = ref(1); // 1: Upload, 2: Map, 3: Preview, 4: Confirm
    const uploadId = ref(null);
    const file = ref(null);
    const loading = ref(false);

    const uploadData = reactive({
      rowCount: 0,
      detectedFormat: '',
      detectedEncoding: '',
      columnMappings: [],
      mediumTypeNormalizations: [],
      previewRows: [],
      validationSummary: null,
    });

    const stepTitles = {
      1: 'Étape 1: Téléverser le fichier CSV',
      2: 'Étape 2: Vérifier les correspondances',
      3: 'Étape 3: Prévisualiser l\'import',
      4: 'Étape 4: Confirmer l\'import',
    };

    const canProceed = computed(() => {
      if (currentStep.value === 1) return file.value !== null;
      if (currentStep.value === 2) {
        return uploadData.columnMappings.every((m) => m.bcd_field !== null);
      }
      if (currentStep.value === 3) {
        return uploadData.validationSummary?.error_rows === 0;
      }
      return true;
    });

    // Step 1: Upload file
    const handleFileSelect = (event) => {
      file.value = event.target.files[0];
    };

    const handleUpload = async () => {
      loading.value = true;
      try {
        const formData = new FormData();
        formData.append('file', file.value);

        const response = await fetch('/api/v1/import/catalog/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message || 'Upload failed');
        }

        const data = await response.json();
        uploadId.value = data.upload_id;
        Object.assign(uploadData, data);

        currentStep.value = 2;
      } catch (error) {
        console.error('Upload error:', error);
        alert(`Erreur: ${error.message}`);
      } finally {
        loading.value = false;
      }
    };

    // Step 2: Review mappings
    const handleMappingChange = (index, bcdField) => {
      uploadData.columnMappings[index].bcd_field = bcdField;
      uploadData.columnMappings[index].match_method = 'manual';
      uploadData.columnMappings[index].confidence = 1.0;
    };

    const handleNextToPreview = async () => {
      loading.value = true;
      try {
        const response = await fetch('/api/v1/import/catalog/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            upload_id: uploadId.value,
            column_mappings: uploadData.columnMappings.map((m) => ({
              csv_column: m.csv_column,
              bcd_field: m.bcd_field,
            })),
          }),
        });

        if (!response.ok) {
          throw new Error('Preview generation failed');
        }

        const data = await response.json();
        Object.assign(uploadData, data);

        currentStep.value = 3;
      } catch (error) {
        console.error('Preview error:', error);
        alert('Erreur lors de la génération de la prévisualisation');
      } finally {
        loading.value = false;
      }
    };

    // Step 3: Preview validation results
    const handleConfirmImport = async () => {
      loading.value = true;
      try {
        const response = await fetch('/api/v1/import/catalog/confirm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            upload_id: uploadId.value,
            skip_errors: true,
          }),
        });

        if (!response.ok) {
          throw new Error('Import failed');
        }

        const result = await response.json();
        alert(
          `Import réussi!\\n${result.imported_count} lignes importées\\n${result.skipped_count} lignes ignorées`
        );

        emit('import-complete', result);
        emit('close');
        resetWizard();
      } catch (error) {
        console.error('Import error:', error);
        alert('Erreur lors de l\'import');
      } finally {
        loading.value = false;
      }
    };

    const resetWizard = () => {
      currentStep.value = 1;
      uploadId.value = null;
      file.value = null;
      Object.assign(uploadData, {
        rowCount: 0,
        detectedFormat: '',
        columnMappings: [],
        mediumTypeNormalizations: [],
        previewRows: [],
        validationSummary: null,
      });
    };

    return {
      currentStep,
      loading,
      file,
      uploadData,
      stepTitles,
      canProceed,
      handleFileSelect,
      handleUpload,
      handleMappingChange,
      handleNextToPreview,
      handleConfirmImport,
      resetWizard,
    };
  },
  template: `
    <div v-if="visible" class="modal-overlay modal-large" @click.self="$emit('close')">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ stepTitles[currentStep] }}</h2>
          <button @click="$emit('close')" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <!-- Step 1: Upload -->
          <div v-if="currentStep === 1" class="upload-step">
            <p>Sélectionnez un fichier CSV à importer (formats acceptés: Standard BCD, BCDI, Dublin Core)</p>
            <input
              type="file"
              accept=".csv"
              @change="handleFileSelect"
              class="form-control"
            />
            <p v-if="file" class="file-info">
              Fichier sélectionné: <strong>{{ file.name }}</strong> ({{ (file.size / 1024).toFixed(1) }} KB)
            </p>
          </div>

          <!-- Step 2: Map Columns -->
          <div v-if="currentStep === 2" class="mapping-step">
            <div class="format-detection">
              <p>
                <strong>Format détecté:</strong> {{ uploadData.detectedFormat }}
                <strong>Encodage:</strong> {{ uploadData.detectedEncoding }}
                <strong>Lignes:</strong> {{ uploadData.rowCount }}
              </p>
            </div>

            <table class="mapping-table">
              <thead>
                <tr>
                  <th>Colonne CSV</th>
                  <th>Champ BCD</th>
                  <th>Confiance</th>
                  <th>Méthode</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(mapping, index) in uploadData.columnMappings" :key="index">
                  <td>{{ mapping.csv_column }}</td>
                  <td>
                    <select
                      :value="mapping.bcd_field"
                      @change="handleMappingChange(index, $event.target.value)"
                      class="form-control"
                    >
                      <option value="">-- Ignorer --</option>
                      <option value="isbn">ISBN</option>
                      <option value="title">Titre</option>
                      <option value="author">Auteur</option>
                      <option value="publisher">Éditeur</option>
                      <option value="medium_type">Type de support</option>
                      <option value="dewey_decimal">Cote Dewey</option>
                    </select>
                  </td>
                  <td>
                    <span :class="{ 'low-confidence': mapping.confidence < 0.8 }">
                      {{ (mapping.confidence * 100).toFixed(0) }}%
                    </span>
                  </td>
                  <td>{{ mapping.match_method }}</td>
                </tr>
              </tbody>
            </table>

            <!-- Medium Type Normalizations -->
            <div v-if="uploadData.mediumTypeNormalizations.length > 0" class="mt-4">
              <h3>Types de support détectés</h3>
              <table class="normalization-table">
                <thead>
                  <tr>
                    <th>Valeur CSV</th>
                    <th>Code BCD</th>
                    <th>Affichage FR</th>
                    <th>Confiance</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(norm, index) in uploadData.mediumTypeNormalizations" :key="index">
                    <td>{{ norm.original_value }}</td>
                    <td>{{ norm.normalized_code }}</td>
                    <td>{{ norm.normalized_display.fr }}</td>
                    <td>{{ (norm.confidence * 100).toFixed(0) }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Step 3: Preview -->
          <div v-if="currentStep === 3" class="preview-step">
            <div class="validation-summary">
              <h3>Résumé de validation</h3>
              <p>
                <span class="badge badge-success">{{ uploadData.validationSummary.valid_rows }} valides</span>
                <span class="badge badge-warning">{{ uploadData.validationSummary.warning_rows }} avertissements</span>
                <span class="badge badge-danger">{{ uploadData.validationSummary.error_rows }} erreurs</span>
              </p>
            </div>

            <!-- Preview Table -->
            <table class="preview-table">
              <thead>
                <tr>
                  <th v-for="(value, key) in uploadData.previewRows[0]" :key="key">
                    {{ key }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in uploadData.previewRows" :key="index">
                  <td v-for="(value, key) in row" :key="key">{{ value }}</td>
                </tr>
              </tbody>
            </table>

            <!-- Validation Errors -->
            <div v-if="uploadData.validationSummary.errors.length > 0" class="errors-list">
              <h4>Erreurs de validation</h4>
              <ul>
                <li v-for="(error, index) in uploadData.validationSummary.errors.slice(0, 10)" :key="index">
                  Ligne {{ error.row_number }}, champ "{{ error.field }}": {{ error.message }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button
            v-if="currentStep > 1"
            @click="currentStep--"
            class="btn btn-secondary"
            :disabled="loading"
          >
            Précédent
          </button>
          <button @click="$emit('close')" class="btn btn-secondary" :disabled="loading">
            Annuler
          </button>

          <button
            v-if="currentStep === 1"
            @click="handleUpload"
            class="btn btn-primary"
            :disabled="!canProceed || loading"
          >
            Téléverser
          </button>
          <button
            v-if="currentStep === 2"
            @click="handleNextToPreview"
            class="btn btn-primary"
            :disabled="!canProceed || loading"
          >
            Prévisualiser
          </button>
          <button
            v-if="currentStep === 3"
            @click="handleConfirmImport"
            class="btn btn-primary"
            :disabled="!canProceed || loading"
          >
            Confirmer l'import
          </button>
        </div>
      </div>
    </div>
  `,
};
```

---

### 3. Admin Medium Types Management

**File**: `src/bcd_web_vue/js/components/settings/MediumTypesTab.js`

```javascript
// MediumTypesTab.js - Admin UI for managing medium types
const { ref, onMounted } = Vue;

export default {
  name: 'MediumTypesTab',
  setup() {
    const mediumTypes = ref([]);
    const loading = ref(false);
    const editingType = ref(null);
    const showCreateDialog = ref(false);

    const newType = ref({
      code: '',
      display_names: {
        en: '',
        fr: '',
        it: '',  // Optional: can add more languages as needed
      },
    });

    // Fetch medium types on mount
    onMounted(async () => {
      await fetchMediumTypes();
    });

    const fetchMediumTypes = async () => {
      loading.value = true;
      try {
        const response = await fetch('/api/v1/admin/medium-types?include_usage_count=true');
        if (!response.ok) throw new Error('Failed to fetch medium types');
        mediumTypes.value = await response.json();
      } catch (error) {
        console.error('Fetch error:', error);
        alert('Erreur lors du chargement des types de support');
      } finally {
        loading.value = false;
      }
    };

    const handleCreate = async () => {
      loading.value = true;
      try {
        const response = await fetch('/api/v1/admin/medium-types', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newType.value),
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message || 'Create failed');
        }

        await fetchMediumTypes();
        showCreateDialog.value = false;
        newType.value = { code: '', display_names: { en: '', fr: '', it: '' } };
      } catch (error) {
        console.error('Create error:', error);
        alert(`Erreur: ${error.message}`);
      } finally {
        loading.value = false;
      }
    };

    const handleEdit = (type) => {
      editingType.value = { ...type };
    };

    const handleSaveEdit = async () => {
      loading.value = true;
      try {
        const response = await fetch(`/api/v1/admin/medium-types/${editingType.value.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            display_names: editingType.value.display_names,
          }),
        });

        if (!response.ok) throw new Error('Update failed');

        await fetchMediumTypes();
        editingType.value = null;
      } catch (error) {
        console.error('Update error:', error);
        alert('Erreur lors de la mise à jour');
      } finally {
        loading.value = false;
      }
    };

    const handleDeactivate = async (id) => {
      if (!confirm('Désactiver ce type de support?')) return;

      loading.value = true;
      try {
        const response = await fetch(`/api/v1/admin/medium-types/${id}/deactivate`, {
          method: 'POST',
        });

        if (!response.ok) throw new Error('Deactivate failed');
        await fetchMediumTypes();
      } catch (error) {
        console.error('Deactivate error:', error);
        alert('Erreur lors de la désactivation');
      } finally {
        loading.value = false;
      }
    };

    const handleDelete = async (id, usageCount) => {
      if (usageCount > 0) {
        alert(`Impossible de supprimer: ${usageCount} documents utilisent ce type`);
        return;
      }

      if (!confirm('Supprimer définitivement ce type de support?')) return;

      loading.value = true;
      try {
        const response = await fetch(`/api/v1/admin/medium-types/${id}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message || 'Delete failed');
        }

        await fetchMediumTypes();
      } catch (error) {
        console.error('Delete error:', error);
        alert(`Erreur: ${error.message}`);
      } finally {
        loading.value = false;
      }
    };

    return {
      mediumTypes,
      loading,
      editingType,
      showCreateDialog,
      newType,
      handleCreate,
      handleEdit,
      handleSaveEdit,
      handleDeactivate,
      handleDelete,
    };
  },
  template: `
    <div class="medium-types-tab">
      <div class="tab-header">
        <h2>Types de support</h2>
        <button @click="showCreateDialog = true" class="btn btn-primary">
          Ajouter un type
        </button>
      </div>

      <table class="admin-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Noms (multilangue)</th>
            <th>État</th>
            <th>Utilisation</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="type in mediumTypes" :key="type.id">
            <td>
              <code>{{ type.code }}</code>
              <span v-if="type.is_system_default" class="badge badge-info">Défaut</span>
            </td>
            <td>
              <div v-if="editingType && editingType.id === type.id">
                <div style="margin-bottom: 8px;">
                  <label style="font-size: 12px; color: #666;">EN:</label>
                  <input v-model="editingType.display_names.en" class="form-control" />
                </div>
                <div style="margin-bottom: 8px;">
                  <label style="font-size: 12px; color: #666;">FR:</label>
                  <input v-model="editingType.display_names.fr" class="form-control" />
                </div>
                <div style="margin-bottom: 8px;">
                  <label style="font-size: 12px; color: #666;">IT:</label>
                  <input v-model="editingType.display_names.it" class="form-control" placeholder="Optional" />
                </div>
              </div>
              <div v-else style="font-size: 14px;">
                <div><strong>EN:</strong> {{ type.display_names.en }}</div>
                <div><strong>FR:</strong> {{ type.display_names.fr }}</div>
                <div v-if="type.display_names.it"><strong>IT:</strong> {{ type.display_names.it }}</div>
                <div v-if="type.display_names.es"><strong>ES:</strong> {{ type.display_names.es }}</div>
                <div v-if="type.display_names.de"><strong>DE:</strong> {{ type.display_names.de }}</div>
              </div>
            </td>
            <td>
              <span :class="type.active ? 'badge badge-success' : 'badge badge-secondary'">
                {{ type.active ? 'Actif' : 'Inactif' }}
              </span>
            </td>
            <td>{{ type.usage_count || 0 }} documents</td>
            <td>
              <button
                v-if="editingType && editingType.id === type.id"
                @click="handleSaveEdit"
                class="btn btn-sm btn-success"
                :disabled="loading"
              >
                Enregistrer
              </button>
              <button
                v-else
                @click="handleEdit(type)"
                class="btn btn-sm btn-secondary"
              >
                Modifier
              </button>

              <button
                v-if="type.active"
                @click="handleDeactivate(type.id)"
                class="btn btn-sm btn-warning"
                :disabled="loading"
              >
                Désactiver
              </button>

              <button
                v-if="!type.is_system_default"
                @click="handleDelete(type.id, type.usage_count)"
                class="btn btn-sm btn-danger"
                :disabled="loading || type.usage_count > 0"
              >
                Supprimer
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Create Dialog -->
      <div v-if="showCreateDialog" class="modal-overlay" @click.self="showCreateDialog = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Ajouter un type de support</h3>
            <button @click="showCreateDialog = false" class="close-btn">&times;</button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label>Code (minuscules, chiffres, underscores)</label>
              <input v-model="newType.code" class="form-control" placeholder="ex: educational_kit" />
            </div>

            <div class="form-group">
              <label>Nom anglais (requis)</label>
              <input v-model="newType.display_names.en" class="form-control" placeholder="ex: Educational Kit" />
            </div>

            <div class="form-group">
              <label>Nom français (requis)</label>
              <input v-model="newType.display_names.fr" class="form-control" placeholder="ex: Mallette pédagogique" />
            </div>

            <div class="form-group">
              <label>Nom italien (optionnel)</label>
              <input v-model="newType.display_names.it" class="form-control" placeholder="ex: Kit educativo" />
            </div>
          </div>

          <div class="modal-footer">
            <button @click="showCreateDialog = false" class="btn btn-secondary">Annuler</button>
            <button @click="handleCreate" class="btn btn-primary" :disabled="loading">Créer</button>
          </div>
        </div>
      </div>
    </div>
  `,
};
```

---

## API Service Integration

### Export Service (Backend)

**File**: `src/bcd_api/services/export_service.py`

```python
"""Export service for generating CSV files from borrowers and catalog."""
import csv
from io import StringIO
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.borrower import Borrower
from src.bcd_api.models.medium_type import MediumType
from src.bcd_api.schemas.import_export import ExportFormat


class ExportService:
    """Service for exporting library data to CSV."""

    def __init__(self, db: Session):
        self.db = db

    def export_catalog(
        self,
        format: ExportFormat = ExportFormat.STANDARD,
        medium_types: Optional[List[str]] = None,
        dewey_range: Optional[Dict[str, str]] = None,
        available_only: bool = False,
    ) -> str:
        """
        Export catalog to CSV string.

        Args:
            format: Export format (standard, bcdi, dublin_core)
            medium_types: Filter by medium type codes
            dewey_range: Filter by Dewey decimal range (min, max)
            available_only: Only export available items

        Returns:
            CSV string with UTF-8 encoding
        """
        # Build query
        query = self.db.query(BibliographicRecord).join(MediumType)

        if medium_types:
            query = query.filter(MediumType.code.in_(medium_types))

        if dewey_range:
            query = query.filter(
                BibliographicRecord.dewey_decimal >= dewey_range.get("min", "000"),
                BibliographicRecord.dewey_decimal <= dewey_range.get("max", "999"),
            )

        if available_only:
            query = query.filter(BibliographicRecord.status == "available")

        records = query.all()

        # Generate CSV based on format
        if format == ExportFormat.BCDI:
            return self._generate_bcdi_catalog(records)
        elif format == ExportFormat.DUBLIN_CORE:
            return self._generate_dublin_core_catalog(records)
        else:
            return self._generate_standard_catalog(records)

    def _generate_standard_catalog(self, records: List[BibliographicRecord]) -> str:
        """Generate standard BCD CSV format."""
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["isbn", "title", "author", "publisher", "medium_type", "dewey_decimal"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        for record in records:
            writer.writerow({
                "isbn": record.isbn or "",
                "title": record.title,
                "author": record.author or "",
                "publisher": record.publisher or "",
                "medium_type": record.medium_type.code,  # Generic English code
                "dewey_decimal": record.dewey_decimal or "",
            })

        return output.getvalue()

    def _generate_bcdi_catalog(self, records: List[BibliographicRecord]) -> str:
        """Generate BCDI-compatible CSV format (French field names)."""
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["ISBN", "Titre", "Auteur", "Editeur", "Support", "Cote"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        for record in records:
            writer.writerow({
                "ISBN": record.isbn or "",
                "Titre": record.title,
                "Auteur": record.author or "",
                "Editeur": record.publisher or "",
                "Support": record.medium_type.display_name_fr,  # French display name
                "Cote": record.dewey_decimal or "",
            })

        return output.getvalue()

    def _generate_dublin_core_catalog(self, records: List[BibliographicRecord]) -> str:
        """Generate Dublin Core CSV format."""
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["dc.identifier", "dc.title", "dc.creator", "dc.publisher", "dc.type", "dc.subject"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()

        # Medium type to Dublin Core type mapping
        dc_type_mapping = {
            "book": "Text",
            "periodical": "Text",
            "audiobook": "Sound",
            "cd": "Sound",
            "dvd": "MovingImage",
            "vhs": "MovingImage",
        }

        for record in records:
            writer.writerow({
                "dc.identifier": f"isbn:{record.isbn}" if record.isbn else "",
                "dc.title": record.title,
                "dc.creator": record.author or "",
                "dc.publisher": record.publisher or "",
                "dc.type": dc_type_mapping.get(record.medium_type.code, "PhysicalObject"),
                "dc.subject": record.dewey_decimal or "",
            })

        return output.getvalue()

    def export_borrowers(
        self,
        format: ExportFormat = ExportFormat.STANDARD,
        class_names: Optional[List[str]] = None,
        grades: Optional[List[str]] = None,
        active_only: bool = True,
    ) -> str:
        """Export borrowers to CSV string."""
        query = self.db.query(Borrower)

        if class_names:
            query = query.filter(Borrower.class_name.in_(class_names))

        if grades:
            query = query.filter(Borrower.grade.in_(grades))

        if active_only:
            query = query.filter(Borrower.active == True)

        borrowers = query.all()

        output = StringIO()

        if format == ExportFormat.BCDI:
            fieldnames = ["Code", "Nom", "Prénom", "Classe", "Niveau"]
        else:
            fieldnames = ["id", "barcode", "last_name", "first_name", "class_name", "grade"]

        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for borrower in borrowers:
            if format == ExportFormat.BCDI:
                writer.writerow({
                    "Code": borrower.barcode,
                    "Nom": borrower.last_name,
                    "Prénom": borrower.first_name,
                    "Classe": borrower.class_name,
                    "Niveau": borrower.grade,
                })
            else:
                writer.writerow({
                    "id": borrower.id,
                    "barcode": borrower.barcode,
                    "last_name": borrower.last_name,
                    "first_name": borrower.first_name,
                    "class_name": borrower.class_name,
                    "grade": borrower.grade,
                })

        return output.getvalue()
```

---

## Database Model Examples

### MediumType Model

**File**: `src/bcd_api/models/medium_type.py`

```python
"""Medium type model for configurable taxonomy."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, Text
import json
from src.bcd_api.core.database import Base


class JSONEncodedDict(TypeDecorator):
    """SQLAlchemy custom type for JSON columns (supports SQLite and PostgreSQL)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Serialize dict to JSON string when saving to database."""
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return None

    def process_result_value(self, value, dialect):
        """Deserialize JSON string to dict when loading from database."""
        if value is not None:
            return json.loads(value)
        return None


class MediumType(Base):
    """Configurable medium type (book, CD, DVD, etc.) with multilingual display names."""

    __tablename__ = "medium_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    display_names = Column(JSONEncodedDict, nullable=False)  # {"en": "Book", "fr": "Livre", "it": "Libro"}
    active = Column(Boolean, nullable=False, default=True)
    is_system_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bibliographic_records = relationship("BibliographicRecord", back_populates="medium_type")
    mappings = relationship("MediumTypeMapping", back_populates="medium_type")

    def get_display_name(self, locale='en'):
        """Get localized display name with fallback to English."""
        return self.display_names.get(locale) or self.display_names.get('en') or self.code

    def __repr__(self):
        return f"<MediumType(code='{self.code}', display_names={self.display_names})>"
```

### MediumTypeMapping Model

**File**: `src/bcd_api/models/medium_type_mapping.py`

```python
"""Medium type mapping model for import normalization."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from src.bcd_api.core.database import Base


class MediumTypeMapping(Base):
    """Mapping from external values to internal medium type codes."""

    __tablename__ = "medium_type_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_value = Column(String(100), nullable=False, index=True)
    medium_type_id = Column(Integer, ForeignKey("medium_types.id"), nullable=False)
    source_format = Column(String(50), nullable=False)  # bcdi, dublin_core, unimarc, custom
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    medium_type = relationship("MediumType", back_populates="mappings")

    def __repr__(self):
        return f"<MediumTypeMapping('{self.external_value}' -> '{self.medium_type.code}')>"
```

---

## Testing Patterns

### Service-Layer Integration Test

**File**: `tests/integration/test_export_service.py`

```python
"""Integration tests for export service."""
import pytest
from src.bcd_api.services.export_service import ExportService
from src.bcd_api.schemas.import_export import ExportFormat


def test_export_catalog_standard_format(db_session, sample_catalog_records):
    """Test exporting catalog in standard format."""
    # Arrange
    service = ExportService(db_session)

    # Act
    csv_output = service.export_catalog(format=ExportFormat.STANDARD)

    # Assert
    assert "isbn,title,author,publisher,medium_type,dewey_decimal" in csv_output
    assert "9782070612758" in csv_output  # Sample ISBN
    assert "book" in csv_output  # Generic code, not "Livre"


def test_export_catalog_bcdi_format(db_session, sample_catalog_records):
    """Test exporting catalog in BCDI format with French field names."""
    # Arrange
    service = ExportService(db_session)

    # Act
    csv_output = service.export_catalog(format=ExportFormat.BCDI)

    # Assert
    assert "ISBN,Titre,Auteur,Editeur,Support,Cote" in csv_output
    assert "Livre" in csv_output  # French display name
    assert "book" not in csv_output  # Generic code should not appear


def test_round_trip_fidelity(db_session, import_service, export_service):
    """Test export → import → export produces identical CSV (FR-064)."""
    # Arrange: Export initial data
    csv1 = export_service.export_catalog(format=ExportFormat.STANDARD)

    # Act: Import then export again
    import_service.import_catalog(csv1)
    csv2 = export_service.export_catalog(format=ExportFormat.STANDARD)

    # Assert: CSVs should be identical
    assert csv1 == csv2


def test_export_catalog_with_medium_type_filter(db_session, sample_catalog_records):
    """Test filtering export by medium types."""
    # Arrange
    service = ExportService(db_session)

    # Act
    csv_output = service.export_catalog(medium_types=["book", "periodical"])

    # Assert
    lines = csv_output.strip().split("\n")
    assert all("book" in line or "periodical" in line or "medium_type" in line for line in lines)


def test_export_catalog_utf8_encoding(db_session):
    """Test French characters survive export (FR-069)."""
    # Arrange: Create record with French characters
    service = ExportService(db_session)
    # ... create record with title "L'Été à Paris"

    # Act
    csv_output = service.export_catalog()

    # Assert
    assert "L'Été à Paris" in csv_output
    assert csv_output.encode("utf-8")  # Should not raise UnicodeEncodeError


@pytest.mark.parametrize("format,expected_fields", [
    (ExportFormat.STANDARD, ["isbn", "title", "author", "medium_type"]),
    (ExportFormat.BCDI, ["ISBN", "Titre", "Auteur", "Support"]),
    (ExportFormat.DUBLIN_CORE, ["dc.identifier", "dc.title", "dc.creator", "dc.type"]),
])
def test_export_formats_have_correct_headers(db_session, format, expected_fields):
    """Test each export format has correct CSV headers."""
    service = ExportService(db_session)
    csv_output = service.export_catalog(format=format)

    header_line = csv_output.split("\n")[0]
    for field in expected_fields:
        assert field in header_line
```

---

## Deployment Checklist

### Phase 1: Database Migration

1. **Create Alembic migration** for `medium_types` and `medium_type_mappings` tables:

```bash
alembic revision --autogenerate -m "Add medium_types and medium_type_mappings tables"
```

2. **Review and test migration**:

```bash
alembic upgrade head  # Apply migration
alembic downgrade -1  # Test rollback
alembic upgrade head  # Re-apply
```

3. **Seed default medium types** (run once):

```python
# In migration script or seed script
from src.bcd_api.models.medium_type import MediumType

default_types = [
    {"code": "book", "display_name_en": "Book", "display_name_fr": "Livre"},
    {"code": "periodical", "display_name_en": "Periodical", "display_name_fr": "Périodique"},
    {"code": "audiobook", "display_name_en": "Audiobook", "display_name_fr": "Livre audio"},
    {"code": "cd", "display_name_en": "CD", "display_name_fr": "CD"},
    {"code": "dvd", "display_name_en": "DVD", "display_name_fr": "DVD"},
    {"code": "vhs", "display_name_en": "VHS", "display_name_fr": "VHS"},
    {"code": "board_game", "display_name_en": "Board Game", "display_name_fr": "Jeu de société"},
    {"code": "video_game", "display_name_en": "Video Game", "display_name_fr": "Jeu vidéo"},
    {"code": "other", "display_name_en": "Other", "display_name_fr": "Autre"},
]

for type_data in default_types:
    db.add(MediumType(**type_data, is_system_default=True, active=True))
db.commit()
```

### Phase 2: Backend Implementation

1. Implement service layer (export_service.py, import_service.py, medium_type_service.py)
2. Write service-layer integration tests (target 90%+ coverage)
3. Add API endpoints (/api/v1/export/*, /api/v1/import/*, /api/v1/admin/medium-types)
4. Test round-trip fidelity with sample BCDI and Dublin Core files

### Phase 3: Frontend Implementation

1. Add export dialogs to Borrowers and Catalog pages
2. Implement import wizard (4-step flow: upload → map → preview → confirm)
3. Add admin UI for medium types and mappings management
4. Update i18n files (locales/en.json, locales/fr.json)

### Phase 4: Testing & Validation

1. Run full test suite: `pytest tests/ --cov=src`
2. Test with real BCDI export from French school library
3. Verify French character encoding (UTF-8 round-trip)
4. Performance test: 1000 records export in <5 seconds, import in <10 seconds
5. Cross-browser testing (Chrome, Firefox, Safari, Edge)

### Phase 5: Documentation

1. Update user documentation (how to export, import, configure medium types)
2. Update API documentation (OpenAPI specs auto-generated)
3. Create migration guide for existing installations

---

## Key Implementation Notes

1. **Database Architecture**: Use foreign key lookup tables (medium_types) instead of hardcoded enums. This enables schools to customize types without code deployment.

2. **Import Direction**: Map FROM French/BCDI TO generic English codes. Database stores "book", UI displays "Livre" via i18n.

3. **Fuzzy Matching**: Use rapidfuzz library with 80% threshold for column and value normalization. Multi-stage normalization: text cleaning → abbreviation expansion → synonym matching.

4. **Transaction Safety**: Wrap imports in database transactions with rollback on error (FR-063).

5. **Performance**: Batch process imports (1000 rows at a time), cache fuzzy match results, use pagination for admin UI.

6. **Testing**: Service-layer integration tests required (90%+ coverage). Test round-trip fidelity, encoding, BCDI compatibility, fuzzy matching edge cases.

7. **i18n**: All user-facing strings externalized to locales/en.json and locales/fr.json. Medium type display names stored in database (display_name_en, display_name_fr).

---

**Next Steps**: Implement backend services first, then add API endpoints, then build Vue 3 UI components. Follow TDD approach (write tests before implementation).
