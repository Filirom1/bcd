/**
 * RecordDetail Component
 * Modal displaying detailed bibliographic record information with support for Edit Mode.
 * Unifies view and edit layouts using read-only plaintext inputs to minimize code size.
 */

const { defineComponent, ref, watch, computed } = Vue;
const { useI18n } = VueI18n;
const { useRouter } = VueRouter;
import Modal from '../ui/Modal.js';
import { formatCivilDate } from '../../utils/date.js';
import LoadingSpinner from '../ui/LoadingSpinner.js';
import AutocompleteInput from '../ui/AutocompleteInput.js';
import Pagination from '../ui/Pagination.js';
import ItemEditForm from './ItemEditForm.js';
import CopiesList from './CopiesList.js';
import RecordDeleteDialog from './RecordDeleteDialog.js';
import BibliographicFields from './BibliographicFields.js';
import { ApiError } from '../../models/error.js';
import { isPeriodicalRecord } from '../../utils/domain.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';
import { useAppState } from '../../composables/useAppState.js';
import { useItemBadge } from '../../composables/useItemBadge.js';
import { getItemStatusBadge, getItemConditionLabel } from '../../utils/itemPresentation.js';
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import { apiClient } from '../../api/client.js';
import { normalizeCollection } from '../../models/pagination.js';
import { events } from '../../utils/events.js';

export default defineComponent({
    name: 'RecordDetail',

    components: {
        Modal,
        LoadingSpinner,
        AutocompleteInput,
        Pagination,
        ItemEditForm,
        CopiesList,
        RecordDeleteDialog,
        BibliographicFields
    },

    props: {
        recordId: {
            type: Number,
            default: null
        },
        record: {
            type: Object,
            default: null
        },
        show: {
            type: Boolean,
            default: false
        },
        initialMode: {
            type: String,
            default: 'view'
        },
        settings: {
            type: Object,
            default: null
        }
    },

    emits: ['close', 'update:show', 'saved', 'deleted', 'quick-return', 'view-borrower'],

    setup(props, { emit }) {
        const { t, locale } = useI18n();
        const router = useRouter();
        const { closeRecord } = useGlobalModal();
        const { settings: globalSettings } = useAppState();
        const settingsValue = computed(() => props.settings || globalSettings.value);
        const { getShelfBadge, getCoteBadge } = useItemBadge(settingsValue);
        const { handleError } = useErrorHandler(t);

        const record = ref(null);
        const items = ref([]);
        const holds = ref([]);
        const loading = ref(false);
        const activeTab = ref('items');
        const coverLoadFailed = ref(false);

        // Edit mode state
        const isEditMode = ref(props.initialMode === 'edit');

        // Form data (all 23 editable fields from BibliographicRecordUpdate)
        const formData = ref({
            isbn: '',
            title: '',
            subtitle: '',
            authors: [],
            illustrators: [],
            publisher: '',
            publication_year: null,
            collection: '',
            series_number: '',
            level: '',
            medium_type: '',
            target_audience: '',
            language: '',
            country_code: '',
            binding_type: '',
            page_count: null,
            has_illustrations: false,
            dimensions: '',
            physical_size: '',
            keywords: [],
            description: ''
        });

        const errors = ref({});
        const isSubmitting = ref(false);

        // ItemEditForm / Item Delete states
        const showItemEditModal = ref(false);
        const editingItem = ref(null);
        const showDeleteDialog = ref(false); // for entire record deletion

        // Hold/reservation state
        const showReserveForm = ref(false);
        const reserveBorrowerQuery = ref('');
        const reserveLoading = ref(false);
        const reserveMessage = ref(null); // { type: 'success'|'error', text: '' }

        // Item history tab state
        const itemHistoryItems = ref([]);
        const itemHistoryPagination = ref(null);
        const itemCurrentLoan = ref(null);
        const itemHistoryLoading = ref(false);
        const itemHistoryLoaded = ref(false);
        const itemHistoryPage = ref(1);
        const itemHistoryDateFrom = ref('');
        const itemHistoryDateTo = ref('');

        const initForm = (newRecord) => {
            if (!newRecord) return;
            formData.value = {
                isbn: newRecord.isbn_value || '',
                title: newRecord.title || '',
                subtitle: newRecord.subtitle || '',
                authors: Array.isArray(newRecord.authors) ? newRecord.authors : [],
                illustrators: Array.isArray(newRecord.illustrators) ? newRecord.illustrators : [],
                publisher: newRecord.publisher || '',
                publication_year: newRecord.publication_year || null,
                collection: newRecord.collection || '',
                series_number: newRecord.series_number || '',
                level: newRecord.level || '',
                medium_type: newRecord.medium_type || '',
                target_audience: newRecord.target_audience || '',
                language: newRecord.language || '',
                country_code: newRecord.country_code || '',
                binding_type: newRecord.binding_type || '',
                page_count: newRecord.page_count || null,
                has_illustrations: newRecord.has_illustrations || false,
                dimensions: newRecord.dimensions || '',
                physical_size: newRecord.physical_size || '',
                keywords: Array.isArray(newRecord.keywords) ? newRecord.keywords : [],
                description: newRecord.description || ''
            };
            errors.value = {};
        };

        const loadRecord = async (recId) => {
            try {
                loading.value = true;
                coverLoadFailed.value = false;
                itemHistoryLoaded.value = false;
                itemHistoryItems.value = [];
                itemHistoryPagination.value = null;
                itemCurrentLoan.value = null;

                // Load record details
                const recData = await apiClient.get(`/catalog/bibliographic/${recId}`);
                record.value = recData;
                initForm(recData);

                // Load items for this record
                await loadRecordItems(recId);

                // Load active holds for this record
                try {
                    holds.value = await apiClient.get(`/holds/bibliographic/${recId}`);
                } catch {
                    holds.value = [];
                }

            } catch (error) {
                console.error('Error loading record:', error);
                record.value = null;
                items.value = [];
                holds.value = [];
            } finally {
                loading.value = false;
            }
        };

        const loadRecordItems = async (recId) => {
            try {
                const itemsData = await apiClient.get(`/catalog/bibliographic/${recId}/items`);
                const rawItems = Array.isArray(itemsData)
                    ? itemsData
                    : (Array.isArray(itemsData?.items) ? itemsData.items : []);
                if (isPeriodicalRecord(record.value)) {
                    rawItems.sort((a, b) => {
                        const na = parseInt(a.call_number);
                        const nb = parseInt(b.call_number);
                        if (!isNaN(na) && !isNaN(nb)) return nb - na;
                        if (!isNaN(na)) return -1;
                        if (!isNaN(nb)) return 1;
                        return (b.call_number || '').localeCompare(a.call_number || '');
                    });
                }
                items.value = rawItems;
            } catch (error) {
                console.error('Error loading record items:', error);
            }
        };

        // Watch for initialMode or show changes to reset edit mode
        watch(
            () => [props.initialMode, props.show],
            ([newMode, newShow]) => {
                if (newShow) {
                    isEditMode.value = newMode === 'edit';
                }
            },
            { immediate: true }
        );

        // Watch for recordId, record and show changes to load data
        watch(
            () => [props.recordId, props.show, props.record],
            async ([newId, newShow, newRecord]) => {
                if (newShow) {
                    if (newRecord) {
                        record.value = newRecord;
                        initForm(newRecord);
                    }
                    if (newId) {
                        await loadRecord(newId);
                    }
                }
            },
            { immediate: true }
        );

        const reloadAllData = async () => {
            if (record.value && record.value.id) {
                await loadRecordItems(record.value.id);
                if (activeTab.value === 'holds') {
                    try {
                        holds.value = await apiClient.get(`/holds/bibliographic/${record.value.id}`);
                    } catch {
                        // Keep current holds on error
                    }
                }
                if (activeTab.value === 'history' && itemHistoryLoaded.value) {
                    await loadItemHistory();
                }
            }
        };

        // Kept as a small compatibility helper for consumers of RecordDetail;
        // the rendered copy list uses the shared presentation helper directly.
        const getStatusBadge = (item) => getItemStatusBadge(t, item.status);

        const formatDate = (dateStr) => formatCivilDate(dateStr, locale.value);

        const handleQuickReturn = (itemId) => {
            emit('quick-return', itemId);
        };

        const fetchBorrowers = async (query, signal) => {
            const data = await apiClient.get('/borrowers', { q: query, limit: 10 }, { signal });
            const normalized = normalizeCollection(data);
            return normalized.items;
        };

        const formatBorrowerResult = (borrower) => {
            const badges = [];
            if (borrower.blocked) badges.push(`<span class="badge bg-danger ms-2">${t('circulation.status_blocked')}</span>`);
            if (borrower.has_overdue) badges.push(`<span class="badge bg-warning text-dark ms-2">${t('circulation.overdue')}</span>`);
            return `
                <div>
                    <div class="fw-bold">${borrower.borrower_id} - ${borrower.first_name} ${borrower.last_name}</div>
                    <small class="text-muted">${borrower.class_name || ''}</small>
                    ${badges.join('')}
                </div>
            `;
        };

        const createHold = async (borrower) => {
            if (!borrower) return;
            reserveLoading.value = true;
            reserveMessage.value = null;
            try {
                await apiClient.post('/holds', {
                    borrower_id: borrower.id,
                    bibliographic_record_id: record.value.id,
                    created_by: 'web-ui'
                });
                reserveMessage.value = { type: 'success', text: t('holds.hold_created_for', { name: `${borrower.first_name} ${borrower.last_name}` }) };
                reserveBorrowerQuery.value = '';
                try {
                    holds.value = await apiClient.get(`/holds/bibliographic/${record.value.id}`);
                } catch {
                    // Keep holds on error
                }
            } catch (err) {
                const msg = err.code === 'hold_limit_exceeded'
                    ? t('holds.hold_limit_exceeded', { limit: err.details?.limit ?? '' })
                    : (err.message || t('errors.generic'));
                reserveMessage.value = { type: 'danger', text: msg };
            } finally {
                reserveLoading.value = false;
            }
        };

        const loadItemHistory = async () => {
            const firstItem = items.value[0];
            if (!firstItem) return;
            itemHistoryLoading.value = true;
            try {
                const params = {
                    page: itemHistoryPage.value,
                    page_size: 20,
                };
                if (itemHistoryDateFrom.value) params.date_from = itemHistoryDateFrom.value;
                if (itemHistoryDateTo.value) params.date_to = itemHistoryDateTo.value;
                const data = await apiClient.get(`/circulation/item/${firstItem.item_id}/history`, params);
                itemHistoryItems.value = data.history || [];
                itemHistoryPagination.value = data.pagination || null;
                itemCurrentLoan.value = data.current_loan || null;
                itemHistoryLoaded.value = true;
            } catch {
                itemHistoryItems.value = [];
                itemHistoryPagination.value = null;
                itemCurrentLoan.value = null;
            } finally {
                itemHistoryLoading.value = false;
            }
        };

        const applyItemHistoryFilter = () => {
            itemHistoryPage.value = 1;
            loadItemHistory();
        };

        const clearItemHistoryFilter = () => {
            itemHistoryDateFrom.value = '';
            itemHistoryDateTo.value = '';
            itemHistoryPage.value = 1;
            loadItemHistory();
        };

        const onItemHistoryPageChange = (page) => {
            itemHistoryPage.value = page;
            loadItemHistory();
        };

        watch(activeTab, (tab) => {
            if (tab === 'history' && !itemHistoryLoaded.value) {
                itemHistoryPage.value = 1;
                loadItemHistory();
            }
        });

        const handleClose = () => {
            emit('close');
            emit('update:show', false);
        };

        const addItem = () => {
            const recordId = record.value?.id || props.recordId;
            if (!recordId) return;

            closeRecord();
            router.push({
                name: 'cataloging',
                query: { record_id: String(recordId) }
            });
        };

        const viewBorrower = (borrowerId) => {
            emit('view-borrower', borrowerId);
        };

        const handleCancelEdit = () => {
            if (props.initialMode === 'edit') {
                handleClose();
            } else {
                isEditMode.value = false;
                if (record.value) {
                    initForm(record.value);
                }
            }
        };

        const handleEditItem = (item) => {
            editingItem.value = item;
            showItemEditModal.value = true;
        };

        const handleItemSaved = (updatedItem) => {
            reloadAllData();
            showItemEditModal.value = false;
            editingItem.value = null;
        };

        // These helpers remain exposed for existing callers/tests while the
        // shared CopiesList owns the actual copy-row rendering.
        const getConditionLabel = (condition) => getItemConditionLabel(t, condition);

        const getStatusLabel = (status) => getItemStatusBadge(t, status).text;

        const handleDeleteItem = async (item) => {
            if (!confirm(t('admin.confirm_delete_item', { item_id: item.item_id }) || `Delete item ${item.item_id}?`)) {
                return;
            }

            try {
                await apiClient.delete(`/catalog/items/${item.item_id}`);
                reloadAllData();
                events.emit('catalog:refresh');
            } catch (error) {
                console.error('Error deleting item:', error);
                handleError(error);
            }
        };

        const validateForm = () => {
            const newErrors = {};
            if (!formData.value.title || formData.value.title.trim() === '') {
                newErrors.title = t('errors.required_field');
            }
            if (formData.value.publication_year) {
                const year = parseInt(formData.value.publication_year);
                if (isNaN(year) || year < 1000 || year > 2100) {
                    newErrors.publication_year = t('errors.invalid_year_range');
                }
            }
            if (formData.value.page_count && formData.value.page_count < 0) {
                newErrors.page_count = t('errors.must_be_positive');
            }
            errors.value = newErrors;
            return Object.keys(newErrors).length === 0;
        };

        const handleSubmit = async () => {
            if (!validateForm()) {
                return;
            }
            isSubmitting.value = true;
            errors.value = {};

            try {
                const payload = {};
                Object.entries(formData.value).forEach(([key, value]) => {
                    if (value === '' || value === null) {
                        payload[key] = null;
                    } else if (key === 'publication_year' || key === 'page_count') {
                        payload[key] = value ? parseInt(value) : null;
                    } else {
                        payload[key] = value;
                    }
                });

                const updatedRecord = await apiClient.patch(`/catalog/records/${record.value.id}`, payload);
                record.value = updatedRecord;
                emit('saved', updatedRecord);
                events.emit('catalog:refresh');

                if (props.initialMode === 'edit') {
                    handleClose();
                } else {
                    isEditMode.value = false;
                }
            } catch (error) {
                console.error('Error updating record:', error);
                if (error.statusCode === 400) {
                    errors.value.general = error.message || t('errors.validation_failed');
                } else {
                    errors.value.general = error.message || t('errors.unknown_error');
                }
            } finally {
                isSubmitting.value = false;
            }
        };

        const handleDeleteClick = () => {
            showDeleteDialog.value = true;
        };

        const handleDeleteConfirm = async (recordIdValue) => {
            try {
                await apiClient.delete(`/catalog/records/${recordIdValue}`);

                showDeleteDialog.value = false;
                emit('deleted', recordIdValue);
                handleClose();
                events.emit('catalog:refresh');
            } catch (error) {
                console.error('Error deleting record:', error);
                errors.value.general = t('errors.network_error');
                showDeleteDialog.value = false;
            }
        };

        return {
            record,
            items,
            holds,
            loading,
            coverLoadFailed,
            activeTab,
            showReserveForm,
            reserveBorrowerQuery,
            reserveLoading,
            reserveMessage,
            itemHistoryItems,
            itemHistoryPagination,
            itemCurrentLoan,
            itemHistoryLoading,
            itemHistoryDateFrom,
            itemHistoryDateTo,
            getStatusBadge,
            formatDate,
            handleQuickReturn,
            handleClose,
            addItem,
            viewBorrower,
            fetchBorrowers,
            formatBorrowerResult,
            createHold,
            applyItemHistoryFilter,
            clearItemHistoryFilter,
            onItemHistoryPageChange,
            settingsValue,
            getShelfBadge,
            getCoteBadge,
            t,

            // Edit Mode
            isEditMode,
            formData,
            errors,
            isSubmitting,
            handleCancelEdit,
            handleEditItem,
            handleItemSaved,
            getConditionLabel,
            getStatusLabel,
            handleDeleteItem,
            handleSubmit,
            handleDeleteClick,
            handleDeleteConfirm,
            showItemEditModal,
            editingItem,
            showDeleteDialog,
            isPeriodicalRecord: computed(() => isPeriodicalRecord(record.value))
        };
    },

    template: `
        <modal :show="show" size="xl" scrollable @close="handleClose">
            <template #header>
                <h5 class="modal-title mb-0">
                    <i class="bi bi-book me-2"></i>
                    {{ isEditMode ? t('admin.edit_record') : (record ? record.title : t('catalog.title')) }}
                </h5>
            </template>

            <loading-spinner v-if="loading" />

            <div v-else-if="record">
                <!-- General Error (only relevant in edit mode) -->
                <div v-if="isEditMode && errors.general" class="alert alert-danger mb-3" data-testid="general-error">
                  <i class="bi bi-exclamation-triangle-fill me-2"></i>
                  {{ errors.general }}
                </div>

                <div class="row">
                    <!-- Left Column: unified bibliographic fields (label left / control right) -->
                    <div class="col-md-8">
                        <form @submit.prevent="handleSubmit">
                          <bibliographic-fields
                            v-model="formData"
                            :edit-mode="isEditMode"
                            :errors="errors"
                            :settings="settingsValue"
                            :hide-series-number="isPeriodicalRecord"
                          />
                        </form>
                    </div>

                    <!-- Right Column: Cover & Quick Actions -->
                    <div class="col-md-4">
                        <div class="card bg-light position-sticky" style="top: 1rem;">
                            <div class="card-body text-center">
                                <div class="mb-3">
                                    <img
                                        v-if="record.cover_image && !coverLoadFailed"
                                        :src="'/covers/' + record.cover_image"
                                        :alt="record.title"
                                        class="img-fluid rounded shadow-sm"
                                        style="max-height: 200px; object-fit: contain;"
                                        @error="coverLoadFailed = true"
                                    />
                                    <i v-else class="bi bi-book display-4 text-muted"></i>
                                </div>
                                <h6>{{ t('catalog.total_copies') }}</h6>
                                <h2 class="mb-0">{{ items.length }}</h2>
                                <small class="text-muted">
                                    {{ items.filter(i => i.status === 'available').length }} {{ t('catalog.available').toLowerCase() }}
                                </small>
                            </div>
                            <div class="card-footer p-2" v-if="!isEditMode">
                                <button
                                    class="btn btn-sm btn-outline-primary w-100"
                                    @click="showReserveForm = !showReserveForm; reserveMessage = null"
                                >
                                    <i class="bi bi-bookmark-plus me-1"></i>{{ t('holds.reserve_for') }}
                                </button>
                                <div v-if="showReserveForm" class="mt-2">
                                    <div v-if="reserveMessage" :class="['alert', 'alert-' + reserveMessage.type, 'py-1', 'small', 'mb-2']">
                                        {{ reserveMessage.text }}
                                    </div>
                                    <autocomplete-input
                                        v-model="reserveBorrowerQuery"
                                        :placeholder="t('borrowers.search_placeholder')"
                                        :fetch-results="fetchBorrowers"
                                        :format-result="formatBorrowerResult"
                                        :disabled="reserveLoading"
                                        @select="createHold"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tabs (Copies, Holds, History) -->
                <div class="mt-4">
                    <ul class="nav nav-tabs mb-3">
                        <li class="nav-item">
                            <a
                                class="nav-link"
                                :class="{ active: activeTab === 'items' }"
                                @click.prevent="activeTab = 'items'"
                                href="#"
                            >
                                <i class="bi bi-list-ul"></i>
                                {{ t('catalog.copies') }}
                                <span class="badge bg-primary ms-1">{{ items.length }}</span>
                            </a>
                        </li>
                        <li class="nav-item" v-if="!isEditMode">
                            <a
                                class="nav-link"
                                :class="{ active: activeTab === 'holds' }"
                                @click.prevent="activeTab = 'holds'"
                                href="#"
                            >
                                <i class="bi bi-bookmark-fill"></i>
                                {{ t('holds.title') }}
                                <span v-if="holds.length > 0" class="badge bg-secondary ms-1">{{ holds.length }}</span>
                            </a>
                        </li>
                        <li class="nav-item" v-if="!isEditMode">
                            <a
                                class="nav-link"
                                :class="{ active: activeTab === 'history' }"
                                @click.prevent="activeTab = 'history'"
                                href="#"
                            >
                                <i class="bi bi-clock-history"></i>
                                {{ t('catalog.circulation_history') }}
                            </a>
                        </li>
                    </ul>

                    <!-- Items Tab: shared with the cataloging copy workflow so
                         copy navigation and status presentation stay consistent. -->
                    <div v-if="activeTab === 'items'">
                        <copies-list
                            :items="items"
                            :settings="settingsValue"
                            :periodical="isPeriodicalRecord"
                            :editable="isEditMode"
                            :allow-delete="isEditMode"
                            :show-current-loan="!isEditMode"
                            :show-condition="isEditMode"
                            :show-quick-return="!isEditMode"
                            :format-date="formatDate"
                            @edit="handleEditItem"
                            @delete="handleDeleteItem"
                            @quick-return="handleQuickReturn"
                            @view-borrower="viewBorrower"
                        />
                    </div>

                    <!-- Holds Tab -->
                    <div v-if="!isEditMode && activeTab === 'holds'">
                        <div v-if="holds.length === 0" class="alert alert-info">
                            <i class="bi bi-info-circle me-2"></i>
                            {{ t('holds.no_holds') }}
                        </div>
                        <div v-else class="table-responsive">
                            <table class="table table-hover table-sm">
                                <thead>
                                    <tr>
                                        <th>{{ t('borrowers.name') }}</th>
                                        <th>{{ t('holds.queue_position') }}</th>
                                        <th>{{ t('circulation.status') }}</th>
                                        <th>{{ t('holds.hold_date') }}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="hold in holds" :key="hold.id">
                                        <td>
                                            <a
                                                href="#"
                                                @click.prevent="viewBorrower(hold.borrower_string_id)"
                                                class="link-entity fw-bold"
                                            >{{ hold.borrower_name || hold.borrower_string_id }}</a>
                                        </td>
                                        <td>#{{ hold.queue_position }}</td>
                                        <td>
                                            <span v-if="hold.status === 'ready'" class="badge bg-success">
                                                <i class="bi bi-check-circle me-1"></i>{{ t('holds.status.ready') }}
                                            </span>
                                            <span v-else class="badge bg-secondary">
                                                {{ t('holds.status.waiting') }}
                                            </span>
                                        </td>
                                        <td>{{ formatDate(hold.created_at) }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- History Tab -->
                    <div v-if="!isEditMode && activeTab === 'history'">
                        <div v-if="itemCurrentLoan" class="alert alert-info mb-3">
                            <i class="bi bi-book me-1"></i>
                            {{ t('circulation.currently_on_loan_to', { name: itemCurrentLoan.borrower_name }) }}
                            &mdash; {{ t('circulation.due_date') }}: {{ formatDate(itemCurrentLoan.due_date) }}
                        </div>

                        <div class="d-flex align-items-center gap-2 mb-3 flex-wrap">
                            <label class="form-label mb-0 small text-muted">{{ t('circulation.date_from') }}</label>
                            <input type="date" class="form-control form-control-sm w-auto" v-model="itemHistoryDateFrom" />
                            <label class="form-label mb-0 small text-muted">{{ t('circulation.date_to') }}</label>
                            <input type="date" class="form-control form-control-sm w-auto" v-model="itemHistoryDateTo" />
                            <button class="btn btn-sm btn-primary" @click="applyItemHistoryFilter">{{ t('circulation.apply_date_filter') }}</button>
                            <button class="btn btn-sm btn-outline-secondary" @click="clearItemHistoryFilter">{{ t('circulation.clear_date_filter') }}</button>
                        </div>

                        <div v-if="itemHistoryLoading" class="text-center py-3">
                            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                        </div>

                        <div v-else-if="itemHistoryItems.length === 0" class="text-muted small">
                            <span v-if="itemHistoryDateFrom || itemHistoryDateTo">{{ t('circulation.no_history_for_period') }}</span>
                            <span v-else>{{ t('circulation.no_history') }}</span>
                        </div>

                        <div v-else class="table-responsive">
                            <table class="table table-sm table-striped">
                                <thead>
                                    <tr>
                                        <th>{{ t('borrowers.name') }}</th>
                                        <th>{{ t('circulation.checkout_date') }}</th>
                                        <th>{{ t('circulation.return_date') }}</th>
                                        <th>{{ t('catalog.status') }}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="entry in itemHistoryItems" :key="entry.borrower_name + entry.checkout_date">
                                        <td>
                                            <a
                                                href="#"
                                                @click.prevent="viewBorrower(entry.borrower_id)"
                                                class="link-entity fw-bold"
                                            >{{ entry.borrower_name }}</a>
                                        </td>
                                        <td>{{ formatDate(entry.checkout_date) }}</td>
                                        <td>{{ formatDate(entry.return_date) }}</td>
                                        <td>
                                            <span v-if="entry.status === 'returned_late'" class="badge bg-warning text-dark">
                                                <i class="bi bi-exclamation-circle"></i>
                                                {{ t('circulation.history_returned_late') }}
                                            </span>
                                            <span v-else class="badge bg-success">
                                                <i class="bi bi-check"></i>
                                                {{ t('circulation.history_returned_on_time') }}
                                            </span>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <pagination
                            v-if="itemHistoryPagination && itemHistoryPagination.total_pages > 1"
                            :current-page="itemHistoryPagination.page"
                            :total-pages="itemHistoryPagination.total_pages"
                            :page-size="itemHistoryPagination.page_size"
                            :total-items="itemHistoryPagination.total_items"
                            @page-change="onItemHistoryPageChange"
                        ></pagination>
                    </div>
                </div>
            </div>

            <div v-else class="alert alert-warning mb-0">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Failed to load record details
            </div>

            <template #footer>
                <!-- VIEW MODE FOOTER (Close and Edit buttons next to each other) -->
                <div v-if="!isEditMode" class="d-flex justify-content-end w-100 gap-2">
                    <button type="button" class="btn btn-secondary" @click="handleClose">
                        {{ t('common.close') }}
                    </button>
                    <button type="button" class="btn btn-success" @click="addItem">
                        <i class="bi bi-plus-circle me-1"></i>
                        {{ t('cataloging.add_copy') }}
                    </button>
                    <button type="button" class="btn btn-primary" @click="isEditMode = true">
                        <i class="bi bi-pencil me-1"></i>
                        {{ t('common.edit') }}
                    </button>
                </div>

                <!-- EDIT MODE FOOTER -->
                <div v-else class="d-flex justify-content-between w-100">
                    <button
                      type="button"
                      class="btn btn-danger"
                      data-testid="button-delete"
                      @click="handleDeleteClick"
                      :disabled="isSubmitting"
                    >
                      <i class="bi bi-trash me-1"></i>
                      {{ t('common.delete') }}
                    </button>
                    <div>
                        <button
                          type="button"
                          class="btn btn-secondary me-2"
                          data-testid="button-cancel"
                          @click="handleCancelEdit"
                          :disabled="isSubmitting"
                        >
                          {{ t('common.cancel') }}
                        </button>
                        <button
                          type="button"
                          class="btn btn-primary"
                          @click="handleSubmit"
                          :disabled="isSubmitting"
                        >
                          <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" data-testid="saving-spinner"></span>
                          {{ isSubmitting ? t('common.saving') : t('common.save') }}
                        </button>
                    </div>
                </div>
            </template>
        </modal>

        <!-- Item Edit Modal -->
        <item-edit-form
          v-if="editingItem"
          :show="showItemEditModal"
          :item="editingItem"
          :record="record"
          :settings="settingsValue"
          @update:show="showItemEditModal = $event"
          @saved="handleItemSaved"
        />

        <!-- Record Delete Dialog -->
        <record-delete-dialog
          v-if="record && showDeleteDialog"
          :show="showDeleteDialog"
          :record-data="{ id: record.id, title: record.title, authors: record.authors, isbn: record.isbn, isbn_value: record.isbn_value, items: items }"
          @close="showDeleteDialog = false"
          @confirm="handleDeleteConfirm"
        />
    `
});
