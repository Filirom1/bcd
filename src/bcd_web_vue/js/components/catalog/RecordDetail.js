/**
 * RecordDetail Component
 * Modal displaying detailed bibliographic record information with support for Edit Mode.
 * Unifies view and edit layouts using read-only plaintext inputs to minimize code size.
 */

const { defineComponent, ref, watch, computed } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';
import { formatCivilDate } from '../../utils/date.js';
import LoadingSpinner from '../ui/LoadingSpinner.js';
import AutocompleteInput from '../ui/AutocompleteInput.js';
import Pagination from '../ui/Pagination.js';
import ItemEditForm from './ItemEditForm.js';
import RecordDeleteDialog from './RecordDeleteDialog.js';
import BibliographicFields from './BibliographicFields.js';
import { ApiError } from '../../models/error.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';
import { useAppState } from '../../composables/useAppState.js';
import { useItemBadge } from '../../composables/useItemBadge.js';
import { apiClient } from '../../api/client.js';
import { normalizeCollection } from '../../models/pagination.js';

export default defineComponent({
    name: 'RecordDetail',

    components: {
        Modal,
        LoadingSpinner,
        AutocompleteInput,
        Pagination,
        ItemEditForm,
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
                const rawItems = Array.isArray(itemsData) ? itemsData : (itemsData.items || []);
                if (record.value && record.value.medium_type === 'P\u00e9riodique') {
                    rawItems.sort((a, b) => {
                        const na = parseInt(a.call_number);
                        const nb = parseInt(b.call_number);
                        if (!isNaN(na) && !isNaN(nb)) return nb - na;
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

        const getStatusBadge = (item) => {
            const statusMap = {
                'available': { class: 'bg-success', text: t('item.status_available'), icon: 'bi-check-circle' },
                'on_loan': { class: 'bg-warning', text: t('item.status_on_loan'), icon: 'bi-clock' },
                'on_hold': { class: 'bg-info', text: t('item.status_on_hold'), icon: 'bi-pause-circle' },
                'in_repair': { class: 'bg-primary', text: t('item.status_in_repair'), icon: 'bi-tools' },
                'lost': { class: 'bg-danger', text: t('item.status_lost'), icon: 'bi-question-circle' },
                'withdrawn': { class: 'bg-dark', text: t('item.status_withdrawn'), icon: 'bi-x-circle' },
                'overdue': { class: 'bg-danger', text: t('catalog.overdue'), icon: 'bi-exclamation-triangle' }
            };
            return statusMap[item.status] || { class: 'bg-secondary', text: item.status, icon: 'bi-dash-circle' };
        };

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

        const getConditionLabel = (condition) => {
            const conditionMap = {
                'good': t('item.condition_good'),
                'damaged': t('item.condition_damaged'),
                'lost': t('item.status_lost') || t('item.condition_lost'),
                'withdrawn': t('item.status_withdrawn') || t('item.condition_withdrawn')
            };
            return conditionMap[condition] || condition;
        };

        const getStatusLabel = (status) => {
            const statusMap = {
                'available': t('item.status_available'),
                'on_loan': t('item.status_on_loan'),
                'on_hold': t('item.status_on_hold'),
                'in_repair': t('item.status_in_repair'),
                'lost': t('item.status_lost'),
                'withdrawn': t('item.status_withdrawn')
            };
            return statusMap[status] || status;
        };

        const handleDeleteItem = async (item) => {
            if (!confirm(t('admin.confirm_delete_item', { item_id: item.item_id }) || `Delete item ${item.item_id}?`)) {
                return;
            }

            try {
                await apiClient.delete(`/catalog/items/${item.item_id}`);
                reloadAllData();
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
            showDeleteDialog
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
                            :hide-series-number="record && record.medium_type === 'P\u00e9riodique'"
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

                    <!-- Items Tab -->
                    <div v-if="activeTab === 'items'">
                        <div v-if="items.length === 0" class="alert alert-info">
                            <i class="bi bi-info-circle me-2"></i>
                            {{ t('catalog.no_items') }}
                        </div>

                        <div v-else class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>{{ t('catalog.item_id') }}</th>
                                        <th v-if="record && record.medium_type === 'P\u00e9riodique'">{{ t('periodical.issue_number') }}</th>
                                        <th v-if="record && record.medium_type !== 'P\u00e9riodique'">{{ t('catalog.shelf_location_call_number') }}</th>
                                        <th>{{ t('catalog.status') }}</th>
                                        <th v-if="!isEditMode">{{ t('catalog.due_date_borrower') }}</th>
                                        <th v-else>{{ t('catalog.condition') }}</th>
                                        <th>{{ t('common.actions') }}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="item in items" :key="item.id">
                                        <td class="font-monospace">{{ item.item_id }}</td>
                                        <td v-if="record && record.medium_type === 'P\u00e9riodique'" class="text-muted">
                                            {{ item.call_number ? (/^\d+$/.test(item.call_number) ? 'n\u00b0 ' + item.call_number : item.call_number) : '\u2014' }}
                                        </td>
                                        <td v-if="record && record.medium_type !== 'P\u00e9riodique'">
                                            <div class="d-flex flex-wrap align-items-center gap-1">
                                                <span v-if="item.shelf_location && getShelfBadge(item.shelf_location)" :style="getShelfBadge(item.shelf_location)">{{ item.shelf_location }}</span>
                                                <span v-if="item.call_number && getCoteBadge(item.call_number)" :style="getCoteBadge(item.call_number)">{{ item.call_number }}</span>
                                                <span v-if="!item.shelf_location && !item.call_number" class="text-muted">&mdash;</span>
                                            </div>
                                        </td>
                                        <td>
                                            <div class="d-flex flex-wrap gap-1">
                                                <span :class="['badge', getStatusBadge(item).class]">
                                                    <i :class="getStatusBadge(item).icon"></i>
                                                    {{ getStatusBadge(item).text }}
                                                </span>
                                                <span v-if="item.condition === 'damaged'" class="badge bg-warning text-dark">
                                                    <i class="bi bi-exclamation-triangle"></i>
                                                    {{ t('item.condition_damaged') }}
                                                </span>
                                                <span v-if="item.loanable === false" class="badge bg-secondary">
                                                    <i class="bi bi-lock"></i>
                                                    {{ t('item.status_not_loanable') || t('catalog.loanable') }}
                                                </span>
                                            </div>
                                        </td>
                                        <td v-if="!isEditMode">
                                            <div v-if="item.current_loan">
                                                <div class="mb-1">
                                                    {{ formatDate(item.current_loan.due_date) }}
                                                    <span v-if="item.current_loan.is_overdue" class="badge bg-danger ms-1">
                                                        <i class="bi bi-exclamation-circle"></i>
                                                        {{ t('catalog.overdue') }}
                                                    </span>
                                                </div>
                                                <div>
                                                    <a
                                                        href="#"
                                                        @click.prevent="viewBorrower(item.current_loan.borrower_id)"
                                                        class="link-entity fw-bold"
                                                    >
                                                        {{ item.current_loan.borrower_name }}
                                                    </a>
                                                </div>
                                            </div>
                                            <span v-else class="text-muted">—</span>
                                        </td>
                                        <td v-else>
                                            {{ getConditionLabel(item.condition) }}
                                        </td>
                                        <td>
                                            <button
                                                v-if="!isEditMode && (item.status === 'on_loan' || item.status === 'overdue')"
                                                class="btn btn-sm btn-outline-primary"
                                                @click="handleQuickReturn(item.item_id)"
                                            >
                                                <i class="bi bi-arrow-return-left"></i>
                                                {{ t('catalog.quick_return') }}
                                            </button>
                                            <div v-else-if="isEditMode" class="d-flex gap-1">
                                                <button
                                                  type="button"
                                                  class="btn btn-sm btn-outline-primary"
                                                  @click.stop="handleEditItem(item)"
                                                  :title="t('common.edit')"
                                                >
                                                  <i class="bi bi-pencil"></i>
                                                </button>
                                                <button
                                                  type="button"
                                                  class="btn btn-sm btn-outline-danger"
                                                  @click.stop="handleDeleteItem(item)"
                                                  :title="t('common.delete')"
                                                >
                                                  <i class="bi bi-trash"></i>
                                                </button>
                                            </div>
                                            <span v-else class="text-muted">—</span>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
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
