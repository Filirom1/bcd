/**
 * Cataloging Page Component
 * Workflow: ISBN Lookup → Bibliographic Form → Item Creation
 */

const { defineComponent, ref, computed } = Vue;
const { useI18n } = VueI18n;
import ISBNLookup from '../components/cataloging/ISBNLookup.js';
import BibliographicForm from '../components/cataloging/BibliographicForm.js';
import ItemBarcodeInput from '../components/cataloging/ItemBarcodeInput.js';
import HelpPanel from '../components/ui/HelpPanel.js';

export default defineComponent({
    name: 'CatalogingPage',

    components: {
        ISBNLookup,
        BibliographicForm,
        ItemBarcodeInput,
        HelpPanel
    },

    setup() {
        const { t } = useI18n();

        // Workflow state machine
        const state = ref('isbn-lookup'); // 'isbn-lookup' | 'bibliographic-form' | 'item-creation'

        // Data passed between workflow steps
        const bnfData = ref(null);
        const isbn = ref('');
        const createdRecord = ref(null);

        /**
         * Handle successful ISBN lookup
         */
        const handleLookupSuccess = (data) => {
            bnfData.value = data;
            isbn.value = data.isbn;
            state.value = 'bibliographic-form';
        };

        /**
         * Handle ISBN not found in BNF
         */
        const handleLookupNotFound = (isbnValue) => {
            bnfData.value = null;
            isbn.value = isbnValue;
            state.value = 'bibliographic-form';
        };

        /**
         * Handle manual entry (no ISBN lookup)
         */
        const handleManualEntry = (isbnValue = '') => {
            bnfData.value = null;
            isbn.value = isbnValue; // Copy ISBN from lookup to form
            state.value = 'bibliographic-form';
        };

        /**
         * Handle existing record found (ISBN already exists in database)
         */
        const handleExistingRecordFound = (record) => {
            // Skip bibliographic form, go directly to item creation
            // Ensure we use the correct ID field (record_id or id)
            createdRecord.value = {
                id: record.record_id || record.id,
                title: record.title,
                medium_type: record.medium_type
            };
            state.value = 'item-creation';
        };

        /**
         * Handle bibliographic record created
         */
        const handleRecordCreated = (record) => {
            createdRecord.value = record;
            state.value = 'item-creation';
        };

        /**
         * Handle cancel from bibliographic form
         */
        const handleFormCancel = () => {
            resetWorkflow();
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
            state.value = 'isbn-lookup';
            bnfData.value = null;
            isbn.value = '';
            createdRecord.value = null;
        };

        // Computed
        const pageTitle = computed(() => {
            switch (state.value) {
                case 'isbn-lookup':
                    return t('cataloging.page_title');
                case 'bibliographic-form':
                    return t('cataloging.bibliographic_form_title');
                case 'item-creation':
                    return t('cataloging.item_creation_title');
                default:
                    return t('cataloging.page_title');
            }
        });

        const showBackButton = computed(() => {
            return state.value !== 'isbn-lookup';
        });

        return {
            state,
            bnfData,
            isbn,
            createdRecord,
            pageTitle,
            showBackButton,
            handleLookupSuccess,
            handleLookupNotFound,
            handleManualEntry,
            handleExistingRecordFound,
            handleRecordCreated,
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
                        <i class="bi bi-arrow-left me-2"></i>
                        {{ $t('cataloging.start_over') }}
                    </button>
                    <help-panel section="cataloging" />
                </div>
            </div>

            <!-- Workflow Steps -->
            <div class="card">
                <div class="card-body">
                    <!-- Step 1: ISBN Lookup -->
                    <ISBNLookup
                        v-if="state === 'isbn-lookup'"
                        @lookup-success="handleLookupSuccess"
                        @lookup-not-found="handleLookupNotFound"
                        @manual-entry="handleManualEntry"
                        @existing-record-found="handleExistingRecordFound"
                    />

                    <!-- Step 2: Bibliographic Form -->
                    <BibliographicForm
                        v-if="state === 'bibliographic-form'"
                        :bnf-data="bnfData"
                        :isbn="isbn"
                        @record-created="handleRecordCreated"
                        @cancel="handleFormCancel"
                    />

                    <!-- Step 3: Item Creation -->
                    <ItemBarcodeInput
                        v-if="state === 'item-creation' && createdRecord"
                        :record-id="createdRecord.id"
                        :record-title="createdRecord.title"
                        :record-medium-type="createdRecord.medium_type"
                        @item-created="(item) => {}"
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
                            :class="state === 'isbn-lookup' ? 'btn-primary' : 'btn-outline-secondary'"
                            disabled
                        >
                            <i class="bi bi-1-circle me-1"></i>
                            {{ $t('cataloging.step_lookup') }}
                        </button>
                        <button
                            type="button"
                            class="btn"
                            :class="state === 'bibliographic-form' ? 'btn-primary' : 'btn-outline-secondary'"
                            disabled
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
