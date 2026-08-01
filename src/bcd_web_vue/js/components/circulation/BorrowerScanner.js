/**
 * BorrowerScanner Component
 * Input field to scan or enter borrower ID with autocomplete
 */

const { defineComponent, ref, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import AutocompleteInput from '../ui/AutocompleteInput.js';

export default defineComponent({
    name: 'BorrowerScanner',

    components: {
        AutocompleteInput
    },

    props: {
        mode: {
            type: String,
            required: true,
            validator: (value) => ['checkout', 'return'].includes(value)
        }
    },

    emits: ['borrower-loaded'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const borrowerId = ref('');
        const autocompleteRef = ref(null);
        const loading = ref(false);

        // Fetch borrowers from API for autocomplete
        const fetchBorrowers = async (query, signal) => {
            try {
                const response = await apiClient.get('/borrowers', {
                    q: query,
                    limit: 10
                }, { signal });
                return response.items || [];
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Error fetching borrowers:', error);
                }
                throw error;
            }
        };

        // Format borrower result for display
        const formatBorrowerResult = (borrower) => {
            const badges = [];

            if (borrower.blocked) {
                badges.push(`<span class="badge bg-danger ms-2">${t('circulation.status_blocked')}</span>`);
            }
            if (borrower.has_overdue) {
                badges.push(`<span class="badge bg-warning text-dark ms-2">${t('common.overdue')}</span>`);
            }

            return `
                <div>
                    <div class="fw-bold">${borrower.borrower_id} - ${borrower.first_name} ${borrower.last_name}</div>
                    <small class="text-muted">
                        ${borrower.class_name || t('common.not_available')} •
                        ${borrower.current_loans_count || 0}/${borrower.loan_limit || 0} ${t('circulation.loans')}
                    </small>
                    ${badges.join('')}
                </div>
            `;
        };

        // Handle borrower selection from autocomplete
        const handleBorrowerSelect = (borrower) => {
            emit('borrower-loaded', borrower.borrower_id);
            borrowerId.value = '';
        };

        // Handle manual submit (Enter or button click)
        const handleSubmit = (value) => {
            const id = value.trim();
            if (id) {
                emit('borrower-loaded', id);
                borrowerId.value = '';
            }
        };

        const focusInput = async () => {
            await nextTick();
            if (autocompleteRef.value) {
                autocompleteRef.value.focusInput();
            }
        };

        onMounted(() => {
            focusInput();
        });

        return {
            borrowerId,
            autocompleteRef,
            loading,
            fetchBorrowers,
            formatBorrowerResult,
            handleBorrowerSelect,
            handleSubmit,
            focusInput,
            t
        };
    },

    template: `
        <div class="card">
            <div class="card-body">
                <div class="d-flex align-items-center mb-3">
                    <div class="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center"
                         style="width: 40px; height: 40px; font-weight: bold;">
                        1
                    </div>
                    <h5 class="ms-3 mb-0">{{ t('circulation.identify_borrower') }}</h5>
                </div>

                <form @submit.prevent="handleSubmit(borrowerId)">
                    <div class="input-group input-group-lg">
                        <span class="input-group-text">
                            <i class="bi bi-person"></i>
                        </span>
                        <autocomplete-input
                            ref="autocompleteRef"
                            v-model="borrowerId"
                            :placeholder="t('circulation.borrower_id_or_name_placeholder')"
                            :fetchResults="fetchBorrowers"
                            :formatResult="formatBorrowerResult"
                            :disabled="loading"
                            inputmode="text"
                            :minChars="2"
                            :autoSelectFirst="true"
                            :otherInputAttrs="{ style: 'border-radius: 0; border-left: 0; border-right: 0;' }"
                            @select="handleBorrowerSelect"
                            @submit="handleSubmit"
                        />
                        <button
                            type="submit"
                            class="btn btn-primary"
                            :disabled="loading || !borrowerId.trim()"
                        >
                            <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
                            {{ t('common.search') }}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `
});
