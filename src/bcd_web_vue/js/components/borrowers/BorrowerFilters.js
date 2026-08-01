/**
 * Borrower Filters Component
 *
 * Search input and filter dropdowns for borrowers list.
 * Replaces Alpine.js state management with Vue reactive refs.
 *
 * COMPARISON WITH OLD SOLUTION:
 * - OLD: Alpine.js state (searchQuery, classFilter, roleFilter, activeFilter)
 * - NEW: Vue Composition API with reactive refs
 * - OLD: Manual DOM manipulation for class dropdown population
 * - NEW: Vue v-for with reactive classes array
 * - OLD: Manual htmx.ajax() calls to reload list
 * - NEW: Emit events to parent, parent handles API calls
 */

import { apiClient } from '../../api/client.js';

export default {
    name: 'BorrowerFilters',

    template: `
        <div class="borrower-filters mb-4">
            <div class="row g-3">
                <!-- Search Input -->
                <div class="col-md-4">
                    <div class="input-group">
                        <span class="input-group-text">
                            <i class="bi bi-search"></i>
                        </span>
                        <input
                            type="text"
                            class="form-control"
                            :placeholder="t('borrowers.search_placeholder')"
                            v-model="searchQuery"
                            @input="debouncedSearch"
                            @keydown.esc="clearSearch"
                            ref="searchInput"
                        >
                        <button
                            v-if="searchQuery"
                            class="btn btn-outline-secondary"
                            type="button"
                            @click="clearSearch"
                            :title="t('common.clear')"
                        >
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                    <small class="text-muted">{{ t('borrowers.search_hint') }}</small>
                </div>

                <!-- Class Filter -->
                <div class="col-md-2">
                    <select
                        class="form-select"
                        v-model="classFilter"
                        @change="applyFilters"
                    >
                        <option value="">{{ t('borrowers.all_classes') }}</option>
                        <option
                            v-for="cls in classes"
                            :key="cls.id"
                            :value="cls.id"
                        >
                            {{ cls.name }}
                        </option>
                    </select>
                </div>

                <!-- Role Filter -->
                <div class="col-md-2">
                    <select
                        class="form-select"
                        v-model="roleFilter"
                        @change="applyFilters"
                    >
                        <option value="">{{ t('borrowers.all_roles') }}</option>
                        <option value="student">{{ t('borrower.role_student') }}</option>
                        <option value="teacher">{{ t('borrower.role_teacher') }}</option>
                        <option value="staff">{{ t('borrower.role_staff') }}</option>
                    </select>
                </div>

                <!-- Status Filter -->
                <div class="col-md-2">
                    <select
                        class="form-select"
                        v-model="statusFilter"
                        @change="applyFilters"
                    >
                        <option value="">{{ t('borrowers.all_statuses') }}</option>
                        <option value="active">{{ t('borrowers.active') }}</option>
                        <option value="blocked">{{ t('borrowers.blocked') }}</option>
                        <option value="overdue">{{ t('borrowers.with_overdue') }}</option>
                    </select>
                </div>

                <!-- Reset Button -->
                <div class="col-md-2">
                    <button
                        class="btn btn-outline-secondary w-100"
                        @click="resetFilters"
                        :disabled="!hasActiveFilters"
                    >
                        <i class="bi bi-arrow-counterclockwise"></i>
                        {{ t('common.reset') }}
                    </button>
                </div>
            </div>

            <!-- Active Filters Display -->
            <div v-if="hasActiveFilters" class="mt-2">
                <small class="text-muted">
                    <i class="bi bi-filter"></i>
                    {{ t('borrowers.active_filters') }}:
                    <span v-if="searchQuery" class="badge bg-primary me-1">
                        {{ t('borrowers.search') }}: "{{ searchQuery }}"
                    </span>
                    <span v-if="classFilter" class="badge bg-primary me-1">
                        {{ t('borrowers.class') }}: {{ getClassName(classFilter) }}
                    </span>
                    <span v-if="roleFilter" class="badge bg-primary me-1">
                        {{ t('borrowers.role') }}: {{ t('borrower.role_' + roleFilter) }}
                    </span>
                    <span v-if="statusFilter" class="badge bg-primary me-1">
                        {{ t('borrowers.status') }}: {{ t('borrowers.' + statusFilter) }}
                    </span>
                </small>
            </div>
        </div>
    `,

    emits: ['filter-change'],

    setup(props, { emit }) {
        const { t } = VueI18n.useI18n();
        const searchQuery = Vue.ref('');
        const classFilter = Vue.ref('');
        const roleFilter = Vue.ref('');
        const statusFilter = Vue.ref('');
        const classes = Vue.ref([]);
        const searchInput = Vue.ref(null);
        let debounceTimer = null;

        // Computed: Check if any filters are active
        const hasActiveFilters = Vue.computed(() => {
            return !!(searchQuery.value || classFilter.value || roleFilter.value || statusFilter.value);
        });

        // Get class name by ID
        const getClassName = (classId) => {
            const cls = classes.value.find(c => c.id === classId);
            return cls ? cls.name : classId;
        };

        // Debounced search (300ms delay)
        const debouncedSearch = () => {
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }
            debounceTimer = setTimeout(() => {
                applyFilters();
            }, 300);
        };

        // Clear search
        const clearSearch = () => {
            searchQuery.value = '';
            applyFilters();
        };

        // Apply filters and emit event
        const applyFilters = () => {
            const filters = {
                q: searchQuery.value,
                class_id: classFilter.value,
                role: roleFilter.value
            };

            // Convert status filter to API parameters
            if (statusFilter.value === 'active') {
                filters.active = true;
            } else if (statusFilter.value === 'blocked') {
                filters.blocked = true;
            } else if (statusFilter.value === 'overdue') {
                // For overdue, we filter for active borrowers with overdue items
                // The API will need to handle this on the backend
                filters.has_overdue = true;
            }

            // Remove empty filters
            Object.keys(filters).forEach(key => {
                if (filters[key] === '' || filters[key] === null || filters[key] === undefined) {
                    delete filters[key];
                }
            });

            emit('filter-change', filters);
        };

        // Reset all filters
        const resetFilters = () => {
            searchQuery.value = '';
            classFilter.value = '';
            roleFilter.value = '';
            statusFilter.value = '';
            applyFilters();
        };

        // Load classes from API
        const loadClasses = async () => {
            try {
                classes.value = await apiClient.get('/classes');
            } catch (error) {
                console.error('Error loading classes:', error);
            }
        };

        // Keyboard shortcut: "/" to focus search
        const handleKeyboardShortcut = (event) => {
            if (event.key === '/' && !event.target.matches('input, textarea')) {
                event.preventDefault();
                searchInput.value?.focus();
            }
        };

        Vue.onMounted(async () => {
            loadClasses();
            document.addEventListener('keydown', handleKeyboardShortcut);
            await Vue.nextTick();
            searchInput.value?.focus();
        });

        Vue.onUnmounted(() => {
            document.removeEventListener('keydown', handleKeyboardShortcut);
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }
        });

        return {
            t,
            searchQuery,
            classFilter,
            roleFilter,
            statusFilter,
            classes,
            searchInput,
            hasActiveFilters,
            getClassName,
            debouncedSearch,
            clearSearch,
            applyFilters,
            resetFilters
        };
    }
};
