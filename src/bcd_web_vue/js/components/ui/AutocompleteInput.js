/**
 * AutocompleteInput Component
 * Reusable autocomplete input with debouncing, keyboard navigation, and barcode scanner support
 */

const { defineComponent, ref, watch, computed, onMounted, onUnmounted, nextTick } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'AutocompleteInput',

    props: {
        modelValue: {
            type: String,
            default: ''
        },
        placeholder: {
            type: String,
            default: ''
        },
        fetchResults: {
            type: Function,
            required: true
        },
        formatResult: {
            type: Function,
            required: true
        },
        debounceMs: {
            type: Number,
            default: 300
        },
        minChars: {
            type: Number,
            default: 2
        },
        disabled: {
            type: Boolean,
            default: false
        },
        inputmode: {
            type: String,
            default: 'text'
        },
        otherInputAttrs: {
            type: Object,
            default: () => ({})
        },
        autoSelectFirst: {
            type: Boolean,
            default: true
        }
    },

    emits: ['update:modelValue', 'select', 'submit'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Refs
        const inputRef = ref(null);
        const dropdownRef = ref(null);
        const inputValue = ref(props.modelValue);
        const results = ref([]);
        const loading = ref(false);
        const error = ref(null);
        const showDropdown = ref(false);
        const selectedIndex = ref(-1);

        // Debounce and scanner detection
        let debounceTimeout = null;
        let abortController = null;
        let lastKeystrokeTime = 0;
        let keystrokeTimes = [];

        // Computed
        const hasMinChars = computed(() => {
            return inputValue.value.trim().length >= props.minChars;
        });

        const hasResults = computed(() => {
            return results.value.length > 0;
        });

        const showNoResults = computed(() => {
            return !loading.value && !error.value && !hasResults.value && hasMinChars.value && showDropdown.value;
        });

        // Scanner detection: rapid keystrokes < 100ms apart
        const isRapidInput = () => {
            if (keystrokeTimes.length < 2) return false;

            // Check if last 3 keystrokes were within 100ms of each other
            const recentTimes = keystrokeTimes.slice(-3);
            if (recentTimes.length < 2) return false;

            for (let i = 1; i < recentTimes.length; i++) {
                if (recentTimes[i] - recentTimes[i - 1] > 100) {
                    return false;
                }
            }
            return true;
        };

        // Detect if Enter was pressed shortly after last keystroke (scanner input)
        const isScannerSubmit = () => {
            const timeSinceLastKey = Date.now() - lastKeystrokeTime;
            return timeSinceLastKey < 200 && isRapidInput();
        };

        // Fetch autocomplete results
        const fetchAutocomplete = async () => {
            const query = inputValue.value.trim();

            if (!hasMinChars.value) {
                results.value = [];
                showDropdown.value = false;
                return;
            }

            // Cancel previous request
            if (abortController) {
                abortController.abort();
            }

            abortController = new AbortController();
            loading.value = true;
            error.value = null;

            try {
                const data = await props.fetchResults(query, abortController.signal);
                results.value = data || [];
                showDropdown.value = true;
                selectedIndex.value = -1; // Reset selection
            } catch (err) {
                if (err.name !== 'AbortError') {
                    console.error('Autocomplete fetch error:', err);
                    error.value = t('autocomplete.error');
                    results.value = [];
                }
            } finally {
                loading.value = false;
            }
        };

        // Debounced search
        const debouncedSearch = () => {
            if (debounceTimeout) {
                clearTimeout(debounceTimeout);
            }

            debounceTimeout = setTimeout(() => {
                fetchAutocomplete();
            }, props.debounceMs);
        };

        // Handle input change
        const handleInput = (event) => {
            const now = Date.now();
            keystrokeTimes.push(now);

            // Keep only last 5 keystroke times
            if (keystrokeTimes.length > 5) {
                keystrokeTimes.shift();
            }

            lastKeystrokeTime = now;

            inputValue.value = event.target.value;
            emit('update:modelValue', inputValue.value);

            // Trigger debounced search
            debouncedSearch();
        };

        // Handle keyboard navigation
        const handleKeydown = (event) => {
            if (!showDropdown.value || !hasResults.value) {
                // If Enter pressed and dropdown not shown, submit
                if (event.key === 'Enter') {
                    event.preventDefault();
                    handleSubmit();
                }
                return;
            }

            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    selectedIndex.value = Math.min(selectedIndex.value + 1, results.value.length - 1);
                    scrollToSelected();
                    break;

                case 'ArrowUp':
                    event.preventDefault();
                    selectedIndex.value = Math.max(selectedIndex.value - 1, -1);
                    scrollToSelected();
                    break;

                case 'Enter':
                    event.preventDefault();

                    // Check if this is a barcode scanner submit
                    if (isScannerSubmit()) {
                        // Scanner detected - bypass autocomplete
                        closeDropdown();
                        handleSubmit();
                        return;
                    }

                    // Manual entry - use autocomplete
                    if (selectedIndex.value >= 0) {
                        // Item is highlighted - select it
                        selectResult(results.value[selectedIndex.value]);
                    } else if (props.autoSelectFirst && results.value.length > 0) {
                        // No highlight but autoSelectFirst is true - select first result
                        selectResult(results.value[0]);
                    } else {
                        // No selection - submit raw input
                        closeDropdown();
                        handleSubmit();
                    }
                    break;

                case 'Escape':
                    event.preventDefault();
                    closeDropdown();
                    break;
            }
        };

        // Scroll selected item into view
        const scrollToSelected = () => {
            nextTick(() => {
                if (selectedIndex.value >= 0 && dropdownRef.value) {
                    const selectedEl = dropdownRef.value.querySelector('.autocomplete-item.selected');
                    if (selectedEl) {
                        selectedEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                    }
                }
            });
        };

        // Select a result
        const selectResult = (result) => {
            emit('select', result);
            closeDropdown();
        };

        // Close dropdown
        const closeDropdown = () => {
            showDropdown.value = false;
            selectedIndex.value = -1;

            // Cancel any pending request
            if (abortController) {
                abortController.abort();
                abortController = null;
            }

            // Clear debounce timer
            if (debounceTimeout) {
                clearTimeout(debounceTimeout);
                debounceTimeout = null;
            }
        };

        // Handle submit (Enter or button click)
        const handleSubmit = () => {
            emit('submit', inputValue.value);
        };

        // Click outside to close dropdown
        const handleClickOutside = (event) => {
            if (inputRef.value && !inputRef.value.contains(event.target) &&
                dropdownRef.value && !dropdownRef.value.contains(event.target)) {
                closeDropdown();
            }
        };

        // Focus input
        const focusInput = async () => {
            await nextTick();
            inputRef.value?.focus();
        };

        // Watch for external changes to modelValue
        watch(() => props.modelValue, (newValue) => {
            if (newValue !== inputValue.value) {
                inputValue.value = newValue;
            }
        });

        // Lifecycle
        onMounted(() => {
            document.addEventListener('click', handleClickOutside);
        });

        onUnmounted(() => {
            document.removeEventListener('click', handleClickOutside);
            closeDropdown();
        });

        return {
            inputRef,
            dropdownRef,
            inputValue,
            results,
            loading,
            error,
            showDropdown,
            selectedIndex,
            hasMinChars,
            hasResults,
            showNoResults,
            handleInput,
            handleKeydown,
            selectResult,
            handleSubmit,
            focusInput,
            t
        };
    },

    template: `
        <div class="autocomplete-container position-relative flex-grow-1">
            <input
                ref="inputRef"
                type="text"
                class="form-control"
                :value="inputValue"
                @input="handleInput"
                @keydown="handleKeydown"
                :placeholder="placeholder"
                :disabled="disabled"
                :inputmode="inputmode"
                v-bind="otherInputAttrs"
                autocomplete="off"
                role="combobox"
                :aria-expanded="showDropdown"
                :aria-autocomplete="'list'"
                :aria-controls="showDropdown ? 'autocomplete-dropdown' : null"
                :aria-activedescendant="selectedIndex >= 0 ? 'autocomplete-item-' + selectedIndex : null"
            />

            <!-- Dropdown -->
            <div
                v-if="showDropdown"
                id="autocomplete-dropdown"
                ref="dropdownRef"
                class="autocomplete-dropdown position-absolute w-100 bg-white border rounded shadow-sm mt-1"
                style="max-height: 400px; overflow-y: auto; z-index: 1050;"
                role="listbox"
            >
                <!-- Loading state -->
                <div v-if="loading" class="autocomplete-item p-3 text-center text-muted">
                    <span class="spinner-border spinner-border-sm me-2"></span>
                    {{ t('autocomplete.loading') }}
                </div>

                <!-- Error state -->
                <div v-else-if="error" class="autocomplete-item p-3 text-center text-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    {{ t('autocomplete.error') }}
                </div>

                <!-- No results -->
                <div v-else-if="showNoResults" class="autocomplete-item p-3 text-center text-muted">
                    <i class="bi bi-search me-2"></i>
                    {{ t('autocomplete.no_results') }}
                </div>

                <!-- Results -->
                <div
                    v-else
                    v-for="(result, index) in results"
                    :key="index"
                    :id="'autocomplete-item-' + index"
                    class="autocomplete-item p-2 border-bottom"
                    :class="{ 'selected bg-light': index === selectedIndex }"
                    @click="selectResult(result)"
                    @mouseenter="selectedIndex = index"
                    role="option"
                    :aria-selected="index === selectedIndex"
                    style="cursor: pointer;"
                    v-html="formatResult(result)"
                ></div>
            </div>
        </div>
    `
});
