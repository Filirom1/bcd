/**
 * SearchBar Component
 * Search input with debouncing for catalog
 */

const { defineComponent, ref, watch, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'SearchBar',

    props: {
        modelValue: {
            type: String,
            default: ''
        },
        debounce: {
            type: Number,
            default: 300
        }
    },

    emits: ['update:modelValue', 'search'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const searchQuery = ref(props.modelValue);
        const inputRef = ref(null);
        let debounceTimeout = null;

        onMounted(async () => {
            await nextTick();
            inputRef.value?.focus();
        });

        // Watch for external changes to modelValue
        watch(() => props.modelValue, (newValue) => {
            searchQuery.value = newValue;
        });

        // Watch for local changes and debounce
        watch(searchQuery, (newValue) => {
            emit('update:modelValue', newValue);

            // Clear previous timeout
            if (debounceTimeout) {
                clearTimeout(debounceTimeout);
            }

            // Set new debounce timeout
            debounceTimeout = setTimeout(() => {
                emit('search', newValue);
            }, props.debounce);
        });

        const handleSubmit = () => {
            // Immediate search on Enter key
            if (debounceTimeout) {
                clearTimeout(debounceTimeout);
            }
            emit('search', searchQuery.value);
        };

        const clearSearch = () => {
            searchQuery.value = '';
            emit('search', '');
        };

        return {
            searchQuery,
            inputRef,
            handleSubmit,
            clearSearch,
            t
        };
    },

    template: `
        <div class="card mb-3">
            <div class="card-body">
                <form @submit.prevent="handleSubmit">
                    <div class="input-group input-group-lg">
                        <span class="input-group-text">
                            <i class="bi bi-search"></i>
                        </span>
                        <input
                            ref="inputRef"
                            type="text"
                            class="form-control"
                            v-model="searchQuery"
                            :placeholder="t('catalog.search_placeholder')"
                        />
                        <button
                            v-if="searchQuery"
                            type="button"
                            class="btn btn-outline-secondary"
                            @click="clearSearch"
                        >
                            <i class="bi bi-x-lg"></i>
                        </button>
                        <button
                            type="submit"
                            class="btn btn-primary"
                        >
                            <i class="bi bi-search me-1"></i>
                            {{ t('common.search') }}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `
});
