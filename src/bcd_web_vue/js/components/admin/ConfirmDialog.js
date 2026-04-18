/**
 * ConfirmDialog Component
 *
 * Reusable confirmation dialog for destructive admin operations.
 * Shows count and scrollable list of items (max 10 visible with "and N more" message).
 *
 * Props:
 * - show (Boolean): Whether to show the dialog
 * - title (String): Dialog title
 * - message (String): Confirmation message with context
 * - items (Array): List of items to display (objects with 'name' or 'title' property)
 * - count (Number): Total count of items (may exceed items.length)
 * - confirmText (String): Text for confirm button (default: "Confirm")
 * - cancelText (String): Text for cancel button (default: "Cancel")
 * - confirmClass (String): Bootstrap class for confirm button (default: "btn-danger")
 *
 * Emits:
 * - confirm: User clicked confirm button
 * - cancel: User clicked cancel button or closed dialog
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';

export default defineComponent({
    name: 'ConfirmDialog',

    components: { Modal },

    props: {
        show: {
            type: Boolean,
            default: false
        },
        title: {
            type: String,
            required: true
        },
        message: {
            type: String,
            required: true
        },
        items: {
            type: Array,
            default: () => []
        },
        count: {
            type: Number,
            default: 0
        },
        confirmText: {
            type: String,
            default: ''
        },
        cancelText: {
            type: String,
            default: ''
        },
        confirmClass: {
            type: String,
            default: 'btn-danger'
        }
    },

    emits: ['confirm', 'cancel'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Default button text with i18n
        const confirmButtonText = computed(() => props.confirmText || t('common.confirm'));
        const cancelButtonText = computed(() => props.cancelText || t('common.cancel'));

        // Show max 10 items, indicate if there are more
        const maxVisibleItems = 10;
        const visibleItems = computed(() => props.items.slice(0, maxVisibleItems));
        const hiddenCount = computed(() => Math.max(0, props.items.length - maxVisibleItems));
        const hasMore = computed(() => hiddenCount.value > 0);

        // Get display name from item (supports both 'name' and 'title' properties)
        const getItemName = (item) => {
            return item.name || item.title || item.full_name || String(item);
        };

        const handleConfirm = () => emit('confirm');
        const handleCancel = () => emit('cancel');

        return {
            t,
            confirmButtonText,
            cancelButtonText,
            visibleItems,
            hiddenCount,
            hasMore,
            getItemName,
            handleConfirm,
            handleCancel
        };
    },

    template: `
        <modal
            :show="show"
            :static="true"
            :centered="true"
            :scrollable="true"
            @close="handleCancel"
        >
            <template #header>
                <i class="bi bi-exclamation-triangle"></i>
                {{ title }}
            </template>

            <!-- Confirmation message -->
            <div class="alert alert-warning mb-3">
                <i class="bi bi-exclamation-triangle"></i>
                {{ message }}
            </div>

            <!-- List of items (scrollable, max 10 visible) -->
            <div v-if="items.length > 0" class="mb-3">
                <h6>{{ t('admin.warning') }}:</h6>
                <ul class="list-group" style="max-height: 300px; overflow-y: auto;">
                    <li
                        v-for="(item, index) in visibleItems"
                        :key="index"
                        class="list-group-item"
                    >
                        {{ getItemName(item) }}
                    </li>
                </ul>
                <div v-if="hasMore" class="text-muted small mt-2">
                    <i class="bi bi-three-dots"></i>
                    {{ t('admin.and_n_more', { count: hiddenCount }) }}
                </div>
            </div>

            <!-- Warning message -->
            <p class="text-danger mb-0">
                <strong>{{ t('admin.warning') }}:</strong>
                {{ t('admin.delete_warning_message') }}
            </p>

            <template #footer>
                <button type="button" class="btn btn-secondary" @click="handleCancel">
                    {{ cancelButtonText }}
                </button>
                <button type="button" :class="['btn', confirmClass]" @click="handleConfirm">
                    {{ confirmButtonText }}
                </button>
            </template>
        </modal>
    `
});
