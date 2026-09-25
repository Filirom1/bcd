/**
 * Cataloging Page Component
 * Workflow: Find a notice → Bibliographic Form → Item Creation
 */

const { defineComponent, ref, computed, onMounted } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;
import FindNotice from '../components/cataloging/FindNotice.js';
import BibliographicForm from '../components/cataloging/BibliographicForm.js';
import ItemBarcodeInput from '../components/cataloging/ItemBarcodeInput.js';
import HelpPanel from '../components/ui/HelpPanel.js';
import { apiClient } from '../api/client.js';

export default defineComponent({
    name: 'CatalogingPage',

    components: {
        FindNotice,
        BibliographicForm,
        ItemBarcodeInput,
        HelpPanel
    },

    setup() {
        const { t } = useI18n();
        const route = useRoute();

        // Workflow state machine
        const state = ref('find-notice'); // 'find-notice' | 'bibliographic-form' | 'item-creation'

        // Data passed between workflow steps
        const bnfData = ref(null);
        const isbn = ref('');
        const originalInput = ref('');
        const inputType = ref('text');
        const initialTitle = ref('');
        const createdRecord = ref(null);
        const existingRecord = ref(null);

        /**
         * Only identifiers should be copied into the ISBN/ISSN form field.
         * Free text is a title/author search query and must not be persisted as
         * an ISBN (for example, entering "J-magazine" to find a periodical).
         * The string form is retained for compatibility with older callers.
         */
        const isSupportedIdentifier = (value, inputType) => {
            if (inputType === 'unsupported_barcode' || inputType === 'ean977' || !value) return false;

            const compact = String(value).trim().replace(/^(isbn:|issn:)/i, '').replace(/[\s-]/g, '');
            return /^(?:\d{9}[\dXx]|(?:978|979)\d{10}|\d{7}[\dXx])$/.test(compact);
        };

        const handleLookupSuccess = (data) => {
            bnfData.value = data;
            isbn.value = data.isbn || '';
            originalInput.value = data.isbn || originalInput.value;
            inputType.value = (data.identifier_type || '').toLowerCase() === 'issn'
                || String(data.isbn || '').toLowerCase().startsWith('issn:') ? 'issn' : 'isbn';
            initialTitle.value = data.title || '';
            state.value = 'bibliographic-form';
        };

        /**
         * Handle a local/external lookup miss.  A title or author query is not
         * an identifier and should start with an empty ISBN/ISSN field.
         */
        const handleLookupNotFound = (value) => {
            const input = typeof value === 'string' ? { value } : (value || {});
            const inputValue = input.value || '';
            const inputTypeValue = input.inputType || 'text';
            bnfData.value = null;
            isbn.value = isSupportedIdentifier(inputValue, inputTypeValue) ? inputValue : '';
            originalInput.value = input.originalInput || inputValue;
            inputType.value = inputTypeValue;
            initialTitle.value = input.title || (inputTypeValue === 'text' ? inputValue : '');
            state.value = 'bibliographic-form';
        };

        /**
         * Handle manual entry after a local miss, source timeout, or barcode
         * that is not an ISBN/ISSN.
         */
        const handleManualEntry = (payload = {}) => {
            const input = typeof payload === 'string' ? { value: payload } : payload;
            const inputValue = input.value || '';
            const inputTypeValue = input.inputType || 'text';
            bnfData.value = null;
            isbn.value = isSupportedIdentifier(inputValue, inputTypeValue) ? inputValue : '';
            originalInput.value = input.originalInput || inputValue;
            inputType.value = inputTypeValue;
            initialTitle.value = input.title || (inputTypeValue === 'text' ? inputValue : '');
            state.value = 'bibliographic-form';
        };

        const handleNoticeSelected = (record) => {
            handleExistingRecordFound(record);
        };

        /**
         * Handle existing record found (ISBN already exists in database)
         */
        const handleExistingRecordFound = (record) => {
            // Selecting an existing notice skips notice creation and goes
            // directly to adding a physical copy.
            const identifierType = record.identifier_type
                || (String(record.isbn || '').toLowerCase().startsWith('issn:') ? 'issn' : 'isbn');
            createdRecord.value = {
                ...record,
                id: record.record_id || record.notice_id || record.id,
                subtitle: record.subtitle || null,
                medium_type: record.medium_type || (identifierType === 'issn' ? 'Périodique' : 'Livre'),
                identifier_type: identifierType,
                dewey_number: record.dewey_number || null,
                authors: record.authors || [],
                collection: record.collection || null,
                illustrators: record.illustrators || []
            };
            state.value = 'item-creation';
        };

        /**
         * Handle bibliographic record created or updated
         */
        const handleRecordCreated = (record) => {
            const identifierType = record.identifier_type
                || (String(record.isbn || '').toLowerCase().startsWith('issn:') ? 'issn' : 'isbn');
            createdRecord.value = {
                ...record,
                id: record.record_id || record.id,
                subtitle: record.subtitle || null,
                medium_type: record.medium_type || (identifierType === 'issn' ? 'Périodique' : 'Livre'),
                identifier_type: identifierType,
                dewey_number: record.dewey_number || null,
                authors: record.authors || [],
                collection: record.collection || null,
                illustrators: record.illustrators || []
            };
            existingRecord.value = null;
            state.value = 'item-creation';
        };

        /**
         * Handle edit record from item creation step
         */
        const handleEditRecord = async () => {
            if (!createdRecord.value) return;
            try {
                const recordId = createdRecord.value.id;
                const freshRecord = await apiClient.get(`/catalog/bibliographic/${recordId}`);
                existingRecord.value = freshRecord;
                state.value = 'bibliographic-form';
            } catch (err) {
                console.error("Error fetching record for editing:", err);
                existingRecord.value = createdRecord.value;
                state.value = 'bibliographic-form';
            }
        };

        /**
         * Handle cancel from bibliographic form
         */
        const handleFormCancel = () => {
            if (existingRecord.value) {
                existingRecord.value = null;
                state.value = 'item-creation';
            } else {
                resetWorkflow();
            }
        };

        /**
         * Handle item creation done
         */
        const handleItemsDone = () => {
            resetWorkflow();
        };

        /**
         * Reset workflow to start
         */
        const resetWorkflow = () => {
            state.value = 'find-notice';
            bnfData.value = null;
            isbn.value = '';
            originalInput.value = '';
            inputType.value = 'text';
            initialTitle.value = '';
            createdRecord.value = null;
            existingRecord.value = null;
        };

        // Open directly on item creation when launched from an existing notice.
        onMounted(async () => {
            const recordId = Number(route.query.record_id);
            if (!Number.isInteger(recordId) || recordId <= 0) return;

            try {
                const record = await apiClient.get(`/catalog/bibliographic/${recordId}`);
                handleExistingRecordFound(record);
            } catch (error) {
                console.error('Error loading record for item creation:', error);
            }
        });

        // Computed
        const pageTitle = computed(() => {
            switch (state.value) {
                case 'find-notice':
                    return t('cataloging.find_notice_title');
                case 'bibliographic-form':
                    return t('cataloging.bibliographic_form_title');
                case 'item-creation':
                    return t('cataloging.item_creation_title');
                default:
                    return t('cataloging.page_title');
            }
        });

        const showBackButton = computed(() => {
            return state.value !== 'find-notice';
        });

        return {
            state,
            bnfData,
            isbn,
            originalInput,
            inputType,
            initialTitle,
            createdRecord,
            existingRecord,
            pageTitle,
            showBackButton,
            handleLookupSuccess,
            handleLookupNotFound,
            handleManualEntry,
            handleNoticeSelected,
            handleExistingRecordFound,
            handleRecordCreated,
            handleEditRecord,
            handleFormCancel,
            handleItemsDone,
            resetWorkflow
        };
    },

    template: `
        <div class="cataloging-page">
            <!-- Page Header -->
            <div class="page-header">
                <div>
                    <h1 class="page-title">
                        <i class="bi bi-pencil-square me-2"></i>
                        {{ pageTitle }}
                    </h1>
                    <p class="text-muted mb-0">
                        {{ $t('cataloging.page_subtitle') }}
                    </p>
                </div>
                <div class="d-flex gap-2 align-items-center">
                    <button
                        v-if="showBackButton"
                        type="button"
                        class="btn btn-outline-secondary"
                        @click="resetWorkflow"
                    >
                        <i :class="state === 'item-creation' ? 'bi bi-plus-circle me-2' : 'bi bi-arrow-left me-2'"></i>
                        {{ state === 'item-creation' ? $t('cataloging.catalog_another') : $t('cataloging.start_over') }}
                    </button>
                    <help-panel section="cataloging" />
                </div>
            </div>

            <!-- Workflow Steps -->
            <div class="card">
                <div class="card-body">
                    <!-- Step 1: Find a notice -->
                    <FindNotice
                        v-if="state === 'find-notice'"
                        @lookup-success="handleLookupSuccess"
                        @lookup-not-found="handleLookupNotFound"
                        @manual-entry="handleManualEntry"
                        @notice-selected="handleNoticeSelected"
                    />

                    <!-- Step 2: Bibliographic Form -->
                    <BibliographicForm
                        v-if="state === 'bibliographic-form'"
                        :bnf-data="bnfData"
                        :isbn="isbn"
                        :original-input="originalInput"
                        :input-type="inputType"
                        :initial-title="initialTitle"
                        :existing-record="existingRecord"
                        @record-created="handleRecordCreated"
                        @cancel="handleFormCancel"
                    />

                    <!-- Step 3: Item Creation -->
                    <ItemBarcodeInput
                        v-if="state === 'item-creation' && createdRecord"
                        :record-id="createdRecord.id"
                        :record-title="createdRecord.title"
                        :record-subtitle="createdRecord.subtitle"
                        :record-medium-type="createdRecord.medium_type"
                        :record-identifier-type="createdRecord.identifier_type"
                        :record-dewey-number="createdRecord.dewey_number"
                        :record-authors="createdRecord.authors"
                        :record-collection="createdRecord.collection"
                        :record-illustrators="createdRecord.illustrators"
                        @item-created="(item) => {}"
                        @edit-record="handleEditRecord"
                        @done="handleItemsDone"
                    />
                </div>
            </div>

            <!-- Workflow Progress Indicator -->
            <div class="mt-4">
                <div class="d-flex justify-content-center">
                    <div class="btn-group btn-group-sm" role="group">
                        <button
                            type="button"
                            class="btn"
                            :class="state === 'find-notice' ? 'btn-primary' : 'btn-outline-secondary'"
                            :disabled="state === 'find-notice'"
                            @click="resetWorkflow"
                        >
                            <i class="bi bi-1-circle me-1"></i>
                            {{ $t('cataloging.step_lookup') }}
                        </button>
                        <button
                            type="button"
                            class="btn"
                            :class="state === 'bibliographic-form' ? 'btn-primary' : 'btn-outline-secondary'"
                            :disabled="state !== 'item-creation'"
                            @click="handleEditRecord"
                        >
                            <i class="bi bi-2-circle me-1"></i>
                            {{ $t('cataloging.step_record') }}
                        </button>
                        <button
                            type="button"
                            class="btn"
                            :class="state === 'item-creation' ? 'btn-primary' : 'btn-outline-secondary'"
                            disabled
                        >
                            <i class="bi bi-3-circle me-1"></i>
                            {{ $t('cataloging.step_items') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `
});
