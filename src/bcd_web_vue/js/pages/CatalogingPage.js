/**
 * Cataloging Page Component
 * Workflow: Find a notice → Bibliographic Form → Item Creation
 */

const { defineComponent, ref, computed, onMounted, onBeforeUnmount, watch, nextTick } = Vue;
const { useI18n } = VueI18n;
const { useRoute, useRouter } = VueRouter;
import FindNotice from '../components/cataloging/FindNotice.js';
import BibliographicForm from '../components/cataloging/BibliographicForm.js';
import ItemBarcodeInput from '../components/cataloging/ItemBarcodeInput.js';
import HelpPanel from '../components/ui/HelpPanel.js';
import { apiClient } from '../api/client.js';
import { useNotification } from '../composables/useNotification.js';

import PageHeader from '../components/ui/PageHeader.js';

export default defineComponent({
    name: 'CatalogingPage',

    components: {
        PageHeader,
        FindNotice,
        BibliographicForm,
        ItemBarcodeInput,
        HelpPanel
    },

    setup() {
        const { t } = useI18n();
        const { error: showError } = useNotification();
        const route = useRoute();
        const router = useRouter();

        // Workflow state machine
        const state = ref('find-notice');

        // Data passed between workflow steps
        const bnfData = ref(null);
        const isbn = ref('');
        const originalInput = ref('');
        const lookupQuery = ref('');
        const inputType = ref('text');
        const initialTitle = ref('');
        const createdRecord = ref(null);
        const existingRecord = ref(null);
        const findNoticeRef = ref(null);
        const bibliographicFormRef = ref(null);
        const itemBarcodeInputRef = ref(null);
        let routeSyncGeneration = 0;

        const routeValue = (value) => Array.isArray(value) ? String(value[0] || '') : String(value || '');
        const routeQuery = (step, query = '', recordId = null) => {
            const result = { step };
            if (query) result.query = query;
            if (recordId) result.record_id = String(recordId);
            return result;
        };
        const updateRoute = (method, query) => router[method]({ query });

        const normalizeRecord = (record) => {
            const identifierType = record.identifier_type
                || (String(record.isbn || '').toLowerCase().startsWith('issn:') ? 'issn' : 'isbn');
            return {
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
        };

        const focusLookup = () => {
            nextTick(() => findNoticeRef.value?.focusQuery?.());
        };

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
            lookupQuery.value = lookupQuery.value || originalInput.value || data.isbn || '';
            originalInput.value = lookupQuery.value;
            inputType.value = (data.identifier_type || '').toLowerCase() === 'issn'
                || String(data.isbn || '').toLowerCase().startsWith('issn:') ? 'issn'
                : (data.isbn ? 'isbn' : 'text');
            initialTitle.value = data.title || '';
            state.value = 'bibliographic-form';
            updateRoute('push', routeQuery(
                'bibliographic-form',
                lookupQuery.value || originalInput.value
            ));
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
            lookupQuery.value = inputValue;
            updateRoute('push', routeQuery('bibliographic-form', lookupQuery.value));
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
            lookupQuery.value = inputValue;
            updateRoute('push', routeQuery('bibliographic-form', lookupQuery.value));
        };

        const handleLocalResults = ({ query }) => {
            lookupQuery.value = query || lookupQuery.value;
            updateRoute('replace', routeQuery('lookup', lookupQuery.value));
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
            createdRecord.value = normalizeRecord(record);
            state.value = 'item-creation';
            updateRoute('push', routeQuery('item-creation', '', createdRecord.value.id));
        };

        /**
         * Handle bibliographic record created or updated
         */
        const handleRecordCreated = (record) => {
            const recordWithCover = { ...record };
            if (!recordWithCover.cover_image && bnfData.value?.cover_image) {
                recordWithCover.cover_image = bnfData.value.cover_image;
            }
            if (!recordWithCover.cover_url && bnfData.value?.cover_url) {
                recordWithCover.cover_url = bnfData.value.cover_url;
            }
            createdRecord.value = normalizeRecord(recordWithCover);
            existingRecord.value = null;
            state.value = 'item-creation';
            if (createdRecord.value.id) {
                const id = createdRecord.value.id;
                updateRoute('replace', routeQuery('bibliographic-form', '', id))
                    .then(() => updateRoute('push', routeQuery('item-creation', '', id)));
            }
        };

        /**
         * Handle edit record from item creation step
         */
        const handleEditRecord = async () => {
            if (!createdRecord.value) return;
            state.value = 'bibliographic-form';
            updateRoute('push', routeQuery(
                'bibliographic-form',
                '',
                createdRecord.value.id
            ));
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
                updateRoute('push', routeQuery(
                    'item-creation',
                    '',
                    createdRecord.value?.id
                ));
            } else {
                resetWorkflow();
            }
        };

        /**
         * Continue to the regular checkout workflow with the newly cataloged
         * copy prefilled. The librarian still selects the borrower and confirms
         * the loan on the circulation page.
         */
        const handleCheckoutItem = (item) => {
            if (!item?.item_id) return;
            router.push({
                name: 'checkout',
                query: { item_id: String(item.item_id) }
            });
        };

        /**
         * Handle item creation done
         */
        const handleItemsDone = () => {
            resetWorkflow();
        };

        const goToLookup = () => {
            const query = lookupQuery.value || originalInput.value;
            state.value = 'find-notice';
            bnfData.value = null;
            existingRecord.value = null;
            createdRecord.value = null;
            updateRoute('push', routeQuery('lookup', query));
            focusLookup();
        };

        /**
         * Reset workflow to start
         */
        const resetWorkflow = () => {
            state.value = 'find-notice';
            bnfData.value = null;
            isbn.value = '';
            originalInput.value = '';
            lookupQuery.value = '';
            inputType.value = 'text';
            initialTitle.value = '';
            createdRecord.value = null;
            existingRecord.value = null;
            updateRoute('replace', routeQuery('lookup'));
            focusLookup();
        };

        const restoreRecord = async (recordId, generation, step) => {
            try {
                const record = await apiClient.get(`/catalog/bibliographic/${recordId}`);
                if (generation !== routeSyncGeneration) return;
                createdRecord.value = normalizeRecord(record);
                if (step === 'bibliographic-form') {
                    existingRecord.value = record;
                    isbn.value = record.isbn || '';
                    initialTitle.value = record.title || '';
                    state.value = 'bibliographic-form';
                } else {
                    existingRecord.value = null;
                    state.value = 'item-creation';
                }
            } catch (error) {
                console.error('Error loading record for item creation:', error);
                if (generation === routeSyncGeneration) {
                    showError(t('cataloging.record_load_error'));
                    resetWorkflow();
                }
            }
        };

        const syncFromRoute = async () => {
            const generation = ++routeSyncGeneration;
            const requestedStep = routeValue(route.query.step);
            const query = routeValue(route.query.query);
            const recordId = Number(routeValue(route.query.record_id));
            const hasRecordId = Number.isInteger(recordId) && recordId > 0;
            const step = requestedStep || (hasRecordId ? 'item-creation' : 'lookup');

            if (!requestedStep && hasRecordId) {
                updateRoute('replace', routeQuery('item-creation', '', recordId));
            }

            if (step === 'lookup') {
                state.value = 'find-notice';
                lookupQuery.value = query;
                bnfData.value = null;
                isbn.value = '';
                originalInput.value = query;
                initialTitle.value = '';
                createdRecord.value = null;
                existingRecord.value = null;
                if (requestedStep !== 'lookup' || route.query.record_id) {
                    updateRoute('replace', routeQuery('lookup', query));
                }
                return;
            }

            if (step === 'bibliographic-form') {
                if (
                    !hasRecordId
                    && state.value === 'bibliographic-form'
                    && lookupQuery.value === query
                ) {
                    return;
                }
                lookupQuery.value = query;
                originalInput.value = query;
                bnfData.value = null;
                if (hasRecordId && Number(createdRecord.value?.id) !== recordId) {
                    await restoreRecord(recordId, generation, step);
                    return;
                }
                if (hasRecordId) {
                    existingRecord.value = createdRecord.value;
                    state.value = 'bibliographic-form';
                    return;
                }
                if (route.query.record_id) {
                    resetWorkflow();
                    return;
                }
                createdRecord.value = null;
                existingRecord.value = null;
                const isIdentifier = isSupportedIdentifier(query, 'text');
                isbn.value = isIdentifier ? query : '';
                inputType.value = isIdentifier ? 'isbn' : 'text';
                initialTitle.value = isIdentifier ? '' : query;
                state.value = 'bibliographic-form';
                return;
            }

            if (step === 'item-creation' && hasRecordId) {
                if (Number(createdRecord.value?.id) === recordId) {
                    existingRecord.value = null;
                    state.value = 'item-creation';
                    return;
                }
                await restoreRecord(recordId, generation, step);
                return;
            }

            resetWorkflow();
        };

        const handleKeydown = (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                resetWorkflow();
                return;
            }
            if (event.key !== 'Enter' || event.repeat) return;

            const target = event.target;
            if (
                target?.isContentEditable
                || target?.matches?.('input, textarea, select, button, a[href], [role="button"]')
            ) {
                return;
            }

            const action = {
                'find-notice': findNoticeRef.value?.search,
                'bibliographic-form': bibliographicFormRef.value?.submitRecord,
                'item-creation': itemBarcodeInputRef.value?.createItem
            }[state.value];
            if (action) {
                event.preventDefault();
                action();
            }
        };

        onMounted(() => {
            syncFromRoute();
            window.addEventListener('keydown', handleKeydown);
        });
        onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown));
        watch(
            () => [route.query.step, route.query.query, route.query.record_id],
            () => syncFromRoute()
        );

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
            lookupQuery,
            findNoticeRef,
            bibliographicFormRef,
            itemBarcodeInputRef,
            pageTitle,
            showBackButton,
            handleLocalResults,
            handleLookupSuccess,
            handleLookupNotFound,
            handleManualEntry,
            handleNoticeSelected,
            handleExistingRecordFound,
            handleRecordCreated,
            handleEditRecord,
            handleCheckoutItem,
            handleFormCancel,
            handleItemsDone,
            goToLookup,
            resetWorkflow,
            syncFromRoute,
            handleKeydown
        };
    },

    template: `
        <div class="cataloging-page">
            <!-- Page Header -->
            <page-header>
                <template #heading>
                    <h1 class="page-title">
                        <i class="bi bi-pencil-square me-2"></i>
                        {{ pageTitle }}
                    </h1>
                </template>
                <template #actions>
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
                </template>
            </page-header>

            <div class="card mb-3" data-testid="cataloging-workflow-card">
                <div class="card-header bg-white">
                    <div class="cataloging-stepper flex-grow-1" data-testid="cataloging-stepper">
                        <div class="btn-group btn-group-sm d-flex w-100" role="group">
                            <button
                                type="button"
                                class="btn flex-fill"
                                :class="state === 'find-notice' ? 'btn-primary' : 'btn-outline-secondary'"
                                :disabled="state === 'find-notice'"
                                @click="goToLookup"
                            >
                                <i class="bi bi-1-circle me-1"></i>
                                {{ $t('cataloging.step_lookup') }}
                            </button>
                            <button
                                type="button"
                                class="btn flex-fill"
                                :class="state === 'bibliographic-form' ? 'btn-primary' : 'btn-outline-secondary'"
                                :disabled="state !== 'item-creation'"
                                @click="handleEditRecord"
                            >
                                <i class="bi bi-2-circle me-1"></i>
                                {{ $t('cataloging.step_record') }}
                            </button>
                            <button
                                type="button"
                                class="btn flex-fill"
                                :class="state === 'item-creation' ? 'btn-primary' : 'btn-outline-secondary'"
                                disabled
                            >
                                <i class="bi bi-3-circle me-1"></i>
                                {{ $t('cataloging.step_items') }}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="card-body">
                    <!-- Workflow Steps -->
                    <!-- Step 1: Find a notice -->
                    <FindNotice
                        ref="findNoticeRef"
                        v-if="state === 'find-notice'"
                        :initial-query="lookupQuery"
                        @lookup-success="handleLookupSuccess"
                        @lookup-not-found="handleLookupNotFound"
                        @manual-entry="handleManualEntry"
                        @local-results="handleLocalResults"
                        @notice-selected="handleNoticeSelected"
                    />

                    <!-- Step 2: Bibliographic Form -->
                    <BibliographicForm
                        ref="bibliographicFormRef"
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
                        ref="itemBarcodeInputRef"
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
                        :record-cover-image="createdRecord.cover_image"
                        :record-cover-url="createdRecord.cover_url"
                        @item-created="(item) => {}"
                        @checkout-item="handleCheckoutItem"
                        @edit-record="handleEditRecord"
                        @done="handleItemsDone"
                    />
                </div>
            </div>

        </div>
    `
});
