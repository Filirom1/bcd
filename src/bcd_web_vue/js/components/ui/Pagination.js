/**
 * Pagination Component
 * Page numbers with ellipsis and page size selector
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'Pagination',

    props: {
        currentPage: {
            type: Number,
            required: true
        },
        totalPages: {
            type: Number,
            required: true
        },
        pageSize: {
            type: Number,
            default: 10
        },
        totalItems: {
            type: Number,
            required: true
        }
    },

    emits: ['page-change', 'page-size-change'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const hasNext = computed(() => props.currentPage < props.totalPages);
        const hasPrevious = computed(() => props.currentPage > 1);
        
        const firstItem = computed(() => {
            if (props.totalItems === 0) return 0;
            return (props.currentPage - 1) * props.pageSize + 1;
        });

        const lastItem = computed(() => {
            const last = props.currentPage * props.pageSize;
            return Math.min(last, props.totalItems);
        });

        const goToPage = (page) => {
            if (page >= 1 && page <= props.totalPages && page !== props.currentPage) {
                emit('page-change', page);
            }
        };

        const changePageSize = (event) => {
            emit('page-size-change', parseInt(event.target.value));
        };

        return {
            t,
            hasNext,
            hasPrevious,
            firstItem,
            lastItem,
            goToPage,
            changePageSize
        };
    },

    template: `
        <div class="d-flex justify-content-between align-items-center">
            <div class="text-muted">
                {{ t('pagination.showing') }} {{ firstItem }}-{{ lastItem }} {{ t('pagination.of') }} {{ totalItems }} {{ t('pagination.items') }}
            </div>

            <nav :aria-label="t('pagination.showing')">
                <ul class="pagination mb-0">
                    <li class="page-item" :class="{ disabled: !hasPrevious }">
                        <button
                            class="page-link"
                            @click="goToPage(currentPage - 1)"
                            :disabled="!hasPrevious"
                        >
                            {{ t('common.previous') }}
                        </button>
                    </li>

                    <li
                        v-for="page in totalPages"
                        :key="page"
                        v-show="page === 1 || page === totalPages || Math.abs(page - currentPage) <= 2"
                        class="page-item"
                        :class="{ active: page === currentPage }"
                    >
                        <button class="page-link" @click="goToPage(page)">
                            {{ page }}
                        </button>
                    </li>

                    <li class="page-item" :class="{ disabled: !hasNext }">
                        <button
                            class="page-link"
                            @click="goToPage(currentPage + 1)"
                            :disabled="!hasNext"
                        >
                            {{ t('common.next') }}
                        </button>
                    </li>
                </ul>
            </nav>

            <div>
                <select class="form-select form-select-sm" :value="pageSize" @change="changePageSize">
                    <option v-for="n in [10, 25, 50, 100, 500]" :key="n" :value="n">{{ n }} {{ t('pagination.per_page') }}</option>
                </select>
            </div>
        </div>
    `
});
