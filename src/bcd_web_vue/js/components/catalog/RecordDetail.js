/**
 * RecordDetail Component
 * Modal displaying detailed bibliographic record information
 */

const { defineComponent, ref, watch, computed } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';
import LoadingSpinner from '../ui/LoadingSpinner.js';
import AutocompleteInput from '../ui/AutocompleteInput.js';
import Pagination from '../ui/Pagination.js';
import { useAppState } from '../../composables/useAppState.js';
import { useItemBadge } from '../../composables/useItemBadge.js';

export default defineComponent({
    name: 'RecordDetail',

    components: {
        Modal,
        LoadingSpinner,
        AutocompleteInput,
        Pagination
    },

    props: {
        recordId: {
            type: Number,
            default: null
        },
        show: {
            type: Boolean,
            default: false
        }
    },

    emits: ['close', 'quick-return', 'view-borrower'],

    setup(props, { emit }) {
        const { t, d } = useI18n();
        const { settings } = useAppState();
        const { getShelfBadge, getCoteBadge } = useItemBadge(settings);
        const record = ref(null);
        const items = ref([]);
        const holds = ref([]);
        const loading = ref(false);
        const activeTab = ref('items');
        const modalRef = ref(null);
        const coverLoadFailed = ref(false);

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

        // Watch for both recordId and show changes to load data
        // Combined into single watcher to prevent duplicate requests
        watch(
            () => [props.recordId, props.show],
            async ([newId, newShow]) => {
                if (newId && newShow) {
                    await loadRecord(newId);
                }
            },
            { immediate: true }
        );

        const loadRecord = async (recordId) => {
            try {
                loading.value = true;
                coverLoadFailed.value = false;
                itemHistoryLoaded.value = false;
                itemHistoryItems.value = [];
                itemHistoryPagination.value = null;
                itemCurrentLoan.value = null;

                // Load record details
                const recordResponse = await fetch(`/api/v1/catalog/bibliographic/${recordId}`);
                if (!recordResponse.ok) throw new Error('Failed to load record');
                record.value = await recordResponse.json();

                // Load items for this record
                const itemsResponse = await fetch(`/api/v1/catalog/bibliographic/${recordId}/items`);
                if (!itemsResponse.ok) throw new Error('Failed to load items');
                const itemsData = await itemsResponse.json();
                // API returns array directly, not wrapped in object
                const rawItems = Array.isArray(itemsData) ? itemsData : (itemsData.items || []);
                // For periodicals, sort by call_number descending (newest issue first)
                if (record.value && record.value.medium_type === 'P\u00e9riodique') {
                    rawItems.sort((a, b) => {
                        const na = parseInt(a.call_number);
                        const nb = parseInt(b.call_number);
                        if (!isNaN(na) && !isNaN(nb)) return nb - na;
                        return (b.call_number || '').localeCompare(a.call_number || '');
                    });
                }
                items.value = rawItems;

                // Load active holds for this record
                const holdsResponse = await fetch(`/api/v1/holds/bibliographic/${recordId}`);
                holds.value = holdsResponse.ok ? (await holdsResponse.json()) : [];

            } catch (error) {
                console.error('Error loading record:', error);
                record.value = null;
                items.value = [];
                holds.value = [];
            } finally {
                loading.value = false;
            }
        };

        const getAuthors = computed(() => {
            if (!record.value || !record.value.authors) return '';
            const authors = record.value.authors;

            // If already an array, join it
            if (Array.isArray(authors)) {
                return authors.length > 0 ? authors.join(', ') : '';
            }

            // If it's a string, try to parse it
            if (typeof authors === 'string') {
                try {
                    const parsed = JSON.parse(authors);
                    return Array.isArray(parsed) ? parsed.join(', ') : authors;
                } catch {
                    return authors;
                }
            }

            return '';
        });

        const getIllustrators = computed(() => {
            if (!record.value || !record.value.illustrators) return '';
            const illustrators = record.value.illustrators;

            // If already an array, join it
            if (Array.isArray(illustrators)) {
                return illustrators.length > 0 ? illustrators.join(', ') : '';
            }

            // If it's a string, try to parse it
            if (typeof illustrators === 'string') {
                try {
                    const parsed = JSON.parse(illustrators);
                    return Array.isArray(parsed) ? parsed.join(', ') : illustrators;
                } catch {
                    return illustrators;
                }
            }

            return '';
        });

        const getKeywords = computed(() => {
            if (!record.value || !record.value.keywords) return '';
            const keywords = record.value.keywords;

            // If already an array, join it
            if (Array.isArray(keywords)) {
                return keywords.length > 0 ? keywords.join(', ') : '';
            }

            // If it's a string, try to parse it
            if (typeof keywords === 'string') {
                try {
                    const parsed = JSON.parse(keywords);
                    return Array.isArray(parsed) ? parsed.join(', ') : keywords;
                } catch {
                    return keywords;
                }
            }

            return '';
        });

        const getLanguageDisplay = computed(() => {
            if (!record.value || !record.value.language) return '';
            const lang = record.value.language.toLowerCase();

            // Map common language codes to readable names
            const languageMap = {
                'fre': 'Français',
                'fr': 'Français',
                'eng': 'English',
                'en': 'English',
                'spa': 'Español',
                'es': 'Español',
                'deu': 'Deutsch',
                'de': 'Deutsch',
                'ita': 'Italiano',
                'it': 'Italiano'
            };

            return languageMap[lang] || record.value.language.toUpperCase();
        });

        const getStatusBadge = (item) => {
            // Map status to translated labels
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

        const formatDate = (dateStr) => {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            // Check if date is valid
            if (isNaN(date.getTime())) return dateStr;
            try {
                return d(date, 'short');
            } catch (e) {
                // Fallback to simple formatting if i18n fails
                return date.toLocaleDateString();
            }
        };

        const getAudienceLabel = (audience) => {
            const audienceMap = {
                'child': t('bibliographic.audience_child'),
                'youth': t('bibliographic.audience_youth'),
                'adult': t('bibliographic.audience_adult')
            };
            return audienceMap[audience] || audience;
        };

        const handleQuickReturn = (itemId) => {
            emit('quick-return', itemId);
        };

        // Fetch borrowers from API for autocomplete
        const fetchBorrowers = async (query, signal) => {
            const url = `/api/v1/borrowers?q=${encodeURIComponent(query)}&limit=10`;
            const resp = await fetch(url, { signal });
            if (!resp.ok) throw new Error('Failed to fetch borrowers');
            const data = await resp.json();
            return data.items || [];
        };

        // Format borrower result for display in dropdown
        const formatBorrowerResult = (borrower) => {
            const badges = [];
            if (borrower.blocked) badges.push('<span class="badge bg-danger ms-2">Bloqué</span>');
            if (borrower.has_overdue) badges.push('<span class="badge bg-warning text-dark ms-2">En retard</span>');
            return `
                <div>
                    <div class="fw-bold">${borrower.borrower_id} - ${borrower.first_name} ${borrower.last_name}</div>
                    <small class="text-muted">${borrower.class_name || ''}</small>
                    ${badges.join('')}
                </div>
            `;
        };

        // Create a hold for this record for the selected borrower
        const createHold = async (borrower) => {
            if (!borrower) return;
            reserveLoading.value = true;
            reserveMessage.value = null;
            try {
                const resp = await fetch('/api/v1/holds', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        borrower_id: borrower.id,
                        bibliographic_record_id: record.value.id,
                        created_by: 'web-ui'
                    })
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    const msg = err.error_code === 'HOLD_LIMIT_EXCEEDED'
                        ? t('holds.hold_limit_exceeded', { limit: err.context?.limit ?? '' })
                        : (err.error || t('errors.generic'));
                    reserveMessage.value = { type: 'danger', text: msg };
                    return;
                }
                reserveMessage.value = { type: 'success', text: t('holds.hold_created_for', { name: `${borrower.first_name} ${borrower.last_name}` }) };
                reserveBorrowerQuery.value = '';
                // Refresh the holds tab
                const holdsResponse = await fetch(`/api/v1/holds/bibliographic/${record.value.id}`);
                holds.value = holdsResponse.ok ? (await holdsResponse.json()) : holds.value;
            } catch {
                reserveMessage.value = { type: 'danger', text: t('errors.generic') };
            } finally {
                reserveLoading.value = false;
            }
        };

        // Load item circulation history for the first physical item of this record
        const loadItemHistory = async () => {
            const firstItem = items.value[0];
            if (!firstItem) return;
            itemHistoryLoading.value = true;
            try {
                const params = new URLSearchParams({
                    page: itemHistoryPage.value,
                    page_size: 20,
                });
                if (itemHistoryDateFrom.value) params.set('date_from', itemHistoryDateFrom.value);
                if (itemHistoryDateTo.value) params.set('date_to', itemHistoryDateTo.value);
                const resp = await fetch(`/api/v1/circulation/item/${firstItem.item_id}/history?${params}`);
                if (!resp.ok) throw new Error('Failed to load item history');
                const data = await resp.json();
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

        // Watch for History tab activation → lazy-load
        watch(activeTab, (tab) => {
            if (tab === 'history' && !itemHistoryLoaded.value) {
                itemHistoryPage.value = 1;
                loadItemHistory();
            }
        });

        const handleClose = () => {
            emit('close');
        };

        const viewBorrower = (borrowerId) => {
            emit('view-borrower', borrowerId);
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
            getAuthors,
            getIllustrators,
            getKeywords,
            getLanguageDisplay,
            getStatusBadge,
            getAudienceLabel,
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
            getShelfBadge,
            getCoteBadge,
            t
        };
    },

    template: `
        <modal :show="show" size="xl" @close="handleClose">
            <template #header>
                <h5 class="modal-title">
                    <i class="bi bi-book me-2"></i>
                    {{ record ? record.title : t('catalog.title') }}
                </h5>
            </template>

            <loading-spinner v-if="loading" />

                <div v-else-if="record">
                    <!-- Record Information -->
                    <div class="row mb-4">
                        <div class="col-md-8">
                            <h4 class="mb-3">{{ record.title }}</h4>

                            <div v-if="record.subtitle" class="text-muted mb-3">
                                <em>{{ record.subtitle }}</em>
                            </div>

                            <table class="table table-sm">
                                <tbody>
                                    <!-- Authors & Contributors -->
                                    <tr v-if="getAuthors">
                                        <th style="width: 30%;">{{ t('catalog.authors') }}</th>
                                        <td>{{ getAuthors }}</td>
                                    </tr>
                                    <tr v-if="getIllustrators">
                                        <th>{{ t('catalog.illustrator') }}s</th>
                                        <td>{{ getIllustrators }}</td>
                                    </tr>

                                    <!-- Publication Information -->
                                    <tr v-if="record.publisher">
                                        <th>{{ t('catalog.publisher') }}</th>
                                        <td>{{ record.publisher }}</td>
                                    </tr>
                                    <tr v-if="record.publication_year">
                                        <th>{{ t('bibliographic.publication_year') }}</th>
                                        <td>{{ record.publication_year }}</td>
                                    </tr>
                                    <tr v-if="record.collection">
                                        <th>{{ t('bibliographic.collection') }}</th>
                                        <td>{{ record.collection }}</td>
                                    </tr>
                                    <tr v-if="record.series_number && record.medium_type !== 'P\u00e9riodique'">
                                        <th>{{ t('bibliographic.series_number') }}</th>
                                        <td>{{ record.series_number }}</td>
                                    </tr>

                                    <!-- Identifiers -->
                                    <tr v-if="record.isbn">
                                        <th>{{ record.identifier_type === 'issn' ? t('catalog.issn') : t('catalog.isbn') }}</th>
                                        <td class="font-monospace">{{ record.isbn_value }}</td>
                                    </tr>

                                    <!-- Classification -->
                                    <tr v-if="record.medium_type">
                                        <th>{{ t('bibliographic.medium_type') }}</th>
                                        <td>{{ record.medium_type }}</td>
                                    </tr>
                                    <tr v-if="record.target_audience">
                                        <th>{{ t('bibliographic.target_audience') }}</th>
                                        <td><span class="badge bg-info">{{ getAudienceLabel(record.target_audience) }}</span></td>
                                    </tr>
                                    <tr v-if="record.level">
                                        <th>{{ t('bibliographic.level') }}</th>
                                        <td>{{ record.level }}</td>
                                    </tr>
                                    <tr v-if="record.language">
                                        <th>{{ t('bibliographic.language') }}</th>
                                        <td>{{ getLanguageDisplay }}</td>
                                    </tr>
                                    <tr v-if="record.country_code">
                                        <th>{{ t('bibliographic.country_code') }}</th>
                                        <td>{{ record.country_code.toUpperCase() }}</td>
                                    </tr>

                                    <!-- Physical Description -->
                                    <tr v-if="record.binding_type">
                                        <th>{{ t('bibliographic.binding_type') }}</th>
                                        <td>{{ record.binding_type }}</td>
                                    </tr>
                                    <tr v-if="record.page_count">
                                        <th>{{ t('bibliographic.page_count') }}</th>
                                        <td>{{ record.page_count }}</td>
                                    </tr>
                                    <tr v-if="record.has_illustrations">
                                        <th>{{ t('bibliographic.has_illustrations') }}</th>
                                        <td><i class="bi bi-check-circle text-success"></i> {{ t('common.yes') }}</td>
                                    </tr>
                                    <tr v-if="record.dimensions">
                                        <th>{{ t('bibliographic.dimensions') }}</th>
                                        <td>{{ record.dimensions }}</td>
                                    </tr>
                                    <tr v-if="record.physical_size">
                                        <th>{{ t('bibliographic.physical_size') }}</th>
                                        <td>{{ record.physical_size }}</td>
                                    </tr>

                                    <!-- Keywords -->
                                    <tr v-if="getKeywords">
                                        <th>{{ t('bibliographic.keywords') }}</th>
                                        <td>{{ getKeywords }}</td>
                                    </tr>
                                </tbody>
                            </table>

                            <!-- Description (separate section for readability) -->
                            <div v-if="record.description" class="mt-3">
                                <h6>{{ t('catalog.description') }}</h6>
                                <p>{{ record.description }}</p>
                            </div>
                        </div>

                        <div class="col-md-4">
                            <div class="card bg-light">
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
                                <div class="card-footer p-2">
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

                    <!-- Tabs -->
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
                        <li class="nav-item">
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
                        <li class="nav-item">
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
                                        <th>{{ t('catalog.due_date_borrower') }}</th>
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
                                            <div v-if="item.acquisition_date || item.funding_source" class="mt-1">
                                                <small v-if="item.acquisition_date" class="text-muted d-block">
                                                    <i class="bi bi-calendar3"></i> {{ formatDate(item.acquisition_date) }}
                                                </small>
                                                <small v-if="item.funding_source" class="text-muted d-block">
                                                    <i class="bi bi-wallet2"></i> {{ item.funding_source }}
                                                </small>
                                            </div>
                                        </td>
                                        <td>
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
                                        <td>
                                            <button
                                                v-if="item.status === 'on_loan' || item.status === 'overdue'"
                                                class="btn btn-sm btn-outline-primary"
                                                @click="handleQuickReturn(item.item_id)"
                                            >
                                                <i class="bi bi-arrow-return-left"></i>
                                                {{ t('catalog.quick_return') }}
                                            </button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- History Tab -->
                    <div v-if="activeTab === 'history'">
                        <!-- Current loan banner -->
                        <div v-if="itemCurrentLoan" class="alert alert-info mb-3">
                            <i class="bi bi-book me-1"></i>
                            {{ t('circulation.currently_on_loan_to', { name: itemCurrentLoan.borrower_name }) }}
                            &mdash; {{ t('circulation.due_date') }}: {{ formatDate(itemCurrentLoan.due_date) }}
                        </div>

                        <!-- Date filter row -->
                        <div class="d-flex align-items-center gap-2 mb-3 flex-wrap">
                            <label class="form-label mb-0 small text-muted">{{ t('circulation.date_from') }}</label>
                            <input type="date" class="form-control form-control-sm w-auto" v-model="itemHistoryDateFrom" />
                            <label class="form-label mb-0 small text-muted">{{ t('circulation.date_to') }}</label>
                            <input type="date" class="form-control form-control-sm w-auto" v-model="itemHistoryDateTo" />
                            <button class="btn btn-sm btn-primary" @click="applyItemHistoryFilter">{{ t('circulation.apply_date_filter') }}</button>
                            <button class="btn btn-sm btn-outline-secondary" @click="clearItemHistoryFilter">{{ t('circulation.clear_date_filter') }}</button>
                        </div>

                        <!-- Loading -->
                        <div v-if="itemHistoryLoading" class="text-center py-3">
                            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                        </div>

                        <!-- Empty state -->
                        <div v-else-if="itemHistoryItems.length === 0" class="text-muted small">
                            <span v-if="itemHistoryDateFrom || itemHistoryDateTo">{{ t('circulation.no_history_for_period') }}</span>
                            <span v-else>{{ t('circulation.no_history') }}</span>
                        </div>

                        <!-- History table -->
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

                        <!-- Pagination -->
                        <pagination
                            v-if="itemHistoryPagination && itemHistoryPagination.total_pages > 1"
                            :current-page="itemHistoryPagination.page"
                            :total-pages="itemHistoryPagination.total_pages"
                            :page-size="itemHistoryPagination.page_size"
                            :total-items="itemHistoryPagination.total_items"
                            @page-change="onItemHistoryPageChange"
                        ></pagination>
                    </div>

                    <!-- Holds Tab -->
                    <div v-if="activeTab === 'holds'">
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
                </div>

                <div v-else class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Failed to load record details
                </div>

            <template #footer>
                <button type="button" class="btn btn-secondary" @click="handleClose">
                    {{ t('common.close') }}
                </button>
            </template>
        </modal>
    `
});
