/**
 * ScannedItemsList Component
 * Displays list of items that have been scanned for checkout/return
 */

const { defineComponent } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'ScannedItemsList',

    props: {
        items: {
            type: Array,
            default: () => []
        },
        mode: {
            type: String,
            required: true,
            validator: (value) => ['checkout', 'return'].includes(value)
        }
    },

    emits: ['remove-item'],

    setup(props, { emit }) {
        const { t, d } = useI18n();

        const removeItem = (itemId) => {
            emit('remove-item', itemId);
        };

        const formatDate = (dateStr) => {
            if (!dateStr) return '';
            return d(new Date(dateStr), 'short');
        };

        const getItemClass = (item) => {
            if (item.error) return 'list-group-item-danger';
            if (props.mode === 'checkout') return 'list-group-item-success';
            if (props.mode === 'return') return 'list-group-item-info';
            return '';
        };

        const getItemIcon = (item) => {
            if (item.error) return 'bi-x-circle-fill text-danger';
            if (props.mode === 'checkout') return 'bi-check-circle-fill text-success';
            if (props.mode === 'return') return 'bi-arrow-return-left text-info';
            return 'bi-check-circle';
        };

        return {
            removeItem,
            formatDate,
            getItemClass,
            getItemIcon,
            t
        };
    },

    template: `
        <div v-if="items.length > 0" class="card mt-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">
                    <i :class="mode === 'checkout' ? 'bi-box-arrow-right' : 'bi-box-arrow-in-left'"></i>
                    {{ mode === 'checkout' ? t('circulation.checked_out_items') : t('circulation.returned_items') }}
                    <span class="badge bg-primary ms-1">{{ items.length }}</span>
                </h6>
            </div>
            <div class="list-group list-group-flush" style="max-height: 400px; overflow-y: auto;">
                <div
                    v-for="(item, index) in items"
                    :key="item.item_id || index"
                    class="list-group-item"
                    :class="getItemClass(item)"
                >
                    <div class="d-flex justify-content-between align-items-start">
                        <img
                            v-if="item.cover_image"
                            :src="'/covers/' + item.cover_image"
                            :alt="item.title"
                            style="width:40px; height:56px; object-fit:contain; flex-shrink:0; margin-right:10px;"
                            @error="$event.target.style.display='none'"
                        />
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center mb-1">
                                <i :class="getItemIcon(item)" class="me-2"></i>
                                <span class="font-monospace fw-bold">{{ item.barcode || item.item_id }}</span>
                            </div>
                            <div v-if="item.title" class="mb-1">
                                {{ item.title }}
                            </div>
                            <div v-if="item.author" class="text-muted small">
                                {{ item.author }}
                            </div>
                            <div v-if="item.due_date && mode === 'checkout'" class="small">
                                <i class="bi bi-calendar3"></i>
                                {{ t('circulation.due_date') }}: <strong>{{ formatDate(item.due_date) }}</strong>
                            </div>
                            <div v-if="item.returned_date && mode === 'return'" class="small text-muted">
                                <i class="bi bi-clock"></i>
                                {{ t('circulation.returned_at') }}: {{ formatDate(item.returned_date) }}
                            </div>
                            <div v-if="item.hold_ready && mode === 'return'" class="alert alert-warning mt-2 mb-0 py-2 px-3">
                                <div class="d-flex align-items-center">
                                    <i class="bi bi-bookmark-star-fill fs-4 me-2"></i>
                                    <div>
                                        <strong class="d-block">{{ t('circulation.hold_ready_title') }}</strong>
                                        <span class="small">
                                            {{ t('circulation.hold_ready_message', {
                                                name: item.hold_ready.borrower_name,
                                                class: item.hold_ready.class_name || item.hold_ready.borrower_id
                                            }) }}
                                        </span>
                                        <div v-if="item.hold_ready.expiration_date" class="small text-muted">
                                            {{ t('circulation.hold_expires') }}: {{ formatDate(item.hold_ready.expiration_date) }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-if="item.error" class="alert alert-danger mt-2 mb-0 py-1 px-2 small">
                                <i class="bi bi-exclamation-triangle me-1"></i>
                                {{ item.error_message }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});
