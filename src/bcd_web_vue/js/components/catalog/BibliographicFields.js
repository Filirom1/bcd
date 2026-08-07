/**
 * BibliographicFields Component
 *
 * Single source of truth for the bibliographic record field layout, used by:
 *   - RecordDetail.js  (book detail view + inline edit)
 *   - BibliographicForm.js (cataloging: new record + edit)
 *
 * Layout: clear sections, each field is a horizontal row with the label aligned
 * left and the control aligned right (Bootstrap grid, no custom CSS).
 *
 * Binding: v-model on a plain object holding the 21 editable fields. Array fields
 * (authors, illustrators, keywords) are stored as arrays in the model and edited
 * as comma-separated text here, so both callers can pass/receive arrays.
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import { AUDIENCE_VALUES, BINDING_TYPE_VALUES, parseCsv } from '../../utils/domain.js';

export default defineComponent({
    name: 'BibliographicFields',

    props: {
        // The bibliographic form object (mutated in place via v-model).
        modelValue: { type: Object, required: true },
        // Edit mode -> real controls; otherwise read-only plaintext.
        editMode: { type: Boolean, default: true },
        // { field: message } for edit-mode validation feedback.
        errors: { type: Object, default: () => ({}) },
        // App settings, used for medium_type / language suggestions.
        settings: { type: Object, default: null },
        // Hide series_number (periodicals in view mode).
        hideSeriesNumber: { type: Boolean, default: false }
    },

    emits: ['update:modelValue'],

    setup(props, { emit }) {
        const { t } = useI18n();

        const form = computed(() => props.modelValue);
        const set = (key, value) => emit('update:modelValue', { ...props.modelValue, [key]: value });


        // Array<->CSV bridge for authors/illustrators/keywords.
        const csvField = (key) => computed({
            get: () => (Array.isArray(form.value[key]) ? form.value[key].join(', ') : (form.value[key] || '')),
            set: (val) => set(key, parseCsv(val))
        });
        const authorsText = csvField('authors');
        const illustratorsText = csvField('illustrators');
        const keywordsText = csvField('keywords');

        const audienceOptions = AUDIENCE_VALUES.map(value => ({ value, label: t(`bibliographic.audience_${value}`) }));
        const bindingTypeOptions = BINDING_TYPE_VALUES.map(value => ({ value, label: t(`bibliographic.binding_${value}`) }));
        const mediumTypeSuggestions = computed(() => parseCsv(props.settings?.catalog_medium_types));
        const levelSuggestions = computed(() => parseCsv(props.settings?.catalog_levels));
        const languageSuggestions = computed(() => parseCsv(props.settings?.catalog_languages));

        const hasValue = (key) => {
            const value = form.value[key];
            return Array.isArray(value) ? value.length > 0 : value !== null && value !== undefined && value !== '';
        };

        const labelFor = (opts, value) => {
            const found = opts.find(o => o.value === value);
            return found ? found.label : (value || '');
        };
        const getLanguageDisplay = computed(() => {
            return form.value.language || ''; 
        });

        return {
            form, set, authorsText, illustratorsText, keywordsText,
            audienceOptions, bindingTypeOptions, mediumTypeSuggestions, levelSuggestions, languageSuggestions,
            hasValue, labelFor, getLanguageDisplay, t
        };
    },

    // A horizontal row: label left (col-sm-3), control right (col-sm-9).
    // Read-only mode uses .form-control-plaintext so alignment matches edit mode.
    template: `
        <div class="biblio-fields">
          <!-- Basic Information -->
          <h6 class="border-bottom pb-2 mb-3">
            <i class="bi bi-info-circle me-2"></i>{{ t('bibliographic.section_basic_info') }}
          </h6>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('title')">
            <label class="col-sm-3 col-form-label fw-bold">
              {{ t('bibliographic.title') }} <span v-if="editMode" class="text-danger">*</span>
            </label>
            <div class="col-sm-9">
              <input type="text" v-model="form.title"
                :class="editMode ? 'form-control' : 'form-control-plaintext fw-bold'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : ''" @input="set('title', form.title)" />
              <div v-if="editMode && errors.title" class="invalid-feedback d-block" data-testid="error-title">{{ errors.title }}</div>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('subtitle')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.subtitle') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.subtitle"
                :class="editMode ? 'form-control' : 'form-control-plaintext fst-italic'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : ''" @input="set('subtitle', form.subtitle)" />
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('isbn')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.isbn') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.isbn" maxlength="17"
                :class="editMode ? 'form-control font-monospace' : 'form-control-plaintext font-monospace'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_isbn')" @input="set('isbn', form.isbn)" />
            </div>
          </div>

          <!-- Authors & Contributors -->
          <h6 class="border-bottom pb-2 mb-3 mt-4">
            <i class="bi bi-people me-2"></i>{{ t('bibliographic.section_authors') }}
          </h6>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('authors')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.authors') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="authorsText"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_authors')" />
              <small v-if="editMode" class="form-text text-muted">{{ t('bibliographic.help_authors') }}</small>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('illustrators')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.illustrators') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="illustratorsText"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_illustrators')" />
              <small v-if="editMode" class="form-text text-muted">{{ t('bibliographic.help_illustrators') }}</small>
            </div>
          </div>

          <!-- Publication -->
          <h6 class="border-bottom pb-2 mb-3 mt-4">
            <i class="bi bi-building me-2"></i>{{ t('bibliographic.section_publication') }}
          </h6>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('publisher')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.publisher') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.publisher"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : ''" @input="set('publisher', form.publisher)" />
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('publication_year')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.publication_year') }}</label>
            <div class="col-sm-9">
              <input type="number" v-model="form.publication_year" min="1000" max="2100"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : ''" @input="set('publication_year', form.publication_year)" />
              <div v-if="editMode && errors.publication_year" class="invalid-feedback d-block" data-testid="error-publication-year">{{ errors.publication_year }}</div>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('collection')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.collection') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.collection"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : ''" @input="set('collection', form.collection)" />
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || (!hideSeriesNumber && hasValue('series_number'))">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.series_number') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.series_number"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_series_number')" @input="set('series_number', form.series_number)" />
            </div>
          </div>

          <!-- Classification -->
          <h6 class="border-bottom pb-2 mb-3 mt-4">
            <i class="bi bi-tags me-2"></i>{{ t('bibliographic.section_classification') }}
          </h6>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('medium_type')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.medium_type') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.medium_type" list="bf-medium-suggestions"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_medium_type')" @input="set('medium_type', form.medium_type)" />
              <datalist id="bf-medium-suggestions" v-if="editMode">
                <option v-for="m in mediumTypeSuggestions" :key="m" :value="m">{{ m }}</option>
              </datalist>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('target_audience')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.target_audience') }}</label>
            <div class="col-sm-9">
              <div v-if="!editMode" class="form-control-plaintext">
                <span v-if="form.target_audience" class="badge bg-info">{{ labelFor(audienceOptions, form.target_audience) }}</span>
                <span v-else class="text-muted">—</span>
              </div>
              <select v-else class="form-select" :value="form.target_audience" @change="set('target_audience', $event.target.value)">
                <option value="">— {{ t('common.select') }} —</option>
                <option v-for="a in audienceOptions" :key="a.value" :value="a.value">{{ a.label }}</option>
              </select>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('level')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.level') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.level" list="bf-level-suggestions"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_level')" @input="set('level', form.level)" />
              <datalist id="bf-level-suggestions" v-if="editMode">
                <option v-for="level in levelSuggestions" :key="level" :value="level">{{ level }}</option>
              </datalist>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('language')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.language') }}</label>
            <div class="col-sm-9">
              <div v-if="!editMode" class="form-control-plaintext">{{ getLanguageDisplay || '—' }}</div>
              <input v-else type="text" class="form-control" :value="form.language" list="bf-language-suggestions"
                :placeholder="t('bibliographic.placeholder_language')" @input="set('language', $event.target.value)" />
              <datalist id="bf-language-suggestions" v-if="editMode">
                <option v-for="lang in languageSuggestions" :key="lang" :value="lang">{{ lang }}</option>
              </datalist>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('country_code')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.country_code') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.country_code" maxlength="5"
                :class="editMode ? 'form-control text-uppercase' : 'form-control-plaintext text-uppercase'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_country_code')" @input="set('country_code', form.country_code)" />
            </div>
          </div>

          <!-- Physical description -->
          <h6 class="border-bottom pb-2 mb-3 mt-4">
            <i class="bi bi-book me-2"></i>{{ t('bibliographic.section_physical') }}
          </h6>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('binding_type')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.binding_type') }}</label>
            <div class="col-sm-9">
              <div v-if="!editMode" class="form-control-plaintext">{{ labelFor(bindingTypeOptions, form.binding_type) || '—' }}</div>
              <select v-else class="form-select" :value="form.binding_type" @change="set('binding_type', $event.target.value)">
                <option value="">— {{ t('common.select') }} —</option>
                <option v-for="b in bindingTypeOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
              </select>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('page_count')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.page_count') }}</label>
            <div class="col-sm-9">
              <input type="number" v-model="form.page_count" min="0"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : ''" @input="set('page_count', form.page_count)" />
              <div v-if="editMode && errors.page_count" class="invalid-feedback d-block" data-testid="error-page-count">{{ errors.page_count }}</div>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('has_illustrations')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.has_illustrations') }}</label>
            <div class="col-sm-9">
              <div v-if="!editMode" class="form-control-plaintext">
                <span v-if="form.has_illustrations"><i class="bi bi-check-circle text-success me-1"></i>{{ t('common.yes') }}</span>
                <span v-else><i class="bi bi-x-circle text-muted me-1"></i>{{ t('common.no') }}</span>
              </div>
              <div v-else class="form-check">
                <input type="checkbox" class="form-check-input" id="bf-has-illustrations"
                  :checked="form.has_illustrations" @change="set('has_illustrations', $event.target.checked)" />
                <label class="form-check-label" for="bf-has-illustrations">{{ t('common.yes') }}</label>
              </div>
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('dimensions')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.dimensions') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.dimensions"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_dimensions')" @input="set('dimensions', form.dimensions)" />
            </div>
          </div>

          <div class="row mb-2 align-items-center" v-if="'physical_size' in form && (editMode || hasValue('physical_size'))">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.physical_size') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="form.physical_size"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_physical_description')" @input="set('physical_size', form.physical_size)" />
            </div>
          </div>

          <!-- Content -->
          <h6 class="border-bottom pb-2 mb-3 mt-4">
            <i class="bi bi-card-text me-2"></i>{{ t('bibliographic.section_content') }}
          </h6>

          <div class="row mb-2 align-items-center" v-if="editMode || hasValue('keywords')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.keywords') }}</label>
            <div class="col-sm-9">
              <input type="text" v-model="keywordsText"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_keywords')" />
              <small v-if="editMode" class="form-text text-muted">{{ t('bibliographic.help_keywords') }}</small>
            </div>
          </div>

          <div class="row mb-2" v-if="editMode || hasValue('description')">
            <label class="col-sm-3 col-form-label fw-bold">{{ t('bibliographic.description') }}</label>
            <div class="col-sm-9">
              <textarea rows="4" v-model="form.description"
                :class="editMode ? 'form-control' : 'form-control-plaintext'"
                :readonly="!editMode" :placeholder="!editMode ? '—' : t('bibliographic.placeholder_description')" @input="set('description', form.description)"></textarea>
            </div>
          </div>
        </div>
    `
});
